# teamserver/teamserver.py
# Core logic for the Teamserver C2 component.

from teamserver.config import Config
from teamserver.listener.http_listener import HttpListener
from teamserver.admin.admin_server import AdminServer
from teamserver.agents.agent_handler import AgentHandler
from queue import Queue
import os
import json
import threading
import time
import socket
import logging
import sys
import random
import string

# redirect all output (info, err...) to CustomLogger
from teamserver.logger.CustomLogger import CustomLogger
log = CustomLogger("volchock")
class StreamToLogger:
    def __init__(self, logger, level):
        self.logger = logger
        self.level = level
    def write(self, message):
        message = message.strip()
        if message:
            self.logger.log(self.level, message)
    def flush(self):
        pass
#sys.stdout = StreamToLogger(log.logger, logging.INFO)
#sys.stderr = StreamToLogger(log.logger, logging.INFO)

class Teamserver:
    def __init__(self, config_path="config/config.json"):
        try:
            self.config = Config(config_path)
        except Exception as e:
            log.error("[!] Configuration file not found or is invalid.", str(e))
            raise
        self.listeners = []
        self.agent_handler = AgentHandler()
        self.shared_queue = Queue()

    def start_admin(self):
        admin_port = self.config.get("server_port", 8080)
        auth_required = self.config.get("auth_required", True)
        users = self.config.get("clients", {})
        admin_server = AdminServer(
            port=admin_port,
            users_dict=users,
            shared_req_queue=self.shared_queue,
            auth_required=auth_required,
            agent_handler=self.agent_handler,
            listeners=self.listeners
        )
        admin_thread = threading.Thread(target=admin_server.start, daemon=True)
        admin_thread.start()

    def start_listeners(self):
        profiles = [
            os.path.join(os.path.dirname(__file__), "profiles", "volchock.profile"),
        ]
        for profile_path in profiles:
            if not os.path.exists(profile_path):
                log.error(f"[!] Listener profile not found: {profile_path}")
                continue
            with open(profile_path, "r", encoding="utf-8") as fp:
                profiles_cfg = json.load(fp)
            for profile_cfg in profiles_cfg:
                port = profile_cfg.get("port")
                if port is None:
                    log.error(f"[!] Port not specified in profile: {profile_path}")
                    continue
                name = profile_cfg.get("name")
                if name is None:
                    log.error(f"[!] Name not specified in profile: {profile_path}")
                    continue
                xor_key = profile_cfg.get("xor_key")
                if xor_key is None:
                    log.error(f"[!] Xor key not specified in profile: {profile_path}")
                    continue
                listener_type = profile_cfg.get("type", "").lower()
                if listener_type == "http":
                    listener = HttpListener(
                        config=profile_cfg,
                        name=name,
                        host="0.0.0.0",
                        port=port,
                        request_queue=self.shared_queue,
                        agent_handler=self.agent_handler,
                        xor_key=xor_key
                    )
                else:
                    log.error(f"[!] Unknown listener type: {listener_type}")
                    continue
                self.listeners.append(listener)
                listener_thread = threading.Thread(target=listener.start, daemon=True)
                listener_thread.start()
                log.info(f"[+] Listener {profile_cfg.get('name')} started on port {port}.")

    def run(self):
        log.debug("[+] Teamserver is running.")
        self.start_listeners()
        self.start_admin()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            log.info("[+] Teamserver shutting down.")
