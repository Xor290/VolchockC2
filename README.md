# VolchockC2
VolchockC2 is a custom-built Command & Control (C2) framework, currently under active development. Designed for red team operations and adversary simulation, VolchokC2 focuses on flexibility, stealth, and efficient post-exploitation capabilities.

---

## Installation

```
git clone https://github.com/ProcessusT/VolchockC2
cd VolchockC2
python -m teamserver.main --config .\config\config.json
```

---

## Implementation Roadmap

### 1. Core Listeners (Communication Channels)
- [x] Implement basic HTTP listener
- [x] Implement QUIC listener with certificate support
- [x] Implement DNS listener
- [ ] Start and stop listeners dynamically

### 2. Basic Agent Functionality
- [x] Develop a basic C/C++ agent for connectivity testing with the teamserver
- [ ] Develop a basic C# agent

### 3. Command & Control Operations
- [x] Implement command sending functionality in the teamserver
- [x] Implement command execution capability in the agents
- [x] Implement a command execution queue in the teamserver

### 4. Multi-Entity Support
- [x] Implement multi-agent support (handle multiple victims/sessions simultaneously)
- [x] Implement multi-user support:
  - [x] The teamserver supports an administrative listening port
  - [x] Develop a client application for operators to connect to the teamserver

### 5. Communication & Evasion Customization
- [x] Implement a configuration/profile file for the teamserver to customize communication parameters (user-agent, sleep, jitter, headers)
- [ ] Implement shellcode generation for specific listeners

### 6. Memory & Execution Techniques
- [ ] Implement in-memory PE (Portable Executable) execution for C/C++ payloads
- [ ] Implement in-memory PE execution for C# payloads

### 7. Graphical User Interface (GUI)
- [ ] Develop a graphical user interface:
  - [ ] Logs view: teamserver logs
  - [ ] User view: user connections and activity
  - [ ] Victim view: list of connected agents with right-click interaction to send commands

---

## Structure

```
VolchockC2                           # Root directory of the VolchockC2 project
├── LICENSE                          # Project license (usage, rights, etc.)
├── README.md                        # Main documentation (overview, usage, etc.)
├── agent/
│   └── http_agent.cpp               # C++ implant/agent: communicates with the teamserver over HTTP
├── client/
│   ├── client.py                    # CLI/console interface to interact with the C2
│   └── gui                          # (Folder reserved for GUI, graphical client interface)
├── config/
│   └── config.json                  # Global project configuration (e.g., endpoints, keys)
├── struct.py                        # Definitions and shared data structures (e.g., protocols/messages)
└── teamserver/                      # Core of the C2 server (management, communications, administration)
    ├── __init__.py                  # Marks teamserver/ as a Python package
    ├── admin/
    │   └── admin_server.py          # Administration server (auth, admin commands, user management)
    ├── agents/
    │   └── agent_handler.py         # Agent handler: tracks, registers, and communicates with agents
    ├── config.py                    # Server-side configuration (loading, parsing, validation)
    ├── encryption/
    │   └── xor_util.py              # Encryption/decryption tools (XOR, base64) for communications
    ├── listener/
    │   ├── base_listener.py         # Base class for listeners (abstractions, utilities)
    │   └── http_listener.py         # HTTP listener: receives and processes agent HTTP requests
    ├── main.py                      # Main server entry point (launches all modules, main loops)
    ├── profiles/
    │   └── volchock.profile         # Profile file to customize agents/listeners (advanced config)
    └── teamserver.py                # Central server script (orchestration, threads, main logic)
```

---