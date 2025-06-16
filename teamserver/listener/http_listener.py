# teamserver/listener/http_listener.py
# HTTP listener for C2 communications (beacon callback).

from flask import Flask, request, jsonify
import threading
import time
from .base_listener import BaseListener

class HttpListener(BaseListener):
    def __init__(self, config, host="0.0.0.0", port=80, request_queue=None, agent_handler=None):
        super().__init__(config)
        self.host = host
        self.port = port
        self.flask_app = Flask(self.config.get('name', 'http_listener'))
        self.request_queue = request_queue 
        self.agent_handler = agent_handler

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
        headers = dict(request.headers)
        print(f"[*] Request on {request.path} with headers {headers}")

        expected_agent = self.config.get('user_agent')
        if expected_agent and request.headers.get("User-Agent") != expected_agent:
            return "Invalid User-Agent", 403

        expected_headers = self.config.get('http_headers', {})
        for header, value in expected_headers.items():
            if request.headers.get(header) != value:
                return f"Invalid header {header}", 403

        # Enregistrement agent : déduire un agent_id minimal (header ou combinaison IP+UA+URL)
        if self.agent_handler is not None:
            agent_id = (
                request.json.get('agent_id')
                if request.is_json and request.json and 'agent_id' in request.json
                else headers.get('X-Agent-Id')
                or (request.remote_addr + "_" + headers.get("User-Agent", ""))
            )
            if agent_id and not self.agent_handler.get_agent(agent_id):
                agent_info = {
                    "remote_addr": request.remote_addr,
                    "headers": headers,
                    "first_seen": time.time(),
                    "uri": request.path
                }
                self.agent_handler.register_agent(agent_id, agent_info)

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
        
        return jsonify({"status": "OK"})

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
