from flask import Flask, request, jsonify
from functools import wraps
from queue import Queue

class AdminServer:
    def __init__(self, port, users_dict, shared_req_queue, auth_required=True, agent_handler=None):
        self.port = port
        self.users = users_dict or {}
        self.auth_required = auth_required
        self.shared_req_queue = shared_req_queue  # <--- permet à un autre module (teamserver HTTP) d'enregistrer ses requêtes ici !
        self.agent_handler = agent_handler        # <--- NOUVEAU : gestionnaire d'agents (facultatif)
        self.app = Flask(__name__)
        self.add_endpoints()

    def check_auth(self, username, password):
        return username in self.users and self.users[username] == password

    def require_auth(self, f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not self.auth_required:
                return f(*args, **kwargs)
            auth = request.authorization
            if not auth or not self.check_auth(auth.username, auth.password):
                return (
                    jsonify({"error": "Unauthorized"}),
                    401,
                    {"WWW-Authenticate": 'Basic realm="Login required"'},
                )
            print(f"[+] Successfull authentication for {auth.username}")
            return f(*args, **kwargs)
        return decorated

    def add_endpoints(self):
        @self.app.route('/status', methods=['GET'])
        @self.require_auth
        def status():
            return jsonify({"status": "teamserver running"})

        @self.app.route('/pending_requests', methods=['GET'])
        @self.require_auth
        def pending_requests():
            reqs = []
            while not self.shared_req_queue.empty():
                reqs.append(self.shared_req_queue.get())
            return jsonify({"requests": reqs})

        # (optionnel) Endpoint d'exemple d'utilisation de l'agent_handler:
        @self.app.route('/list_agents', methods=['GET'])
        @self.require_auth
        def list_agents():
            if self.agent_handler is not None:
                return jsonify({"agents": self.agent_handler.all_agents()})
                return jsonify({"agents": {}})

    def start(self):
        print(f"[+] Admin server started on port {self.port}")
        self.app.run(host="0.0.0.0", port=self.port, threaded=True)
