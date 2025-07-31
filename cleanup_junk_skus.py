# cleanup_junk_skus.py

import db

# List of known bad/test SKUs
bad_skus = ["TEST", "ADFD", "ADFD", "ADAFD", "ADFFDF", "ADDFD", "BLACKWHITE", "HOTPINK", "RAINBOW"]  # Add any more you see

with db.get_conn() as conn:
    for sku in bad_skus:
        conn.execute("DELETE FROM inventory WHERE sku = ?", (sku,))
        conn.execute("DELETE FROM logs WHERE sku = ?", (sku,))
        conn.execute("DELETE FROM sku_info WHERE sku = ?", (sku,))
    print("✅ Removed test SKUs from inventory, logs, and sku_info.")
