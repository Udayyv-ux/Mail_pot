import streamlit as st
import requests
import time

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Auto Email Tool", layout="wide")

st.markdown("""
    <style>
    .main { padding-top: 2rem; }
    h1 { font-weight: 300; color: #1f2937; margin-bottom: 0.2rem; }
    h3 { font-weight: 400; color: #374151; margin-top: 1.5rem; }
    .stButton>button { border-radius: 4px; font-weight: 500; }
    [data-testid="metric-container"] { background-color: #f9fafb; border-radius: 8px; padding: 15px; border: 1px solid #e5e7eb; }
    </style>
""", unsafe_allow_html=True)

st.title("Auto Email Tool")
st.markdown("---")

is_connected = False
try:
    response = requests.get(f"{API_URL}/status")
    if response.status_code == 200:
        data = response.json()
        is_running = data.get("is_running", False)
        emails_sent = data.get("emails_sent_today", 0)
        is_connected = True
except:
    is_running = False
    emails_sent = 0
    st.error("Backend server is offline. Please ensure Terminal 1 is running.")

col1, col2, col3 = st.columns(3)
col1.metric("Bot Status", "Running" if is_running else "Stopped")
col2.metric("Emails Sent Today", emails_sent)
col3.metric("System Health", "Connected" if is_connected else "Disconnected")

# --- DATA SOURCE (NEW) ---
st.subheader("Data Source")
if is_connected:
    try:
        config = requests.get(f"{API_URL}/config").json()
        current_sheet = config.get("sheet_id", "")
    except:
        current_sheet = ""

    with st.expander("Configure Google Sheet Link", expanded=(not current_sheet)):
        if current_sheet:
            st.success("Currently connected to a Google Sheet.")
            st.caption(f"Sheet ID: {current_sheet}")
        
        with st.form("sheet_config_form"):
            new_sheet_link = st.text_input("Paste Full Google Sheet Link Here:")
            if st.form_submit_button("Update Data Source"):
                if new_sheet_link:
                    requests.post(f"{API_URL}/config/sheet", json={"sheet_link": new_sheet_link})
                    st.toast("Data Source Updated Successfully!")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("Please enter a link.")

# --- ENGINE CONTROLS ---
st.subheader("Engine Controls")
if is_connected:
    if is_running:
        if st.button("Stop Automation", type="primary"):
            requests.post(f"{API_URL}/stop")
            st.rerun()
    else:
        if current_sheet:
            if st.button("Start Automation", type="primary"):
                requests.post(f"{API_URL}/start")
                st.rerun()
        else:
            st.warning("Please configure your Google Sheet link above before starting the bot.")

# --- TEMPLATE MANAGER ---
st.subheader("Template Manager")
if is_connected:
    try:
        templates = requests.get(f"{API_URL}/templates").json()
        st.markdown("**Active Projects**")
        if not templates:
            st.info("No templates saved yet.")
        else:
            for proj_id, details in templates.items():
                col_text, col_btn = st.columns([4, 1])
                with col_text:
                    st.markdown(f"**{proj_id}**<br><span style='color: #6b7280; font-size: 0.9em;'>Subject: {details['subject']}</span>", unsafe_allow_html=True)
                with col_btn:
                    if st.button("Delete", key=f"del_{proj_id}"):
                        requests.delete(f"{API_URL}/templates/{proj_id}")
                        st.rerun()
                st.divider()
    except:
        st.warning("Could not load templates.")

    with st.form("new_template_form", clear_on_submit=True):
        st.markdown("**Add New Template**")
        new_project_id = st.text_input("Project ID (e.g., Real estate , Kukatpally)")
        new_subject = st.text_input("Email Subject Line")
        new_html_body = st.text_area("HTML Email Body", height=200)
        
        if st.form_submit_button("Save Template"):
            if new_project_id and new_subject and new_html_body:
                requests.post(f"{API_URL}/templates", json={"project_id": new_project_id, "subject": new_subject, "body": new_html_body})
                time.sleep(0.5)
                st.rerun()

st.subheader("Live Monitor")
live_sync = st.toggle("Enable Live Sync")
if live_sync and is_connected:
    with st.spinner("Listening for new emails..."):
        time.sleep(2) 
        st.rerun()