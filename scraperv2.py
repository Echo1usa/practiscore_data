import sqlite3
import re
import time
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError

VENUE_MAP = {
    'cheyenne': 1,
    'laramie': 2,
    'pawnee': 3,
    'larkspur': 4,
    'rawlins': 5,
}

def init_db():
    conn = sqlite3.connect("allshooters_prs.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_name TEXT,
            match_date TEXT,
            venue_id INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS shooters (
            shooter_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            wyco_number TEXT,
            wyco_points REAL,
            classification TEXT,
            membership_active INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            score_id INTEGER PRIMARY KEY AUTOINCREMENT,
            match_id INTEGER,
            shooter_id INTEGER,
            stage_name TEXT,
            place INTEGER,
            percentage REAL,
            points REAL,
            FOREIGN KEY(match_id) REFERENCES matches(match_id),
            FOREIGN KEY(shooter_id) REFERENCES shooters(shooter_id)
        )
    """)
    conn.commit()
    conn.close()

def extract_shooter_data(rows, column_map):
    shooter_data = []
    for row in rows:
        cells = row.query_selector_all("th, td")
        data = [cell.inner_text().strip() for cell in cells]

        if not column_map and any("match pts" in cell.lower() or "stage pts" in cell.lower() for cell in data):
            column_map.update({cell.lower(): idx for idx, cell in enumerate(data)})
            continue

        if len(data) < 4 or not column_map:
            continue

        try:
            name = data[column_map.get("name", 1)]
            place = int(data[column_map.get("place", 0)])
            points_key = "match pts" if "match pts" in column_map else "stage pts"
            percentage_key = "match %" if "match %" in column_map else "stage %"
            points = float(data[column_map[points_key]])
            percentage = float(data[column_map[percentage_key]].replace('%', '').strip())
            shooter_data.append((name, place, percentage, points))
        except (ValueError, IndexError):
            continue

    return shooter_data

def insert_shooter_and_score(conn, match_id, shooter_data, stage_name):
    cur = conn.cursor()

    # ✅ Skip stage if already present
    cur.execute("SELECT 1 FROM scores WHERE match_id = ? AND stage_name = ?", (match_id, stage_name))
    if cur.fetchone():
        print(f"⏩ Stage '{stage_name}' already exists. Skipping.")
        return

    for name, place, percentage, points in shooter_data:
        cur.execute("SELECT shooter_id FROM shooters WHERE name = ?", (name,))
        result = cur.fetchone()
        if result:
            shooter_id = result[0]
        else:
            cur.execute("INSERT INTO shooters (name, wyco_number, wyco_points, classification, membership_active) VALUES (?, '', 0, '', 0)", (name,))
            shooter_id = cur.lastrowid

        cur.execute("""
            INSERT INTO scores (match_id, shooter_id, stage_name, place, percentage, points)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (match_id, shooter_id, stage_name, place, percentage, points))
    conn.commit()

def scrape_match(overall_url, base_stage_url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        page.goto(overall_url)
        time.sleep(2)

        match_title = page.query_selector("h3") or page.query_selector("h2")
        match_name = match_title.inner_text().strip() if match_title else "Unknown Match"
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", match_name)
        match_date = date_match.group(0) if date_match else datetime.now().strftime("%Y-%m-%d")
        venue_id = None
        for venue, vid in VENUE_MAP.items():
            if venue in match_name.lower():
                venue_id = vid
                break
        if not venue_id:
            venue_id = int(input(f"Couldn't determine venue from '{match_name}'. Enter venue ID manually: "))

        print(f"📋 Match: {match_name} | Date: {match_date} | Venue ID: {venue_id}")

        conn = sqlite3.connect("allshooters_prs.db")
        cur = conn.cursor()

        # ✅ Check for existing match
        cur.execute("SELECT match_id FROM matches WHERE match_name = ?", (match_name,))
        existing_match = cur.fetchone()
        if existing_match:
            print(f"⏩ Match already exists. Skipping match '{match_name}'.")
            conn.close()
            browser.close()
            return

        cur.execute("INSERT INTO matches (match_name, match_date, venue_id) VALUES (?, ?, ?)",
                    (match_name, match_date, venue_id))
        match_id = cur.lastrowid

        rows = page.query_selector_all("table tr")
        overall_column_map = {}
        overall_data = extract_shooter_data(rows, overall_column_map)
        insert_shooter_and_score(conn, match_id, overall_data, "Overall")

        browser.close()

        # === Loop through stages
        stage_index = 0
        while True:
            stage_url = f"{base_stage_url}=stage{stage_index}-combined"
            stage_name = f"Stage {stage_index + 1}"
            print(f"🔍 Trying {stage_name} @ {stage_url}")

            try:
                browser = p.chromium.launch(headless=False)
                page = browser.new_page()
                page.goto(stage_url)
                time.sleep(2)

                rows = page.query_selector_all("table tr")
                if not rows or len(rows) < 3:
                    print(f"⚠️ No data rows on {stage_name}. Ending stage scraping.")
                    browser.close()
                    break

                stage_column_map = {}
                stage_data = extract_shooter_data(rows, stage_column_map)
                insert_shooter_and_score(conn, match_id, stage_data, stage_name)

                print(f"✅ {stage_name} scraped.")
                browser.close()
                stage_index += 1

            except TimeoutError:
                print(f"⏱️ Timeout on {stage_name}. Ending stage scraping.")
                browser.close()
                break
            except Exception as e:
                print(f"❌ Error scraping {stage_name}: {e}")
                browser.close()
                break

        conn.close()

if __name__ == "__main__":
    init_db()

    with open("match_urls.txt") as f:
        match_urls = [
            line.strip() for line in f
            if line.strip() and not line.strip().startswith("#")
        ]

    for overall_url in match_urls:
        print(f"\n📦 Processing match: {overall_url}")
        base_stage_url = overall_url.split("?")[0] + "?page"
        scrape_match(overall_url, base_stage_url)

    print("\n🎯 All matches processed!")
