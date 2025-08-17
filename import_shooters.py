# wyco_members_import_mysql.py
import os
import pandas as pd
from sqlalchemy import create_engine, text

# --- DB connection via env vars ---
# Required: MYSQL_USER, MYSQL_PASS, MYSQL_DB
# Optional: MYSQL_HOST (defaults to gator4033.hostgator.com)
def get_engine():
    user = os.getenv("MYSQL_USER")
    pw   = os.getenv("MYSQL_PASS")
    host = os.getenv("MYSQL_HOST", "gator4033.hostgator.com")
    db   = os.getenv("MYSQL_DB")
    if not all([user, pw, db]):
        raise RuntimeError("Missing env vars: MYSQL_USER, MYSQL_PASS, MYSQL_DB")
    return create_engine(
        f"mysql+pymysql://{user}:{pw}@{host}/{db}?charset=utf8mb4",
        pool_pre_ping=True,
    )

# --- Load the CSV ---
csv_path = "wyconumbers.csv"
df = pd.read_csv(csv_path)

# Normalize headers
df.columns = df.columns.str.strip().str.lower()

# Format name: "Last, First" (handle NaNs safely)
df["member_last_name"]  = df["member_last_name"].fillna("").astype(str).str.strip()
df["member_first_name"] = df["member_first_name"].fillna("").astype(str).str.strip()
df["formatted_name"] = df["member_last_name"] + ", " + df["member_first_name"]
df["formatted_name"] = df["formatted_name"].str.strip().str.replace(r"^, ", "", regex=True)

# Convert status to 1 = active, 0 = inactive (treat non-"active" as 0)
df["membership_status"] = df["membership_status"].fillna("").astype(str).str.strip().str.lower()
df["membership_active"] = df["membership_status"].map(lambda s: 1 if s == "active" else 0)

# Coerce user_id to string (DB column is VARCHAR)
df["user_id"] = df["user_id"].fillna("").astype(str).str.strip()

inserted = 0
updated = 0

engine = get_engine()

# NOTE: This assumes you have a UNIQUE KEY on shooters.name
# (created earlier by our self-healing scripts). If not, add it:
# ALTER TABLE shooters ADD UNIQUE KEY uniq_shooter_name (name);

with engine.begin() as conn:  # transaction with auto-commit/rollback
    for _, row in df.iterrows():
        name = row["formatted_name"]
        wyco_number = row["user_id"]
        is_active = int(row["membership_active"])

        if not name:
            continue  # skip blank names

        # Check if shooter exists by name
        res = conn.execute(
            text("SELECT shooter_id FROM shooters WHERE name = :name"),
            {"name": name}
        ).fetchone()

        if res:
            conn.execute(
                text("""
                    UPDATE shooters
                    SET wyco_number = :wyco_number,
                        membership_active = :is_active
                    WHERE name = :name
                """),
                {"wyco_number": wyco_number, "is_active": is_active, "name": name}
            )
            updated += 1
        else:
            conn.execute(
                text("""
                    INSERT INTO shooters (name, wyco_number, membership_active, wyco_points, classification)
                    VALUES (:name, :wyco_number, :is_active, 0, '')
                """),
                {"name": name, "wyco_number": wyco_number, "is_active": is_active}
            )
            inserted += 1

print(f"✅ Done. Inserted: {inserted} | Updated: {updated}")
