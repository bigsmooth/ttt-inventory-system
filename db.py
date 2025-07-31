import sqlite3
import pandas as pd

DB_PATH = "ttt_inventory.db"

def get_conn():
    return sqlite3.connect(DB_PATH)

def init_db():
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            hubs TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            sku TEXT,
            hub TEXT,
            quantity INTEGER,
            PRIMARY KEY (sku, hub)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            sku TEXT,
            hub TEXT,
            action TEXT,
            qty INTEGER,
            comment TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS shipments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            supplier TEXT,
            tracking TEXT,
            carrier TEXT,
            ship_date TEXT,
            hub TEXT,
            sku TEXT,
            qty INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS warehouses (
            code TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            address TEXT,
            contact TEXT,
            status TEXT,
            region TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS sku_info (
            sku TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            barcode TEXT
        )
        """)

# --- INVENTORY FUNCTIONS ---

def get_skus_for_hub(hub):
    with get_conn() as conn:
        return conn.execute("SELECT sku, quantity FROM inventory WHERE hub=?", (hub,)).fetchall()

def update_inventory(sku, hub, qty, action):
    with get_conn() as conn:
        cur = conn.cursor()
        current = cur.execute("SELECT quantity FROM inventory WHERE sku=? AND hub=?", (sku, hub)).fetchone()
        new_qty = (current[0] if current else 0) + (qty if action == 'IN' else -qty)
        cur.execute("INSERT OR REPLACE INTO inventory (sku, hub, quantity) VALUES (?, ?, ?)", (sku, hub, new_qty))

def get_all_inventory():
    with get_conn() as conn:
        return conn.execute("SELECT sku, hub, quantity FROM inventory").fetchall()

# --- LOGS ---

def log_action(username, sku, hub, action, qty, comment):
    with get_conn() as conn:
        conn.execute("""
        INSERT INTO logs (username, sku, hub, action, qty, comment)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (username, sku, hub, action, qty, comment))

def get_logs_for_hub(hub):
    with get_conn() as conn:
        return conn.execute("""
        SELECT timestamp, username, sku, action, qty, comment
        FROM logs
        WHERE hub=?
        ORDER BY timestamp DESC
        """, (hub,)).fetchall()

def get_all_logs():
    with get_conn() as conn:
        return conn.execute("""
        SELECT timestamp, username, sku, hub, action, qty, comment
        FROM logs
        ORDER BY timestamp DESC
        """).fetchall()

# --- SHIPMENTS ---

def record_shipment(supplier, tracking, carrier, ship_date, hub, sku, qty):
    with get_conn() as conn:
        conn.execute("""
        INSERT INTO shipments (supplier, tracking, carrier, ship_date, hub, sku, qty)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (supplier, tracking, carrier, ship_date, hub, sku, qty))

def get_shipments_for_hub(hub):
    with get_conn() as conn:
        return conn.execute("""
        SELECT timestamp, supplier, tracking, carrier, ship_date, sku, qty
        FROM shipments
        WHERE hub=?
        ORDER BY timestamp DESC
        """, (hub,)).fetchall()

def get_all_shipments(start_date=None, end_date=None, hub=None):
    conn = get_conn()
    query = """
        SELECT timestamp, supplier, tracking, carrier, ship_date, sku, qty
        FROM shipments
        WHERE 1=1
    """
    params = []
    if start_date:
        query += " AND date(ship_date) >= ?"
        params.append(start_date)
    if end_date:
        query += " AND date(ship_date) <= ?"
        params.append(end_date)
    if hub:
        query += " AND hub = ?"
        params.append(hub)
    query += " ORDER BY timestamp DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return rows

# --- USERS ---

def reset_password(username, new_hashed_pw):
    with get_conn() as conn:
        conn.execute("UPDATE users SET password=? WHERE username=?", (new_hashed_pw, username))

def get_all_users():
    with get_conn() as conn:
        return conn.execute("SELECT username, role, hubs FROM users").fetchall()

def add_user(username, password_hash, role, hubs):
    with get_conn() as conn:
        conn.execute("""
        INSERT INTO users (username, password, role, hubs)
        VALUES (?, ?, ?, ?)
        """, (username, password_hash, role, hubs))

def delete_user(username):
    with get_conn() as conn:
        conn.execute("DELETE FROM users WHERE username=?", (username,))

def get_all_sku_info():
    with get_conn() as conn:
        return conn.execute("SELECT sku, name, barcode FROM sku_info ORDER BY name").fetchall()


# --- WAREHOUSES ---

def seed_warehouses():
    hubs = [
        ("HUB1", "Hub 1 - Stafford, VA", "2142 Richmond Hwy Ste 103, Stafford, VA 22554", "Kevin Mornot (+1)5404973359", "Open", "United States"),
        ("HUB2", "Hub 2 - Hartford, CT", "12 Charter Oak Pl, Hartford, CT 06106", "Customer Service (+1)5714122402", "Open", "United States"),
        ("HUB3", "Hub 3 - Cali", "3600 Sisk Rd Bldg 5 Ste 9, Modesto, CA 95356", "Customer Service (+1)5714122402", "Open", "United States"),
        ("RETAIL", "Retail - Woodbridge, VA", "3062 Ps Business Center Dr, Woodbridge, VA 22192", "Customer Service (+1)5714122402", "Open", "United States"),
    ]
    with get_conn() as conn:
        for hub in hubs:
            conn.execute("INSERT OR IGNORE INTO warehouses (code, name, address, contact, status, region) VALUES (?, ?, ?, ?, ?, ?)", hub)

def get_all_warehouses():
    with get_conn() as conn:
        return conn.execute("SELECT code, name, address, contact, status, region FROM warehouses").fetchall()

# --- SKU SEEDING ---
def seed_skus():
    data = pd.read_csv("Master_Updated_Barcode_Inventory.csv")
    with get_conn() as conn:
        for i, row in data.iterrows():
            conn.execute("INSERT OR IGNORE INTO sku_info (sku, name, barcode) VALUES (?, ?, ?)", (row["SKU"], row["Product Name"], row["Barcode Number"]))

import pandas as pd

def seed_skus(csv_path="Master_Updated_Barcode_Inventory.csv"):
    try:
        df = pd.read_csv(csv_path)
        with get_conn() as conn:
            conn.execute("""
            CREATE TABLE IF NOT EXISTS sku_info (
                sku TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                barcode TEXT
            )
            """)
            for _, row in df.iterrows():
                conn.execute("""
                    INSERT OR REPLACE INTO sku_info (sku, name, barcode)
                    VALUES (?, ?, ?)
                """, (row["SKU"], row["Product Name"], str(row["Barcode"])))
        print("✅ SKUs seeded from CSV.")
    except FileNotFoundError:
        print(f"❌ CSV file not found at path: {csv_path}")
    except Exception as e:
        print(f"❌ Error while seeding SKUs: {e}")
        
def clean_junk_skus():
    junk = ["ADFD", "ADAFD", "ADDFD", "TEST", "BLACK-WHITE", "BLACKWHITE", "RAINBOW", "HOT-PINK"]
    with get_conn() as conn:
        for sku in junk:
            conn.execute("DELETE FROM inventory WHERE sku=?", (sku,))
            conn.execute("DELETE FROM sku_info WHERE sku=?", (sku,))
    print(f"✅ Removed {len(junk)} junk/test SKUs.")


# --- Init Run ---
if __name__ == "__main__":
    init_db()
    seed_warehouses()
    seed_skus()
    clean_junk_skus()  # 👈 optional
    print("✅ Database initialized with SKUs.")


