import sqlite3
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "interactions.db")

# Priscus 2.0 / PIM-Referenzkatalog
PRISCUS_PIM_CATALOG = {
    "diazepam": {
        "reason": "Lange Eliminationshalbwertszeit (bis 100 h) und aktive Metaboliten.",
        "risk": "Hohes Risiko fuer Hangover, Ataxie, Sedierung, Stuerze und Frakturen.",
        "alternative": "Kurzwirksame Alternativen ohne aktive Metaboliten (z. B. Lorazepam, Oxazepam) zeitlich streng befristet."
    },
    "amitriptyline": {
        "reason": "Sehr ausgepraegte anticholinerge und sedierende Eigenschaften.",
        "risk": "Kognitiver Abbau, akutes Delir, Harnverhalt, Engwinkelglaukom, orthostatische Hypotonie und Stuerze.",
        "alternative": "SSRI (z. B. Sertralin, Citalopram) oder SNRI unter Hyponatriaemie-Monitoring."
    },
    "clomipramine": {
        "reason": "Starke anticholinerge und kardiotoxische Last.",
        "risk": "Delir, erhoehtes Sturzrisiko und Arrhythmien.",
        "alternative": "Moderne Antidepressiva (SSRI/SNRI)."
    },
    "doxepin": {
        "reason": "Starke Anticholinergika-Wirkung und ZNS-Daempfung.",
        "risk": "Kognitive Beeintraechtigung und kardiale Leitungsverzoegerung.",
        "alternative": "Nicht-medikamentoese Schlafhygiene, Melatonin oder kurzfristig Z-Substanzen in halber Dosis."
    },
    "oxybutynin": {
        "reason": "Ueberwindet die Blut-Hirn-Schranke, massive muskarinische Blockade.",
        "risk": "Verstaerkung von Demenzsymptomen, akute Verwirrtheitszustaende und Mundtrockenheit.",
        "alternative": "Trospiumchlorid (quartaeres Amin, passiert Bluthirnschranke kaum) oder Mirabegron."
    },
    "indometacin": {
        "reason": "Sehr starke ZNS-Nebenwirkungen unter den NSAR.",
        "risk": "Kopfschmerzen, Schwindel, Verwirrtheit sowie schwere GI-Ulkus- und renale Risiken.",
        "alternative": "Ibuprofen in niedrigster wirksamer Dosis mit PPI oder Paracetamol/Metamizol."
    },
    "glibenclamide": {
        "reason": "Lange Wirkdauer und renale Akkumulation aktiver Metaboliten.",
        "risk": "Gefahr protrahierter, lebensbedrohlicher Hypoglykaemien.",
        "alternative": "Metformin (bei ausreichender Nierenfunktion), DPP-4-Inhibitoren oder SGLT-2-Inhibitoren."
    }
}

# Substanzen mit renaler Dosisanpassung
RENAL_DOSE_CATALOG = {
    "metformin": {
        "cutoff_severe": 30,
        "cutoff_moderate": 45,
        "message_severe": "Kontraindiziert bei eGFR < 30 ml/min wegen des Risikos einer lebensbedrohlichen Laktatazidose.",
        "message_moderate": "Dosisreduktion erforderlich (max. 1000 mg/Tag bei eGFR 30-44 ml/min) und engmaschige Nierenfunktionskontrolle."
    },
    "spironolactone": {
        "cutoff_severe": 30,
        "cutoff_moderate": 50,
        "message_severe": "Kontraindiziert bei eGFR < 30 ml/min oder Serum-K > 5.0 mmol/l wegen exzessivem Hyperkaliaemierisiko.",
        "message_moderate": "Hohes Hyperkaliaemierisiko: Dosis auf max. 25 mg/Tag limitieren und Serum-Kalium woechentlich monitoren."
    },
    "digoxin": {
        "cutoff_severe": 30,
        "cutoff_moderate": 50,
        "message_severe": "Hauptsaechlich renal eliminiert. Massive Akkumulations- und Intoxikationsgefahr (AV-Block, Arrhythmien). TDM zwingend erforderlich.",
        "message_moderate": "Dosisanpassung und engmaschiges Monitoring der Talspiegel erforderlich."
    },
    "rivaroxaban": {
        "cutoff_severe": 15,
        "cutoff_moderate": 50,
        "message_severe": "Kontraindiziert bei eGFR < 15 ml/min.",
        "message_moderate": "Dosisreduktion von 20 mg auf 15 mg 1x taeglich bei eGFR 15-49 ml/min erforderlich."
    },
    "allopurinol": {
        "cutoff_severe": 30,
        "cutoff_moderate": 50,
        "message_severe": "Akkumulation des toxischen Metaboliten Oxipurinol (Gefahr eines lebensbedrohlichen DRESS-Syndroms). Dosis auf max. 100 mg/Tag limitieren.",
        "message_moderate": "Dosisreduktion und engmaschige Harns resultContent-Kontrolle empfohlen."
    }
}


