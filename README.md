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
- [ ] Implement basic obfuscation

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


### Teammates

A big thank to my bros for their support and help :

<a href="https://www.linkedin.com/in/christopher-simon33/">FrozenK</a><br />
<a href="https://www.linkedin.com/in/wakedxy/">Waked XY</a><br />
<a href="https://www.linkedin.com/in/kondah/">Anak0nda</a><br />
<a href="https://www.linkedin.com/in/tristan-manzano-963223103/">X-n0</a><br />
