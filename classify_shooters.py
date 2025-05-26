import sqlite3

# --- Connect to the development database ---
db_path = "allshooters_dev.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# --- Ensure wyco_points column exists ---
try:
    cursor.execute("ALTER TABLE results ADD COLUMN wyco_points REAL")
except sqlite3.OperationalError:
    pass  # Column already exists

# Define classification thresholds
A_THRESHOLD = 87.0
B_THRESHOLD = 67.0

# Define class ranks for comparison
class_rank = {"Unclassified": 0, "C": 1, "B": 2, "A": 3}

def calculate_wyco_points():
    print("\n🎯 Calculating WYCO points...")

    match_ids = cursor.execute("SELECT id FROM matches").fetchall()
    for (match_id,) in match_ids:
        cursor.execute("""
            SELECT MAX(points) FROM results
            WHERE match_id = ?
        """, (match_id,))
        max_points = cursor.fetchone()[0]

        if not max_points or max_points == 0:
            continue  # avoid divide by zero

        cursor.execute("""
            SELECT id, points FROM results
            WHERE match_id = ?
        """, (match_id,))
        for result_id, points in cursor.fetchall():
            wyco = round((points / max_points) * 100, 3)
            cursor.execute("UPDATE results SET wyco_points = ? WHERE id = ?", (wyco, result_id))

    conn.commit()
    print("✅ WYCO points updated.\n")

def determine_initial_class(percentages):
    if len(percentages) < 3:
        return "Unclassified"
    if all(p > A_THRESHOLD for p in percentages[:3]):
        return "A"
    elif all(p <= B_THRESHOLD for p in percentages[:3]):
        return "C"
    else:
        return "B"

def evaluate_class_promotion(existing_class, all_percentages):
    for i in range(len(all_percentages) - 2):
        window = all_percentages[i:i+3]
        if existing_class == "C" and all(p > B_THRESHOLD for p in window):
            return "B"
        elif existing_class == "B" and all(p > A_THRESHOLD for p in window):
            return "A"
    return existing_class

def classify_shooters():
    print("\n🔍 Re-classifying shooters based on match history...")

    shooter_ids = cursor.execute("""
        SELECT id, name, COALESCE(classification, 'Unclassified') AS classification
        FROM shooters
    """).fetchall()

    updated_count = 0

    for shooter_id, name, current_class in shooter_ids:
        percentages = cursor.execute("""
            SELECT wyco_points FROM results
            WHERE shooter_id = ?
            ORDER BY match_id ASC
        """, (shooter_id,)).fetchall()
        percentages = [p[0] for p in percentages if p[0] is not None]

        initial_class = determine_initial_class(percentages)
        final_class = evaluate_class_promotion(initial_class, percentages)

        if class_rank[final_class] > class_rank[current_class]:
            cursor.execute(
                "UPDATE shooters SET classification = ? WHERE id = ?",
                (final_class, shooter_id)
            )
            updated_count += 1
            print(f"🔹 {name}: {current_class} → {final_class}")

    conn.commit()
    print(f"\n✅ Classification updated for {updated_count} shooter(s).")

# --- Execute ---
calculate_wyco_points()
classify_shooters()
conn.close()
