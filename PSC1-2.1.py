import sqlite3
import time
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
import os
import sys

# --- Debug Environment Info ---
print("🐍 Python version:", sys.version)
print("📁 Working directory:", os.getcwd())
print("📄 Looking for match_urls.txt in:", os.path.abspath("match_urls.txt"))

# --- File with match URLs (one per line) ---
url_file = "match_urls.txt"  # keep it relative in DevContainer

# --- Check for file before opening ---
if not os.path.exists(url_file):
    print(f"❌ match_urls.txt not found at {os.path.abspath(url_file)}")
    sys.exit(1)

with open(url_file, "r") as f:
    urls = [line.strip() for line in f if line.strip()]
print(f"✅ Loaded {len(urls)} match URL(s)")

# --- Database path ---
db_path = "allshooters_dev.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# --- Add columns if needed ---
for col in ["classification", "wyco_number", "wpr_number"]:
    try:
        cursor.execute(f"ALTER TABLE shooters ADD COLUMN {col} TEXT")
    except sqlite3.OperationalError:
        pass  # already exists

# --- Table setup ---
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

            # Match name & date
            match_name_element = page.query_selector("h3") or page.query_selector("h1")
            match_name = match_name_element.inner_text().strip() if match_name_element else "Unknown Match"
            print(f"📌 Match: {match_name}")
            match_date = re.search(r"(\d{4}-\d{2}-\d{2})", match_name)
            match_date = match_date.group(1) if match_date else None
            print(f"📅 Date: {match_date}")

            # Insert or update match
            cursor.execute("SELECT id FROM matches WHERE url = ?", (match_url,))
            row = cursor.fetchone()
            if row:
                match_id = row[0]
                cursor.execute("UPDATE matches SET name=?, date_added=?, match_date=? WHERE id=?",
                               (match_name, datetime.now().isoformat(), match_date, match_id))
            else:
                cursor.execute("INSERT INTO matches (name, url, date_added, match_date) VALUES (?, ?, ?, ?)",
                               (match_name, match_url, datetime.now().isoformat(), match_date))
                match_id = cursor.lastrowid
            conn.commit()

            # --- Parse results table ---
            rows = page.query_selector_all("table tr")
            column_map = {}

            for row in rows:
                cells = row.query_selector_all("th, td")
                data = [cell.inner_text().strip() for cell in cells]

                if not column_map and any("match pts" in cell.lower() for cell in data):
                    column_map = {cell.lower(): idx for idx, cell in enumerate(data)}
                    continue

                if len(data) < 4 or not column_map:
                    continue

                try:
                    name = data[column_map.get("name", 1)]
                    place = int(data[column_map.get("place", 0)])
                    points = float(data[column_map.get("match pts")])
                    percentage = float(data[column_map.get("match %")].replace("%", "").strip())
                except (IndexError, ValueError):
                    continue

                cursor.execute("INSERT OR IGNORE INTO shooters (name) VALUES (?)", (name,))
                conn.commit()
                cursor.execute("SELECT id FROM shooters WHERE name = ?", (name,))
                shooter_id = cursor.fetchone()[0]

                cursor.execute("REPLACE INTO results (match_id, shooter_id, place, points, percentage) VALUES (?, ?, ?, ?, ?)",
                               (match_id, shooter_id, place, points, percentage))
                conn.commit()

            print("✅ Match processed.")

        except Exception as e:
            print(f"❌ Error processing {match_url}: {e}")

        browser.close()

conn.close()
print("\n✅ All matches processed.")
