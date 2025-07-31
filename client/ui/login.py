from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.core.text import LabelBase
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty
import requests
from requests.auth import HTTPBasicAuth
import os
from constants.colors import RED, GREEN, GRAY, WHITE, INPUT_GRAY

class LoginScreen(Screen):
    def __init__(self, **kwargs):
        super(LoginScreen, self).__init__(**kwargs)
        self.app_ref = None
        layout = BoxLayout(orientation='vertical', padding=[30, 25, 30, 25], spacing=10)
        # Custom font
        font_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.', '..', 'assets', 'font.ttf'))
        logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '.', '..', 'assets', 'logo.jpg'))
        font_face_name = "RegularEarth"
        font_name = None
        if os.path.exists(font_path):
            LabelBase.register(name=font_face_name, fn_regular=font_path)
            font_name = font_face_name
        # Logo
        if os.path.exists(logo_path):
            logo = Image(source=logo_path, size_hint=(None, None), size=(100, 100), allow_stretch=True)
            box_logo = BoxLayout(size_hint=(1, None), height=120)
            box_logo.add_widget(Label())
            box_logo.add_widget(logo)
            box_logo.add_widget(Label())
            layout.add_widget(box_logo)
        else:
            title_lbl = Label(
                text="VOLCHOCK LOGIN",
                color=RED,
                font_size=28,
                bold=True,
                size_hint=(1, None),
                height=40,
                font_name=font_name
            )
            layout.add_widget(title_lbl)
        layout.add_widget(Label(size_hint=(1, 0.1)))
        volchock = Label(
            text="VOLCHOCK LOGIN",
            color=RED,
            font_size=28,
            font_name=font_name,
            bold=True,
            size_hint=(1, None),
            height=40
        )
        layout.add_widget(volchock)
        layout.add_widget(Label(size_hint=(1, 0.01)))

        def make_row(label_txt, hint, passwd=False, _default="", _id=None):
            row = BoxLayout(orientation="horizontal", size_hint=(1, None), height=38, spacing=6)
            label = Label(text=label_txt, color=GRAY, font_size=16, size_hint=(0.32, None), height=38, halign="left", valign="middle")
            label.bind(size=label.setter('text_size'))
            ti = TextInput(
                text=_default,
                hint_text=hint,
                multiline=False,
                password=passwd,
                foreground_color=WHITE,
                background_color=INPUT_GRAY,
                size_hint=(0.68, None),
                height=38,
                cursor_color=WHITE
            )
            setattr(self, _id, ti)
            row.add_widget(label)
            row.add_widget(ti)
            return row

        layout.add_widget(make_row("IP Address:", "Enter IP address", _default="52.178.4.207", _id="ip_txt"))
        layout.add_widget(make_row("Port:", "Enter port", _default="8088", _id="port_txt"))
        layout.add_widget(make_row("Username:", "Enter username", _default="proc", _id="user_txt"))
        layout.add_widget(make_row("Password:", "Enter password", True, _default="mdp2PR0C", _id="pwd_txt"))

        self.msg_lbl = Label(
            text='',
            color=RED,
            size_hint=(1, None),
            height=22
        )
        layout.add_widget(self.msg_lbl)
        layout.add_widget(Label(size_hint=(1, 0.04)))
        login_btn = Button(
            text="Log in",
            size_hint=(1, None),
            background_color=WHITE,
            color=RED,
            height=48
        )
        login_btn.bind(on_press=self.on_login)
        layout.add_widget(login_btn)
        layout.add_widget(Label(size_hint=(1, 0.18)))
        self.add_widget(layout)

    def on_login(self, instance):
        ip = self.ip_txt.text.strip()
        port = self.port_txt.text.strip()
        user = self.user_txt.text.strip()
        pwd = self.pwd_txt.text.strip()
        base_url = f"http://{ip}:{port}"
        auth = HTTPBasicAuth(user, pwd)
        try:
            resp = requests.get(f"{base_url}/agents", auth=auth, timeout=5)
            if resp.status_code == 401:
                self.msg_lbl.text = "Bad credentials"
                self.msg_lbl.color = RED
            elif not resp.ok:
                self.msg_lbl.text = f"[!] Fail to connect: {resp.status_code}"
                self.msg_lbl.color = RED
            else:
                agents = resp.json().get("agents", [])
                # Next screen/logic placeholder
                self.msg_lbl.text = "Login successful"
                self.msg_lbl.color = GREEN
                if self.app_ref is not None:
                    self.app_ref.on_login_success(base_url, auth, agents)
                return True
        except Exception as e:
            self.msg_lbl.text = f"[!] {str(e)}"

class LoginApp(App):
    def build(self):
        self.title = "VOLCHOCK C2"
        return LoginScreen()

if __name__ == '__main__':
    LoginApp().run()
