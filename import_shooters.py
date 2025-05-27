import sqlite3
import pandas as pd

# --- Load the CSV ---
csv_path = "wyconumbers.csv"
df = pd.read_csv(csv_path)

# Normalize headers
df.columns = df.columns.str.strip().str.lower()

# Build full name in "Last, First" format to match DB
df['formatted_name'] = df['member_last_name'].str.strip() + ", " + df['member_first_name'].str.strip()

# Convert membership_status to a 1/0 flag
df['is_active_member'] = df['membership_status'].str.strip().str.lower().map(lambda status: 1 if status == 'active' else 0)

# Connect to DB
db_path = "allshooters_dev.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

inserted = 0
updated = 0

for _, row in df.iterrows():
    name = row['formatted_name']
    wyco_number = row['user_id']
    is_active = int(row['is_active_member'])

    # Check if shooter already exists
    cursor.execute("SELECT id FROM shooters WHERE name = ?", (name,))
    result = cursor.fetchone()

    if result:
        cursor.execute("""
            UPDATE shooters
            SET wyco_number = ?, is_active_member = ?
            WHERE name = ?
        """, (wyco_number, is_active, name))
        updated += 1
    else:
        cursor.execute("""
            INSERT INTO shooters (name, wyco_number, is_active_member)
            VALUES (?, ?, ?)
        """, (name, wyco_number, is_active))
        inserted += 1

conn.commit()
conn.close()

print(f"✅ Imported WYCO members: {inserted} new, {updated} updated.")
