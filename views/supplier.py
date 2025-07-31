import streamlit as st
from datetime import date
import pandas as pd
import db
from utils import require_login

def supplier_upload(user):
    require_login()
    st.title("📦 Supplier Shipment Upload")

    tabs = st.tabs(["🚚 Upload Shipment", "📜 Your Shipments", "📬 Admin Replies"])

    # Upload tab
    with tabs[0]:
        tracking = st.text_input("Tracking Number")
        carrier = st.selectbox("Carrier", ["UPS", "FedEx", "USPS", "DHL", "Amazon", "Other"])
        ship_date = st.date_input("Shipping Date", value=date.today())

        # Get formatted warehouse list
        warehouse_options = db.get_all_warehouses()
        label_to_code = {f"{name}": code for code, name, *_ in warehouse_options}
        selected_label = st.selectbox("Destination Hub", list(label_to_code.keys()))
        dest_hub = label_to_code[selected_label]  # actual code like "HUB1"

        notes = st.text_input("Optional Notes to Admin")

        st.markdown("### SKUs in Shipment")

        all_skus = sorted(set(sku for sku, _, _ in db.get_all_inventory()))

        sku_data = []
        sku_count = st.number_input("How many SKUs are you shipping?", min_value=1, max_value=50, value=5)
        with st.form("shipment_form"):
            for i in range(int(sku_count)):
                col1, col2 = st.columns([3, 2])
                sku = col1.selectbox(f"SKU {i+1}", all_skus, key=f"sku_{i}")
                qty = col2.number_input("Qty", min_value=0, step=1, key=f"qty_{i}")
                if sku and qty > 0:
                    sku_data.append((sku.upper(), qty))

            submitted = st.form_submit_button("Submit Shipment")
            if submitted:
                if not tracking or not carrier or not sku_data:
                    st.error("Please fill in all required fields and at least one SKU.")
                else:
                    for sku, qty in sku_data:
                        db.update_inventory(sku, dest_hub, qty, "IN")
                        db.log_action(user["username"], sku, dest_hub, "SUPPLIER-IN", qty,
                                      f"Tracking: {tracking}, Carrier: {carrier}, Date: {ship_date}, Notes: {notes}")
                        db.record_shipment(user["username"], tracking, carrier, str(ship_date), dest_hub, sku, qty)
                    st.success(f"Shipment recorded for {selected_label} with {len(sku_data)} SKUs.")

                    st.markdown("### ✅ Submitted Shipment")
                    for sku, qty in sku_data:
                        st.write(f"- **{sku}**: {qty}")

        if st.button("Clear All"):
            st.rerun()

    # Shipments tab
    with tabs[1]:
        shipments = db.get_all_shipments()
        your_shipments = [s for s in shipments if s[1] == user["username"]]

        st.subheader("📆 Filter by Date Range")
        start_date = st.date_input("Start Date", value=date.today())
        end_date = st.date_input("End Date", value=date.today())

        filtered_shipments = [s for s in your_shipments if start_date <= pd.to_datetime(s[4]).date() <= end_date]

        if filtered_shipments:
            df = pd.DataFrame(filtered_shipments, columns=[
                "timestamp", "supplier", "tracking", "carrier", "ship_date", "sku", "qty"])
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 Download CSV", df.to_csv(index=False).encode("utf-8"),
                               f"shipments_{user['username']}.csv", "text/csv")
        else:
            st.info("No shipments found.")

    # Admin Replies tab
    with tabs[2]:
        st.subheader("📬 Replies from Admin")
        replies = [log for log in db.get_all_logs() if log[4] == "REPLY" and f"TO {user['username']}" in log[6]]

        if replies:
            df = pd.DataFrame(replies, columns=["timestamp", "admin", "sku", "hub", "action", "qty", "comment"])
            st.dataframe(df[["timestamp", "admin", "comment"]], use_container_width=True)
        else:
            st.info("No replies from admin yet.")
