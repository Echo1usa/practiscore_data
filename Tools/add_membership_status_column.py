import sqlite3

# Connect to DB
conn = sqlite3.connect("allshooters_dev.db")
cursor = conn.cursor()

# Step 1: Add the column (only once)
try:
    cursor.execute("ALTER TABLE shooters ADD COLUMN is_active_member INTEGER DEFAULT 0")
    print("✅ Column 'is_active_member' added.")
except sqlite3.OperationalError:
    print("⚠️ Column 'is_active_member' already exists.")

# Step 2: Set values based on wyco_number
cursor.execute("""
    UPDATE shooters
    SET is_active_member = CASE
        WHEN wyco_number IS NOT NULL THEN 1
        ELSE 0
    END
""")

conn.commit()
conn.close()
print("✅ 'is_active_member' values populated based on wyco_number.")
