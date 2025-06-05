import sqlite3

DB_PATH = "allshooters_prs.db"

# Connect to the database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create the achievements table
cursor.execute("""
CREATE TABLE IF NOT EXISTS achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    shooter_id INTEGER,
    match_id INTEGER,
    achievement TEXT,
    date_awarded TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(shooter_id, match_id, achievement)
)
""")

conn.commit()
conn.close()

print("✅ Achievements table created.")
