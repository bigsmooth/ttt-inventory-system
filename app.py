import streamlit as st
from auth import login_user
from views import admin_dashboard, manager_dashboard, supplier_upload, retail_inventory
from utils import require_login
import db

# Seed the warehouse data on startup (only once)
db.init_db()
db.seed_warehouses()

st.set_page_config(page_title="TTT Inventory System", layout="wide")

# Show login if no user is logged in
if "user" not in st.session_state:
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.session_state["user"] = {
                "username": username,
                "role": user["role"],
                "hubs": user["hubs"]
            }
            st.success("✅ Login successful. Loading dashboard...")
            st.rerun()  # ✅ Safe and current
        else:
            st.error("Invalid credentials")

# Show dashboard if user is logged in
if "user" in st.session_state:
    user = st.session_state["user"]
    st.sidebar.success(f"Logged in as {user['username']} ({user['role']})")

    role = user["role"]

    if role == "admin":
        admin_dashboard(user)
    elif role == "manager":
        manager_dashboard(user)
    elif role == "supplier":
        supplier_upload(user)
    elif role == "retail":
        retail_inventory(user)
    else:
        st.error("Role not recognized.")
