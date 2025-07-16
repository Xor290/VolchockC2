import json
import argparse
import requests
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.scrollview import ScrollView
from requests.auth import HTTPBasicAuth
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from constants.colors import RED, GREEN

def color_to_hex(color):
    return f"#{int(color[0]*255):02x}{int(color[1]*255):02x}{int(color[2]*255):02x}"

class LogsView(BoxLayout):
    def __init__(self, base_url, auth, **kwargs):
        super().__init__(orientation='vertical', **kwargs)
        self.base_url = base_url
        self.auth = auth
        self.label = Label(text="Fetching logs...", size_hint_y=None, halign='left', valign='top', markup=True)
        self.label.bind(texture_size=self._set_label_height)
        self.scroll = ScrollView(size_hint=(1, 1))
        self.scroll.add_widget(self.label)
        self.add_widget(self.scroll)
        Clock.schedule_interval(self.update_logs, 3)
        self.update_logs(0)

    def _set_label_height(self, instance, value):
        self.label.height = value[1]
        self.label.text_size = (self.width, None)

    def update_logs(self, dt):
        try:
            print(f"{self.base_url}/logs")
            resp = requests.get(f"{self.base_url}/logs", auth=self.auth)
            if resp.ok:
                data = resp.json()
                logs = []
                for log in data["logs"]:
                    if "DEBUG" in log:
                        logs.append(f"[color={color_to_hex(GREEN)}]{log}[/color]")
                    elif "INFO" in log:
                        logs.append(f"[color={color_to_hex(GREEN)}]{log}[/color]")
                    elif "ERROR" in log:
                        logs.append(f"[color={color_to_hex(RED)}]{log}[/color]")
                    else:
                        logs.append(log)
                self.label.text = "\n".join(logs)
                self.scroll.scroll_y = 0  # Faire défiler vers le bas
            else:
                self.label.text = f"[color={RED}]Erreur log: {resp.status_code}[/color]"
        except Exception as e:
            self.label.text = f"[color={RED}]Erreur logs: {e}[/color]"

class LogsApp(App):
    def __init__(self, base_url, auth, **kwargs):
        self.base_url = base_url
        self.auth = auth
        super().__init__(**kwargs)

    def build(self):
        return LogsView(self.base_url, self.auth)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    print(parser)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--auth', required=True)
    args = parser.parse_args()
    base_url = args.base_url
    auth_data = json.loads(args.auth)
    username = auth_data['username']
    passwd = auth_data['password']
    print(username)
    auth = HTTPBasicAuth(username, passwd)
    from kivy.core.window import Window
    Window.size = (900, 500)
    LogsApp(base_url, auth).run()
