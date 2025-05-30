import sqlite3
import pandas as pd

# --- Load the CSV ---
csv_path = "wyconumbers.csv"
df = pd.read_csv(csv_path)

# Normalize headers
df.columns = df.columns.str.strip().str.lower()

# Format name: "Last, First"
df['formatted_name'] = df['member_last_name'].str.strip() + ", " + df['member_first_name'].str.strip()

# Convert status to 1 = active, 0 = inactive
df['membership_active'] = df['membership_status'].str.strip().str.lower().map(lambda status: 1 if status == 'active' else 0)

# Connect to the database
db_path = "allshooters_prs.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

inserted = 0
updated = 0

for _, row in df.iterrows():
    name = row['formatted_name']
    wyco_number = row['user_id']
    is_active = int(row['membership_active'])

    # Check if shooter exists by name
    cursor.execute("SELECT shooter_id FROM shooters WHERE name = ?", (name,))
    result = cursor.fetchone()

    if result:
        cursor.execute("""
            UPDATE shooters
            SET wyco_number = ?, membership_active = ?
            WHERE name = ?
        """, (wyco_number, is_active, name))
        updated += 1
    else:
        cursor.execute("""
            INSERT INTO shooters (name, wyco_number, membership_active, wyco_points, classification)
            VALUES (?, ?, ?, 0, '')
        """, (name, wyco_number, is_active))
        inserted += 1

conn.commit()
conn.close()

print(f"✅ WYCO data imported: {inserted} new, {updated} updated.")
