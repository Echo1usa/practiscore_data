import sqlite3

conn = sqlite3.connect("allshooters_v2.db")
cursor = conn.cursor()

# Add match_id column to matches table if it doesn't exist
try:
    cursor.execute("ALTER TABLE matches ADD COLUMN match_id TEXT")
    print("✅ match_id column added to matches table.")
except sqlite3.OperationalError:
    print("ℹ️ match_id column already exists.")

conn.commit()
conn.close()
