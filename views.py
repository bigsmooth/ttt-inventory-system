import db
import streamlit as st
import pandas as pd
import altair as alt
from utils import require_login
from datetime import date

__all__ = ["admin_dashboard", "manager_dashboard", "supplier_upload", "retail_inventory"]

def admin_dashboard(user):
    require_login()
    st.title("Admin Dashboard 🌚")

    tabs = st.tabs(["🏦 Inventory", "📋 Logs", "📊 Chart", "📢 Messages", "🔧 Manage SKUs"])

    inventory = db.get_all_inventory()
    df = pd.DataFrame(inventory, columns=["SKU", "Hub", "Quantity"])

    logs = db.get_all_logs()
    log_df = pd.DataFrame(logs, columns=["timestamp", "username", "sku", "hub", "action", "qty", "comment"])
    unread_count = sum(1 for log in logs if log[4] == "MESSAGE")

    # Inventory tab
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

    # Logs tab
    with tabs[1]:
        st.subheader("📋 Full Inventory Log")
        st.dataframe(log_df, use_container_width=True)
        st.download_button(
            label="📅 Download Log CSV",
            data=log_df.to_csv(index=False).encode("utf-8"),
            file_name="admin_log.csv",
            mime="text/csv"
        )

    # Chart tab
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

    # Messages tab
    with tabs[3]:
        st.subheader(f"📢 Messages from Hubs {'🔴' if unread_count else ''}")
        messages = [log for log in logs if log[4] == "MESSAGE"]

        if messages:
            msg_df = pd.DataFrame(messages, columns=["timestamp", "username", "sku", "hub", "action", "qty", "comment"])
            st.dataframe(msg_df[["timestamp", "username", "hub", "comment"]], use_container_width=True)

            st.markdown("### ✏️ Reply to a Hub")
            selected_hub = st.selectbox("Select Hub to Reply", sorted(msg_df["hub"].unique()))
            selected_user = st.selectbox("Select User to Reply", sorted(msg_df[msg_df["hub"] == selected_hub]["username"].unique()))
            reply_subject = st.text_input("Subject")
            reply_message = st.text_area("Reply Message")

            if st.button("Send Reply"):
                full_msg = f"REPLY TO {selected_user} @ {selected_hub} // SUBJECT: {reply_subject} // {reply_message}"
                db.log_action(user["username"], "N/A", selected_hub, "REPLY", 0, full_msg)
                st.success("📤 Reply sent.")
        else:
            st.info("No messages from hubs.")

    # Manage SKUs tab
    with tabs[4]:
        st.subheader("🔧 Add or Remove SKUs")
        hubs = ["HUB1", "HUB2", "HUB3", "RETAIL"]
        action = st.radio("Action", ["Add", "Remove"], horizontal=True)
        hub = st.selectbox("Select Hub", hubs)
        sku = st.text_input("SKU").upper()
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

