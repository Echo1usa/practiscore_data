import sqlite3

# --- Connect to the database ---
db_path = "allshooters_dev.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# --- Ensure wyco_points column exists ---
try:
    cursor.execute("ALTER TABLE shooters ADD COLUMN wyco_points REAL")
except sqlite3.OperationalError:
    pass

# --- Step 1: Gather top WYCO score per venue per shooter ---
cursor.execute("""
    SELECT s.id AS shooter_id, m.venue_id, MAX(r.wyco_points) AS best_venue_score
    FROM results r
    JOIN matches m ON r.match_id = m.id
    JOIN shooters s ON r.shooter_id = s.id
    WHERE r.wyco_points IS NOT NULL AND m.venue_id IS NOT NULL
    GROUP BY s.id, m.venue_id
""")

from collections import defaultdict

shooter_venue_scores = defaultdict(list)

for shooter_id, venue_id, score in cursor.fetchall():
    shooter_venue_scores[shooter_id].append(score)

# --- Step 2: For each shooter, sum their top 3 venue scores ---
for shooter_id, scores in shooter_venue_scores.items():
    top_three = sorted(scores, reverse=True)[:3]
    total = round(sum(top_three), 3)
    cursor.execute("UPDATE shooters SET wyco_points = ? WHERE id = ?", (total, shooter_id))

conn.commit()
conn.close()
print("\n✅ WYCO totals calculated and stored in shooters.wyco_points")
