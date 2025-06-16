# teamserver/main.py
# Entry point for starting the Teamserver.

import argparse
from teamserver.teamserver import Teamserver

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VolchockC2 Teamserver")
    parser.add_argument("--config", default="config.json", help="Chemin du fichier de configuration")
    args = parser.parse_args()

    server = Teamserver(config_path=args.config)
    server.run()