import sqlite3
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "interactions.db")


def init_db():
    """Erstellt alle benoetigten Tabellen und initialisiert Kern-Klassenregeln."""
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "phytomed_rules" (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                phyto_code TEXT NOT NULL,
                target_atc TEXT NOT NULL,
                severity TEXT NOT NULL,
                system TEXT NOT NULL,
                effect TEXT NOT NULL,
                mechanism TEXT NOT NULL
            )
        """)

        # Neue Kern-Klassenregeln hinterlegen
        CORE_CLASS_RULES = [
            # 1. Opioide + Benzodiazepine (FDA Black Box)
            ("N02A", "N05BA", "Opioide", "Benzodiazepine", "Hoch", "Zentralnervensystem / Atmung",
             "Lebensbedrohliche Atemdepression, Koma und letale Sedierung.",
             "Synergistische zentralnervöse Dämpfung an mu-Opioid- und GABAA-Rezeptoren."),
            ("N02A", "N05CD", "Opioide", "Benzodiazepin-Derivate", "Hoch", "Zentralnervensystem / Atmung",
             "Schwere ZNS-Depression und Hypoventilation.",
             "Synergistische Atemdepressionsverstärkung."),
            ("N02A", "N05CF", "Opioide", "Z-Substanzen (Hypnotika)", "Hoch", "Zentralnervensystem / Atmung",
             "Ausgepraegte Sedierung und erhoehtes Atemstillstandrisiko.",
             "Additive Verstärkung inhibitorischer GABAerger und opioider Signalwege."),

            # 2. Digitalis + P-gp-Hemmer / Verapamil / Amiodaron
            ("C01AA", "C08D", "Digitalisglykoside", "Calciumantagonisten (Verapamil/Diltiazem)", "Hoch", "Kardiovaskulaer / Rhythmus",
             "Digoxin-Intoxikation mit AV-Block und ventrikulaeren Arrhythmien.",
             "Hemmung des renalen und biliaeren P-Glykoprotein-Transporters erhoeht Digoxin-Spiegel um 50-100%."),
            ("C01AA", "C01BD", "Digitalisglykoside", "Klasse-III-Antiarrhythmika (Amiodaron)", "Hoch", "Kardiovaskulaer / Rhythmus",
             "Akute Digitalistoxizitaet und Bradykardie.",
             "Amiodaron inhibiert P-gp-vermittelten renalen Digoxintransport signifikant."),

            # 3. SSRI + Antikoagulanzien / Thrombozytenaggregationshemmer
            ("N06AB", "B01A", "SSRI-Antidepressiva", "Antithrombotika (DOAK/VKA/ASS)", "Moderat", "Haemostase / Gastrointestinal",
             "Verdopplung bis Verdreifachung des oberen Magen-Darm-Blutungsrisikos.",
             "SSRI blockieren den SERT-Transporter auf Thrombozyten und entleeren deren Serotoningranula, was die Blutstillung beeintraechtigt."),

            # 4. RAAS-Blockade + Kaliumsparende Diuretika
            ("C09A", "C03D", "ACE-Hemmer", "Kaliumsparende Diuretika (Aldosteron-Antagonisten)", "Hoch", "Elektrolyte & Herz",
             "Schwere, potenziell toedliche Hyperkaliaemie.",
             "Synergistische Hemmung der renalen Kaliumausscheidung."),
            ("C09C", "C03D", "AT1-Antagonisten (Sartane)", "Kaliumsparende Diuretika (Aldosteron-Antagonisten)", "Hoch", "Elektrolyte & Herz",
             "Schwere Hyperkaliaemie und Herzrhythmusstoerungen.",
             "Additive Unterdrueckung der Aldosteron-vermittelten Kaliumsekretion.")
        ]

        for r in CORE_CLASS_RULES:
            cursor.execute("""
                SELECT COUNT(*) FROM "class_rules" 
                WHERE atc_a = ? AND atc_b = ?
            """, (r[0], r[1]))
            if cursor.fetchone()[0] == 0:
                cursor.execute("""
                    INSERT INTO "class_rules" (atc_a, atc_b, class_name_a, class_name_b, severity, system, effect, mechanism)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, r)

        conn.commit()


init_db()


