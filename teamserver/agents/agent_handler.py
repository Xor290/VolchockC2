# teamserver/agents/agent_handler.py
# Manages agent (beacon) sessions and their communication.

class AgentHandler:
    def __init__(self):
        self.agents = {}

    def register_agent(self, agent_id, info):
        self.agents[agent_id] = info
        print(f"[*] Registered new agent: {agent_id}")

    def get_agent(self, agent_id):
        return self.agents.get(agent_id)

    def all_agents(self):
        return self.agents
