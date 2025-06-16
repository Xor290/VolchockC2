# teamserver/agents/agent_handler.py
# Manages agent (beacon) sessions and their communication.

import threading

class AgentHandler:
    def __init__(self):
        self.agents = {}
        self.lock = threading.Lock()

    def register_agent(self, agent_id, info):
        with self.lock:
            # Mise à jour ou ajout
            self.agents[agent_id] = info
        print(f"[*] Registered new agent: {agent_id}")

    def update_agent(self, agent_id, fields):
        with self.lock:
            if agent_id in self.agents:
                self.agents[agent_id].update(fields)
                print(f"[*] Updated agent: {agent_id}")
    
    def get_agent(self, agent_id):
        with self.lock:
            return self.agents.get(agent_id)

    def all_agents(self):
        with self.lock:
            return dict(self.agents)
