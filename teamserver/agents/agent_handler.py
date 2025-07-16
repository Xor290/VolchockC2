# teamserver/agents/agent_handler.py
# Manages agent (beacon) sessions and their communication.

import threading
from collections import deque 
from teamserver.logger.CustomLogger import CustomLogger
log = CustomLogger("volchock")

class AgentHandler:
    def __init__(self):
        self.agents = {}
        self.agent_commands = {}  # commandes par agent
        self.agent_results = {}   # résultats par agent
        self.lock = threading.Lock()

    def register_agent(self, agent_id, info):
        with self.lock:
            self.agents[agent_id] = info
            if agent_id not in self.agent_commands:
                self.agent_commands[agent_id] = deque()  # init queue commande
            if agent_id not in self.agent_results:
                self.agent_results[agent_id] = deque()   # init queue résultats
        log.info(f"[+] New agent registered : {agent_id}")

    def update_agent(self, agent_id, fields):
        with self.lock:
            if agent_id in self.agents:
                self.agents[agent_id].update(fields)
                log.debug(f"[+] Beacon update received for {agent_id}")
    
    def get_agent(self, agent_id):
        with self.lock:
            return self.agents.get(agent_id)

    def all_agents(self):
        with self.lock:
            return dict(self.agents)

    def queue_command(self, agent_id, command):
        with self.lock:
            if agent_id in self.agent_commands:
                self.agent_commands[agent_id].append(command)
                log.debug(f"[+] Queued command for agent {agent_id}")
                return True
            log.error(f"[!] Unknown agent {agent_id} (queue_command)")
            return False

    def pop_commands(self, agent_id):
        with self.lock:
            if agent_id in self.agent_commands:
                while self.agent_commands[agent_id]:
                    return self.agent_commands[agent_id].popleft()
        return ""

    def push_agent_result(self, agent_id, output):
        with self.lock:
            if agent_id not in self.agent_results:
                self.agent_results[agent_id] = deque()
            self.agent_results[agent_id].append(output)
            log.debug(f"[+] Stocked result for agent {agent_id}")

    def pop_agent_results(self, agent_id):
        with self.lock:
            if agent_id in self.agent_results:
                results = list(self.agent_results[agent_id])  # récupère tout
                self.agent_results[agent_id].clear()          # efface la queue
                return results
            return []