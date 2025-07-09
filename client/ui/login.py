import wx
from requests.auth import HTTPBasicAuth
import requests
import os
from constants.colors import RED, GRAY, WHITE, INPUT_GRAY

class LoginFrame(wx.Frame):
    def __init__(self):
        super().__init__(parent=None, title="", size=(450, 400))
        self.SetBackgroundColour(WHITE)
        panel = wx.Panel(self)
        panel.SetBackgroundColour(WHITE)
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.', '..', 'assets', 'logo.jpg'))
        font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.', '..', 'assets', 'font.ttf'))
        vbox = wx.BoxSizer(wx.VERTICAL)
        if os.path.exists(logo_path):
            img = wx.Image(logo_path, wx.BITMAP_TYPE_JPEG)
            img = img.Scale(100, 100, wx.IMAGE_QUALITY_HIGH)
            logo_bitmap = wx.StaticBitmap(panel, bitmap=wx.Bitmap(img))
            vbox.Add(logo_bitmap, flag=wx.ALIGN_CENTER | wx.TOP, border=15)
        else:
            title = wx.StaticText(panel, label="VOLCHOCK LOGIN")
            title.SetForegroundColour(RED)
            title_font = title.GetFont()
            title_font.SetWeight(wx.FONTWEIGHT_BOLD)
            title_font.SetPointSize(16)
            title.SetFont(title_font)
            vbox.Add(title, flag=wx.ALIGN_CENTER | wx.TOP, border=5)
        volchock_label = wx.StaticText(panel, label="VOLCHOCK LOGIN")
        volchock_label.SetForegroundColour(RED)
        font_face_name = "Regular Earth"
        use_custom_font = False
        if os.path.exists(font_path):
            wx.Font.AddPrivateFont(font_path)
            try:
                custom_font = wx.Font(28, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, font_face_name)
                volchock_label.SetFont(custom_font)
                use_custom_font = True
            except Exception as e:
                print("Erreur font custom :", e)
        if not use_custom_font:
            default_font = wx.Font(28, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
            volchock_label.SetFont(default_font)
        vbox.Add(volchock_label, flag=wx.ALIGN_CENTER | wx.TOP, border=10)
        ip_label = wx.StaticText(panel, label="   IP Address:")
        ip_label.SetForegroundColour(GRAY)
        port_label = wx.StaticText(panel, label="   Port:")
        port_label.SetForegroundColour(GRAY)
        user_label = wx.StaticText(panel, label="   Username:")
        user_label.SetForegroundColour(GRAY)
        pwd_label = wx.StaticText(panel, label="   Password:")
        pwd_label.SetForegroundColour(GRAY)
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
        from ui.mainframe import MainFrame 
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