def get_cache_key(drug_a, drug_b):
    """Sortiert zwei Wirkstoffnamen alphabetisch fuer einen konsistenten Primaerschluessel."""
    sorted_pair = sorted([drug_a.strip().lower(), drug_b.strip().lower()])
    return f"{sorted_pair[0]}___{sorted_pair[1]}"


def check_cache(drug_a, drug_b):
    """Stufe 1: Direkter Cache-Lookup fuer zuvor gepruefte Einzelpaare."""
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


def get_all_atc_codes(drug_name):
    """
    Ermittelt alle hinterlegten ATC- oder Phyto-Codes fuer eine Substanz.
    Priorisiert systemische Darreichungen vor lokalen Formen (S, D).
    """
    if not drug_name:
        return []

    clean = drug_name.strip()
    clean_no_emoji = re.sub(r'[\U00010000-\U0010ffff]', '', clean).strip()

    search_terms = [clean, clean_no_emoji]
    if "(" in clean and ")" in clean:
        inside = clean[clean.find("(") + 1:clean.find(")")].strip()
        search_terms.extend([inside, clean.split("(")[0].strip()])

    first_word = clean_no_emoji.split()[0] if " " in clean_no_emoji else clean_no_emoji
    if len(first_word) >= 4:
        search_terms.append(first_word)

    found_codes = []
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        for term in search_terms:
            cursor.execute("""
                SELECT DISTINCT atc_code FROM "drugs"
                WHERE name = ? COLLATE NOCASE OR name LIKE ? COLLATE NOCASE
            """, (term, f"{term}%"))
            rows = cursor.fetchall()
            for r in rows:
                if r[0] and r[0] not in found_codes:
                    found_codes.append(r[0])

    def sort_priority(code):
        if code.startswith("PHYTO_"):
            return 0
        if (code.startswith("J01") or code.startswith("C") or 
            code.startswith("N") or code.startswith("L04") or 
            code.startswith("L") or code.startswith("B01") or 
            code.startswith("M01") or code.startswith("H03")):
            return 1
        if code.startswith("S") or code.startswith("D"):
            return 3
        return 2

    found_codes.sort(key=sort_priority)
    return found_codes


def get_atc_code(drug_name):
    """Gibt den am hoechsten priorisierten ATC-Code zurueck."""
    codes = get_all_atc_codes(drug_name)
    return codes[0] if codes else None


