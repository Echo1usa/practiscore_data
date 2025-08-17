# recalc_wyco_mysql_no_scoreid.py
import os
from decimal import Decimal, InvalidOperation
from sqlalchemy import create_engine, text

# --- DB connection (env vars: MYSQL_HOST, MYSQL_USER, MYSQL_PASS, MYSQL_DB) ---
def get_engine():
    user = os.getenv("MYSQL_USER")
    pw   = os.getenv("MYSQL_PASS")
    host = os.getenv("MYSQL_HOST", "gator4033.hostgator.com")
    db   = os.getenv("MYSQL_DB")
    if not all([user, pw, db]):
        raise RuntimeError("Missing env vars: MYSQL_USER, MYSQL_PASS, MYSQL_DB")
    return create_engine(f"mysql+pymysql://{user}:{pw}@{host}/{db}?charset=utf8mb4", pool_pre_ping=True)

# --- Self-heal helpers ---
def column_exists(conn, table, column):
    q = text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c
    """)
    return conn.execute(q, {"t": table, "c": column}).scalar() > 0

def ensure_columns_and_indexes(conn):
    # Ensure wyco_points columns
    if not column_exists(conn, "scores", "wyco_points"):
        conn.execute(text("ALTER TABLE scores ADD COLUMN wyco_points DECIMAL(10,2) NULL AFTER points"))
    if not column_exists(conn, "shooters", "wyco_points"):
        conn.execute(text("ALTER TABLE shooters ADD COLUMN wyco_points DECIMAL(10,2) NOT NULL DEFAULT 0"))

    # Ensure stage_name exists (script logic depends on it)
    if not column_exists(conn, "scores", "stage_name"):
        conn.execute(text("ALTER TABLE scores ADD COLUMN stage_name VARCHAR(255) NOT NULL DEFAULT 'Overall'"))

    # Ensure unique composite index for upserts/updates
    # (match_id, shooter_id, stage_name)
    have_idx = conn.execute(text("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = 'scores'
          AND INDEX_NAME = 'uniq_score'
    """)).scalar() > 0
    if not have_idx:
        # If another uniq exists that conflicts, drop it safely
        try:
            conn.execute(text("DROP INDEX uniq_score ON scores"))
        except Exception:
            pass
        conn.execute(text("ALTER TABLE scores ADD UNIQUE KEY uniq_score (match_id, shooter_id, stage_name)"))

def safe_dec(x):
    try:
        return Decimal(str(x))
    except (InvalidOperation, TypeError):
        return Decimal("0")

if __name__ == "__main__":
    engine = get_engine()

    # Self-heal once
    with engine.begin() as conn:
        ensure_columns_and_indexes(conn)

    print("🎯 Recalculating WYCO points using 2-decimal rounding...")

    # --- Step 1: per-match WYCO (Overall only) ---
    with engine.begin() as conn:
        match_ids = [r[0] for r in conn.execute(text("SELECT match_id FROM matches")).fetchall()]

        for mid in match_ids:
            top_score = conn.execute(
                text("""SELECT MAX(points)
                        FROM scores
                        WHERE match_id = :mid AND stage_name = 'Overall'"""),
                {"mid": mid}
            ).scalar()

            if not top_score or safe_dec(top_score) == 0:
                continue

            # Pull shooter_id + points (no score_id needed)
            rows = conn.execute(
                text("""SELECT shooter_id, points
                        FROM scores
                        WHERE match_id = :mid AND stage_name = 'Overall'"""),
                {"mid": mid}
            ).fetchall()

            for shooter_id, pts in rows:
                pts_dec = safe_dec(pts)
                if pts_dec > 0:
                    wyco = (pts_dec / safe_dec(top_score)) * Decimal("100")
                    wyco = wyco.quantize(Decimal("0.01"))
                else:
                    wyco = Decimal("0.00")

                # Update by composite key
                conn.execute(
                    text("""UPDATE scores
                            SET wyco_points = :w
                            WHERE match_id = :mid
                              AND shooter_id = :sid
                              AND stage_name = 'Overall'"""),
                    {"w": wyco, "mid": mid, "sid": shooter_id}
                )

    print("✅ Match-level WYCO points updated.\n")

    # --- Step 2: shooter totals from top 3 venue scores (Overall only) ---
    print("📊 Calculating shooter totals from top 3 venue scores...")
    with engine.begin() as conn:
        shooter_ids = [r[0] for r in conn.execute(text("""
            SELECT shooter_id
            FROM shooters
            WHERE membership_active = 1
              AND wyco_number IS NOT NULL
              AND wyco_number <> ''
        """)).fetchall()]

        for sid in shooter_ids:
            rows = conn.execute(
                text("""SELECT m.venue_id, MAX(s.wyco_points)
                        FROM scores s
                        JOIN matches m ON s.match_id = m.match_id
                        WHERE s.shooter_id = :sid
                          AND s.stage_name = 'Overall'
                          AND m.venue_id IS NOT NULL
                        GROUP BY m.venue_id"""),
                {"sid": sid}
            ).fetchall()

            per_venue = [safe_dec(v) for _, v in rows if v is not None]
            top3 = sorted(per_venue, reverse=True)[:3]
            total = (sum(top3).quantize(Decimal("0.01")) if top3 else Decimal("0.00"))

            conn.execute(
                text("UPDATE shooters SET wyco_points = :total WHERE shooter_id = :sid"),
                {"total": total, "sid": sid}
            )

    print("🏁 Shooter WYCO totals recalculated successfully.")
