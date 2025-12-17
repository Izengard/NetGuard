
import json
import hashlib
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import USERS_FILE


class UserManager:
    
    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.users_file = os.path.join(base_dir, USERS_FILE)
        self._ensure_file_exists()
    
    def _ensure_file_exists(self):
        dir_path = os.path.dirname(self.users_file)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)
        
        if not os.path.exists(self.users_file):
            # Crear usuario admin por defecto
            users = {"admin": self._hash_password("admin123")}
            self._save_users(users)
            print("[USERS] Usuario admin creado (password: admin123)")
    
    def _hash_password(self, password: str) -> str:
        salt = os.urandom(16).hex()
        hash_value = hashlib.sha256((salt + password).encode()).hexdigest()
        return f"{salt}:{hash_value}"
    
    def _verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            salt, _ = stored_hash.split(':', 1)
            new_hash = hashlib.sha256((salt + password).encode()).hexdigest()
            return stored_hash == f"{salt}:{new_hash}"
        except:
            return False
    
    def _load_users(self) -> dict:
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_users(self, users: dict):
        with open(self.users_file, 'w') as f:
            json.dump(users, f, indent=2)
    
    def authenticate(self, username: str, password: str) -> bool:
        users = self._load_users()
        if username not in users:
            return False
        return self._verify_password(password, users[username])
    
    def add_user(self, username: str, password: str) -> bool:
        users = self._load_users()
        if username in users:
            return False
        users[username] = self._hash_password(password)
        self._save_users(users)
        print(f"[USERS] Usuario creado: {username}")
        return True
    
    def delete_user(self, username: str) -> bool:
        users = self._load_users()
        if username not in users:
            return False
        del users[username]
        self._save_users(users)
        return True
