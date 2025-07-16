# teamserver/config.py
# Handles loading and parsing configuration for the Teamserver.

import json
from teamserver.logger.CustomLogger import CustomLogger
log = CustomLogger("volchock")

class Config:
    def __init__(self, path):
        log.debug(f"[+] Config file initialized: {path}")
        with open(path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def get(self, key, default=None):
        return self.data.get(key, default)
