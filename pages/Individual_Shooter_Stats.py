import streamlit as st
import sqlite3
import pandas as pd
import altair as alt
from contextlib import closing

# --- Settings ---
DB_PATH = "allshooters_prs.db"

st.set_page_config(page_title="Individual Shooter Data", layout="centered")
st.title("Individual Shooter Data")

# ---------- Data access (cached) ----------
@st.cache_data(show_spinner=False)
def get_all_shooters(db_path: str) -> list[str]:
    with closing(sqlite3.connect(db_path)) as conn:
        df = pd.read_sql_query(
            "SELECT name FROM shooters ORDER BY name COLLATE NOCASE", conn
        )
    return df["name"].tolist()

@st.cache_data(show_spinner=False)
def get_shooter_meta(db_path: str, name: str) -> tuple[str, float]:
    with closing(sqlite3.connect(db_path)) as conn:
        meta = pd.read_sql_query(
            """
            SELECT classification, wyco_points
            FROM shooters
            WHERE name = ?
            """,
            conn,
            params=(name,),
        )
    if meta.empty:
        return "Unclassified", 0.0
    classification = meta["classification"].fillna("Unclassified").iloc[0]
    wyco_points = float(meta["wyco_points"].fillna(0).iloc[0])
    return classification, wyco_points

@st.cache_data(show_spinner=False)
def get_shooter_results(db_path: str, name: str) -> pd.DataFrame:
    with closing(sqlite3.connect(db_path)) as conn:
        df = pd.read_sql_query(
            """
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
              AND sc.stage_name = 'Overall'
            """,
            conn,
            params=(name,),
        )

    # Clean + types
    df["match_date"] = pd.to_datetime(df["match_date"], errors="coerce")
    df = df.dropna(subset=["match_date"]).copy()
    for col in ["place", "points", "percentage", "wyco_points"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    # Ignore zero scores (percentage or points)
    df = df[(df["percentage"] > 0) & (df["points"] > 0)]

    df.sort_values("match_date", inplace=True)
    return df

# ---------- UI ----------
shooter_names = get_all_shooters(DB_PATH)

if not shooter_names:
    st.warning("No shooters found in the database.")
    st.stop()

selected_shooter = st.selectbox("Select a shooter:", shooter_names)

# Pull all results up front so the year list reflects actual data for this shooter
all_results = get_shooter_results(DB_PATH, selected_shooter)

if all_results.empty:
    st.info("No results found for this shooter.")
    st.stop()

available_years = (
    all_results["match_date"].dt.year.dropna().astype(int).sort_values().unique().tolist()
)
year_options = ["All Years"] + [str(y) for y in available_years]
year_filter = st.selectbox("Filter by year:", year_options, index=0)

# Apply year filter without losing original
if year_filter != "All Years":
    df = all_results[all_results["match_date"].dt.year == int(year_filter)].copy()
else:
    df = all_results.copy()

classification, wyco_points_total = get_shooter_meta(DB_PATH, selected_shooter)

st.subheader(f"🏷️ Classification: **{classification}**")
st.markdown(f"💯 **WYCO Points:** {wyco_points_total}")

if df.empty:
    st.info("No results found for this shooter in selected year.")
    st.stop()

# ---------- Stats Summary ----------
st.subheader("📊 Stats Summary")

total_matches = len(df)
avg_place = df["place"].mean() if df["place"].notna().any() else float("nan")
avg_pct = df["percentage"].mean() if df["percentage"].notna().any() else float("nan")

best_pct_match = df.loc[df["percentage"].idxmax()] if df["percentage"].notna().any() else None
best_pts_match = df.loc[df["points"].idxmax()] if df["points"].notna().any() else None
best_place_match = df.loc[df["place"].idxmin()] if df["place"].notna().any() else None

summary_lines = [
    f"- 🏁 **Total Matches:** {total_matches}",
]
if pd.notna(avg_pct):
    summary_lines.append(f"- 🧮 **Average Match %:** {avg_pct:.2f}%")
if pd.notna(avg_place):
    summary_lines.append(f"- 📉 **Average Placement:** {avg_place:.1f}")
if best_pct_match is not None:
    summary_lines.append(
        f"- 🏆 **Best Match %:** {best_pct_match['percentage']:.2f}% — *{best_pct_match['match_name']}*"
    )
if best_pts_match is not None:
    summary_lines.append(
        f"- 🧨 **Best Points Earned:** {best_pts_match['points']:.2f} — *{best_pts_match['match_name']}*"
    )
if best_place_match is not None:
    summary_lines.append(
        f"- 🥇 **Best Placement:** {int(best_place_match['place'])} — *{best_place_match['match_name']}*"
    )
if df["wyco_points"].notna().any():
    best_wyco = df.loc[df["wyco_points"].idxmax()]
    summary_lines.append(
        f"- 🏅 **Best WYCO Points:** {best_wyco['wyco_points']:.2f} — *{best_wyco['match_name']}*"
    )

st.markdown("\n".join(summary_lines))

# ---------- Match Table ----------
st.subheader("📋 Match Results")

# Friendly column names + formatting
show_df = df[
    ["match_date", "match_name", "place", "points", "percentage", "wyco_points"]
].rename(
    columns={
        "match_date": "Date",
        "match_name": "Match",
        "place": "Place",
        "points": "Points",
        "percentage": "Match %",
        "wyco_points": "WYCO",
    }
)

st.dataframe(
    show_df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Date": st.column_config.DateColumn(format="YYYY-MM-DD"),
        "Place": st.column_config.NumberColumn(format="%d"),
        "Points": st.column_config.NumberColumn(format="%.2f"),
        "Match %": st.column_config.NumberColumn(format="%.2f"),
        "WYCO": st.column_config.NumberColumn(format="%.2f"),
    },
)

# Download
csv_bytes = show_df.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇️ Download results as CSV",
    data=csv_bytes,
    file_name=f"{selected_shooter.replace(' ', '_').lower()}_results.csv",
    mime="text/csv",
)

# ---------- Charts ----------
st.subheader("📈 Match % Over Time")

pct_chart = (
    alt.Chart(df)
    .mark_line(point=True)
    .encode(
        x=alt.X("match_date:T", title="Date"),
        y=alt.Y("percentage:Q", title="Match %"),
        tooltip=[
            alt.Tooltip("match_name:N", title="Match"),
            alt.Tooltip("match_date:T", title="Date"),
            alt.Tooltip("percentage:Q", title="Match %"),
        ],
    )
    .properties(height=400)
)

st.altair_chart(pct_chart, use_container_width=True)

# Optional: cumulative WYCO points
if df["wyco_points"].notna().any():
    st.subheader("🏅 Cumulative WYCO Points")
    df2 = df.copy()
    df2["wyco_points"] = df2["wyco_points"].fillna(0)
    df2["cum_wyco"] = df2["wyco_points"].cumsum()

    wyco_chart = (
        alt.Chart(df2)
        .mark_line(point=True)
        .encode(
            x=alt.X("match_date:T", title="Date"),
            y=alt.Y("cum_wyco:Q", title="Cumulative WYCO"),
            tooltip=[
                alt.Tooltip("match_name:N", title="Match"),
                alt.Tooltip("match_date:T", title="Date"),
                alt.Tooltip("cum_wyco:Q", title="Cumulative WYCO"),
            ],
        )
        .properties(height=300)
    )
    st.altair_chart(wyco_chart, use_container_width=True)
