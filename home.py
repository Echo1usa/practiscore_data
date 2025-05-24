import streamlit as st
import sqlite3
import pandas as pd

# --- Connect to DB ---
db_path = "allshooters_dev.db"
conn = sqlite3.connect(db_path)

st.set_page_config(page_title="2025 Season Scores", layout="centered")
st.title("2025 WYCO Points Leaderboard")

# --- Load shooter WYCO scores ---
query = """
SELECT
    s.name AS shooter_name,
    s.classification,
    s.wyco_points
FROM shooters s
WHERE s.wyco_points IS NOT NULL
ORDER BY s.wyco_points DESC
"""

df = pd.read_sql_query(query, conn)

# --- Add Rank Column ---
df.insert(0, "Rank", range(1, len(df) + 1))

# --- Display Leaderboard ---
st.dataframe(df.reset_index(drop=True), use_container_width=True)

# --- Footer Info ---
st.markdown("""
- 🥇 Rankings are based on the sum of a shooter's top 3 venue scores
- ✨ Finale score will be added at the end of the season
- 📊 Use classification to track development tiers
""")

conn.close()
