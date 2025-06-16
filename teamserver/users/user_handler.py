# teamserver/users/user_handler.py
# Handles authentication and management of server users/admins.

class UserHandler:
    def __init__(self):
        self.users = {}

    def add_user(self, username, password):
        self.users[username] = password
        print(f"[*] Added user: {username}")

    def authenticate(self, username, password):
        return self.users.get(username) == password
