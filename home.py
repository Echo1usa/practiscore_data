import streamlit as st
import sqlite3
import pandas as pd

# --- Page config ---
st.set_page_config(page_title="WYCO 2025 Season Standings as of 7/26/2025", layout="centered")
st.title("WYCO 2025 Season Standings as of 7/26/2025")

# --- Connect to the database ---
db_path = "allshooters_prs.db"
conn = sqlite3.connect(db_path)

# --- Query shooter WYCO data ---
query = """
SELECT
    s.name AS shooter_name,
    s.classification,
    s.wyco_points
FROM shooters s
WHERE s.wyco_points IS NOT NULL
AND s.wyco_number IS NOT NULL
AND s.membership_active = 1
"""

df = pd.read_sql_query(query, conn)

# --- Global sort by WYCO points descending ---
df = df.sort_values(by="wyco_points", ascending=False).reset_index(drop=True)

# --- Add overall Rank column ---
df.insert(0, "Rank", range(1, len(df) + 1))

# --- Filter by classification (doesn't change sort order) ---
class_filter = st.selectbox("Filter by classification:", options=["All", "A", "B", "C", "Unclassified"])
if class_filter != "All":
    df = df[df["classification"] == class_filter].copy()

# --- Highlight rows by classification ---
def highlight_class(row):
    color = {
        "A": "#3caa6a",
        "B": "#eb8d3b",
        "C": "#3498db",
        "Unclassified": "#000000"
    }.get(row["classification"], "#2c3e50")
    return [f'background-color: {color}; color: white'] * len(row)

# --- Display leaderboard ---
st.dataframe(
    df[["Rank", "shooter_name", "classification", "wyco_points"]]
      .style.apply(highlight_class, axis=1)
      .hide(axis="index"),
    use_container_width=True
)


# --- Footer ---
st.markdown("""
- 🥇 Ranked by total WYCO points across all classes  
- 🔍 Use the filter to narrow results, but rankings reflect full leaderboard order  
- ✨ WYCO points = sum of your best score at your top 3 venues
""")

# --- Cleanup ---
conn.close()
