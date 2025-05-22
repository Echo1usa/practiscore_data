import sqlite3

# --- DB path ---
db_path = "allshooters_dev.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def classify_shooters():
    print("\n🧮 Re-classifying shooters...")

    shooter_ids = cursor.execute("SELECT id, name FROM shooters").fetchall()
    for shooter_id, name in shooter_ids:
        percentages = cursor.execute("""
            SELECT percentage
            FROM results
            WHERE shooter_id = ?
            ORDER BY match_id ASC
            LIMIT 3
        """, (shooter_id,)).fetchall()

        if len(percentages) < 3:
            classification = 'Unclassified'
        else:
            avg = sum(p[0] for p in percentages) / 3
            if avg > 87:
                classification = 'A'
            elif avg > 67:
                classification = 'B'
            else:
                classification = 'C'

        print(f"🔹 {name} => {classification}")
        cursor.execute("UPDATE shooters SET classification = ? WHERE id = ?", (classification, shooter_id))

    conn.commit()
    print("✅ Done.")

classify_shooters()
conn.close()
