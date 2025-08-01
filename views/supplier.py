import streamlit as st
import pandas as pd
import db
from utils import require_login

def supplier_dashboard(user):
    require_login()
    st.title("📦 Supplier Dashboard")

    tabs = st.tabs(["🚚 Upload Shipment", "📜 Shipment Log"])

    with tabs[0]:
        st.subheader("📦 Upload Shipment Info")

        hubs = ["HUB1", "HUB2", "HUB3"]
        hub = st.selectbox("Destination Hub", hubs)

        # Get clean SKU dropdown
        sku_rows = db.get_all_sku_info()
        sku_options = [f"{row[1]} ({row[0]}) - {row[2]}" for row in sku_rows]
        sku_map = {opt: row[0] for opt, row in zip(sku_options, sku_rows)}

        if sku_options:
            selected_sku_display = st.selectbox("Select SKU", sku_options)
            selected_sku = sku_map[selected_sku_display]
        else:
            st.warning("No SKUs available. Contact admin to upload SKUs.")
            return

        qty = st.number_input("Quantity", min_value=1, step=1)
        tracking = st.text_input("Tracking Number")
        carrier = st.text_input("Carrier")
        ship_date = st.date_input("Shipment Date", pd.to_datetime("today"))

        if st.button("Submit Shipment"):
            db.record_shipment(user["username"], tracking, carrier, str(ship_date), hub, selected_sku, qty)
            st.success(f"✅ Shipment of {qty} units of {selected_sku} recorded for {hub}")

    with tabs[1]:
        st.subheader("📜 Your Shipment Log")
        shipments = db.get_all_shipments()
        supplier_logs = [s for s in shipments if s[1] == user["username"]]

        if supplier_logs:
            df = pd.DataFrame(supplier_logs, columns=["timestamp", "supplier", "tracking", "carrier", "ship_date", "sku", "qty"])
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 Download CSV", df.to_csv(index=False).encode("utf-8"), f"shipments_{user['username']}.csv", "text/csv")
        else:
            st.info("No shipments recorded yet.")

__all__ = ["supplier_dashboard"]
