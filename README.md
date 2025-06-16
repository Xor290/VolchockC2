# VolchockC2
VolchokC2 is a custom-built Command & Control (C2) framework, currently under active development. Designed for red team operations and adversary simulation, VolchokC2 focuses on flexibility, stealth, and efficient post-exploitation capabilities.


## Implementation Roadmap

### 1. Core Listeners (Communication Channels)
- [ ] Implement basic HTTP listener
- [ ] Implement HTTPS listener with certificate support
- [ ] Implement DNS listener
- [ ] Implement FTP listener
- [ ] Implement ICMP listener
- [ ] Start, edit, and stop listeners dynamically

### 2. Basic Agent Functionality
- [ ] Develop a basic C/C++ agent for connectivity testing with the teamserver
- [ ] Develop a basic C# agent

### 3. Command & Control Operations
- [ ] Implement command sending functionality in the teamserver
- [ ] Implement command execution capability in the agents
- [ ] Implement a command execution queue in the teamserver

### 4. Multi-Entity Support
- [ ] Implement multi-agent support (handle multiple victims/sessions simultaneously)
- [ ] Implement multi-user support:
  - [ ] The teamserver supports an administrative listening port
  - [ ] Develop a client application for operators to connect to the teamserver

### 5. Communication & Evasion Customization
- [ ] Implement a configuration/profile file for the teamserver to customize communication parameters (user-agent, sleep, jitter, headers)
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
VolchokC2/
│
├── teamserver/ # Python Teamserver (C2 server)
│ ├── init.py # Init file for Python package
│ ├── main.py # Bootstraps and launches the teamserver
│ ├── config.py # Handles server configuration loading/parsing
│ ├── teamserver.py # Main teamserver logic and routines
│ ├── command_queue.py # Command queue management for agents
│ ├── listener/ # Directory for listener types (protocols)
│ │ ├── init.py # Init file for listener package
│ │ ├── base_listener.py # Abstract class/interface for all listeners
│ │ ├── http_listener.py # HTTP listener implementation
│ │ ├── https_listener.py # HTTPS listener implementation
│ │ ├── dns_listener.py # DNS C2 listener implementation
│ │ ├── ftp_listener.py # FTP listener implementation
│ │ └── icmp_listener.py # ICMP C2 listener implementation
│ ├── agents/ # Directory handling agent connections
│ │ ├── init.py # Init file for agents package
│ │ └── agent_handler.py # Logic for agent session and communication
│ ├── users/ # Directory handling authenticated users/admins
│ │ ├── init.py # Init file for users package
│ │ └── user_handler.py # Logic for user authentication/management
│ └── profiles/ # Communication profiles for C2
│ └── example_profile.json # Example config/profile for listener
│
├── client/ # Python client for operator/admin interaction
│ ├── init.py # Init file for Python package
│ ├── main.py # Launches the client UI
│ ├── client.py # Main client logic (connection to teamserver)
│ ├── gui/ # Graphical User Interface module
│ │ ├── init.py # Init file for GUI package
│ │ ├── main_window.py # Main app GUI window (core interface)
│ │ ├── logs_view.py # View for displaying logs
│ │ ├── users_view.py # View for managing team users
│ │ └── victims_view.py # View for listing and managing agents/victims
│ └── utils/ # Utility/helper functions for client
│ └── ... # (Any utility files as needed)
│
├── agent_c/ # C/C++ agent beacon generator and sources
│ ├── generator.py # Python script to generate agent source/prebuilt
│ ├── CMakeLists.txt # CMake build configuration
│ └── agent_template.c # Main C agent template (beacon code)
│
├── agent_cs/ # C# agent beacon generator and sources
│ ├── generator.py # Python script to generate C# agent source
│ ├── Agent.csproj # C# project file
│ └── AgentTemplate.cs # Main C# agent template (beacon code)
│
├── payloads/ # Output directory for compiled/generated payloads
│
├── requirements.txt # Python dependencies for both server and client
├── README.md # Project documentation
└── LICENSE # License file
```

---