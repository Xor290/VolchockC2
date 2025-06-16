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
- [ ] Implement HTTPS listener with certificate support
- [ ] Implement DNS listener
- [ ] Implement FTP listener
- [ ] Implement ICMP listener
- [ ] Start, edit, and stop listeners dynamically

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
VolchockC2                           # Racine du projet VolchockC2
├── LICENSE                          # Licence du projet (usage, droits, etc.)
├── README.md                        # Documentation principale (présentation, usage, etc.)
├── agent/
│   └── http_agent.cpp               # Implant/agent C++ : communique avec le teamserver en HTTP
├── client/
│   ├── client.py                    # Interface CLI/console pour interagir avec le C2
│   └── gui                          # (Dossier prévu pour GUI, interface graphique du client)
├── config/
│   └── config.json                  # Configuration globale du projet (ex: endpoints, clés)
├── struct.py                        # Définitions et structures de données partagées (ex: protocoles/messages)
└── teamserver/                      # Coeur du serveur C2 (gestion, communication, administration)
    ├── __init__.py                  # Indique que teamserver/ est un package Python
    ├── admin/
    │   └── admin_server.py          # Serveur d’administration (auth, commandes admin, gestion utilisateurs)
    ├── agents/
    │   └── agent_handler.py         # Gestionnaire des agents : suivi, registre, communication agents
    ├── config.py                    # Configuration côté serveur (chargement, parsing, validation)
    ├── encryption/
    │   └── xor_util.py              # Outils de chiffrement/déchiffrement (XOR, base64) pour la comm
    ├── listener/
    │   ├── base_listener.py         # Classe de base pour les listeners (abstractions, utilitaires)
    │   └── http_listener.py         # Listener HTTP : reçoit et traite les requêtes agents via HTTP
    ├── main.py                      # Point d’entrée principal côté serveur (lance tous les modules, boucles)
    ├── profiles/
    │   └── volchock.profile         # Fichier de profil pour personnaliser agents/écouteurs (config avancée)
    └── teamserver.py                # Script central du serveur (orchestration, threads, logiques principales)

```

---