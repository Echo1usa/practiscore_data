import streamlit as st
import sqlite3
import pandas as pd
import subprocess

# --- Page config ---
st.set_page_config(page_title="WYCO Admin Panel", layout="wide")
st.title("🔧 WYCO Admin Dashboard")

# --- Admin Authentication (Basic) ---
PASSWORD = "letmein123"  # Replace with secure password or use st.secrets
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.text_input("Enter admin password", type="password")
    if password == PASSWORD:
        st.session_state.authenticated = True
        st.rerun()
    else:
        st.stop()

# --- Connect to the database ---
db_path = "allshooters_prs.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# --- Shooter editor ---
st.subheader("🧑 Shooter Management")
cursor.execute("SELECT shooter_id, name, wyco_number, classification, membership_active FROM shooters ORDER BY name")
data = cursor.fetchall()
df = pd.DataFrame(data, columns=["ID", "Name", "WYCO Number", "Classification", "Active Member"])

selected = st.selectbox("Select a shooter to edit:", options=df["Name"])
selected_row = df[df["Name"] == selected].iloc[0]

new_wyco = st.text_input("WYCO Number", value=selected_row["WYCO Number"] or "")
new_class = st.selectbox("Classification", ["", "A", "B", "C", "Unclassified"], index=["", "A", "B", "C", "Unclassified"].index(selected_row["Classification"] or ""))
new_active = st.checkbox("Active Member", value=bool(selected_row["Active Member"]))

if st.button("💾 Save Shooter Info"):
    cursor.execute("""
        UPDATE shooters SET wyco_number = ?, classification = ?, membership_active = ?
        WHERE shooter_id = ?
    """, (new_wyco or None, new_class or None, int(new_active), selected_row["ID"]))
    conn.commit()
    st.success("Shooter info updated.")

# --- Admin Scripts ---
st.subheader("🧮 Scoring & Classification Tools")
col1, col2 = st.columns(2)

with col1:
    if st.button("🔁 Recalculate WYCO Points"):
        try:
            subprocess.run(["python", "calculate_wyco_points.py"], check=True)
            st.success("WYCO points recalculated.")
        except subprocess.CalledProcessError:
            st.error("Failed to run WYCO points script.")

with col2:
    if st.button("🎯 Reclassify Shooters"):
        try:
            subprocess.run(["python", "classify_shooters.py"], check=True)
            st.success("Shooters reclassified.")
        except subprocess.CalledProcessError:
            st.error("Failed to run classification script.")

conn.close()
