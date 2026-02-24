#!/usr/bin/env python3
"""
Run once on PythonAnywhere to set up initial usernames and passwords.
Usage: python3 set_passwords.py
"""
import sqlite3
from werkzeug.security import generate_password_hash
import os
import getpass

DB_PATH = os.environ.get('DB_PATH', 'deathpool.db')

# Map participant names to usernames — edit usernames here if desired
users = [
    ('Jim',  'jim'),
    ('Drew', 'drew'),
    ('Oost', 'oost'),
]

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

for name, username in users:
    password = getpass.getpass(f"Set password for {name} (username: {username}): ")
    password_hash = generate_password_hash(password)
    cursor.execute(
        "UPDATE participants SET username = ?, password_hash = ? WHERE name = ?",
        (username, password_hash, name)
    )
    if cursor.rowcount == 0:
        print(f"  WARNING: No participant named '{name}' found — skipping")
    else:
        print(f"  OK: credentials set for {name}")

conn.commit()
conn.close()
print("\nDone! You can delete this script or keep it for password resets.")
