# teamserver/logger/CustomLogger.py
# Defines a customizable in-memory logging system for the Teamserver, 
# supporting log retrieval and integration with other components.

import logging

class InMemoryLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.log_records = []
        self.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s in %(name)s: %(message)s'))

    def emit(self, record):
        msg = self.format(record)
        self.log_records.append(msg)

    def get_logs(self, limit=30):
        return self.log_records[-limit:]

    def clear_logs(self):
        self.log_records.clear()

class CustomLogger:
    _instances = {}

    def __new__(cls, name: str = None):
        if name is None:
            name = __name__
        if name not in cls._instances:
            instance = super(CustomLogger, cls).__new__(cls)
            instance.logger = logging.getLogger(name)
            instance.logger.setLevel(logging.DEBUG)
            instance.memory_handler = InMemoryLogHandler()
            if not any(isinstance(h, InMemoryLogHandler) for h in instance.logger.handlers):
                instance.logger.addHandler(instance.memory_handler)
            cls._instances[name] = instance
        return cls._instances[name]

    def debug(self, msg, *args, **kwargs):
        self.logger.debug(msg, *args, **kwargs)
    def info(self, msg, *args, **kwargs):
        self.logger.info(msg, *args, **kwargs)
    def warning(self, msg, *args, **kwargs):
        self.logger.warning(msg, *args, **kwargs)
    def error(self, msg, *args, **kwargs):
        self.logger.error(msg, *args, **kwargs)
    def critical(self, msg, *args, **kwargs):
        self.logger.critical(msg, *args, **kwargs)

    def get_logs(self):
        return self.memory_handler.get_logs()

    def clear_logs(self):
        self.memory_handler.clear_logs()
