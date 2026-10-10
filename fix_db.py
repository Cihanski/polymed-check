import sqlite3
import csv
import io
import os
import sys
import urllib.request

print("--- 1. Starte Datenbank-Reparatur ---", flush=True)

# Absoluter Pfad zur Datenbank im gleichen Verzeichnis
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "interactions.db")
print(f"Ziel-Datenbank: {DB_FILE}", flush=True)

# WHO-ATC CSV Quelle
URL = "https://raw.githubusercontent.com/fabkury/atcd/master/WHO%20ATC-DDD%202021-12-03.csv"

csv_content = ""
try:
    print("Lade WHO-ATC Katalog...", flush=True)
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=10) as response:
        csv_content = response.read().decode('utf-8', errors='ignore')
    print("Download erfolgreich abgeschlossen!", flush=True)
except Exception as e:
    print(f"Fehler beim Download: {e}", flush=True)
    sys.exit(1)

conn = sqlite3.connect(DB_FILE)
cursor = conn.cursor()

# Tabelle anlegen
cursor.execute("""
    CREATE TABLE IF NOT EXISTS drugs (
        name TEXT PRIMARY KEY,
        atc_code TEXT NOT NULL,
        drug_class TEXT NOT NULL,
        organ_system TEXT NOT NULL,
        metabolism TEXT NOT NULL
    )
""")

reader = csv.reader(io.StringIO(csv_content))
header = next(reader, None)

count = 0
for row in reader:
    if len(row) < 2:
        continue
    code = row[0].strip()
    name = row[1].strip()
    
    # 7-stellige Einzelwirkstoffe (Level 5)
    if len(code) == 7 and name and name.lower() != "combinations":
        clean_name = name.strip().capitalize()
        cursor.execute("""
            INSERT OR REPLACE INTO drugs (name, atc_code, drug_class, organ_system, metabolism)
            VALUES (?, ?, ?, ?, ?)
        """, (clean_name, code, "WHO-ATC Wirkstoff", "Systemisch", "Standard"))
        count += 1

conn.commit()

cursor.execute("SELECT COUNT(*) FROM drugs")
total_drugs = cursor.fetchone()[0]
conn.close()

print(f"--- FERTIG: {count} Substanzen eingetragen. Bestand in 'drugs': {total_drugs} ---", flush=True)