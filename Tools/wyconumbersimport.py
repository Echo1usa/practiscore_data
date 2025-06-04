import sqlite3
import pandas as pd

# --- Load CSV ---
csv_path = "wyconumbers.csv"  # Replace with your actual file path
df = pd.read_csv(csv_path)

# Normalize column headers and whitespace
df.columns = df.columns.str.strip().str.lower()

# Format shooter name to match database: "Last, First"
df['formatted_name'] = df['member_last_name'].str.strip() + ", " + df['member_first_name'].str.strip()

# --- Connect to the database ---
db_path = "allshooters_dev.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

updated = 0

# --- Loop and update ---
for _, row in df.iterrows():
    name = row['formatted_name']
    wyco_number = row['user_id']

    cursor.execute("""
        UPDATE shooters
        SET wyco_number = ?
        WHERE name = ?
    """, (wyco_number, name))

    if cursor.rowcount > 0:
        updated += 1
    else:
        print(f"⚠️ Shooter not found: {name}")

# --- Finish up ---
conn.commit()
conn.close()

print(f"\n✅ WYCO numbers updated for {updated} shooter(s).")
