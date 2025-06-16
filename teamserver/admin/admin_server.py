from flask import Flask, request, jsonify
from functools import wraps

class AdminServer:
    def __init__(self, port, users_dict, auth_required=True):
        self.port = port
        self.users = users_dict or {}
        self.auth_required = auth_required
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
            return f(*args, **kwargs)
        return decorated

    def add_endpoints(self):
        @self.app.route('/status', methods=['GET'])
        @self.require_auth
        def status():
            return jsonify({"status": "teamserver running"})

        # Ajoute ici d'autres endpoints admin si besoin (ex: /list_agents, /kick_agent, ...)

    def start(self):
        print(f"[+] Admin server started on port {self.port}")
        self.app.run(host="0.0.0.0", port=self.port, threaded=True)
