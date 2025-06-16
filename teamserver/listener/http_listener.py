# teamserver/listener/http_listener.py
# HTTP listener for C2 communications (beacon callback).

from flask import Flask, request, jsonify
import threading
import time
from .base_listener import BaseListener

class HttpListener(BaseListener):
    def __init__(self, config, host="0.0.0.0", port=80):
        super().__init__(config)
        self.host = host
        self.port = port
        self.flask_app = Flask(self.config.get('name', 'http_listener'))

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
