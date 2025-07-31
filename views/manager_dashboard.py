import db
import streamlit as st
import pandas as pd
import altair as alt
from utils import require_login

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
            st.download_button("📥 Download Log CSV", log_df.to_csv(index=False).encode("utf-8"), f"log_{hub}.csv", "text/csv")
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
            st.download_button("📥 Download Shipments CSV", df.to_csv(index=False).encode("utf-8"), f"shipments_{hub}.csv", "text/csv")
        else:
            st.info("No incoming shipments logged.")

    with tabs[4]:
        low_stock_threshold = st.slider("Alert threshold", min_value=1, max_value=50, value=10)
        low_stock = [(sku, qty) for sku, qty in skus if qty < low_stock_threshold]

        if low_stock:
            df = pd.DataFrame(low_stock, columns=["SKU", "Quantity"])
            st.warning(f"⚠️ {len(low_stock)} SKUs below threshold ({low_stock_threshold})")
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 Download Low Stock CSV", df.to_csv(index=False).encode("utf-8"), f"low_stock_{hub}.csv", "text/csv")
        else:
            st.success("✅ No SKUs are below the alert threshold.")

    with tabs[5]:
        st.subheader("Send Message to Admin/HQ")
        subject = st.text_input("Subject")
        message = st.text_area("Message")
        if st.button("Send Message"):
            db.log_action(user["username"], selected_sku, hub, "MESSAGE", 0, f"SUBJECT: {subject} // {message}")
            st.success("📨 Message sent to admin!")

        with st.expander("📬 Admin Replies to Your Hub"):
            replies = [log for log in db.get_all_logs() if log[4] == "REPLY" and log[3] == hub]
            if replies:
                df = pd.DataFrame(replies, columns=["timestamp", "username", "sku", "hub", "action", "qty", "comment"])
                st.dataframe(df[["timestamp", "username", "comment"]], use_container_width=True)
            else:
                st.info("No replies from admin yet.")
