import requests

def queue_shell_command(base_url, agent_id, command, auth):
    payload = {"command": command}
    resp = requests.post(f"{base_url}/agent/{agent_id}/command", json=payload, auth=auth)
    return resp
