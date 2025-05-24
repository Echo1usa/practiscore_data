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

# --- Filter by Classification ---
class_filter = st.selectbox(
    "Filter by classification:", 
    options=["All"] + sorted(df["classification"].dropna().unique())
)
if class_filter != "All":
    df = df[df["classification"] == class_filter]

# --- Highlight Rows by Classification ---
def highlight_class(row):
    color = {
        "A": "#d4f4dd",        # light green
        "B": "#fff6b3",        # light yellow
        "C": "#ffe5e5",        # light red
        "Unclassified": "#e0e0e0"  # light gray
    }.get(row["classification"], "#ffffff")
    return ['background-color: {}'.format(color)] * len(row)

# --- Display Leaderboard ---
st.dataframe(df.style.apply(highlight_class, axis=1), use_container_width=True)

# --- Footer Info ---
st.markdown("""
- 🥇 Rankings are based on the sum of a shooter's top 3 venue scores  
- ✨ Finale score will be added at the end of the season  
- 📊 Use classification to track development tiers
""")

conn.close()
