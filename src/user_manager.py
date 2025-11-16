import json
import hashlib
import sys
import os
from datetime import datetime

USERS_FILE = 'users.json'


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    
    with open(USERS_FILE, 'r') as f:
        return json.load(f)


def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)


def add_user(username, password):
    users = load_users()
    
    if username in users:
        print(f"ERROR: El usuario '{username}' ya existe")
        return False
    
    users[username] = hash_password(password)
    save_users(users)
    
    print(f"Usuario '{username}' agregado exitosamente")
    return True


def remove_user(username):
    users = load_users()
    
    if username not in users:
        print(f"ERROR: El usuario '{username}' no existe")
        return False
    
    del users[username]
    save_users(users)
    
    print(f"Usuario '{username}' eliminado exitosamente")
    return True


def change_password(username, new_password):
    users = load_users()
    
    if username not in users:
        print(f"ERROR: El usuario '{username}' no existe")
        return False
    
    users[username] = hash_password(new_password)
    save_users(users)
    
    print(f"Contraseña de '{username}' actualizada exitosamente")
    return True


def verify_password(username, password):
    users = load_users()
    
    if username not in users:
        print(f"ERROR: El usuario '{username}' no existe")
        return False
    
    if users[username] == hash_password(password):
        print(f"Contraseña correcta para '{username}'")
        return True
    else:
        print(f"Contraseña incorrecta para '{username}'")
        return False


def print_usage():
    """Imprime ayuda de uso"""
    print("""
NetGuard - Gestor de Usuarios

Uso:
    python3 user_manager.py <comando> [argumentos]

Comandos:
    add <usuario> <contraseña>        Agrega un nuevo usuario
    remove <usuario>                  Elimina un usuario
    change <usuario> <contraseña>     Cambia contraseña de usuario
    verify <usuario> <contraseña>     Verifica contraseña de usuario

Ejemplos:
    python3 user_manager.py add john secretpass123
    python3 user_manager.py remove john
    python3 user_manager.py change admin newpassword
    python3 user_manager.py verify admin newpassword
""")


def main():
    if len(sys.argv) < 2:
        print_usage()
        return 1
    
    command = sys.argv[1].lower()
    
    
    if command == 'add':
        if len(sys.argv) != 4:
            print("ERROR: Uso: add <usuario> <contraseña>")
            return 1
        add_user(sys.argv[2], sys.argv[3])
    
    elif command == 'remove':
        if len(sys.argv) != 3:
            print("ERROR: Uso: remove <usuario>")
            return 1
        remove_user(sys.argv[2])
    
    elif command == 'change':
        if len(sys.argv) != 4:
            print("ERROR: Uso: change <usuario> <contraseña>")
            return 1
        change_password(sys.argv[2], sys.argv[3])
    
    elif command == 'verify':
        if len(sys.argv) != 4:
            print("ERROR: Uso: verify <usuario> <contraseña>")
            return 1
        verify_password(sys.argv[2], sys.argv[3])
    
    else:
        print(f"ERROR: Comando desconocido '{command}'")
        print_usage()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
