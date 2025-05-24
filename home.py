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
ORDER BY s.wyco_points DESC
"""

df = pd.read_sql_query(query, conn)

# --- Add Rank column ---
df.insert(0, "Rank", range(1, len(df) + 1))

# --- Filter by classification ---
class_filter = st.selectbox("Filter by classification:", options=["All", "A", "B", "C", "Unclassified"])
if class_filter != "All":
    df = df[df["classification"] == class_filter]

# --- Highlight rows by classification with vivid dark-mode-friendly colors ---
def highlight_class(row):
    style = {
        "A": {"bg": "#1f7a1f", "fg": "white"},
        "B": {"bg": "#eb6434", "fg": "white"},
        "C": {"bg": "#3483eb", "fg": "white"},
        "Unclassified": {"bg": "#4d4d4d", "fg": "white"}
    }.get(row["Class"], {"bg": "#000000", "fg": "white"})

    return [f'background-color: {style["bg"]}; color: {style["fg"]}'] * len(row)

# --- Set 🏅 Rank as index to remove extra column ---
df = df.set_index("🏅 Rank")

# --- Display leaderboard ---
st.dataframe(df.style.apply(highlight_class, axis=1), use_container_width=True)

# --- Footer / Info ---
st.markdown("""
- 🥇 Rankings are based on the sum of a shooter's top 3 venue scores  
- ✨ Finale score will be added at the end of the season  
- 📊 Filter above to compare within a class
""")

# --- Cleanup ---
conn.close()
