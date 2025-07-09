import wx
from ui.login import LoginFrame

if __name__ == '__main__':
    app = wx.App(False)
    login = LoginFrame()
    login.Show()
    app.MainLoop()
