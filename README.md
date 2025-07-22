# VolchockC2
VolchockC2 is a custom-built Command & Control (C2) framework, currently under active development. Designed for red team operations and adversary simulation, VolchokC2 focuses on flexibility, stealth, and efficient post-exploitation capabilities.

<p align="center">
  <img src="client/assets/logo.jpg" alt="Logo" width="150px"/>
  <br /><hr /><br />
  <img src="assets/demo-GUI-kivy.jpg" alt="Demo" width="100%"/>
  <br />
</p>


---

## Installation

```
git clone https://github.com/ProcessusT/VolchockC2
cd VolchockC2

# for the teamserver :
python -m teamserver.main --config .\config\config.json

# for the client :
cd client
python client.py

# agent compilation (in client GUI console) :
> listeners
> generate <listener_name> <agent_type>
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
        "<TYPE>": "<CONTENT>"
    }
}
```

#### **Supported Task Types**

- cmd: Execute the content value as a command using cmd.exe and return the result
```json
{
    "task": {
        "cmd": "whoami"
    }
}
```

- download: Download a file from the target machine to the server.
```json
{
    "task": {
        "download": "<remote_file_path>"
    }
}
```

- upload: Upload a file from the server to the target machine.
```json
{
    "task": {
        "upload": "<local_file_path>"
    }
}
```

- exec-pe: In-memory execution of a local PE on the target machine.
```json
{
    "task": {
        "exec-pe": {
            "filename": "<filename>",
            "content": "<b64_encoded_file>",
            "args": "<b64_encoded_args>"
        }
    }
}
```

---

### Reflective Loading

The shellcode payload is based on a DLL with a reflective position-independant loader (aka Stephen Fewer sRDI) :
<p align="center">
  <br />
  <img src="assets/reflectiveloader.jpg" alt="Reflective Loader schema" width="100%"/>
  <br />
</p>

---

## Implementation Roadmap

### 1. Core Listeners (Communication Channels)
- [x] Implement HTTP listener
- [ ] Implement basic DNS listener [REMOVED]

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
- [x] Implement DLL agent 
- [x] Implement sRDI execution of shellcode agent
- [x] Implement agent generation for specific listeners

### 5. Memory & Execution Techniques
- [x] Implement in-memory PE (Portable Executable) execution for C/C++ payloads
- [ ] Implement in-memory PE execution for C# payloads
- [ ] Implement Beacon Object File (BOF) support

### 6. Graphical User Interface (GUI)
- [x] Develop a ugly graphical user interface:
  - [x] Logs view: teamserver logs
  - [x] User view: user connections and activity
  - [x] Agent view: list of connected agents with interaction to send commands
  - [x] Try to make the GUI acceptable

### 7. Advanced features (It will probably never be implemented)
  - [ ] Record all commands and output for each agents (sqlite db maybe ?)
  - [ ] Make contributors rich and famous
  - [ ] Stop all wars in the world


---

## Structure

```
VolchockC2
├── .gitattributes
├── LICENSE
├── README.md
├── agent
│   ├── ReflectiveLoader
│   │   ├── DllLoaderShellcode
│   │   │   ├── CREDITS.txt
│   │   │   ├── Loader
│   │   │   │   ├── Loader.vcxproj
│   │   │   │   ├── Loader.vcxproj.filters
│   │   │   │   ├── Loader.vcxproj.user
│   │   │   │   ├── ReflectiveLoader.cpp
│   │   │   │   ├── ReflectiveLoader.h
│   │   │   │   ├── order.x64.txt
│   │   │   │   └── order.x86.txt
│   │   │   ├── Loader.sln
│   │   │   └── x64
│   │   │       └── Release
│   │   │           ├── Loader.exe
│   │   │           └── Loader.pdb
│   │   └── shellcodize.py
│   ├── http
│   │   ├── base64.cpp
│   │   ├── base64.h
│   │   ├── config.h
│   │   ├── crypt.cpp
│   │   ├── crypt.h
│   │   ├── file_utils.cpp
│   │   ├── file_utils.h
│   │   ├── http_client.cpp
│   │   ├── http_client.h
│   │   ├── main_dll.cpp
│   │   ├── main_exe.cpp
│   │   ├── pe-exec.cpp
│   │   ├── pe-exec.h
│   │   ├── system_utils.cpp
│   │   ├── system_utils.h
│   │   ├── task.cpp
│   │   └── task.h
│   └── simple_dropper.cpp
├── assets
│   ├── demo-GUI-kivy.jpg
│   ├── demo.jpg
│   └── gui-demo.jpg
├── client
│   ├── assets
│   │   ├── font.ttf
│   │   └── logo.jpg
│   ├── client.py
│   ├── constants
│   │   └── colors.py
│   ├── ui
│   │   ├── get_logs.py
│   │   ├── get_users_logs.py
│   │   ├── login.py
│   │   └── mainframe.py
│   └── utils
│       └── requests_utils.py
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
│   │   └── http_listener.py
│   ├── logger
│   │   └── CustomLogger.py
│   ├── main.py
│   ├── profiles
│   │   └── volchock.profile
│   └── teamserver.py
└── tree_map.py
```

---

### Teammates

A big thank to my bros for their support and help :

<a href="https://www.linkedin.com/in/christopher-simon33/">FrozenK</a><br />
<a href="https://www.linkedin.com/in/wakedxy/">Waked XY</a><br />
<a href="https://www.linkedin.com/in/kondah/">Anak0nda</a><br />
<a href="https://www.linkedin.com/in/tristan-manzano-963223103/">X-n0</a><br />