def manager_dashboard(user):
    require_login()
    st.title("Hub Manager Dashboard")

    hub = user["hubs"][0] if len(user["hubs"]) == 1 else st.selectbox("Select Hub", user["hubs"])

    tabs = st.tabs(["🔄 IN/OUT", "📜 Log", "📊 Chart", "📦 Shipments", "⚠️ Low Stock", "✉️ Message Admin"])

    with tabs[0]:
        if "last_action" not in st.session_state:
            st.session_state["last_action"] = None
        if "selected_sku" not in st.session_state:
            st.session_state["selected_sku"] = None

        skus = db.get_skus_for_hub(hub)
        sku_dict = {sku: qty for sku, qty in skus}
        sku_list = list(sku_dict.keys())

        selected_sku = st.selectbox("SKU", sku_list, index=sku_list.index(st.session_state["selected_sku"]) if st.session_state["selected_sku"] in sku_list else 0)
        st.session_state["selected_sku"] = selected_sku

        st.write(f"Current quantity: **{sku_dict.get(selected_sku, 0)}**")

        action = st.radio("Action", ["IN", "OUT"], horizontal=True)
        qty = st.number_input("Quantity", min_value=1, step=1)
        comment = st.text_input("Comment (optional)")

        if st.button("Submit"):
            db.update_inventory(selected_sku, hub, qty, action)
            db.log_action(user["username"], selected_sku, hub, action, qty, comment)
            st.session_state["last_action"] = f"{action} {qty} of {selected_sku}"
            st.success(f"✅ {action} {qty} units of {selected_sku} recorded for {hub}")
            skus = db.get_skus_for_hub(hub)
            sku_dict = {sku: qty for sku, qty in skus}

        if st.session_state["last_action"]:
            st.caption(f"Last action: {st.session_state['last_action']}")

    with tabs[1]:
        raw_logs = db.get_logs_for_hub(hub)
        if raw_logs:
            log_df = pd.DataFrame(raw_logs, columns=["timestamp", "username", "sku", "action", "qty", "comment"])
            st.dataframe(log_df, use_container_width=True)
            st.download_button("\U0001f4c5 Download Log CSV", log_df.to_csv(index=False).encode("utf-8"), f"log_{hub}.csv", "text/csv")
        else:
            st.info("No logs yet.")

    with tabs[2]:
        if raw_logs:
            chart = alt.Chart(log_df).mark_bar().encode(
                x="timestamp:T",
                y="qty:Q",
                color="action:N",
                tooltip=["sku", "qty", "action", "timestamp"]
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No chart data available.")

    with tabs[3]:
        shipments = db.get_shipments_for_hub(hub)
        if shipments:
            df = pd.DataFrame(shipments, columns=["timestamp", "supplier", "tracking", "carrier", "ship_date", "sku", "qty"])
            st.dataframe(df, use_container_width=True)
            st.download_button("\U0001f4c5 Download Shipments CSV", df.to_csv(index=False).encode("utf-8"), f"shipments_{hub}.csv", "text/csv")
        else:
            st.info("No incoming shipments logged.")

    with tabs[4]:
        low_stock_threshold = st.slider("Alert threshold", min_value=1, max_value=50, value=10)
        low_stock = [(sku, qty) for sku, qty in skus if qty < low_stock_threshold]

        if low_stock:
            df = pd.DataFrame(low_stock, columns=["SKU", "Quantity"])
            st.warning(f"\u26a0\ufe0f {len(low_stock)} SKUs below threshold ({low_stock_threshold})")
            st.dataframe(df, use_container_width=True)
            st.download_button("\U0001f4c5 Download Low Stock CSV", df.to_csv(index=False).encode("utf-8"), f"low_stock_{hub}.csv", "text/csv")
        else:
            st.success("\u2705 No SKUs are below the alert threshold.")

    with tabs[5]:
        st.subheader("Send Message to Admin/HQ")
        subject = st.text_input("Subject")
        message = st.text_area("Message")
        if st.button("Send Message"):
            db.log_action(user["username"], selected_sku, hub, "MESSAGE", 0, f"SUBJECT: {subject} // {message}")
            st.success("\ud83d\udce8 Message sent to admin!")

        # View Admin Replies
        with st.expander("\ud83d\udcec Admin Replies to Your Hub"):
            replies = [log for log in db.get_all_logs() if log[4] == "REPLY" and log[3] == hub]
            if replies:
                df = pd.DataFrame(replies, columns=["timestamp", "username", "sku", "hub", "action", "qty", "comment"])
                st.dataframe(df[["timestamp", "username", "comment"]], use_container_width=True)
            else:
                st.info("No replies from admin yet.")

# supplier_upload and retail_inventory stay unchanged

def supplier_upload(user):
    require_login()
    st.title("📦 Supplier Shipment Upload")

    tracking = st.text_input("Tracking Number")
    carrier = st.selectbox("Carrier", ["UPS", "FedEx", "USPS", "DHL", "Amazon", "Other"])
    ship_date = st.date_input("Shipping Date", value=date.today())
    dest_hub = st.selectbox("Destination Hub", ["HUB1", "HUB2", "HUB3", "RETAIL"])

    st.markdown("### SKUs in Shipment")
    with st.form("shipment_form"):
        sku_data = []
        for i in range(5):
            col1, col2 = st.columns([3, 2])
            sku = col1.text_input(f"SKU {i+1}", key=f"sku_{i}")
            qty = col2.number_input(f"Qty", min_value=0, step=1, key=f"qty_{i}")
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
                                  f"Tracking: {tracking}, Carrier: {carrier}, Date: {ship_date}")
                    db.record_shipment(user["username"], tracking, carrier, str(ship_date), dest_hub, sku, qty)
                st.success(f"Shipment recorded for {dest_hub} with {len(sku_data)} SKUs.")

def retail_inventory(user):
    require_login()
    st.title("Retail Inventory IN / OUT")

    all_inventory = db.get_all_inventory()
    sku_dict = {}
    for sku, hub, qty in all_inventory:
        sku_dict.setdefault(sku, 0)
        sku_dict[sku] += qty

    sku_list = sorted(sku_dict.keys())
    selected_sku = st.selectbox("Select SKU", sku_list)
    current_total = sku_dict.get(selected_sku, 0)
    st.write(f"Total quantity across all hubs: **{current_total}**")

    action = st.radio("Action", ["IN", "OUT", "COUNT"], horizontal=True)
    qty = st.number_input("Quantity", min_value=1, step=1)
    comment = st.text_input("Comment (optional)")

    if st.button("Submit"):
        if action == "COUNT":
            db.update_inventory(selected_sku, "RETAIL", qty, "IN")
            db.log_action(user["username"], selected_sku, "RETAIL", "COUNT", qty, comment)
        else:
            db.update_inventory(selected_sku, "RETAIL", qty, action)
            db.log_action(user["username"], selected_sku, "RETAIL", action, qty, comment)
        st.success(f"{action} {qty} units of {selected_sku} recorded (RETAIL)")

    with st.expander("📜 View Retail Log"):
        logs = db.get_logs_for_hub("RETAIL")
        if logs:
            log_df = pd.DataFrame(logs, columns=["timestamp", "username", "sku", "action", "qty", "comment"])
            st.dataframe(log_df, use_container_width=True)
        else:
            st.info("No logs yet.")

    with st.expander("📈 Retail Activity Chart"):
        if logs:
            log_df = pd.DataFrame(logs, columns=["timestamp", "username", "sku", "action", "qty", "comment"])
            chart = alt.Chart(log_df).mark_bar().encode(
                x="timestamp:T",
                y="qty:Q",
                color="action:N",
                tooltip=["sku", "qty", "action", "timestamp"]
            ).properties(height=300)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("No chart data available.")

