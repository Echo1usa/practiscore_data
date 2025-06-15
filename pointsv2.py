import sqlite3

# --- Connect to the database ---
db_path = r"C:\Practiscore\allshooters_prs.db"  # Update path if needed
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# --- Ensure required columns exist ---
try:
    cursor.execute("ALTER TABLE scores ADD COLUMN wyco_points REAL")
except sqlite3.OperationalError:
    pass

try:
    cursor.execute("ALTER TABLE shooters ADD COLUMN wyco_points REAL")
except sqlite3.OperationalError:
    pass

print("🎯 Recalculating WYCO points using 2-decimal rounding...")

# --- Step 1: Calculate WYCO points for each match ---
match_ids = cursor.execute("SELECT match_id FROM matches").fetchall()

for (match_id,) in match_ids:
    cursor.execute("""
        SELECT MAX(points)
        FROM scores
        WHERE match_id = ? AND stage_name = 'Overall'
    """, (match_id,))
    top_score = cursor.fetchone()[0]

    if not top_score or top_score == 0:
        continue

    cursor.execute("""
        SELECT score_id, points
        FROM scores
        WHERE match_id = ? AND stage_name = 'Overall'
    """, (match_id,))
    for score_id, points in cursor.fetchall():
        wyco = round((points / top_score) * 100, 2) if points else 0
        cursor.execute("UPDATE scores SET wyco_points = ? WHERE score_id = ?", (wyco, score_id))

conn.commit()
print("✅ Match-level WYCO points updated.\n")

# --- Step 2: Recalculate shooter totals from top 3 venue scores ---
print("📊 Calculating shooter totals from top 3 venue scores...")

cursor.execute("SELECT shooter_id FROM shooters WHERE wyco_number IS NOT NULL AND membership_active = 1")
shooter_ids = [row[0] for row in cursor.fetchall()]

for shooter_id in shooter_ids:
    cursor.execute("""
        SELECT m.venue_id, MAX(s.wyco_points)
        FROM scores s
        JOIN matches m ON s.match_id = m.match_id
        WHERE s.shooter_id = ? AND s.stage_name = 'Overall' AND m.venue_id IS NOT NULL
        GROUP BY m.venue_id
    """, (shooter_id,))
    top_scores = [row[1] for row in cursor.fetchall() if row[1] is not None]
    top_3 = sorted(top_scores, reverse=True)[:3]
    total = round(sum(top_3), 2)
    cursor.execute("UPDATE shooters SET wyco_points = ? WHERE shooter_id = ?", (total, shooter_id))

conn.commit()
conn.close()
print("🏁 Shooter WYCO totals recalculated successfully.")
