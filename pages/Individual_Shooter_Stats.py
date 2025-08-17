import streamlit as st
import sqlite3
import pandas as pd
import altair as alt

# --- Settings ---
DB_PATH = "allshooters_prs.db"

st.set_page_config(page_title="Individual Shooter Data", layout="centered")
st.title("Individual Shooter Data")

# Connect to the database
conn = sqlite3.connect(DB_PATH)

# Get list of all shooters
shooters = pd.read_sql_query("SELECT name FROM shooters ORDER BY name", conn)
shooter_names = shooters['name'].tolist()

if shooter_names:
    selected_shooter = st.selectbox("Select a shooter:", shooter_names)
    year_filter = st.selectbox("Filter by year:", ["All Years", "2024", "2025"])

    # Fetch shooter's classification and WYCO points
    meta_query = """
    SELECT classification, wyco_points
    FROM shooters
    WHERE name = ?
    """
    meta = pd.read_sql_query(meta_query, conn, params=(selected_shooter,))
    classification = meta['classification'].fillna("Unclassified").iloc[0]
    wyco_points = meta['wyco_points'].fillna(0).iloc[0]

    st.subheader(f"🏷️ Classification: **{classification}**")
    st.markdown(f"💯 **WYCO Points:** {wyco_points}")

    # Fetch match results (only Overall)
    results_query = """
    SELECT m.match_name,
           sc.place,
           sc.points,
           sc.percentage,
           sc.wyco_points,
           m.match_date
    FROM scores sc
    JOIN matches m ON sc.match_id = m.match_id
    JOIN shooters s ON sc.shooter_id = s.shooter_id
    WHERE s.name = ?
    AND sc.stage_name = "Overall"
    """
    df = pd.read_sql_query(results_query, conn, params=(selected_shooter,))
    df['match_date'] = pd.to_datetime(df['match_date'], errors='coerce')
    df.dropna(subset=['match_date'], inplace=True)

    # Ignore zero scores
    df = df[(df['percentage'] > 0) & (df['points'] > 0)]

    df.sort_values("match_date", inplace=True)

    if year_filter != "All Years":
        df = df[df['match_date'].dt.year == int(year_filter)]

    if not df.empty:
        # --- Stats Summary ---
        st.subheader("📊 Stats Summary")

        total_matches = len(df)
        avg_place = df['place'].mean()
        avg_pct = df['percentage'].mean()
        best_pct_match = df.loc[df['percentage'].idxmax()]
        best_pts_match = df.loc[df['points'].idxmax()]
        best_place_match = df.loc[df['place'].idxmin()]

        st.markdown(f"""
        - 🏁 **Total Matches:** {total_matches}
        - 🧮 **Average Match %:** {avg_pct:.2f}%
        - 📉 **Average Placement:** {avg_place:.1f}
        - 🏆 **Best Match %:** {best_pct_match['percentage']:.2f}% — *{best_pct_match['match_name']}*
        - 🧨 **Best Points Earned:** {best_pts_match['points']} — *{best_pts_match['match_name']}*
        - 🥇 **Best Placement:** {best_place_match['place']} — *{best_place_match['match_name']}*
        """)

        if df['wyco_points'].notna().any():
            best_wyco = df.loc[df['wyco_points'].idxmax()]
            st.markdown(f"- 🏅 **Best WYCO Points:** {best_wyco['wyco_points']} — *{best_wyco['match_name']}*")

        # --- Match Table ---
        st.subheader("📋 Match Results")
        st.dataframe(df[["match_date", "match_name", "place", "points", "percentage", "wyco_points"]],
                     hide_index=True, use_container_width=True)

        # --- Match % Chart ---
        st.subheader("📈 Match % Over Time")
        df['label'] = df['match_date'].dt.strftime('%b %Y') + " – " + df['match_name']
        chart = alt.Chart(df).mark_line(point=True).encode(
            x=alt.X('label:N', sort=df['match_date'].tolist(), title='Match'),
            y=alt.Y('percentage:Q', title='Match %'),
            tooltip=[
                alt.Tooltip('match_name:N', title='Match'),
                alt.Tooltip('match_date:T', title='Date'),
                alt.Tooltip('percentage:Q', title='Match %')
            ]
        ).properties(width=800, height=400)

        st.altair_chart(chart, use_container_width=True)

    else:
        st.info("No results found for this shooter in selected year.")
else:
    st.warning("No shooters found in the database.")

conn.close()
