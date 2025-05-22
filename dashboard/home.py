import streamlit as st
import sqlite3
import pandas as pd

# --- Connect to DB ---
db_path = "allshooters.db"
conn = sqlite3.connect(db_path)

st.set_page_config(page_title="2025 Season Scores", layout="centered")
st.title("2025 Season Scores")

# --- Load aggregated shooter data ---
query = """
SELECT
    s.name AS shooter_name,
    s.classification,
    COUNT(r.id) AS matches_shot,
    ROUND(AVG(r.percentage), 2) AS avg_percentage,
    ROUND(MAX(r.percentage), 2) AS best_percentage
FROM
    shooters s
JOIN 
    results r ON s.id = r.shooter_id
GROUP BY 
    s.id
ORDER BY 
    avg_percentage DESC
"""

df = pd.read_sql_query(query, conn)

# --- Add Rank Column ---
df.insert(0, "Rank", range(1, len(df) + 1))

# --- Remove unwanted column ---
df = df.drop(columns=['matches_shot'])

# --- Display Leaderboard ---
st.dataframe(df.reset_index(drop=True), use_container_width=True)

# --- Optional Highlighting ---
st.markdown

