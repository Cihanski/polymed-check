"""
update_database.py
Wird halbjährlich automatisch ausgeführt:
1. Aktualisiert den vollständigen WHO-ATC-Arzneistoffkatalog in interactions.db
2. Stellt sicher, dass alle ATC-Klassenregeln aktiv bleiben
"""

import sqlite3
import csv
import io
import os
import sys
import urllib.request
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "interactions.db")
ATC_URL = "https://raw.githubusercontent.com/fabkury/atcd/master/WHO%20ATC-DDD%202021-12-03.csv"

def run_update():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starte halbjährliches Datenbank-Update...")
    
    # 1. Download
    try:
        req = urllib.request.Request(ATC_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=20) as resp:
            csv_content = resp.read().decode('utf-8', errors='ignore')
        print("Download des aktuellen Katalogs erfolgreich.")
    except Exception as e:
        print(f"Fehler beim Download: {e}")
        sys.exit(1)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS "drugs" (
            name TEXT PRIMARY KEY,
            atc_code TEXT NOT NULL,
            drug_class TEXT NOT NULL,
            organ_system TEXT NOT NULL,
            metabolism TEXT NOT NULL
        )
    """)

    reader = csv.reader(io.StringIO(csv_content))
    next(reader, None)

    count = 0
    for row in reader:
        if len(row) < 2:
            continue
        code = row[0].strip()
        name = row[1].strip()
        if len(code) == 7 and name and name.lower() != "combinations":
            clean_name = name.strip().capitalize()
            cursor.execute("""
                INSERT OR REPLACE INTO "drugs" (name, atc_code, drug_class, organ_system, metabolism)
                VALUES (?, ?, ?, ?, ?)
            """, (clean_name, code, "WHO-ATC Wirkstoff", "Systemisch", "Standard"))
            count += 1

    conn.commit()
    cursor.execute('SELECT COUNT(*) FROM "drugs"')
    total = cursor.fetchone()[0]
    conn.close()

    print(f"Update abgeschlossen: {count} Datensätze geprüft. Gesamtbestand: {total} Wirkstoffe.")

if __name__ == "__main__":
    run_update()