# teamserver/listener/base_listener.py
# Abstract base class for all C2 listeners.

class BaseListener:
    def __init__(self, config):
        self.config = config

    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError
