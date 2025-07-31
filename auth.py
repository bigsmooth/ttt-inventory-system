import sqlite3
import hashlib

def login_user(username, password):
    hashed_pw = hashlib.sha256(password.encode()).hexdigest()
    conn = sqlite3.connect("ttt_inventory.db")
    cur = conn.cursor()
    user = cur.execute("""
        SELECT username, role, hubs FROM users
        WHERE username=? AND password=?
    """, (username, hashed_pw)).fetchone()
    conn.close()
    
    if user:
        return {
            "username": user[0],
            "role": user[1],
            "hubs": user[2].split(",") if user[2] else []
        }
    return None
