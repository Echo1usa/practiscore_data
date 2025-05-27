import streamlit as st
import sqlite3
import pandas as pd

# --- Page config ---
st.set_page_config(page_title="2025 WYCO Points Leaderboard", layout="centered")
st.title("2025 WYCO Points Leaderboard")

# --- Connect to the database ---
db_path = "allshooters_dev.db"
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
AND s.is_active_member = 1
"""

df = pd.read_sql_query(query, conn)

# --- Define custom class sorting ---
class_order = {"A": 0, "B": 1, "C": 2, "Unclassified": 3}
df["class_order"] = df["classification"].map(class_order)

# --- Sort by classification first, then WYCO points ---
df = df.sort_values(by=["class_order", "wyco_points"], ascending=[True, False]).reset_index(drop=True)

# --- Add Rank column after sorting ---
df.insert(0, "Rank", range(1, len(df) + 1))

# --- Filter by classification ---
class_filter = st.selectbox("Filter by classification:", options=["All", "A", "B", "C", "Unclassified"])
if class_filter != "All":
    df = df[df["classification"] == class_filter]

# --- Highlight rows by classification with vivid and dark-mode-friendly colors ---
def highlight_class(row):
    color = {
        "A": "#3caa6a",        # green
        "B": "#eb8d3b",        # orange
        "C": "#3498db",        # blue
        "Unclassified": "#000000"  # black
    }.get(row["classification"], "#2c3e50")
    return [f'background-color: {color}; color: white'] * len(row)

# --- Display leaderboard ---
st.dataframe(df.drop(columns=["class_order"]).style.apply(highlight_class, axis=1), use_container_width=True)

# --- Footer / Info ---
st.markdown("""
- 🥇 Shooters are grouped by classification, then sorted by WYCO points  
- ✨ Finale score will be added at the end of the season  
- 📊 Filter above to compare within a class
""")

# --- Cleanup ---
conn.close()
