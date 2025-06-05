import sqlite3
import pandas as pd

DB_PATH = "allshooters_prs.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Load scores and matches
scores = pd.read_sql_query("SELECT * FROM scores WHERE stage_name = 'Overall'", conn)
matches = pd.read_sql_query("SELECT match_id, match_date FROM matches", conn)

# Merge match date
scores = scores.merge(matches, on="match_id", how="left")
scores["match_month"] = pd.to_datetime(scores["match_date"]).dt.to_period("M")

earned = []

# 🥇 Top Gun
top_guns = scores[scores["place"] == 1]
for _, row in top_guns.iterrows():
    earned.append((row["shooter_id"], row["match_id"], "🥇 Top Gun"))

# 😬 Well, you tried...
tried = scores[(scores["percentage"] > 0) & (scores["percentage"] < 20)]
for _, row in tried.iterrows():
    earned.append((row["shooter_id"], row["match_id"], "😬 Well, you tried..."))

# 🎯 Threesome
grouped = scores.groupby(["shooter_id", "match_month"]).size().reset_index(name="count")
threesomes = grouped[grouped["count"] >= 3]

for _, row in threesomes.iterrows():
    sid = row["shooter_id"]
    month = row["match_month"]
    matched = scores[(scores["shooter_id"] == sid) & (scores["match_month"] == month)]
    for _, r in matched.iterrows():
        earned.append((r["shooter_id"], r["match_id"], "🎯 Threesome"))

# Insert into achievements table
cursor.executemany("""
    INSERT OR IGNORE INTO achievements (shooter_id, match_id, achievement)
    VALUES (?, ?, ?)
""", earned)

conn.commit()
conn.close()

print(f"✅ {len(earned)} achievements awarded and stored.")
