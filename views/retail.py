import streamlit as st
import pandas as pd
import altair as alt
import db
from utils import require_login

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
