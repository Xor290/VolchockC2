# VolchockC2
VolchockC2 is a custom-built Command & Control (C2) framework, currently under active development. Designed for red team operations and adversary simulation, VolchokC2 focuses on flexibility, stealth, and efficient post-exploitation capabilities.

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

## Implementation Roadmap

### 1. Core Listeners (Communication Channels)
- [x] Implement basic HTTP listener
- [x] Implement QUIC listener with certificate support
- [x] Implement DNS listener
- [ ] Start and stop listeners dynamically

### 2. Command & Control Operations
- [x] Implement command sending functionality in the teamserver
- [x] Implement command execution capability in the agents
- [x] Implement a command execution queue in the teamserver

### 3. Multi-Entity Support
- [x] Implement multi-agent support (handle multiple victims/sessions simultaneously)
- [x] Implement multi-user support:
  - [x] The teamserver supports an administrative listening port
  - [x] Develop a client application for operators to connect to the teamserver

### 4. Communication & Evasion Customization
- [x] Implement a configuration/profile file for the teamserver to customize communication parameters (user-agent, sleep, jitter, headers)
- [ ] Implement shellcode generation for specific listeners

### 5. Memory & Execution Techniques
- [ ] Implement in-memory PE (Portable Executable) execution for C/C++ payloads
- [ ] Implement in-memory PE execution for C# payloads

### 6. Graphical User Interface (GUI)
- [ ] Develop a graphical user interface:
  - [ ] Logs view: teamserver logs
  - [ ] User view: user connections and activity
  - [ ] Victim view: list of connected agents with right-click interaction to send commands

---

## Structure

```
VolchockC2
├── LICENSE
├── README.md
├── agent
│   ├── dns
│   │   └── dns_agent.c
│   ├── http
│   │   └── http_agent.cpp
│   ├── http_dll
│   │   ├── http_agent_dll.c
│   │   ├── rdi_loader.cpp
│   │   └── simple_dll_loader.c
│   └── quic
│       ├── agent_quic.exe
│       ├── curl.exe
│       └── quic_agent.cpp
├── client
│   ├── client.py
│   └── gui
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
│   │   ├── http_listener.py
│   │   └── quic_listener.py
│   ├── main.py
│   ├── profiles
│   │   ├── quic_server.crt
│   │   ├── quic_server.key
│   │   └── volchock.profile
│   └── teamserver.py
└── tree_map.py
```

---