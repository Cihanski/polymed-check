"""
import_all_who_atc.py
Lädt den vollständigen amtlichen WHO-ATC-Index (über 4.000 Wirkstoffe)
herunter und speichert alle zugelassenen Wirkstoffe direkt in interactions.db.
"""

import sqlite3
import csv
import io
import requests

DB_FILE = "interactions.db"
# Offizieller GitHub-Mirror des vollständigen WHO ATC-DDD Datensatzes
ATC_CSV_URL = "https://raw.githubusercontent.com/fabkury/atcd/master/WHO%20ATC-DDD%202024-07-31.csv"

def run_full_import():
    print("=" * 65)
    print("🚀 Lade kompletten WHO/BfArM-ATC-Katalog herunter...")
    print("=" * 65)
    
    try:
        resp = requests.get(ATC_CSV_URL, timeout=15)
        resp.raise_for_status()
        csv_text = resp.content.decode("utf-8")
    except Exception as e:
        print(f"❌ Fehler beim Download: {e}")
        return

    reader = csv.DictReader(io.StringIO(csv_text))
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drugs (
            name TEXT PRIMARY KEY,
            atc_code TEXT NOT NULL,
            drug_class TEXT NOT NULL,
            organ_system TEXT NOT NULL,
            metabolism TEXT NOT NULL
        )
    """)
    
    inserted = 0
    for row in reader:
        code = row.get("atc_code", "").strip()
        name = row.get("atc_name", "").strip()
        
        # Nur Ebene-5-Einträge sind konkrete Einzelwirkstoffe (z.B. C09AA05 = Ramipril, 7 Zeichen)
        if len(code) == 7 and name:
            # Organ-Hauptgruppe nach Buchstabe (A = Magen/Stoffwechsel, C = Herz, etc.)
            first_char = code[0]
            organ_map = {
                "A": "Magen-Darm & Stoffwechsel",
                "B": "Blut & blutbildende Organe",
                "C": "Herz-Kreislauf-System",
                "D": "Dermatika (Haut)",
                "G": "Urogenitalsystem & Sexualhormone",
                "H": "Systemische Hormonpräparate",
                "J": "Antiinfektiva (Antibiotika/Virostatika)",
                "L": "Antineoplastische Mittel (Onkologie/Immun)",
                "M": "Muskel- & Skelettsystem",
                "N": "Nervensystem (ZNS/Psyche/Schmerz)",
                "P": "Antiparasitäre Mittel",
                "R": "Respirationstrakt (Atmungsorgane)",
                "S": "Sinnesorgane (Auge/Ohr)",
                "V": "Varia (Diagnostika & Sonstiges)"
            }
            organ = organ_map.get(first_char, "Allgemein")
            
            # Saubere Groß-/Kleinschreibung (z. B. "Ramipril", "Flucloxacillin")
            clean_name = name.capitalize()
            
            cursor.execute("""
                INSERT OR REPLACE INTO drugs (name, atc_code, drug_class, organ_system, metabolism)
                VALUES (?, ?, ?, ?, ?)
            """, (clean_name, code, "WHO-ATC Wirkstoff", organ, "Standard"))
            inserted += 1

    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM drugs")
    total_count = cursor.fetchone()[0]
    conn.close()
    
    print(f"✅ Erfolgreich eingespielt: {inserted} chemische Reinsubstanzen.")
    print(f"📊 Neuer Gesamtbestand in der Tabelle 'drugs': {total_count} Wirkstoffe!")
    print("=" * 65)

if __name__ == "__main__":
    run_full_import()