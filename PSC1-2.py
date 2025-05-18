import sqlite3
import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
#smol pp
# --- File with match URLs (one per line) ---
url_file = r"C:\coding project\match_urls.txt"

# --- Database path ---
db_path = r"C:\coding project\allshooters.db"

# --- Setup database and tables ---
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    date_added TEXT NOT NULL,
    match_date TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS shooters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    shooter_id INTEGER NOT NULL,
    place INTEGER,
    points REAL,
    percentage REAL,
    FOREIGN KEY(match_id) REFERENCES matches(id),
    FOREIGN KEY(shooter_id) REFERENCES shooters(id),
    UNIQUE(match_id, shooter_id)
)
""")

conn.commit()

# --- Read URLs ---
with open(url_file, "r") as f:
    urls = [line.strip() for line in f if line.strip()]

# --- Scraping loop ---
with sync_playwright() as p:
    for match_url in urls:
        print(f"\n🔎 Loading: {match_url}")

        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            page.goto(match_url)
            time.sleep(2)
            page.wait_for_selector("table tr td", timeout=15000)

            # Match name and date
            match_name_element = page.query_selector("h3") or page.query_selector("h1")
            match_name = match_name_element.inner_text().strip() if match_name_element else "Unknown Match"
            print(f"📌 Match: {match_name}")

            match_date = None
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", match_name)
            if date_match:
                match_date = date_match.group(1)
            print(f"📅 Parsed Match Date: {match_date}")

            # Insert or update match (overwrite existing record)
            cursor.execute("SELECT id FROM matches WHERE url = ?", (match_url,))
            existing = cursor.fetchone()
            if existing:
                match_id = existing[0]
                cursor.execute("""
                    UPDATE matches
                    SET name = ?, date_added = ?, match_date = ?
                    WHERE id = ?
                """, (match_name, datetime.now().isoformat(), match_date, match_id))
            else:
                cursor.execute("""
                    INSERT INTO matches (name, url, date_added, match_date)
                    VALUES (?, ?, ?, ?)
                """, (match_name, match_url, datetime.now().isoformat(), match_date))
                match_id = cursor.lastrowid
            conn.commit()

            # Parse results table
            rows = page.query_selector_all("table tr")
            column_map = {}

            for row in rows:
                cells = row.query_selector_all("th, td")
                data = [cell.inner_text().strip() for cell in cells]

                # Detect header
                if not column_map and any("match pts" in cell.lower() for cell in data):
                    column_map = {cell.lower(): idx for idx, cell in enumerate(data)}
                    continue

                if len(data) < 4 or not column_map:
                    continue

                try:
                    name = data[column_map.get("name", 1)].strip()
                    place = int(data[column_map.get("place", 0)])
                    points = float(data[column_map.get("match pts")])
                    percentage = float(data[column_map.get("match %")].replace("%", "").strip())
                except (IndexError, ValueError):
                    continue

                # Insert or get shooter
                cursor.execute("INSERT OR IGNORE INTO shooters (name) VALUES (?)", (name,))
                conn.commit()
                cursor.execute("SELECT id FROM shooters WHERE name = ?", (name,))
                shooter_id = cursor.fetchone()[0]

                # Replace existing result if needed
                cursor.execute("REPLACE INTO results (match_id, shooter_id, place, points, percentage) VALUES (?, ?, ?, ?, ?)",
                               (match_id, shooter_id, place, points, percentage))
                conn.commit()

            print("✅ Match processed.")

        except Exception as e:
            print(f"❌ Error processing {match_url}: {e}")

        browser.close()

conn.close()
print("\n✅ All matches processed.")
