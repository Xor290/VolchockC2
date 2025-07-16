from kivy.app import App
from kivy.uix.screenmanager import ScreenManager
from ui.login import LoginScreen
from ui.mainframe import MainFrame

class MainScreenManager(ScreenManager): pass

class LoginApp(App):
    title = "VOLCHOCK C2"
    def build(self):
        self.sm = MainScreenManager()
        self.login_screen = LoginScreen(name="VOLCHOCK C2")
        self.login_screen.app_ref = self
        self.sm.add_widget(self.login_screen)
        return self.sm
    def on_login_success(self, base_url, auth, agents):
        if self.sm.has_screen("main"):
            self.sm.remove_widget(self.sm.get_screen("main"))
        self.main_screen = MainFrame(base_url, auth, agents, name="main")
        self.sm.add_widget(self.main_screen)
        self.sm.current = "main"
if __name__ == '__main__':
    LoginApp().run()
