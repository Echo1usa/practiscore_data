import streamlit as st
import sqlite3
import pandas as pd

# --- Connect to DB ---
db_path = "allshooters.db"
conn = sqlite3.connect(db_path)

st.set_page_config(page_title="2025 Season Scores", layout="centered")
st.title("2025 Scores")

# --- Load aggregated shooter data ---
query = """
SELECT
    s.name AS shooter_name,
    COUNT(r.id) AS matches_shot,
    ROUND(AVG(r.percentage), 2) AS avg_percentage,
    ROUND(MAX(r.percentage), 2) AS best_percentage
FROM results r
JOIN shooters s ON r.shooter_id = s.id
GROUP BY s.id
ORDER BY avg_percentage DESC
"""

df = pd.read_sql_query(query, conn)

# --- Add Rank Column ---
df.insert(0, "Rank", range(1, len(df) + 1))

# --- Display Leaderboard ---
st.dataframe(df, use_container_width=True)

# --- Optional Highlighting ---
st.markdown("""
- 🥇 **Top 3** shooters based on average match %
- 📊 Click sidebar to view individual history
""")

conn.close()