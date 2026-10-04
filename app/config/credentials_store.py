"""Saved connection profiles.

Non-secret fields (name, host, port, username) go in a local JSON file.
Passwords go through the `keyring` library, which uses the Windows Credential
Manager on Windows and the Secret Service (gnome-keyring/kwallet) on Ubuntu --
never written to disk in plain text by this app.
"""

import json
import os

import keyring

SERVICE_NAME = "mysql-db-manager"
CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".config", "mysql-db-manager")
PROFILES_FILE = os.path.join(CONFIG_DIR, "profiles.json")


def _ensure_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def _keyring_key(profile_name, host, port, username):
    return f"{profile_name}|{host}|{port}|{username}"


def load_profiles():
    _ensure_dir()
    if not os.path.exists(PROFILES_FILE):
        return []
    try:
        with open(PROFILES_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_profile(name, host, port, username, password):
    _ensure_dir()
    profiles = [p for p in load_profiles() if p["name"] != name]
    profiles.append({"name": name, "host": host, "port": port, "username": username})
    with open(PROFILES_FILE, "w") as f:
        json.dump(profiles, f, indent=2)
    keyring.set_password(SERVICE_NAME, _keyring_key(name, host, port, username), password)


def get_password(name, host, port, username):
    return keyring.get_password(SERVICE_NAME, _keyring_key(name, host, port, username))


def delete_profile(name):
    profiles = load_profiles()
    target = next((p for p in profiles if p["name"] == name), None)
    profiles = [p for p in profiles if p["name"] != name]
    with open(PROFILES_FILE, "w") as f:
        json.dump(profiles, f, indent=2)
    if target:
        try:
            keyring.delete_password(
                SERVICE_NAME,
                _keyring_key(target["name"], target["host"], target["port"], target["username"]),
            )
        except keyring.errors.PasswordDeleteError:
            pass
