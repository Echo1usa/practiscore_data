import sqlite3
from collections import defaultdict

# --- Connect to the database ---
db_path = "allshooters_prs.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# --- Helper: Normalize shooter name ---
def normalize_name(name: str) -> str:
    parts = [part.strip().capitalize() for part in name.split(",")]
    if len(parts) == 2:
        return f"{parts[0]}, {parts[1]}"
    return name.strip().title()

# --- Step 1: Fetch all shooters and normalize names ---
cursor.execute("SELECT shooter_id, name, wyco_number, classification, membership_active FROM shooters")
shooters = cursor.fetchall()

normalized_map = defaultdict(list)
for shooter_id, name, wyco, cl, active in shooters:
    norm = normalize_name(name)
    normalized_map[norm].append({
        "id": shooter_id,
        "name": name,
        "wyco_number": wyco,
        "classification": cl,
        "membership_active": active
    })

# --- Step 2: Merge duplicates and preserve data ---
merge_log = []
merged_count = 0

for norm_name, entries in normalized_map.items():
    if len(entries) < 2:
        continue

    primary = entries[0]
    primary_id = primary["id"]
    updated_fields = {
        "wyco_number": primary["wyco_number"],
        "classification": primary["classification"],
        "membership_active": primary["membership_active"]
    }

    for duplicate in entries[1:]:
        dup_id = duplicate["id"]
        merge_log.append(f'Merged: "{duplicate["name"]}" (ID {dup_id}) → "{primary["name"]}" (ID {primary_id})')

        # Transfer scores
        cursor.execute("UPDATE scores SET shooter_id = ? WHERE shooter_id = ?", (primary_id, dup_id))

        # Preserve data if primary is missing something
        if not updated_fields["wyco_number"] and duplicate["wyco_number"]:
            updated_fields["wyco_number"] = duplicate["wyco_number"]
        if not updated_fields["classification"] and duplicate["classification"]:
            updated_fields["classification"] = duplicate["classification"]
        if updated_fields["membership_active"] is None and duplicate["membership_active"] is not None:
            updated_fields["membership_active"] = duplicate["membership_active"]

        # Delete the duplicate
        cursor.execute("DELETE FROM shooters WHERE shooter_id = ?", (dup_id,))
        merged_count += 1

    # Update the primary shooter with any improved data
    cursor.execute("""
        UPDATE shooters
        SET wyco_number = ?, classification = ?, membership_active = ?
        WHERE shooter_id = ?
    """, (
        updated_fields["wyco_number"],
        updated_fields["classification"],
        updated_fields["membership_active"],
        primary_id
    ))

# --- Finalize ---
conn.commit()
conn.close()

# --- Print merge log ---
print(f"\n✅ Merged {merged_count} duplicate shooter profiles.\n")
print("📋 Merge Log:")
for log in merge_log:
    print(" -", log)
