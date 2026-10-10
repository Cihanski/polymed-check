import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "interactions.db")


def init_db():
    """Erstellt alle benötigten Tabellen."""
    with sqlite3.connect(DB_FILE) as conn:
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "interactions" (
                pair_key TEXT PRIMARY KEY,
                drug_a TEXT NOT NULL,
                drug_b TEXT NOT NULL,
                severity TEXT NOT NULL,
                system TEXT NOT NULL,
                effect TEXT NOT NULL,
                mechanism TEXT NOT NULL,
                source TEXT DEFAULT 'SQLite-Cache'
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "class_rules" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                atc_a TEXT NOT NULL,
                atc_b TEXT NOT NULL,
                class_name_a TEXT NOT NULL,
                class_name_b TEXT NOT NULL,
                severity TEXT NOT NULL,
                system TEXT NOT NULL,
                effect TEXT NOT NULL,
                mechanism TEXT NOT NULL
            )
        """)
        conn.commit()


init_db()


def get_cache_key(drug_a, drug_b):
    """Sortiert zwei Wirkstoffnamen alphabetisch für einen eindeutigen Schlüssel."""
    sorted_pair = sorted([drug_a.strip().lower(), drug_b.strip().lower()])
    return f"{sorted_pair[0]}___{sorted_pair[1]}"


def check_cache(drug_a, drug_b):
    """Stufe 1: Prüft, ob ein spezifisches Einzelpaar in 'interactions' hinterlegt ist."""
    key = get_cache_key(drug_a, drug_b)
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT severity, system, effect, mechanism, source 
            FROM "interactions" 
            WHERE pair_key = ?
        """, (key,))
        row = cursor.fetchone()

    if row:
        return {
            "severity": row[0],
            "system": row[1],
            "effect": row[2],
            "mechanism": row[3],
            "source": row[4]
        }
    return None


def get_atc_code(drug_name):
    """
    Ermittelt robust den ATC-Code eines Medikaments aus 'drugs'.
    Priorisiert systemische Hauptkatalog-Codes (z. B. M01 vor M02 für NSAR).
    """
    if not drug_name:
        return None

    clean = drug_name.strip()
    if "(" in clean and ")" in clean:
        inside = clean[clean.find("(")+1:clean.find(")")].strip()
        clean_candidates = [inside, clean.split("(")[0].strip()]
    else:
        clean_candidates = [clean]

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        for cand in clean_candidates:
            # 1. Bevorzuge systemische Codes (M01, C09, etc.), falls mehrere Treffer existieren
            cursor.execute("""
                SELECT atc_code FROM "drugs" 
                WHERE name = ? COLLATE NOCASE 
                ORDER BY 
                    CASE 
                        WHEN atc_code LIKE 'M01%' THEN 1
                        WHEN atc_code LIKE 'C%' THEN 1
                        WHEN atc_code LIKE 'J%' THEN 1
                        WHEN atc_code LIKE 'N%' THEN 1
                        ELSE 2
                    END,
                    LENGTH(name) ASC
            """, (cand,))
            rows = cursor.fetchall()
            if rows:
                return rows[0][0]

            # 2. Präfix-Suche mit derselben Priorisierung
            cursor.execute("""
                SELECT atc_code FROM "drugs" 
                WHERE name LIKE ? 
                ORDER BY 
                    CASE 
                        WHEN atc_code LIKE 'M01%' THEN 1
                        WHEN atc_code LIKE 'C%' THEN 1
                        WHEN atc_code LIKE 'J%' THEN 1
                        WHEN atc_code LIKE 'N%' THEN 1
                        ELSE 2
                    END,
                    LENGTH(name) ASC
            """, (f"{cand}%",))
            rows = cursor.fetchall()
            if rows:
                return rows[0][0]

            # 3. Erstes Wort als Fallback
            first_word = cand.split()[0] if " " in cand else cand
            if len(first_word) >= 4:
                cursor.execute("""
                    SELECT atc_code FROM "drugs" 
                    WHERE name LIKE ? 
                    ORDER BY 
                        CASE 
                            WHEN atc_code LIKE 'M01%' THEN 1
                            WHEN atc_code LIKE 'C%' THEN 1
                            WHEN atc_code LIKE 'J%' THEN 1
                            WHEN atc_code LIKE 'N%' THEN 1
                            ELSE 2
                        END,
                        LENGTH(name) ASC
                """, (f"{first_word}%",))
                rows = cursor.fetchall()
                if rows:
                    return rows[0][0]

    return None


