
import streamlit as st
import sqlite3
import pandas as pd

# Connect to database
conn = sqlite3.connect("allshooters_prs.db")

st.title("📊 Individual Match Scores")

# --- Load shooter list ---
shooters_df = pd.read_sql_query("SELECT shooter_id, name FROM shooters ORDER BY name", conn)
shooter_name_to_id = dict(zip(shooters_df['name'], shooters_df['shooter_id']))
selected_shooter_name = st.selectbox("Select your name", shooters_df['name'])
selected_shooter_id = shooter_name_to_id[selected_shooter_name]

# --- Load match list ---
matches_df = pd.read_sql_query("SELECT match_id, match_name FROM matches ORDER BY match_date DESC", conn)
match_name_to_id = dict(zip(matches_df['match_name'], matches_df['match_id']))
selected_match_name = st.selectbox("Select a match", matches_df['match_name'])
selected_match_id = match_name_to_id[selected_match_name]

# --- Query overall scores for selected match ---
overall_query = '''
SELECT s.name AS shooter, sc.place, sc.points, sc.percentage, sh.classification
FROM scores sc
JOIN shooters s ON sc.shooter_id = s.shooter_id
JOIN shooters sh ON s.shooter_id = sh.shooter_id
WHERE sc.match_id = ?
AND sc.stage_name = "Overall"
ORDER BY sc.place ASC
'''
overall_df = pd.read_sql_query(overall_query, conn, params=(selected_match_id,))

# --- Highlight selected shooter ---
def highlight_shooter(row):
    if row['shooter'] == selected_shooter_name:
        return ['background-color: yellow'] * len(row)
    else:
        return [''] * len(row)

st.subheader("🏁 Overall Match Results")
st.dataframe(overall_df[["place", "shooter", "points", "percentage"]].style.apply(highlight_shooter, axis=1), hide_index=True, use_container_width=True)

# --- View individual stages ---
if st.checkbox("View individual stage scores"):
    # Get distinct stage names and format as "Stage 1", "Stage 2", etc.
    stage_names = pd.read_sql_query('''
        SELECT DISTINCT stage_name FROM scores
        WHERE match_id = ? AND stage_name != "Overall"
        ORDER BY stage_name
    ''', conn, params=(selected_match_id,))

    formatted_stages = [f"Stage {i+1}" for i in range(len(stage_names))]
    stage_map = dict(zip(formatted_stages, stage_names['stage_name']))
    selected_stage_label = st.selectbox("Select a stage", formatted_stages)
    selected_stage = stage_map[selected_stage_label]

    # Query stage results
    stage_query = '''
    SELECT s.name AS shooter, sc.points, sc.percentage
    FROM scores sc
    JOIN shooters s ON sc.shooter_id = s.shooter_id
    WHERE sc.match_id = ? AND sc.stage_name = ?
    ORDER BY sc.percentage DESC
    '''
    stage_df = pd.read_sql_query(stage_query, conn, params=(selected_match_id, selected_stage))

    st.subheader(f"🎯 {selected_stage_label}")
    st.dataframe(stage_df[["shooter", "points", "percentage"]].style.apply(highlight_shooter, axis=1), hide_index=True, use_container_width=True)

conn.close()
