# streamlit_app: title = "📄 Individual Results"


import streamlit as st
import sqlite3
import pandas as pd
import altair as alt

#comment

# --- Settings ---
DB_PATH = "allshooters_dev.db"

st.set_page_config(page_title="Individual Shooter Data", layout="centered")
st.title("Individual Shooter Data")

# Connect to the database
conn = sqlite3.connect(DB_PATH)

# Get list of all shooters
shooters = pd.read_sql_query("SELECT name FROM shooters ORDER BY name", conn)
shooter_names = shooters['name'].tolist()

if shooter_names:
    selected_shooter = st.selectbox("Select a shooter:", shooter_names)

    # Year filter
    year_filter = st.selectbox("Filter by year:", ["All Years", "2024", "2025"])

    # Fetch results for selected shooter
    query = """
    SELECT m.name AS match_name,
           r.place,
           r.points,
           r.percentage,
           m.match_date
    FROM results r
    JOIN matches m ON r.match_id = m.id
    JOIN shooters s ON r.shooter_id = s.id
    WHERE s.name = ?
    """
    df = pd.read_sql_query(query, conn, params=(selected_shooter,))
    df['match_date'] = pd.to_datetime(df['match_date'], errors='coerce')
    df.dropna(subset=['match_date'], inplace=True)

    # Apply year filter
    if year_filter != "All Years":
        year = int(year_filter)
        df = df[df['match_date'].dt.year == year]

    if not df.empty:
        # 📊 Stats Summary
        
        # Sort by most recent match date
        df_sorted = df.sort_values("match_date", ascending=False).head(3)

        # Get the last 3 match percentages
        recent_percentages = df_sorted["percentage"].tolist()

        # Determine classification
        if all(p >= 87 for p in recent_percentages):
            classification = "Class A"
        elif all(p >= 67 for p in recent_percentages):
            classification = "Class B"
        else:
            classification = "Class C"

        st.subheader(f"🏷️ Current Classification: **{classification}**")

        
        st.subheader("📊 Stats Summary")

        total_matches = len(df)
        avg_place = df['place'].mean()
        avg_pct = df['percentage'].mean()
        best_pct = df['percentage'].max()
        best_pts = df['points'].max()
        best_place = df['place'].min()

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

        # 📋 Match Table
        st.subheader("📋 Match Results")
        st.dataframe(df)

        # 📈 Match % Chart
        st.subheader("📈 Match % Over Time")

        df['label'] = df['match_date'].dt.strftime('%b %Y') + " – " + df['match_name']
        df['label_order'] = df['match_date']
        df.sort_values('match_date', inplace=True)

        chart = alt.Chart(df).mark_line(point=True).encode(
            x=alt.X('label:N', sort=df['label_order'].tolist(), title='Match'),
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
