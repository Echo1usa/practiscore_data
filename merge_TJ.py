import sqlite3

correct_id = 85     # "Rizzo, TJ"
duplicate_id = 34  # "Rizzo, Thomas"

conn = sqlite3.connect("allshooters_prs.db")
cursor = conn.cursor()

# Reassign scores from duplicate to correct
cursor.execute("UPDATE scores SET shooter_id = ? WHERE shooter_id = ?", (correct_id, duplicate_id))

# Remove duplicate shooter
cursor.execute("DELETE FROM shooters WHERE shooter_id = ?", (duplicate_id,))

conn.commit()
conn.close()

print(f"✅ Merged shooter ID {duplicate_id} into {correct_id}")
