# VolchockC2
VolchockC2 is a custom-built Command & Control (C2) framework, currently under active development. Designed for red team operations and adversary simulation, VolchokC2 focuses on flexibility, stealth, and efficient post-exploitation capabilities.

<p align="center">
  <img src="assets/demo.jpg" alt="Demo" width="90%"/>
</p>


---

## Installation

```
git clone https://github.com/ProcessusT/VolchockC2
cd VolchockC2

# for the teamserver :
python -m teamserver.main --config .\config\config.json

# for the client
python client/client.py -i 127.0.0.1 -p 8088 -u user1 --password superpassword
```

---

## Communication Protocol

### Encryption/Decryption Process

- **Encryption:**  
  `string → xor → base64`
- **Decryption:**  
  `base64 → xor → string`

---

### Communication Content Templates

#### **Agent ➔ Server**

```json
{
    "agent_id": "<ID>",
    "hostname": "<HOSTNAME>",
    "username": "<USERNAME>",
    "process_name": "<PROCESS_NAME>",
    "results": "<RESULTS>"
}
```

#### **Server ➔ Agent**

```json
{
    "task": {
        "type": "<TYPE>",
        "content": "<CONTENT>"
    }
}
```

#### **Supported Task Types**

- cmd: Execute the content value as a command using cmd.exe and return the result.


#### **Example**

```json
{
    "task": {
        "type": "cmd",
        "content": "whoami"
    }
}
```

---

## Implementation Roadmap

### 1. Core Listeners (Communication Channels)
- [x] Implement basic HTTP listener
- [ ] Implement DNS listener

### 2. Command & Control Operations
- [x] Implement command execution queue
- [x] Implement upload and download commands

### 3. Multi-Entity Support
- [x] Implement multi-agent support (handle multiple victims/sessions simultaneously)
- [x] Implement multi-user support:
  - [x] The teamserver supports an administrative listening port
  - [x] Develop a client application for operators to connect to the teamserver

### 4. Communication & Evasion Customization
- [x] Implement a configuration/profile file for the teamserver to customize communication parameters
- [ ] Implement agent generation for specific listeners

### 5. Memory & Execution Techniques
- [ ] Implement in-memory PE (Portable Executable) execution for C/C++ payloads
- [ ] Implement in-memory PE execution for C# payloads
- [ ] Implement Beacon Object File (BOF) support

### 6. Graphical User Interface (GUI)
- [ ] Develop a graphical user interface:
  - [ ] Logs view: teamserver logs
  - [ ] User view: user connections and activity
  - [ ] Agent view: list of connected agents with right-click interaction to send commands

---

## Structure

```
VolchockC2
├── README.md
├── agent
│   ├── dns
│   │   ├── agent_dns.exe
│   │   └── dns_agent.c
│   └── http
│       └── http_agent.cpp
├── assets
│   └── demo.jpg
├── client
│   ├── client.py
│   ├── gui
│   ├── loot
│   │   └── Hertz_Proc_agent.exe
│   │       └── franky.png
│   └── musique.jpg
├── config
│   └── config.json
├── teamserver
│   ├── __init__.py
│   ├── admin
│   │   └── admin_server.py
│   ├── agents
│   │   └── agent_handler.py
│   ├── config.py
│   ├── encryption
│   │   └── xor_util.py
│   ├── listener
│   │   ├── base_listener.py
│   │   ├── dns_listener.py
│   │   └── http_listener.py
│   ├── main.py
│   ├── profiles
│   │   └── volchock.profile
│   └── teamserver.py
└── tree_map.py
```

---