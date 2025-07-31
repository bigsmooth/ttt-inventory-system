import streamlit as st

def require_login():
    if "user" not in st.session_state:
        st.error("Please log in to continue.")
        st.stop()

def show_header(title):
    st.markdown(f"### {title}")
