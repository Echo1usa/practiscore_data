# scrape_to_mysql_self_healing_v3.py
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError
import pymysql

# ---------- CONFIG: hardcoded for quick testing ----------
MYSQL_HOST = "gator4033.hostgator.com"    # use "localhost" if running on HostGator
MYSQL_USER = "wycoprl3_dbbot"
MYSQL_PASS = "Ab7!tX9%Qz_4Kc3&"
MYSQL_DB   = "wycoprl3_all_shooters"
# ---------------------------------------------------------

VENUE_MAP = {"cheyenne":1,"laramie":2,"pawnee":3,"larkspur":4,"rawlins":5}

def get_conn():
    return pymysql.connect(host=MYSQL_HOST, user=MYSQL_USER, password=MYSQL_PASS, database=MYSQL_DB, autocommit=True)

# ---------- Base table creation ----------
def init_db_mysql():
    conn = get_conn(); cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id INT AUTO_INCREMENT PRIMARY KEY,
            match_name VARCHAR(255),
            match_date DATE,
            venue_id INT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS shooters (
            shooter_id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            score_id INT AUTO_INCREMENT PRIMARY KEY
            -- columns added/ensured in ensure_scores_schema()
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    cur.close(); conn.close()

# ---------- Self-heal helpers ----------
def column_exists(cur, table, column):
    cur.execute("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME=%s
    """, (table, column))
    return cur.fetchone()[0] > 0

def ensure_column(cur, table, column, ddl):
    if not column_exists(cur, table, column):
        print(f"🛠️ Adding {table}.{column} ...")
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

def index_columns(cur, table, key_name):
    cur.execute(f"SHOW INDEX FROM {table} WHERE Key_name=%s", (key_name,))
    rows = cur.fetchall()
    return [r[4] for r in rows] if rows else []

def ensure_matches_schema():
    conn = get_conn(); cur = conn.cursor()
    # unique(match_name) for your de-dupe logic
    cols = index_columns(cur, "matches", "uniq_match")
    if set(cols) != {"match_name"}:
        try: cur.execute("DROP INDEX uniq_match ON matches")
        except Exception: pass
        cur.execute("ALTER TABLE matches ADD UNIQUE KEY uniq_match (match_name)")
    cur.close(); conn.close()

def ensure_shooters_schema():
    conn = get_conn(); cur = conn.cursor()
    ensure_column(cur, "shooters", "wyco_number",       "wyco_number VARCHAR(50) NULL AFTER name")
    ensure_column(cur, "shooters", "wyco_points",       "wyco_points DECIMAL(10,2) NOT NULL DEFAULT 0 AFTER wyco_number")
    ensure_column(cur, "shooters", "classification",    "classification VARCHAR(50) NULL AFTER wyco_points")
    ensure_column(cur, "shooters", "membership_active", "membership_active TINYINT(1) NOT NULL DEFAULT 0 AFTER classification")

    # unique(name) for idempotent inserts
    cols = index_columns(cur, "shooters", "uniq_shooter_name")
    if set(cols) != {"name"}:
        try: cur.execute("DROP INDEX uniq_shooter_name ON shooters")
        except Exception: pass
        cur.execute("ALTER TABLE shooters ADD UNIQUE KEY uniq_shooter_name (name)")
    cur.close(); conn.close()

def ensure_scores_schema():
    conn = get_conn(); cur = conn.cursor()
    # Make sure all needed columns exist (order hints via AFTER where possible)
    # Minimal safe ordering: match_id, shooter_id, stage_name, place, percentage, points
    ensure_column(cur, "scores", "match_id",   "match_id INT NULL")
    ensure_column(cur, "scores", "shooter_id", "shooter_id INT NULL AFTER match_id")
    ensure_column(cur, "scores", "stage_name", "stage_name VARCHAR(255) NOT NULL DEFAULT 'Overall' AFTER shooter_id")
    ensure_column(cur, "scores", "place",      "place INT NULL AFTER stage_name")
    ensure_column(cur, "scores", "percentage", "percentage DECIMAL(8,3) NULL AFTER place")
    ensure_column(cur, "scores", "points",     "points DECIMAL(10,2) NULL AFTER percentage")

    # Unique key for upserts
    cols = index_columns(cur, "scores", "uniq_score")
    if set(cols) != {"match_id", "shooter_id", "stage_name"}:
        try: cur.execute("DROP INDEX uniq_score ON scores")
        except Exception: pass
        print("🛠️ Creating uniq_score on (match_id, shooter_id, stage_name) ...")
        cur.execute("ALTER TABLE scores ADD UNIQUE KEY uniq_score (match_id, shooter_id, stage_name)")

    # (Optional) add FKs if columns exist; skip if older table formats cause issues.
    cur.close(); conn.close()

# ---------- Scraper helpers ----------
def extract_shooter_data(rows, column_map):
    shooter_data = []
    for row in rows:
        cells = row.query_selector_all("th, td")
        data = [cell.inner_text().strip() for cell in cells]

        if not column_map and any("match pts" in d.lower() or "stage pts" in d.lower() for d in data):
            column_map.update({d.lower(): i for i, d in enumerate(data)})
            continue

        if len(data) < 4 or not column_map:
            continue

        try:
            name = data[column_map.get("name", 1)]
            place = int(data[column_map.get("place", 0)])
            points_key = "match pts" if "match pts" in column_map else "stage pts"
            pct_key    = "match %"   if "match %"   in column_map else "stage %"
            points = float(data[column_map[points_key]])
            percentage = float(data[column_map[pct_key]].replace('%', '').strip())
            shooter_data.append((name, place, percentage, points))
        except (ValueError, IndexError):
            continue
    return shooter_data

def upsert_shooter(cur, name):
    cur.execute("SELECT shooter_id FROM shooters WHERE name=%s", (name,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur.execute("""
        INSERT INTO shooters (name, wyco_number, wyco_points, classification, membership_active)
        VALUES (%s, %s, %s, %s, %s)
    """, (name, "", 0, "", 0))
    cur.execute("SELECT LAST_INSERT_ID()")
    return cur.fetchone()[0]

def insert_shooter_and_score(conn, match_id, shooter_data, stage_name):
    cur = conn.cursor()

    # Bail early if this stage already present
    cur.execute("SELECT 1 FROM scores WHERE match_id=%s AND stage_name=%s LIMIT 1", (match_id, stage_name))
    if cur.fetchone():
        print(f"⏩ Stage '{stage_name}' already exists. Skipping.")
        cur.close(); return

    inserted = 0
    for name, place, percentage, points in shooter_data:
        if percentage is None or float(percentage) <= 0:
            continue
        shooter_id = upsert_shooter(cur, name)
        cur.execute("""
            INSERT INTO scores (match_id, shooter_id, stage_name, place, percentage, points)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE place=VALUES(place), percentage=VALUES(percentage), points=VALUES(points)
        """, (match_id, shooter_id, stage_name, int(place), float(percentage), float(points)))
        inserted += 1

    cur.close()
    if inserted:
        print(f"✅ Inserted/updated {inserted} rows for stage '{stage_name}'")

# ---------- Main scrape ----------
def scrape_match(overall_url, base_stage_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(overall_url); time.sleep(2)

        match_title = page.query_selector("h3") or page.query_selector("h2")
        match_name = match_title.inner_text().strip() if match_title else "Unknown Match"
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", match_name)
        match_date = date_match.group(0) if date_match else datetime.now().strftime("%Y-%m-%d")

        venue_id = next((vid for venue, vid in VENUE_MAP.items() if venue in match_name.lower()), None)
        if not venue_id:
            venue_id = int(input("Enter venue ID (1 Cheyenne, 2 Laramie, 3 Pawnee, 4 Larkspur, 5 Rawlins): "))

        print(f"📋 Match: {match_name} | Date: {match_date} | Venue ID: {venue_id}")

        conn = get_conn(); cur = conn.cursor()
        cur.execute("SELECT match_id FROM matches WHERE match_name=%s", (match_name,))
        existing = cur.fetchone()
        if existing:
            print(f"⏩ Match already exists. Skipping match '{match_name}'.")
            cur.close(); browser.close(); return

        cur.execute("INSERT INTO matches (match_name, match_date, venue_id) VALUES (%s, %s, %s)",
                    (match_name, match_date, venue_id))
        cur.execute("SELECT LAST_INSERT_ID()"); match_id = cur.fetchone()[0]
        cur.close()

        rows = page.query_selector_all("table tr")
        overall_column_map = {}
        overall_data = extract_shooter_data(rows, overall_column_map)
        insert_shooter_and_score(conn, match_id, overall_data, "Overall")

        browser.close()

        stage_index = 0
        while True:
            stage_url = f"{base_stage_url}=stage{stage_index}-combined"
            stage_name = f"Stage {stage_index + 1}"
            print(f"🔍 Trying {stage_name} @ {stage_url}")

            try:
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                page.goto(stage_url); time.sleep(2)

                rows = page.query_selector_all("table tr")
                if not rows or len(rows) < 3:
                    print(f"⚠️ No data rows on {stage_name}. Ending stage scraping.")
                    browser.close(); break

                stage_column_map = {}
                stage_data = extract_shooter_data(rows, stage_column_map)
                insert_shooter_and_score(conn, match_id, stage_data, stage_name)

                print(f"✅ {stage_name} scraped.")
                browser.close(); stage_index += 1

            except TimeoutError:
                print(f"⏱️ Timeout on {stage_name}. Ending stage scraping.")
                browser.close(); break
            except Exception as e:
                print(f"❌ Error scraping {stage_name}: {e}")
                browser.close(); break

        conn.close()

if __name__ == "__main__":
    # Create minimal tables, then self-heal schemas BEFORE scraping
    init_db_mysql()
    ensure_matches_schema()
    ensure_shooters_schema()
    ensure_scores_schema()

    with open("match_urls.txt") as f:
        match_urls = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

    for overall_url in match_urls:
        print(f"\n📦 Processing match: {overall_url}")
        base_stage_url = overall_url.split("?")[0] + "?page"
        scrape_match(overall_url, base_stage_url)

    print("\n🎯 All matches processed!")
