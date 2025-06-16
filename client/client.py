import argparse
import requests
import time
from requests.auth import HTTPBasicAuth

def poll_pending_requests(ip, port, username, password, interval=5):
    url = f"http://{ip}:{port}/pending_requests"
    print(f"[*] Polling {url} toutes les {interval} sec.")
    while True:
        try:
            resp = requests.get(url, auth=HTTPBasicAuth(username, password))
            if resp.status_code == 200:
                datas = resp.json().get('requests', [])
                if datas:
                    print(f"[+] {len(datas)} requête(s) reçues :\n{datas}\n")
            elif resp.status_code == 401:
                print("[!] Accès refusé ! Identifiants invalides.")
                break
            else:
                print(f"[!] Erreur HTTP {resp.status_code}")
        except Exception as e:
            print(f"[!] Exception : {e}")
        time.sleep(interval)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Client admin pour le teamserver (polls pending requests)")
    parser.add_argument('-i', '--ip-address', required=True, help='IP address du teamserver')
    parser.add_argument('-p', '--port', required=True, type=int, help='Port du teamserver')
    parser.add_argument('-u', '--username', required=True, help="Nom d'utilisateur admin")
    parser.add_argument('--pwd', '--password', dest='password', required=True, help="Mot de passe admin")
    parser.add_argument('--interval', default=5, type=int, help='Interval de polling en secondes (défaut: 5)')
    args = parser.parse_args()

    poll_pending_requests(args.ip_address, args.port, args.username, args.password, args.interval)
