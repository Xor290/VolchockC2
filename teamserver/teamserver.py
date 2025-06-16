# teamserver/teamserver.py
# Core logic for the Teamserver C2 component.

from teamserver.config import Config
from teamserver.listener.http_listener import HttpListener
from teamserver.admin.admin_server import AdminServer
import os
import json
import threading
import time

class Teamserver:
    def __init__(self, config_path="config/config.json"):
        try:
            self.config = Config(config_path)
        except Exception as e:
            print("[!] Configuration file not found or is invalid.", str(e))
            raise

        self.listeners = []


    def start_admin(self):
        admin_port = self.config.get("server_port", 8080)
        auth_required = self.config.get("auth_required", True)
        users = self.config.get("clients", {})          # dict utilisateur:password

        admin_server = AdminServer(
            port=admin_port,
            users_dict=users,
            auth_required=auth_required
        )
        admin_thread = threading.Thread(target=admin_server.start, daemon=True)
        admin_thread.start()


    def start_listeners(self):
        profiles = [
            os.path.join(os.path.dirname(__file__), "profiles", "volchock.profile"),
        ]

        for profile_path in profiles:
            if not os.path.exists(profile_path):
                print(f"[!] Listener profile not found: {profile_path}")
                continue
            with open(profile_path, "r", encoding="utf-8") as fp:
                profile_cfg = json.load(fp)

            port = profile_cfg.get("port")
            if port is None:
                print(f"[!] Port not specified in profile: {profile_path}")
                continue

            listener_type = profile_cfg.get("type", "").lower()
            if listener_type == "http":
                listener = HttpListener(config=profile_cfg, host="0.0.0.0", port=port)
            else:
                print(f"[!] Unknown listener type: {listener_type}")
                continue

            listener_thread = threading.Thread(target=listener.start, daemon=True)
            listener_thread.start()
            self.listeners.append((listener, listener_thread))

            print(f"[+] Listener {profile_cfg.get('name')} started on port {port}.")



    def run(self):
        print("[*] Teamserver is running.")
        self.start_admin()
        self.start_listeners()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("[*] Teamserver shutting down.")
            for listener, _ in self.listeners:
                listener.stop()
