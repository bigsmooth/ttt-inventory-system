import sqlite3, hashlib

DB = "ttt_inventory.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Admin credentials
username = "kevin"
password = "admin123"
hashed_pw = hashlib.sha256(password.encode()).hexdigest()

cur.execute("""
INSERT OR REPLACE INTO users (username, password, role, hubs)
VALUES (?, ?, ?, ?)
""", (username, hashed_pw, "admin", "ALL"))

conn.commit()
conn.close()
print(f"✅ Admin user '{username}' created with password '{password}'")