def check_class_rules(drug_a, drug_b):
    """
    Stufe 2: Prüft, ob die ATC-Klassen beider Wirkstoffe eine bekannte Gruppeninteraktion auslösen.
    """
    atc_a = get_atc_code(drug_a)
    atc_b = get_atc_code(drug_b)

    if not atc_a or not atc_b:
        return None

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT atc_a, atc_b, class_name_a, class_name_b, severity, system, effect, mechanism 
            FROM "class_rules"
        """)
        rules = cursor.fetchall()

    for r_atc_a, r_atc_b, c_name_a, c_name_b, sev, sys_name, eff, mech in rules:
        # Erlaube auch M02 (topische Formen), falls ein NSAR darüber gefunden wurde
        match_dir1 = (atc_a.startswith(r_atc_a) or (r_atc_a == "M01A" and atc_a.startswith("M02AA"))) and atc_b.startswith(r_atc_b)
        match_dir2 = (atc_b.startswith(r_atc_a) or (r_atc_a == "M01A" and atc_b.startswith("M02AA"))) and atc_a.startswith(r_atc_b)

        if match_dir1 or match_dir2:
            return {
                "severity": sev,
                "system": sys_name,
                "effect": f"[{c_name_a} + {c_name_b}] {eff}",
                "mechanism": mech,
                "source": "ATC-Klassenregel"
            }

    return None


def check_multidrug_synergies(drug_list):
    """
    Prüft die gesamte Medikamentenliste auf kumulative Mehrfach-Risiken:
    1. Kumulative anticholinerge Last (ACB)
    2. Additives Risiko für QT-Intervall-Verlängerung
    """
    synergies = []
    atc_map = {d: get_atc_code(d) for d in drug_list}

    # 1. Anticholinerge Last
    anticholinergic_drugs = []
    for d, code in atc_map.items():
        if code:
            if (code.startswith("N06AA") or code.startswith("G04BD") or 
                code.startswith("R06AA") or code.startswith("R06AB") or 
                code.startswith("N05AA")):
                anticholinergic_drugs.append(d)

    if len(anticholinergic_drugs) >= 2:
        synergies.append({
            "type": "Anticholinerge Last",
            "drugs": anticholinergic_drugs,
            "severity": "Hoch" if len(anticholinergic_drugs) >= 3 else "Moderat",
            "title": f"Kumulative anticholinerge Last ({len(anticholinergic_drugs)} Substanzen)",
            "effect": "Stark erhöhtes Risiko für kognitive Störungen, akute Verwirrtheit, Delir, Stürze, Obstipation und Harnverhalt.",
            "mechanism": "Additive Blockade zentraler und peripherer Muskarinrezeptoren durch gleichzeitige Einnahme mehrerer anticholinerg wirksamer Wirkstoffe."
        })

    # 2. Kumulative QT-Verlängerung
    qt_prolonging_drugs = []
    for d, code in atc_map.items():
        if code:
            if (code.startswith("J01FA") or code.startswith("J01MA") or 
                code.startswith("C01B") or code.startswith("N05A") or 
                code.startswith("N06AB")):
                qt_prolonging_drugs.append(d)

    if len(qt_prolonging_drugs) >= 2:
        synergies.append({
            "type": "Kardiale QT-Verlängerung",
            "drugs": qt_prolonging_drugs,
            "severity": "Hoch",
            "title": f"Kumulative QT-Zeit-Verlängerung ({len(qt_prolonging_drugs)} Substanzen)",
            "effect": "Kritisches Risiko für Torsade-de-Pointes-Arrhythmien und plötzlichen Herztod.",
            "mechanism": "Synergistische Hemmung der myokardialen Kaliumkanäle (hERG/IKr) verzögert die ventrikuläre Repolarisation."
        })

    return synergies


def save_to_cache(drug_a, drug_b, data):
    """Speichert ein Analyse-Ergebnis transaktionssicher in SQLite."""
    key = get_cache_key(drug_a, drug_b)
    source = data.get("source", "SQLite-DB")

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO "interactions" 
            (pair_key, drug_a, drug_b, severity, system, effect, mechanism, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            key,
            drug_a.strip(),
            drug_b.strip(),
            data.get("severity", "Moderat"),
            data.get("system", "Allgemein"),
            data.get("effect", ""),
            data.get("mechanism", ""),
            source
        ))
        conn.commit()


def get_total_cached_count():
    """Gibt die Gesamtanzahl aller Einzelinteraktionen zurück."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM "interactions"')
            count = cursor.fetchone()[0]
            return count
    except Exception:
        return 0


def get_total_class_rules_count():
    """Gibt die Anzahl aktiver ATC-Klassenregeln zurück."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM "class_rules"')
            count = cursor.fetchone()[0]
            return count
    except Exception:
        return 0


def get_all_cached_drugs():
    """Liest alle ~4.800 Substanzen aus 'drugs' und 'interactions' aus."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            query = """
                SELECT name FROM "drugs"
                UNION
                SELECT DISTINCT drug_a FROM "interactions"
                UNION
                SELECT DISTINCT drug_b FROM "interactions"
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            return [r[0] for r in rows if r[0]]
    except Exception as e:
        print(f"Fehler: {e}")
        return []