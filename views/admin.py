import streamlit as st
import pandas as pd
import altair as alt
import hashlib
import db
from utils import require_login

def admin_dashboard(user):
    require_login()
    st.title("Admin Dashboard 🌚")

    tabs = st.tabs([
        "🏦 Inventory", "📋 Logs", "📊 Chart", "📢 Messages",
        "⚖️ Manage SKUs", "🔐 User Access", "🏢 Manage Hubs", "📥 Upload SKUs"
    ])

    inventory = db.get_all_inventory()
    df = pd.DataFrame(inventory, columns=["SKU", "Hub", "Quantity"])

    logs = db.get_all_logs()
    log_df = pd.DataFrame(logs, columns=["timestamp", "username", "sku", "hub", "action", "qty", "comment"])
    unread_count = sum(1 for log in logs if log[4] == "MESSAGE")

    with tabs[0]:
        st.subheader("📦 Inventory by Hub")
        sku_filter = st.text_input("Filter by SKU (optional)")
        hub_filter = st.selectbox("Filter by Hub", ["All"] + df["Hub"].unique().tolist())
        filtered = df.copy()
        if sku_filter:
            filtered = filtered[filtered["SKU"].str.contains(sku_filter.upper())]
        if hub_filter != "All":
            filtered = filtered[filtered["Hub"] == hub_filter]
        st.dataframe(filtered, use_container_width=True)

    with tabs[1]:
        st.subheader("📋 Full Inventory Log")
        st.dataframe(log_df, use_container_width=True)
        st.download_button(
            label="📅 Download Log CSV",
            data=log_df.to_csv(index=False).encode("utf-8"),
            file_name="admin_log.csv",
            mime="text/csv"
        )

    with tabs[2]:
        st.subheader("📊 Activity Chart")
        if not log_df.empty:
            chart = alt.Chart(log_df).mark_bar().encode(
                x="timestamp:T",
                y="qty:Q",
                color="action:N",
                tooltip=["sku", "hub", "qty", "action"]
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No chart data available.")

    with tabs[3]:
        st.subheader(f"📢 Messages from Hubs {'🔴' if unread_count else ''}")
        messages = [log for log in logs if log[4] == "MESSAGE"]
        if messages:
            msg_df = pd.DataFrame(messages, columns=["timestamp", "username", "sku", "hub", "action", "qty", "comment"])
            st.dataframe(msg_df[["timestamp", "username", "hub", "comment"]], use_container_width=True)

            st.markdown("### ✏️ Reply to a Hub")
            selected_msg = st.selectbox("Select a message to reply to", msg_df["comment"])
            match_row = msg_df[msg_df["comment"] == selected_msg].iloc[0]
            selected_hub = match_row["hub"]
            selected_user = match_row["username"]
            reply_subject = f"RE: {selected_msg.split('//')[0].replace('SUBJECT:', '').strip()}"
            st.text_input("Subject", value=reply_subject, disabled=True)
            reply_message = st.text_area("Reply Message")
            if st.button("Send Reply"):
                full_msg = f"REPLY TO {selected_user} @ {selected_hub} // {reply_message}"
                db.log_action(user["username"], "N/A", selected_hub, "REPLY", 0, full_msg)
                st.success("📤 Reply sent.")
        else:
            st.info("No messages from hubs.")

    with tabs[4]:
        st.subheader("⚖️ Add or Remove SKUs")
        hubs = ["HUB1", "HUB2", "HUB3", "RETAIL"]
        action = st.radio("Action", ["Add", "Remove"], horizontal=True)
        hub = st.selectbox("Select Hub", hubs)

        sku_rows = db.get_all_sku_info()
        sku_options = [f"{row[0]} — {row[1]} — {row[2]}" for row in sku_rows]
        sku_map = {display: row[0] for display, row in zip(sku_options, sku_rows)}

        selected_sku_display = st.selectbox("SKU", sku_options)

        sku = sku_map.get(selected_sku_display)
        if not sku:
            st.error("❌ SKU not found. Please make sure your SKU info table is correctly populated.")
            st.stop()

        qty = st.number_input("Quantity", min_value=1, step=1)
        if st.button("Apply Change"):
            if action == "Add":
                db.update_inventory(sku, hub, qty, "IN")
                db.log_action(user["username"], sku, hub, "ADMIN-ADD", qty, "Manual add by admin")
                st.success(f"Added {qty} units of {sku} to {hub}")
            else:
                db.update_inventory(sku, hub, qty, "OUT")
                db.log_action(user["username"], sku, hub, "ADMIN-REMOVE", qty, "Manual remove by admin")
                st.success(f"Removed {qty} units of {sku} from {hub}")

    with tabs[5]:
        st.subheader("🔐 Manage Users")
        users = db.get_all_users()
        user_df = pd.DataFrame(users, columns=["Username", "Role", "Hubs"])
        st.dataframe(user_df, use_container_width=True)

        st.markdown("### ➕ Add New User")
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        new_role = st.selectbox("Role", ["admin", "manager", "supplier", "retail"])
        new_hubs = st.multiselect("Hubs", ["HUB1", "HUB2", "HUB3", "RETAIL"])
        if st.button("Create User"):
            if new_username and new_password and new_role:
                hashed = hashlib.sha256(new_password.encode()).hexdigest()
                db.add_user(new_username, hashed, new_role, ",".join(new_hubs))
                st.success(f"✅ User '{new_username}' created.")
                st.rerun()
            else:
                st.error("All fields are required.")

        st.markdown("### ❌ Remove User")
        user_to_delete = st.selectbox("Select user to delete", [u[0] for u in users if u[0] != user["username"]])
        if st.button("Delete User"):
            db.delete_user(user_to_delete)
            st.success(f"User '{user_to_delete}' deleted.")
            st.rerun()

        st.markdown("### 🔁 Reset Password")
        reset_user = st.selectbox("Select user to reset password", [u[0] for u in users])
        new_pw = st.text_input("New Password", type="password")
        if st.button("Reset Password"):
            if reset_user and new_pw:
                new_hash = hashlib.sha256(new_pw.encode()).hexdigest()
                db.reset_password(reset_user, new_hash)
                st.success(f"Password for '{reset_user}' reset.")

    with tabs[6]:
        st.subheader("🏢 Manage Warehouses")
        hubs = db.get_all_warehouses()
        hub_df = pd.DataFrame(hubs, columns=["Code", "Name", "Address", "Contact", "Status", "Region"])
        st.dataframe(hub_df, use_container_width=True)

        if not hub_df.empty:
            st.markdown("### ✏️ Edit Hub Info")
            selected_code = st.selectbox("Select Hub Code", hub_df["Code"])
            selected_hub_row = hub_df[hub_df["Code"] == selected_code]

            if not selected_hub_row.empty:
                selected_hub = selected_hub_row.iloc[0]

                new_address = st.text_input("Address", selected_hub["Address"])
                new_contact = st.text_input("Contact", selected_hub["Contact"])
                new_status = st.selectbox("Status", ["Open", "Closed"], index=0 if selected_hub["Status"] == "Open" else 1)
                new_region = st.text_input("Region", selected_hub["Region"])

                if st.button("Save Changes to Hub"):
                    with db.get_conn() as conn:
                        conn.execute("""
                            UPDATE warehouses
                            SET address=?, contact=?, status=?, region=?
                            WHERE code=?
                        """, (new_address, new_contact, new_status, new_region, selected_code))
                    st.success(f"✅ Hub '{selected_code}' updated.")
                    st.rerun()
            else:
                st.warning("⚠️ Selected hub not found.")
        else:
            st.info("No hubs available.")

    with tabs[7]:
        st.subheader("📥 Upload & Seed SKUs from CSV")
        st.info("Upload a CSV with columns: `SKU`, `Product Name`, and `Barcode Number`.")
        uploaded_file = st.file_uploader("Upload SKU CSV", type="csv")

        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                st.dataframe(df.head(), use_container_width=True)

                if st.button("Seed SKUs into Database"):
                    with db.get_conn() as conn:
                        conn.execute("""
                            CREATE TABLE IF NOT EXISTS sku_info (
                                sku TEXT PRIMARY KEY,
                                name TEXT NOT NULL,
                                barcode TEXT
                            )
                        """)
                        inserted = 0
                        for _, row in df.iterrows():
                            sku = str(row.get("SKU", "")).strip()
                            name = str(row.get("Product Name", "")).strip()
                            barcode = str(row.get("Barcode Number", "")).strip()

                            if not sku or not name:
                                continue

                            conn.execute("INSERT OR IGNORE INTO sku_info (sku, name, barcode) VALUES (?, ?, ?)", (sku, name, barcode))
                            inserted += 1

                    st.success(f"✅ Seeded {inserted} SKUs into `sku_info` table.")
            except Exception as e:
                st.error(f"❌ Failed to process file: {e}")

__all__ = ["admin_dashboard"]