def check_phytomed_rules(drug_a, drug_b):
    """
    Prueft Interaktionen zwischen Phytopharmaka/Kationen und Arzneistoffen.
    """
    codes_a = get_all_atc_codes(drug_a)
    codes_b = get_all_atc_codes(drug_b)

    if not codes_a or not codes_b:
        return None

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT phyto_code, target_atc, severity, system, effect, mechanism 
            FROM "phytomed_rules"
        """)
        rules = cursor.fetchall()

    for p_code, t_atc, sev, sys_name, eff, mech in rules:
        for ca in codes_a:
            for cb in codes_b:
                match_ab = (ca == p_code) and (cb.startswith(t_atc) or cb == t_atc)
                match_ba = (cb == p_code) and (ca.startswith(t_atc) or ca == t_atc)

                if match_ab or match_ba:
                    return {
                        "severity": sev,
                        "system": sys_name,
                        "effect": eff,
                        "mechanism": mech,
                        "source": "Phyto-Regelwerk"
                    }

    return None


def check_class_rules(drug_a, drug_b):
    """Stufe 2b: Prueft ATC-Gruppeninteraktionen zwischen zwei chemischen Wirkstoffen."""
    codes_a = get_all_atc_codes(drug_a)
    codes_b = get_all_atc_codes(drug_b)

    if not codes_a or not codes_b:
        return None

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT atc_a, atc_b, class_name_a, class_name_b, severity, system, effect, mechanism 
            FROM "class_rules"
        """)
        rules = cursor.fetchall()

    for r_atc_a, r_atc_b, c_name_a, c_name_b, sev, sys_name, eff, mech in rules:
        for ca in codes_a:
            for cb in codes_b:
                match_dir1 = (ca.startswith(r_atc_a) or (r_atc_a == "M01A" and ca.startswith("M02AA"))) and cb.startswith(r_atc_b)
                match_dir2 = (cb.startswith(r_atc_a) or (r_atc_a == "M01A" and cb.startswith("M02AA"))) and ca.startswith(r_atc_b)

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
    """Erkennt kumulative Risiken ueber die gesamte Medikationsliste."""
    synergies = []
    atc_map = {d: get_all_atc_codes(d) for d in drug_list}

    # 1. Anticholinerge Last
    anticholinergic_drugs = []
    for d, codes in atc_map.items():
        if any(c.startswith("N06AA") or c.startswith("G04BD") or 
               c.startswith("R06AA") or c.startswith("R06AB") or 
               c.startswith("N05AA") for c in codes):
            anticholinergic_drugs.append(d)

    if len(anticholinergic_drugs) >= 2:
        synergies.append({
            "type": "Anticholinerge Last",
            "drugs": anticholinergic_drugs,
            "severity": "Hoch" if len(anticholinergic_drugs) >= 3 else "Moderat",
            "title": f"Kumulative anticholinerge Last ({len(anticholinergic_drugs)} Substanzen)",
            "effect": "Stark erhoehtes Risiko fuer kognitive Stoerungen, akute Verwirrtheit, Delir, Stuerze, Obstipation und Harnverhalt.",
            "mechanism": "Additive Blockade zentraler und peripherer Muskarinrezeptoren durch gleichzeitige Einnahme mehrerer anticholinerg wirksamer Wirkstoffe."
        })

    # 2. QT-Verlaengerung
    qt_prolonging_drugs = []
    for d, codes in atc_map.items():
        if any(c.startswith("J01FA") or c.startswith("J01MA") or 
               c.startswith("C01B") or c.startswith("N05A") or 
               c.startswith("N06AB") for c in codes):
            qt_prolonging_drugs.append(d)

    if len(qt_prolonging_drugs) >= 2:
        synergies.append({
            "type": "Kardiale QT-Verlaengerung",
            "drugs": qt_prolonging_drugs,
            "severity": "Hoch",
            "title": f"Kumulative QT-Zeit-Verlaengerung ({len(qt_prolonging_drugs)} Substanzen)",
            "effect": "Kritisches Risiko fuer Torsade-de-Pointes-Arrhythmien und ploetzlichen Herztod.",
            "mechanism": "Synergistische Hemmung der myokardialen Kaliumkanaele (hERG/IKr) verzoegert die ventrikulaere Repolarisation."
        })

    # 3. ZNS-Depression (Sedativa + Opioide)
    zns_depressant_drugs = []
    for d, codes in atc_map.items():
        if any(c.startswith("N02A") or c.startswith("N05B") or 
               c.startswith("N05C") or c.startswith("N03AE") for c in codes):
            zns_depressant_drugs.append(d)

    if len(zns_depressant_drugs) >= 2:
        synergies.append({
            "type": "Kumulative ZNS-Depression",
            "drugs": zns_depressant_drugs,
            "severity": "Hoch",
            "title": f"Kumulative ZNS- & Atemdepression ({len(zns_depressant_drugs)} Substanzen)",
            "effect": "Gefahr exzessiver Sedierung, schwerer Koordinationsstoerungen, Stuerzen und potentiell letaler Hypoventilation.",
            "mechanism": "Synergistische zentralnervöse Daempfung ueber erhoehte GABAerge Transmission und mu-Opioid-Rezeptoraktivierung."
        })

    return synergies


def save_to_cache(drug_a, drug_b, data):
    """Speichert ein neu ermitteltes Analyseergebnis in SQLite."""
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
    """Gibt die Gesamtzahl aller hinterlegten Paar-Interaktionen zurueck."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM "interactions"')
            return cursor.fetchone()[0]
    except Exception:
        return 0


def get_total_class_rules_count():
    """Gibt die Gesamtanzahl aktiver ATC- und Phyto-Regeln zurueck."""
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM "class_rules"')
            c_rules = cursor.fetchone()[0]
            cursor.execute('SELECT COUNT(*) FROM "phytomed_rules"')
            p_rules = cursor.fetchone()[0]
            return c_rules + p_rules
    except Exception:
        return 0


def get_all_cached_drugs():
    """Liest alle Substanzen fuer Autocomplete aus."""
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
        print(f"Fehler beim Laden der Wirkstoffe: {e}")
        return []