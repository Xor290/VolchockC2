# teamserver/agents/agent_handler.py
# Manages agent (beacon) sessions and their communication.

import threading
from collections import deque 

class AgentHandler:
    def __init__(self):
        self.agents = {}
        self.agent_commands = {}  # commandes par agent
        self.agent_results = {}   # résultats par agent
        self.lock = threading.Lock()

    def register_agent(self, agent_id, info):
        with self.lock:
            # Mise à jour ou ajout
            self.agents[agent_id] = info
            if agent_id not in self.agent_commands:
                self.agent_commands[agent_id] = deque()  # init queue commande
            if agent_id not in self.agent_results:
                self.agent_results[agent_id] = deque()   # init queue résultats
        print(f"[*] New agent registered : {agent_id}")

    def update_agent(self, agent_id, fields):
        with self.lock:
            if agent_id in self.agents:
                self.agents[agent_id].update(fields)
                print(f"[*] Beacon update received for {agent_id}")
    
    def get_agent(self, agent_id):
        with self.lock:
            return self.agents.get(agent_id)

    def all_agents(self):
        with self.lock:
            return dict(self.agents)

    # --- Gestion des commandes par agent ---
    def queue_command(self, agent_id, command):
        with self.lock:
            if agent_id in self.agent_commands:
                self.agent_commands[agent_id].append(command)
                print(f"[*] Queued command for agent {agent_id}: {command}")
                return True
            print(f"[!] Agent {agent_id} inconnu (queue_command)")
            return False

    def pop_commands(self, agent_id):
        # Vide la queue de commandes à chaque pull de l'implant
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
            print(f"[*] Stocked result for agent {agent_id}: {output[:100]}")

    def pop_agent_results(self, agent_id):
        with self.lock:
            if agent_id in self.agent_results:
                results = list(self.agent_results[agent_id])  # récupère tout
                self.agent_results[agent_id].clear()          # efface la queue
                return results
            return []

