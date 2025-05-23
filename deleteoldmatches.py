import sqlite3

# --- Connect to the development database ---
db_path = "allshooters_dev.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# --- Step 1: Find matches before April 2025 ---
cursor.execute("""
    SELECT id, name, match_date FROM matches
    WHERE match_date < '2025-04-01'
""")
old_matches = cursor.fetchall()

print(f"🗑️ Deleting {len(old_matches)} match(es) before April 2025:")

# --- Step 2: Delete related results and the matches themselves ---
for match_id, name, match_date in old_matches:
    print(f" - {name} ({match_date})")

    # Delete associated results
    cursor.execute("DELETE FROM results WHERE match_id = ?", (match_id,))
    
    # Optional: Also delete from stage_results if used
    #cursor.execute("DELETE FROM stage_results WHERE match_id = ?", (match_id,))

    # Delete match entry
    cursor.execute("DELETE FROM matches WHERE id = ?", (match_id,))

conn.commit()
conn.close()

print("✅ Cleanup complete.")
