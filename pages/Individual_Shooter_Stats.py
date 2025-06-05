import streamlit as st
import sqlite3
import pandas as pd
import altair as alt

# --- Settings ---
DB_PATH = "allshooters_prs.db"

st.set_page_config(page_title="Individual Shooter Data", layout="centered")
st.title("Individual Shooter Data")

# Connect to DB
conn = sqlite3.connect(DB_PATH)

# Load shooter list
shooters = pd.read_sql_query("SELECT name FROM shooters ORDER BY name", conn)
shooter_names = shooters['name'].tolist()

# --- Achievement descriptions ---
achievement_info = {
    "🥇 Top Gun": "Placed 1st overall in a match",
    "🎯 Threesome": "Shot 3 or more matches in the same month",
    "😬 Well, you tried...": "Scored between 0% and 20% in a match"
}

if shooter_names:
    selected_shooter = st.selectbox("Select a shooter:", shooter_names)
    year_filter = st.selectbox("Filter by year:", ["All Years", "2024", "2025"])

    # Get shooter metadata
    meta = pd.read_sql_query("""
        SELECT classification, wyco_points
        FROM shooters WHERE name = ?
    """, conn, params=(selected_shooter,))
    classification = meta['classification'].fillna("Unclassified").iloc[0]
    wyco_points = meta['wyco_points'].fillna(0).iloc[0]

    st.subheader(f"🏷️ Classification: **{classification}**")
    st.markdown(f"💯 **WYCO Points:** {wyco_points}")

    # Class Rank
    rank_query = """
    SELECT s.name AS shooter_name,
           s.classification,
           SUM(sc.wyco_points) AS total_points
    FROM scores sc
    JOIN shooters s ON sc.shooter_id = s.shooter_id
    WHERE sc.stage_name = "Overall"
    GROUP BY s.name, s.classification
    """
    ranks_df = pd.read_sql_query(rank_query, conn)
    ranks_df['class_rank'] = ranks_df.groupby('classification')['total_points'].rank(method='dense', ascending=False)

    shooter_row = ranks_df[ranks_df['shooter_name'] == selected_shooter]
    if not shooter_row.empty:
        class_rank = int(shooter_row['class_rank'].iloc[0])
        total_in_class = ranks_df[ranks_df['classification'] == classification].shape[0]
        st.markdown(f"📊 You are currently **#{class_rank}** out of **{total_in_class}** in **{classification or 'Unclassified'}** class.")

    # Match results
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
    df.sort_values("match_date", inplace=True)

    if year_filter != "All Years":
        df = df[df['match_date'].dt.year == int(year_filter)]

    if not df.empty:
        # Stats summary
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

        # Match Table
        st.subheader("📋 Match Results")
        st.dataframe(df[["match_date", "match_name", "place", "points", "percentage", "wyco_points"]],
                     hide_index=True, use_container_width=True)

        # Chart with trend
        st.subheader("📈 Match % Over Time")
        show_trend = st.checkbox("Show trend line")

        df['match_label'] = df['match_name'] + ' ' + df['match_date'].dt.strftime('%b%Y')

        base = alt.Chart(df).mark_line(point=True).encode(
            x=alt.X('match_label:N', title='Match', sort=df['match_date'].tolist(), axis=alt.Axis(labelAngle=-45)),
            y=alt.Y('percentage:Q', title='Match %'),
            tooltip=[
                alt.Tooltip('match_name:N', title='Match'),
                alt.Tooltip('match_date:T', title='Date'),
                alt.Tooltip('percentage:Q', title='Match %')
            ]
        ).properties(width=800, height=400)

        if show_trend:
            trend = alt.Chart(df).transform_regression('match_date', 'percentage').mark_line(color='orange').encode(
                x='match_date:T',
                y='percentage:Q'
            )
            st.altair_chart(base + trend, use_container_width=True)
        else:
            st.altair_chart(base, use_container_width=True)

        # --- Achievements Badge Board ---
        st.subheader("🏅 Achievements Unlocked")

        achievements_query = """
        SELECT a.achievement, m.match_name, m.match_date
        FROM achievements a
        JOIN matches m ON a.match_id = m.match_id
        WHERE a.shooter_id = (
            SELECT shooter_id FROM shooters WHERE name = ?
        )
        ORDER BY m.match_date DESC
        """
        achievements_df = pd.read_sql_query(achievements_query, conn, params=(selected_shooter,))

        if achievements_df.empty:
            st.info("No achievements yet. Keep shooting!")
        else:
            for _, row in achievements_df.iterrows():
                desc = achievement_info.get(row['achievement'], "Achievement unlocked!")
                date_str = pd.to_datetime(row['match_date']).strftime('%b %d, %Y')
                st.markdown(
                    f"- **{row['achievement']}** — *{row['match_name']}* on `{date_str}`  \n"
                    f"  <span style='color:gray;font-size:0.9em;'>{desc}</span>",
                    unsafe_allow_html=True
                )

    else:
        st.info("No results found for this shooter in selected year.")
else:
    st.warning("No shooters found in the database.")

conn.close()
