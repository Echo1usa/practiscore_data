import streamlit as st
import sqlite3
import pandas as pd

# --- Page config ---
st.set_page_config(page_title="WYCO 2025 Season Standings as of 7/19/2025", layout="centered")
st.title("WYCO 2025 Season Standings as of 7/19/2025  THIS IS THE DEV BRANCH")

# --- Connect to the database ---
db_path = "allshooters_prs.db"
conn = sqlite3.connect(db_path)

# --- Venue ID to Name Mapping ---
venue_names = {
    1: "Cheyenne",
    2: "Laramie",
    3: "Pawnee",
    4: "Larkspur",
    5: "Rawlins"
}

# --- Query base shooter data ---
query_base = """
SELECT
    s.shooter_id,
    s.name AS shooter_name,
    s.classification,
    s.wyco_points
FROM shooters s
WHERE s.wyco_points IS NOT NULL
AND s.wyco_number IS NOT NULL
AND s.membership_active = 1
"""
df = pd.read_sql_query(query_base, conn)

# --- Query top score per shooter per venue ---
query_scores = """
SELECT
    sc.shooter_id,
    m.venue_id,
    MAX(sc.percentage) AS top_score
FROM scores sc
JOIN matches m ON sc.match_id = m.match_id
GROUP BY sc.shooter_id, m.venue_id
"""
venue_scores = pd.read_sql_query(query_scores, conn)

# --- Pivot venue scores to wide format ---
venue_wide = venue_scores.pivot(index="shooter_id", columns="venue_id", values="top_score")
venue_wide.rename(columns={vid: f"Top {vname}" for vid, vname in venue_names.items()}, inplace=True)
venue_wide.reset_index(inplace=True)

# --- Merge with leaderboard ---
df = df.merge(venue_wide, on="shooter_id", how="left")

# --- Ensure all expected venue columns exist ---
expected_venue_cols = [f"Top {v}" for v in venue_names.values()]
for col in expected_venue_cols:
    if col not in df.columns:
        df[col] = None

# --- Sort by WYCO points ---
df = df.sort_values(by="wyco_points", ascending=False).reset_index(drop=True)

# --- Add Rank column ---
df.insert(0, "Rank", range(1, len(df) + 1))

# --- Filter by classification ---
class_filter = st.selectbox("Filter by classification:", options=["All", "A", "B", "C", "Unclassified"])
if class_filter != "All":
    df = df[df["classification"] == class_filter].copy()

# --- Highlight by classification ---
def highlight_class(row):
    color = {
        "A": "#3caa6a",
        "B": "#eb8d3b",
        "C": "#3498db",
        "Unclassified": "#000000"
    }.get(row["classification"], "#2c3e50")
    return [f'background-color: {color}; color: white'] * len(row)

# --- Display leaderboard without index column ---
core_cols = ["Rank", "shooter_name", "classification", "wyco_points"]
display_cols = core_cols + expected_venue_cols
styled_df = df[display_cols].reset_index(drop=True)

styled = styled_df.style.apply(highlight_class, axis=1)

st.dataframe(styled, use_container_width=True, hide_index=True)

# --- Footer ---
st.markdown("""
- 🥇 Ranked by total WYCO points across all classes  
- 📍 View each shooter’s top percentage score from each venue  
- 🔍 Use the filter to narrow results, but rankings reflect full leaderboard order  
- ✨ WYCO points = sum of your best score at your top 3 venues
""")

# --- Cleanup ---
conn.close()
