import sqlite3

# --- Connect to the development database ---
db_path = "allshooters_dev.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Define classification thresholds
A_THRESHOLD = 87.0
B_THRESHOLD = 67.0

# Define class ranks for comparison
class_rank = {"Unclassified": 0, "C": 1, "B": 2, "A": 3}

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
    # Check if the shooter qualifies for a promotion
    for i in range(len(all_percentages) - 2):
        window = all_percentages[i:i+3]
        if existing_class == "C" and all(p > B_THRESHOLD for p in window):
            return "B"
        elif existing_class == "B" and all(p > A_THRESHOLD for p in window):
            return "A"
    return existing_class

def classify_shooters():
    print("\n🧮 Re-classifying shooters based on match history...")

    shooter_ids = cursor.execute("""
        SELECT id, name, COALESCE(classification, 'Unclassified') AS classification
        FROM shooters
    """).fetchall()

    updated_count = 0

    for shooter_id, name, current_class in shooter_ids:
        percentages = cursor.execute("""
            SELECT percentage FROM results
            WHERE shooter_id = ?
            ORDER BY match_id ASC
        """, (shooter_id,)).fetchall()
        percentages = [p[0] for p in percentages]

        initial_class = determine_initial_class(percentages)
        final_class = evaluate_class_promotion(initial_class, percentages)

        # Enforce no class-down rule
        if class_rank[final_class] > class_rank[current_class]:
            cursor.execute(
                "UPDATE shooters SET classification = ? WHERE id = ?",
                (final_class, shooter_id)
            )
            updated_count += 1
            print(f"🔹 {name}: {current_class} → {final_class}")

    conn.commit()
    print(f"\n✅ Classification updated for {updated_count} shooter(s).")

classify_shooters()
conn.close()
