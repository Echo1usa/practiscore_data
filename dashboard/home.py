import streamlit as st
import sqlite3
import pandas as pd

# --- Page config ---
st.set_page_config(page_title="2025 Season Scores", layout="centered")
st.title("2025 Season Scores")

# --- Connect to the database ---
db_path = "allshooters_dev.db"
conn = sqlite3.connect(db_path)

# --- Query: Get shooter stats including total points ---
query = """
SELECT
    s.name AS shooter_name,
    s.classification,
    COUNT(r.id) AS matches_shot,
    ROUND(AVG(r.percentage), 2) AS avg_percentage,
    ROUND(MAX(r.percentage), 2) AS best_percentage,
    ROUND(SUM(r.percentage), 2) AS total_points
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
df = df.reset_index(drop=True)

# --- Add Rank column ---
df.insert(0, "Rank", range(1, len(df) + 1))

# --- Optional: Filter by classification ---
class_filter = st.selectbox("Filter by classification:", options=["All", "A", "B", "C", "Unclassified"])
if class_filter != "All":
    df = df[df["classification"] == class_filter]

# --- Remove matches_shot if not needed ---
df = df.drop(columns=["matches_shot"])

# --- Rename columns for display ---
df = df.rename(columns={
    "Rank": "🏅 Rank",
    "shooter_name": "Shooter Name",
    "classification": "Class",
    "avg_percentage": "Average %",
    "best_percentage": "Best %",
    "total_points": "Total Points"
})

# --- Highlight rows by classification ---
def highlight_class(row):
    style = {
        "A": {"bg": "#1f7a1f", "fg": "white"},         # dark green
        "B": {"bg": "#997a00", "fg": "white"},         # dark yellow
        "C": {"bg": "#802626", "fg": "white"},         # dark red
        "Unclassified": {"bg": "#4d4d4d", "fg": "white"}  # dark gray
    }.get(row["Class"], {"bg": "#000000", "fg": "white"})  # changed to "Class" to match renamed column

    return [f'background-color: {style["bg"]}; color: {style["fg"]}'] * len(row)

# --- Display leaderboard ---
if df.empty:
    st.warning("No shooters found for the selected classification.")
else:
    st.dataframe(df.style.apply(highlight_class, axis=1), use_container_width=True)

# --- Footer / Info ---
st.markdown("""
- 🥇 Shooters ranked by **average match %**
- 🧮 Classification calculated from **first 3 matches**
- 📊 Filter above to compare within a class
""")

# --- Cleanup ---
conn.close()
