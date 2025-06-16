# teamserver/command_queue.py
# Handles queuing and dispatching commands to agents.

class CommandQueue:
    def __init__(self):
        self.queue = {}

    def add_command(self, agent_id, command):
        if agent_id not in self.queue:
            self.queue[agent_id] = []
        self.queue[agent_id].append(command)

    def get_commands(self, agent_id):
        return self.queue.get(agent_id, [])

    def pop_commands(self, agent_id):
        cmds = self.queue.get(agent_id, [])
        self.queue[agent_id] = []
        return cmds