def init_db():
    """Erstellt Tabellen und Klassenregeln."""
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

        CORE_CLASS_RULES = [
            ("N02A", "N05BA", "Opioide", "Benzodiazepine", "Hoch", "Zentralnervensystem / Atmung",
             "Lebensbedrohliche Atemdepression, Koma und letale Sedierung.",
             "Synergistische zentralnervöse Dämpfung an mu-Opioid- und GABAA-Rezeptoren."),
            ("N02A", "N05CD", "Opioide", "Benzodiazepin-Derivate", "Hoch", "Zentralnervensystem / Atmung",
             "Schwere ZNS-Depression und Hypoventilation.",
             "Synergistische Atemdepressionsverstärkung."),
            ("N02A", "N05CF", "Opioide", "Z-Substanzen (Hypnotika)", "Hoch", "Zentralnervensystem / Atmung",
             "Ausgepraegte Sedierung und erhoehtes Atemstillstandrisiko.",
             "Additive Verstärkung inhibitorischer GABAerger und opioider Signalwege."),
            ("C01AA", "C08D", "Digitalisglykoside", "Calciumantagonisten (Verapamil/Diltiazem)", "Hoch", "Kardiovaskulaer / Rhythmus",
             "Digoxin-Intoxikation mit AV-Block und ventrikulaeren Arrhythmien.",
             "Hemmung des renalen und biliaeren P-Glykoprotein-Transporters erhoeht Digoxin-Spiegel um 50-100%."),
            ("C01AA", "C01BD", "Digitalisglykoside", "Klasse-III-Antiarrhythmika (Amiodaron)", "Hoch", "Kardiovaskulaer / Rhythmus",
             "Akute Digitalistoxizitaet und Bradykardie.",
             "Amiodaron inhibiert P-gp-vermittelten renalen Digoxintransport signifikant."),
            ("N06AB", "B01A", "SSRI-Antidepressiva", "Antithrombotika (DOAK/VKA/ASS)", "Moderat", "Haemostase / Gastrointestinal",
             "Verdopplung bis Verdreifachung des oberen Magen-Darm-Blutungsrisikos.",
             "SSRI blockieren den SERT-Transporter auf Thrombozyten und entleeren deren Serotoningranula, was die Blutstillung beeintraechtigt."),
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
    sorted_pair = sorted([drug_a.strip().lower(), drug_b.strip().lower()])
    return f"{sorted_pair[0]}___{sorted_pair[1]}"


def check_cache(drug_a, drug_b):
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
    codes = get_all_atc_codes(drug_name)
    return codes[0] if codes else None


def get_drug_pharmacology(drug_name):
    if not drug_name:
        return None

    clean = drug_name.strip()
    clean_no_emoji = re.sub(r'[\U00010000-\U0010ffff]', '', clean).strip()
    search_terms = [clean, clean_no_emoji]
    if "(" in clean and ")" in clean:
        inside = clean[clean.find("(") + 1:clean.find(")")].strip()
        search_terms.extend([inside, clean.split("(")[0].strip()])

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        for term in search_terms:
            cursor.execute("""
                SELECT name, atc_code, drug_class, organ_system, metabolism
                FROM "drugs"
                WHERE name = ? COLLATE NOCASE OR name LIKE ? COLLATE NOCASE
                LIMIT 1
            """, (term, f"{term}%"))
            row = cursor.fetchone()
            if row:
                return {
                    "name": row[0],
                    "atc_code": row[1],
                    "drug_class": row[2] if row[2] else "Standard-Wirkstoff",
                    "organ_system": row[3] if row[3] else "Systemisch",
                    "metabolism": row[4] if row[4] else "Renal / Hepatisch"
                }

    return None


def generate_intake_schedule(active_drugs):
    """
    Erstellt einen chronopharmakologisch optimierten Einnahmeplan
    unter Beruecksichtigung von Chelatbildungsabstaenden und Organpeaks.
    """
    schedule = {
        "Morgens (nüchtern / 30 Min. vor dem Frühstück)": [],
        "Morgens (zum Frühstück)": [],
        "Mittags (mit Mahlzeit / 2-3h Abstand zu Mineralstoffen)": [],
        "Abends (zum Abendessen)": [],
        "Zur Nacht (vor dem Schlafen)": []
    }

    has_chelator = any(d.lower() in ["milchprodukte & calciumreiches wasser 🥛", "eisenpraeparate / eisentabletten (fe2+/fe3+) 🩸", "magnesiumpraeparate (hochdosiert) ⚡"] or "iron" in d.lower() or "calcium" in d.lower() for d in active_drugs)

    for drug in active_drugs:
        d_lower = drug.lower().strip()
        codes = get_all_atc_codes(drug)
        primary_code = codes[0] if codes else ""

        # 1. Schilddruese & Bisphosphonate -> Morgens nuechtern
        if primary_code.startswith("H03AA") or primary_code.startswith("M05BA") or "thyrox" in d_lower:
            schedule["Morgens (nüchtern / 30 Min. vor dem Frühstück)"].append({
                "drug": drug,
                "note": "Nüchtern mit Leitungswasser (min. 30 Min. vor Kaffee/Frühstück). Unbedingt getrennt von Eisen/Calcium!"
            })
        # 2. Schleifendiuretika & Thiazide -> Morgens zum Fruehstueck (Nykturie-Vermeidung)
        elif primary_code.startswith("C03") or "torasemid" in d_lower or "furosemid" in d_lower or "hydrochlorothiazid" in d_lower:
            schedule["Morgens (zum Frühstück)"].append({
                "drug": drug,
                "note": "Morgens einnehmen, um nächtlichen Harndrang (Nykturie) zu vermeiden."
            })
        # 3. Blutdruck-Basismedikation (ACE/Sartane/Betablocker) -> Morgens
        elif primary_code.startswith("C09") or primary_code.startswith("C07") or primary_code.startswith("C08"):
            schedule["Morgens (zum Frühstück)"].append({
                "drug": drug,
                "note": "Regelmäßig zum Frühstück für stabilen 24h-Blutdruckverlauf."
            })
        # 4. Chelatbildner (Eisen, Mineralstoffe) -> Mittags (falls L-Thyroxin morgens eingenommen wird)
        elif "eisen" in d_lower or "iron" in d_lower or primary_code == "PHYTO_IRON" or "magnesium" in d_lower:
            schedule["Mittags (mit Mahlzeit / 2-3h Abstand zu Mineralstoffen)"].append({
                "drug": drug,
                "note": "Mindestens 2-3 Stunden zeitlicher Abstand zu L-Thyroxin und Antibiotika."
            })
        # 5. Fluorchinolone / Tetracycline -> Mittags
        elif primary_code.startswith("J01M") or primary_code.startswith("J01AA"):
            schedule["Mittags (mit Mahlzeit / 2-3h Abstand zu Mineralstoffen)"].append({
                "drug": drug,
                "note": "Mit reichlich Wasser. 2-3 Stunden Abstand zu Milch, Joghurt oder Mineralstoff-Tabletten."
            })
        # 6. Statine -> Abends (hoechste hepatische Enzymsynthese nachts)
        elif primary_code.startswith("C10AA") or "statin" in d_lower:
            schedule["Abends (zum Abendessen)"].append({
                "drug": drug,
                "note": "Optimale lipidsenkende Wirksamkeit bei abendlicher Einnahme."
            })
        # 7. Sedativa, Z-Substanzen & Hypnotika -> Zur Nacht
        elif primary_code.startswith("N05C") or primary_code.startswith("N05BA") or "lorazepam" in d_lower or "diazepam" in d_lower or "zopiclon" in d_lower:
            schedule["Zur Nacht (vor dem Schlafen)"].append({
                "drug": drug,
                "note": "Direkt vor dem Schlafengehen einnehmen. Sturzrisiko beim nächtlichen Aufstehen beachten!"
            })
        # Standard: Mittags oder Morgens
        else:
            schedule["Morgens (zum Frühstück)"].append({
                "drug": drug,
                "note": "Mit etwas Flüssigkeit zu oder nach der Mahlzeit."
            })

    # Leere Zeitschienen entfernen
    return {k: v for k, v in schedule.items() if len(v) > 0}


def check_priscus_pim(active_drugs):
    findings = []
    for d in active_drugs:
        d_lower = d.strip().lower()
        if d_lower in PRISCUS_PIM_CATALOG:
            data = PRISCUS_PIM_CATALOG[d_lower]
            findings.append({
                "drug": d,
                "reason": data["reason"],
                "risk": data["risk"],
                "alternative": data["alternative"]
            })
    return findings


def check_renal_risks(active_drugs, egfr):
    if egfr >= 60:
        return []

    alerts = []
    for d in active_drugs:
        d_lower = d.strip().lower()
        if d_lower in RENAL_DOSE_CATALOG:
            info = RENAL_DOSE_CATALOG[d_lower]
            if egfr < info["cutoff_severe"]:
                alerts.append({
                    "drug": d,
                    "severity": "Hoch",
                    "cutoff": info["cutoff_severe"],
                    "message": info["message_severe"]
                })
            elif egfr < info["cutoff_moderate"]:
                alerts.append({
                    "drug": d,
                    "severity": "Moderat",
                    "cutoff": info["cutoff_moderate"],
                    "message": info["message_moderate"]
                })
    return alerts


def check_phytomed_rules(drug_a, drug_b):
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

    # 3. ZNS-Depression
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
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM "interactions"')
            return cursor.fetchone()[0]
    except Exception:
        return 0


def get_total_class_rules_count():
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