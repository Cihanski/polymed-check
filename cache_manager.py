import os
import sqlite3
import requests

DB_PATH = os.path.join(os.path.dirname(__file__), "interactions.db")


def get_db_connection():
    """Erstellt eine Thread-sichere Verbindung zur lokalen SQLite-Datenbank."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialisiert das Datenbankschema und fuehrt noetige Migrationen durch."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            drug_a TEXT NOT NULL,
            drug_b TEXT NOT NULL,
            severity TEXT NOT NULL,
            system TEXT NOT NULL,
            effect TEXT NOT NULL,
            mechanism TEXT,
            advice TEXT,
            source TEXT DEFAULT 'Lokal verifiziert',
            UNIQUE(drug_a, drug_b)
        )
    """)

    # Fehlende Spalten in bestehenden interactions.db automatisch nachruesten
    cursor.execute("PRAGMA table_info(interactions)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    if "advice" not in existing_cols:
        cursor.execute("ALTER TABLE interactions ADD COLUMN advice TEXT")
    if "mechanism" not in existing_cols:
        cursor.execute("ALTER TABLE interactions ADD COLUMN mechanism TEXT")
    if "source" not in existing_cols:
        cursor.execute("ALTER TABLE interactions ADD COLUMN source TEXT DEFAULT 'Lokal verifiziert'")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pharmacology (
            drug_name TEXT PRIMARY KEY,
            drug_class TEXT,
            elimination_route TEXT,
            atc_code TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS class_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_a TEXT NOT NULL,
            class_b TEXT NOT NULL,
            severity TEXT NOT NULL,
            system TEXT NOT NULL,
            effect TEXT NOT NULL,
            mechanism TEXT,
            advice TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS phyto_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phyto_name TEXT NOT NULL,
            interacts_with_type TEXT NOT NULL,
            target_identifier TEXT NOT NULL,
            severity TEXT NOT NULL,
            system TEXT NOT NULL,
            effect TEXT NOT NULL,
            mechanism TEXT,
            advice TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS atc_codes (
            drug_name TEXT NOT NULL,
            atc_code TEXT NOT NULL,
            PRIMARY KEY(drug_name, atc_code)
        )
    """)

    conn.commit()
    conn.close()


def get_all_atc_codes(drug_name):
    """Ermittelt alle hinterlegten ATC-Codes fuer einen Wirkstoff (defensiv gegen fehlende Tabellen)."""
    d_clean = drug_name.lower().strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT atc_code FROM atc_codes WHERE LOWER(drug_name) = ?", (d_clean,))
        rows = cursor.fetchall()
        return [r["atc_code"] for r in rows]
    except sqlite3.OperationalError:
        # Falls Tabelle in der Cloud-DB noch fehlt, automatisch nachziehen
        init_database()
        try:
            cursor.execute("SELECT atc_code FROM atc_codes WHERE LOWER(drug_name) = ?", (d_clean,))
            rows = cursor.fetchall()
            return [r["atc_code"] for r in rows]
        except Exception:
            return []
    finally:
        conn.close()


def get_drug_pharmacology(drug_name):
    """Liefert das pharmakologische Profil (Klasse, Elimination, ATC)."""
    d_clean = drug_name.lower().strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM pharmacology WHERE LOWER(drug_name) = ?", (d_clean,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def fetch_exact_cache(drug_a, drug_b):
    """Prueft die SQLite-Datenbank auf eine direkte 1:1 Interaktion."""
    da, db = drug_a.lower().strip(), drug_b.lower().strip()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM interactions 
        WHERE (LOWER(drug_a) = ? AND LOWER(drug_b) = ?)
           OR (LOWER(drug_a) = ? AND LOWER(drug_b) = ?)
    """, (da, db, db, da))
    row = cursor.fetchone()
    conn.close()

    if row:
        res = dict(row)
        res["pair"] = (drug_a, drug_b)
        return res
    return None


def check_phyto_and_cation_rules(drug_a, drug_b):
    """Prueft Komplexierungs- und Phyto-Regeln (z.B. Eisen/Calcium-Chelate, Johanniskraut)."""
    da, db = drug_a.lower().strip(), drug_b.lower().strip()

    cations = ["eisen", "calcium", "magnesium", "zink", "milch", "antazida"]
    quinolones_and_tetras = ["ciprofloxacin", "levofloxacin", "moxifloxacin", "doxycyclin", "tetracyclin"]
    thyroid = ["l-thyroxin", "levothyroxin"]

    is_cat_a = any(c in da for c in cations)
    is_cat_b = any(c in db for c in cations)

    if (is_cat_a and any(q in db for q in quinolones_and_tetras)) or (is_cat_b and any(q in da for q in quinolones_and_tetras)):
        return {
            "pair": (drug_a, drug_b),
            "severity": "Hoch",
            "system": "Resorption / Chelatbildung",
            "effect": "Dramatische Verringerung der Bioverfuegbarkeit des Antibiotikums durch Bildung unloeslicher Chelatkomplexe.",
            "mechanism": "Mehrwertige Kationen binden die funktionellen Ketogruppen des Antibiotikums im Darmlumen.",
            "advice": "Mindestens 2 bis 3 Stunden zeitlichen Abstand zwischen der Einnahme einhalten.",
            "source": "Kationen-Komplexierungs-Regelwerk"
        }

    if (is_cat_a and any(t in db for t in thyroid)) or (is_cat_b and any(t in da for t in thyroid)):
        return {
            "pair": (drug_a, drug_b),
            "severity": "Hoch",
            "system": "Resorption / Chelatbildung",
            "effect": "Verminderte Aufnahme von L-Thyroxin fuehrt zu unzureichender Schilddruesenhormonsubstitution.",
            "mechanism": "Unloesliche Adsorptionskomplexe im Gastrointestinaltrakt hemmen die enterale Resorption.",
            "advice": "L-Thyroxin morgens nuechtern 30 Min vor dem Fruehstueck einnehmen; Mineralstoffe fruehestens 2-4 Stunden spaeter.",
            "source": "Kationen-Komplexierungs-Regelwerk"
        }

    phyto_inducers = ["johanniskraut", "hypericum"]
    cyp3a4_substrates = ["simvastatin", "atorvastatin", "cyclosporin", "tacrolimus", "apixaban", "rivaroxaban"]

    is_ind_a = any(p in da for p in phyto_inducers)
    is_ind_b = any(p in db for p in phyto_inducers)

    if (is_ind_a and any(s in db for s in cyp3a4_substrates)) or (is_ind_b and any(s in da for s in cyp3a4_substrates)):
        return {
            "pair": (drug_a, drug_b),
            "severity": "Hoch",
            "system": "Hepatische Induktion / CYP3A4",
            "effect": "Signifikanter Wirkungsverlust des Begleitmedikaments durch beschleunigten Abbau.",
            "mechanism": "Hyperforin induziert potent die Expression von CYP3A4 und P-Glykoprotein.",
            "advice": "Kombination meiden; auf alternative pflanzliche oder synthetische Praeparate ausweichen.",
            "source": "Phytomedizin-Regelwerk"
        }

    return None


def check_class_level_rules(drug_a, drug_b):
    """Gleicht Wirkstoffklassen und ATC-Codes auf Klassenebene ab."""
    da, db = drug_a.lower().strip(), drug_b.lower().strip()
    atc_a = get_all_atc_codes(da)
    atc_b = get_all_atc_codes(db)

    # 1. Opioid + Benzodiazepin
    is_opioid = any(c.startswith("N02A") for c in atc_a + atc_b) or any(o in da or o in db for o in ["tilidin", "tramadol", "morphin", "fentanyl", "oxycodon"])
    is_benzo = any(c.startswith("N05BA") or c.startswith("N05CF") for c in atc_a + atc_b) or any(b in da or b in db for b in ["diazepam", "lorazepam", "oxazepam", "zolpidem"])

    if is_opioid and is_benzo:
        return {
            "pair": (drug_a, drug_b),
            "severity": "Hoch",
            "system": "ZNS / Atemdepression",
            "effect": "Potenzierte ZNS-Daempfung, erhoehtes Koma- und toedliches Atemdepressionsrisiko.",
            "mechanism": "Synergistische additive GABAerge und opioide Hemmung pontomedullaerer Atemneurone.",
            "advice": "Kombination nach Moeglichkeit vermeiden; Dosis streng titrieren.",
            "source": "Klassenregel Opioid-Benzodiazepin"
        }

    # 2. Digoxin + Verapamil (P-gp Hemmung)
    is_digoxin = "digoxin" in da or "digoxin" in db
    is_verapamil = "verapamil" in da or "verapamil" in db

    if is_digoxin and is_verapamil:
        return {
            "pair": (drug_a, drug_b),
            "severity": "Hoch",
            "system": "Kinetik / P-Glykoprotein & AV-Knoten",
            "effect": "Verdoppelung des Digoxin-Plasmaspiegels mit Gefahr von Intoxikation und AV-Blockierungen.",
            "mechanism": "Inhibition des renalen P-Glykoprotein-Transporters plus additive negativ dromotrope Wirkung.",
            "advice": "Digoxin-Dosis halbieren, Plasmaspiegel und EKG engmaschig kontrollieren.",
            "source": "Klassenregel Herzglykoside"
        }

    return None


def fetch_fda_interaction(drug_a, drug_b):
    """
    Fragt bei Bedarf die openFDA Drug Labeling API ab und speichert
    positive Treffer direkt lokal in SQLite, um Folgeanfragen zu vermeiden.
    """
    da, db = drug_a.lower().strip(), drug_b.lower().strip()
    try:
        url = f"https://api.fda.gov/drug/label.json?search=drug_interactions:{da}+AND+openfda.brand_name:{db}&limit=1"
        res = requests.get(url, timeout=3.0)
        if res.status_code == 200:
            data = res.json()
            if "results" in data and len(data["results"]) > 0:
                result = {
                    "pair": (drug_a, drug_b),
                    "severity": "Moderat",
                    "system": "openFDA Drug Label",
                    "effect": f"Dokumentierter Hinweis in den FDA-Produktinformationen zu {drug_a.capitalize()} und {drug_b.capitalize()}.",
                    "mechanism": "Pharmakokinetische oder -dynamische Warnung laut FDA-Herstellerdossier.",
                    "advice": "Klinische Relevanz pruefen und engmaschig auf unerwuenschte Wirkungen ueberwachen.",
                    "source": "openFDA (Auto-Cache)"
                }
                # Positiven Treffer sofort lokal sichern fuer Offline- und High-Speed-Zugriff
                try:
                    save_to_cache(
                        drug_a=da,
                        drug_b=db,
                        data_or_severity=result["severity"],
                        system=result["system"],
                        effect=result["effect"],
                        mechanism=result["mechanism"],
                        advice=result["advice"],
                        source=result["source"]
                    )
                except Exception:
                    pass
                return result
    except Exception:
        # Bei Timeout oder fehlendem Netz geraeuschlos abfangen
        pass
    return None


def check_interaction_pair(drug_a, drug_b):
    """Fuehrt alle Pruefstufen sequenziell fuer ein Wirkstoffpaar aus."""
    # Stufe 1: SQLite Exakt
    res = fetch_exact_cache(drug_a, drug_b)
    if res:
        return res

    # Stufe 2: Kation / Phyto
    res = check_phyto_and_cation_rules(drug_a, drug_b)
    if res:
        return res

    # Stufe 3: Klassenregeln
    res = check_class_level_rules(drug_a, drug_b)
    if res:
        return res

    # Stufe 4: openFDA Fallback
    res = fetch_fda_interaction(drug_a, drug_b)
    if res:
        return res

    return None


def check_multidrug_synergies(active_drugs):
    """
    Erkennt pharmakodynamische und kinetische Synergien:
    1. Kardiale QT-Verlaengerung
    2. Anticholinerge Last
    3. ZNS- & Atemdepression
    4. Serotonin-Syndrom
    5. DOAK-Blutungsrisiko via CYP3A4/P-gp
    """
    synergies = []
    if len(active_drugs) < 2:
        return synergies

    def match_substance(drug_name, target_keywords):
        d_lower = drug_name.lower()
        return any(k.lower() in d_lower for k in target_keywords)

    # 1. Kardiale QT-Verlaengerung
    qt_keywords = [
        "ciprofloxacin", "levofloxacin", "moxifloxacin", 
        "amiodaron", "amiodarone", "sotalol", "dronedaron", "dronedarone",
        "clarithromycin", "erythromycin", "azithromycin",
        "haloperidol", "citalopram", "escitalopram", "methadon", "methadone"
    ]
    matched_qt = []
    for d in active_drugs:
        atc_codes = get_all_atc_codes(d)
        is_qt_atc = any(c.startswith("C01B") or c.startswith("J01MA") or c.startswith("N05A") for c in atc_codes)
        if match_substance(d, qt_keywords) or is_qt_atc:
            if d not in matched_qt:
                matched_qt.append(d)

    if len(matched_qt) >= 2:
        synergies.append({
            "type": "Kardiale QT-Verlaengerung",
            "title": "Kumulatives Torsade-de-Pointes-Risiko (QT-Verlaengerung)",
            "severity": "Hoch",
            "drugs": matched_qt,
            "effect": "Gleichzeitige Gabe mehrerer QT-verlaengernder Arzneistoffe erhoeht das Risiko ventrikulaerer Tachyarrhythmien drastisch.",
            "mechanism": "Additive Blockade des kardialen hERG-Kaliumkanaels (IKr-Strom) waehrend der myokardialen Repolarisationsphase."
        })

    # 2. Anticholinerge Last
    anticholinergic_keywords = [
        "amitriptylin", "amitriptyline", "doxepin", "nortriptylin",
        "oxybutynin", "tolterodin", "solifenacin", "darifenacin",
        "diphenhydramin", "dimenhydrinat", "promethazin", "clozapin"
    ]
    matched_anti = []
    for d in active_drugs:
        atc_codes = get_all_atc_codes(d)
        is_anti_atc = any(c.startswith("N06AA") or c.startswith("G04BD") for c in atc_codes)
        if match_substance(d, anticholinergic_keywords) or is_anti_atc:
            if d not in matched_anti:
                matched_anti.append(d)

    if len(matched_anti) >= 2:
        synergies.append({
            "type": "Anticholinerge Last",
            "title": "Hohe kumulative anticholinerge Last",
            "severity": "Moderat",
            "drugs": matched_anti,
            "effect": "Verstaerkung anticholinerger Nebenwirkungen: Mundtrockenheit, Obstipation, Harnverhalt, Verwirrtheitszustaende und erhoehtes Sturzrisiko.",
            "mechanism": "Kompetitive Antagonisierung zentraler und peripherer Muskarinrezeptoren (M1-M5)."
        })

    # 3. ZNS- & Atemdepression
    sedative_keywords = [
        "morphin", "morphine", "fentanyl", "oxycodon", "oxycodone", "tilidin", "tramadol",
        "diazepam", "lorazepam", "oxazepam", "zolpidem", "zopiclon"
    ]
    matched_sed = []
    for d in active_drugs:
        atc_codes = get_all_atc_codes(d)
        is_sed_atc = any(c.startswith("N02A") or c.startswith("N05BA") or c.startswith("N05CF") for c in atc_codes)
        if match_substance(d, sedative_keywords) or is_sed_atc:
            if d not in matched_sed:
                matched_sed.append(d)

    if len(matched_sed) >= 2:
        synergies.append({
            "type": "Kumulative ZNS-Depression",
            "title": "Verstaerkte Sedierung & Atemdepression",
            "severity": "Hoch",
            "drugs": matched_sed,
            "effect": "Potenzierte ZNS-Daempfung, erhoehte Sturzgefahr und kritisches Risiko einer zentralen Atemdepression.",
            "mechanism": "Synergistische Daempfung des Atemzentrums ueber GABA_A- und mu-Opioid-Rezeptor-Signalwege."
        })

    # 4. Serotonin-Syndrom
    serotonin_keywords = [
        "citalopram", "escitalopram", "sertralin", "sertraline", "fluoxetin", "fluoxetine",
        "paroxetin", "paroxetine", "venlafaxin", "venlafaxine", "duloxetin", "duloxetine",
        "tramadol", "tilidin", "fentanyl", "sumatriptan", "zolmitriptan", "johanniskraut",
        "hypericum", "linezolid", "moclobemid", "moclobemide"
    ]
    matched_sero = []
    for d in active_drugs:
        atc_codes = get_all_atc_codes(d)
        is_sero_atc = any(c.startswith("N06AB") or c.startswith("N06AX") for c in atc_codes)
        if match_substance(d, serotonin_keywords) or is_sero_atc:
            if d not in matched_sero:
                matched_sero.append(d)

    if len(matched_sero) >= 2:
        synergies.append({
            "type": "Serotonin-Syndrom",
            "title": "Kritisches Serotonin-Syndrom-Risiko",
            "severity": "Hoch",
            "drugs": matched_sero,
            "effect": "Potenziell lebensbedrohliche serotonerge Ueberstimulation: Hyperthermie, Myoklonien, Tremor, autonome Instabilitaet und Verwirrtheit.",
            "mechanism": "Additive Erhoehung der intrasynaptischen Serotoninkonzentration ueber Wiederaufnahmehemmung (SERT) und/oder MAO-Hemmung."
        })

    # 5. DOAK-Blutungsrisiko via CYP3A4 / P-gp
    doac_keywords = ["apixaban", "rivaroxaban", "edoxaban", "dabigatran"]
    strong_inhibitor_keywords = [
        "clarithromycin", "erythromycin", "itraconazol", "itraconazole",
        "ketoconazol", "ketoconazole", "verapamil", "diltiazem", "dronedaron"
    ]
    matched_doac = [d for d in active_drugs if match_substance(d, doac_keywords)]
    matched_inhibitor = [d for d in active_drugs if match_substance(d, strong_inhibitor_keywords)]

    if matched_doac and matched_inhibitor:
        synergies.append({
            "type": "DOAK-Interaktion",
            "title": "Akutes DOAK-Blutungsrisiko (CYP3A4 / P-gp-Inhibition)",
            "severity": "Hoch",
            "drugs": matched_doac + matched_inhibitor,
            "effect": "Massiver Anstieg der Plasmaspiegel des oralen Antikoagulans mit erhoehtem Risiko schwerer gastrointestinaler oder intrakranieller Blutungen.",
            "mechanism": "Kompetitive Inhibition des intestinalen/hepatischen Effluxtransporters P-Glykoprotein (P-gp) und des Cytochrom-P450-Enzyms CYP3A4."
        })

    return synergies


def check_priscus_pim(active_drugs):
    """
    Gleicht aktive Wirkstoffe gegen den erweiterten PRISCUS 2.0-Katalog ab.
    Liefert PIM-Warnungen, Begruendungen und leitliniengestuetzte Alternativen fuer geriatrische Patienten.
    """
    alerts = []
    if not active_drugs:
        return alerts

    priscus_db = {
        # --- Sedativa, Hypnotika & Benzodiazepine ---
        "diazepam": {
            "risk": "Sturzgefahr, Sedierung, kognitive Einschraenkung, Hangover-Effekt durch lange Halbwertszeit.",
            "reason": "Kumulation aktiver Metaboliten (Nordazepam t1/2 bis zu 100h) im Alter.",
            "alternative": "Bei zwingender Indikation kurz wirksame Benzodiazepine ohne aktive Metaboliten (z. B. Lorazepam, Oxazepam) niedrig dosiert und streng befristet."
        },
        "flurazepam": {
            "risk": "Schwere Sedierung am Folgetag, erhoehte Fraktur- und Sturzgefahr.",
            "reason": "Extrem lange Eliminationshalbwertszeit aktiver Metaboliten.",
            "alternative": "Nicht-medikamentoese Schlafhygiene, Melatonin oder streng befristet Lorazepam/Oxazepam."
        },
        "chlordiazepoxid": {
            "risk": "Ueberhangsedierung, Verwirrtheit, Sturz- und Frakturrisiko.",
            "reason": "Lange Eliminationshalbwertszeit und verlangsamte hepatische Clearance.",
            "alternative": "Kurzwirksame Alternativen wie Oxazepam oder Lorazepam."
        },
        "prazepam": {
            "risk": "Lange Sedierungsdauer, Ataxie, erhoehtes Sturzrisiko.",
            "reason": "Metabolisierung zu langlebigem Nordazepam.",
            "alternative": "Oxazepam oder Lorazepam in minimaler Dosierung."
        },
        "zolpidem": {
            "risk": "Naechtliche Verwirrtheit, Schlafwandeln, Sturzgefahr und Toleranzentwicklung.",
            "reason": "Z-Substanzen weisen im Alter ein mit Benzodiazepinen vergleichbares Sturzrisiko auf.",
            "alternative": "Kognitive Verhaltenstherapie fuer Insomnie (KVT-I), Melatonin."
        },
        "zopiclon": {
            "risk": "Morgendlicher Hangover, Geschmacksstoerungen, Stuerze und Abhaengigkeit.",
            "reason": "Verzoegerte Elimination bei eingeschraenkter Nieren- oder Leberfunktion.",
            "alternative": "Schlafhygiene, pflanzliche Baldrian-Praeparate, ggf. Melatonin."
        },

        # --- Antidepressiva mit hoher anticholinerger Last ---
        "amitriptylin": {
            "risk": "Delir, kognitiver Abbau, Harnverhalt, Engwinkelglaukom, Orthostase und QTc-Verlaengerung.",
            "reason": "Sehr starke periphere und zentrale anticholinerge sowie sedierende Wirkung.",
            "alternative": "Sertralin, Citalopram (Dosisdeckelung beachten) oder Mirtazapin bei Schlafstoerung."
        },
        "amitriptyline": {
            "risk": "Delir, kognitiver Abbau, Harnverhalt, Engwinkelglaukom, Orthostase und QTc-Verlaengerung.",
            "reason": "Sehr starke periphere und zentrale anticholinerge sowie sedierende Wirkung.",
            "alternative": "Sertralin, Citalopram (Dosisdeckelung beachten) oder Mirtazapin bei Schlafstoerung."
        },
        "doxepin": {
            "risk": "Starke anticholinerge Nebenwirkungen, Sedierung, orthostatische Hypotonie und Verwirrtheit.",
            "reason": "Hohe Affinitaet zu Muskarin- und H1-Histaminrezeptoren.",
            "alternative": "SSRI (z. B. Sertralin) oder Mirtazapin in niedriger Initialdosis."
        },
        "clomipramin": {
            "risk": "Schwere anticholinerge Effekte, erhoehte Krampfbereitschaft und kardiale Toxizitaet.",
            "reason": "Ausgepraegte anticholinerge und kardiodepressive Eigenschaften.",
            "alternative": "Sertralin oder Escitalopram."
        },
        "imipramin": {
            "risk": "Orthostatische Dysregulation, Delir, Sturz- und Arrhythmierisiko.",
            "reason": "Potenter Muskarinrezeptor-Antagonist mit kardialen Erregungsleitungsstoerungen.",
            "alternative": "Selektive Serotonin-Wiederaufnahmehemmer (SSRI wie Sertralin)."
        },
        "nortriptylin": {
            "risk": "Harnretention, kognitive Einschraenkung, QTc-Verlaengerung.",
            "reason": "Hohe anticholinerge Last bei aelteren Patienten.",
            "alternative": "Sertralin, Duloxetin oder Mirtazapin."
        },

        # --- Urologische Spasmolytika & Anticholinergika ---
        "oxybutynin": {
            "risk": "Zentralnervoese Stoerungen, akutes Delir, kognitiver Verfall, schwere Obstipation.",
            "reason": "Geringe Rezeptorselektivitaet und hohe ZNS-Gaengigkeit ueber die Blut-Hirn-Schranke.",
            "alternative": "Beckenbodentraining, Trospiumchlorid (quartiaeres Amin, passiert BHS schlechter) oder beta-3-Agonist Mirabegron."
        },
        "tolterodin": {
            "risk": "Mundtrockenheit, Verschlechterung einer Demenz, Harnverhalt.",
            "reason": "Anticholinerge Wirkung erschwert die Acetylcholin-Uebertragung im ZNS.",
            "alternative": "Trospiumchlorid oder Mirabegron."
        },
        "solifenacin": {
            "risk": "Anticholinerge Nebenwirkungen, Obstipation und kognitive Beeintraechtigung.",
            "reason": "Kumulative anticholinerge Belastung bei geriatrischen Patienten.",
            "alternative": "Konservative Therapie, ggf. Trospiumchlorid."
        },

        # --- NSAR & Analgetika ---
        "indometacin": {
            "risk": "Schwere gastrointestinale Ulzera/Blutungen, akute Niereninsuffizienz, zentralnervoese Toxizitaet (Kopfschmerzen, Verwirrtheit).",
            "reason": "Potente unselektive COX-Hemmung mit ausgepraegter ZNS-Penetration.",
            "alternative": "Topische NSAR (z. B. Diclofenac-Gel), Paracetamol oder zeitlich streng limitiertes Ibuprofen oral mit PPI-Schutz."
        },
        "ketoprofen": {
            "risk": "Sehr hohes gastrointestinales Blutungs- und Perforationsrisiko.",
            "reason": "Starke COX-1-Hemmung schaedigt die Magenschleimhautbarriere.",
            "alternative": "Topische NSAR, Paracetamol oder orales Ibuprofen in niedriger Dosierung kombiniert mit PPI."
        },
        "piroxicam": {
            "risk": "Gastrointestinale Blutungen, langanhaltende Nierenfunktionsstoerungen.",
            "reason": "Sehr lange Halbwertszeit (ca. 50 Stunden) fuehrt zu Kumulation.",
            "alternative": "Kurzwirksame Analgetika, topische NSAR."
        },
        "acemetacin": {
            "risk": "Gastrointestinale Ulzera, Nierenschaedigung, Schwindel und Verwirrtheit.",
            "reason": "Prodrug von Indometacin mit identischem Nebenwirkungsprofil.",
            "alternative": "Paracetamol, topische Schmerzgele, Metamizol."
        },

        # --- Antiemetika / Prokinetika ---
        "metoclopramid": {
            "risk": "Extrapyramidal-motorische Stoerungen (EPS), Tardive Dyskinesien, Parkinsonoid.",
            "reason": "Zentraler Dopamin-D2-Rezeptor-Antagonismus fuehrt im Alter haeufig zu motorischen Stoerungen.",
            "alternative": "Dimenhydrinat (kurzzeitig), Ondansetron oder Domperidon (unter EKG-Monitoring)."
        },

        # --- Kardiovaskulaere Praeparate ---
        "moxonidin": {
            "risk": "Sedierung, Mundtrockenheit, Bradykardie, Rebound-Hypertonie beim Absetzen.",
            "reason": "Zentraler Sympathikolytikus-Effekt daempft das vegetative Nervensystem.",
            "alternative": "Standard-Antihypertensiva: ACE-Hemmer, Sartane, Calciumantagonisten (Amlodipin) oder Thiaziddiuretika."
        },
        "doxazosin": {
            "risk": "Schwere orthostatische Hypotonie, Schwindel und Synkopen mit Sturzfolge.",
            "reason": "Periphere alpha-1-Blockade stoert die physiologische Kreislaufregulation.",
            "alternative": "Bei BPH: Tamsulosin oder Finasterid. Bei Hypertonie: First-Line Antihypertensiva."
        },
        "terazosin": {
            "risk": "Orthostase, Schwindelattacken, erhoehtes Sturz- und Frakturrisiko.",
            "reason": "Unselektive arterielle und venoese Vasodilation.",
            "alternative": "Tamsulosin (uroselektiv) oder 5-alpha-Reduktasehemmer."
        }
    }

    def match_priscus_name(drug_str):
        d_clean = drug_str.lower().strip()
        for key in priscus_db:
            if key in d_clean:
                return key
        return None

    for d in active_drugs:
        matched_key = match_priscus_name(d)
        if matched_key:
            data = priscus_db[matched_key]
            alerts.append({
                "drug": d,
                "risk": data["risk"],
                "reason": data["reason"],
                "alternative": data["alternative"]
            })

    return alerts


def check_renal_risks(active_drugs, egfr_value):
    """
    Prueft Kontraindikationen und Dosisanpassungen bei eingeschraenkter eGFR.
    """
    alerts = []
    if not egfr_value or egfr_value >= 60:
        return alerts

    for d in active_drugs:
        d_lower = d.lower()

        # Metformin: Dosisanpassung bei < 45, KI bei < 30 ml/min
        if "metformin" in d_lower:
            if egfr_value < 30:
                alerts.append({
                    "drug": d,
                    "severity": "Hoch",
                    "title": "Metformin: Kontraindiziert bei eGFR < 30 ml/min",
                    "message": "Akute Gefahr einer lebensbedrohlichen Laktatazidose durch verminderte renale Elimination.",
                    "action": "Metformin unverzueglich absetzen; Umstellung auf Insulin oder DPP-4-Inhibitor (Linagliptin) erwaegen."
                })
            elif egfr_value < 45:
                alerts.append({
                    "drug": d,
                    "severity": "Moderat",
                    "title": "Metformin: Maximale Tagesdosis reduzieren (eGFR 30-44 ml/min)",
                    "message": "Maximale Tagesdosis auf 1000 mg begrenzen und Nierenwerte vierteljaehrlich kontrollieren.",
                    "action": "Dosis anpassen und Patient auf Fruehzeichen einer Azidose hinweisen."
                })

        # Spironolacton: Hyperkaliaemiegefahr bei < 30 ml/min
        if "spironolacton" in d_lower and egfr_value < 30:
            alerts.append({
                "drug": d,
                "severity": "Hoch",
                "title": "Spironolacton: Kontraindiziert bei schwerer Niereninsuffizienz",
                "message": "Massives Risiko einer kardial bedrohlichen Hyperkaliaemie.",
                "action": "Absetzen oder extrem engmaschige Serum-Kaliumkontrollen."
            })

        # NSAR bei eGFR < 30 ml/min
        if any(nsar in d_lower for nsar in ["ibuprofen", "diclofenac", "naproxen", "etoricoxib"]) and egfr_value < 30:
            alerts.append({
                "drug": d,
                "severity": "Hoch",
                "title": f"{d.capitalize()}: Hohes Risiko eines akuten Nierenversagens",
                "message": "Hemmung vasodilatatorischer Prostaglandine fuehrt zum Einbruch der renalen Perfusion.",
                "action": "NSAR absetzen; Schmerztherapie auf Paracetamol, Metamizol oder Opioide umstellen."
            })

    return alerts


def generate_intake_schedule(active_drugs):
    """
    Erstellt einen evidenzbasierten Einnahmezeitplan mit zeitlicher Entzerrung kritischer Interaktionspaare.
    """
    schedule = {
        "Morgens (Nuechtern)": [],
        "Morgens (Zum Fruehstueck)": [],
        "Mittags": [],
        "Abends": [],
        "Zur Nacht": []
    }

    cations = ["eisen", "calcium", "magnesium", "zink"]
    has_cations = any(any(c in d.lower() for c in cations) for d in active_drugs)

    for d in active_drugs:
        d_lower = d.lower()

        # Schilddruese
        if "l-thyroxin" in d_lower or "levothyroxin" in d_lower:
            schedule["Morgens (Nuechtern)"].append(f"{d.capitalize()} (30 Min vor dem Fruehstueck mit Wasser)")
            continue

        # Protonenpumpenhemmer
        if any(ppi in d_lower for ppi in ["pantoprazol", "omeprazol", "esomeprazol"]):
            schedule["Morgens (Nuechtern)"].append(f"{d.capitalize()} (30-60 Min vor dem Essen)")
            continue

        # Statine
        if any(statin in d_lower for statin in ["simvastatin", "atorvastatin", "pravastatin"]):
            schedule["Abends"].append(f"{d.capitalize()} (Cholesterinsynthese hemmend, optimal abends)")
            continue

        # Diuretika
        if any(diur in d_lower for diur in ["torasemid", "furosemid", "hct", "hydrochlorothiazid"]):
            schedule["Morgens (Zum Fruehstueck)"].append(f"{d.capitalize()} (Vermeidung naechtlicher Nykturie)")
            continue

        # Kationen (Eisen, Calcium etc.) zeitlich nach mittags verschieben bei Komplexierungsgefahr
        if any(c in d_lower for c in cations):
            if has_cations:
                schedule["Mittags"].append(f"{d.capitalize()} (Zeitabstand zu Fruehstuecksmedikamenten)")
            else:
                schedule["Mittags"].append(f"{d.capitalize()}")
            continue

        # Sedativa / Schlafmittel
        if any(sed in d_lower for sed in ["zolpidem", "zopiclon", "melatonin", "mirtazapin"]):
            schedule["Zur Nacht"].append(f"{d.capitalize()} (Direkt vor dem Schlafengehen)")
            continue

        # Standard: Morgens zum Fruehstueck
        schedule["Morgens (Zum Fruehstueck)"].append(d.capitalize())

    # Leere Zeiteinheiten entfernen
    return {k: v for k, v in schedule.items() if len(v) > 0}

def generate_lab_monitoring_checklist(active_drugs, egfr_value=None):
    """
    Erstellt eine leitliniengestuetzte Labor-Checkliste basierend auf den
    aktiven Substanzen und Begleiterkrankungen (z. B. eGFR).
    """
    checklist = []
    if not active_drugs:
        return checklist

    def has_any(keywords):
        return any(any(k.lower() in d.lower() for k in keywords) for d in active_drugs)

    # 1. Kalium & Nierenretentionsparameter (Kreatinin, Harnstoff, eGFR)
    raas_and_diuretics = [
        "ramipril", "enalapril", "lisinopril", "candesartan", "valsartan", 
        "losartan", "spironolacton", "eplerenon", "torasemid", "furosemid", "hct"
    ]
    if has_any(raas_and_diuretics) or (egfr_value and egfr_value < 60):
        checklist.append({
            "parameter": "Serum-Kalium & Serum-Kreatinin (eGFR)",
            "urgency": "Hoch" if (has_any(["spironolacton"]) or (egfr_value and egfr_value < 30)) else "Standard",
            "interval": "Initial nach 1–2 Wochen, danach alle 3–6 Monate",
            "reason": "Risiko fuer Entgleisungen des Kaliumhaushalts (Hyper- oder Hypokaliaemie) und akute Verschlechterung der Nierenperfusion.",
            "triggers": [d.capitalize() for d in active_drugs if any(k in d.lower() for k in raas_and_diuretics)]
        })

    # 2. Lebertransaminasen (GOT, GPT, gamma-GT)
    liver_drugs = ["simvastatin", "atorvastatin", "pravastatin", "amiodaron", "methotrexat"]
    if has_any(liver_drugs):
        checklist.append({
            "parameter": "Leberenzyme (ALT/GPT, AST/GOT, Bilirubin)",
            "urgency": "Standard",
            "interval": "Vor Therapiebeginn, nach Dosiserhoehung und jaehrlich",
            "reason": "Ueberwachung auf medikamentoes-toxische Hepatopathie oder erhoehte Transaminasenwerte.",
            "triggers": [d.capitalize() for d in active_drugs if any(k in d.lower() for k in liver_drugs)]
        })

    # 3. Schilddruesenparameter (TSH, fT3, fT4)
    thyroid_drugs = ["amiodaron", "l-thyroxin", "levothyroxin"]
    if has_any(thyroid_drugs):
        checklist.append({
            "parameter": "Schilddruesenstatus (basales TSH, ggf. freies T3/T4)",
            "urgency": "Hoch" if has_any(["amiodaron"]) else "Standard",
            "interval": "Alle 3–6 Monate (bei Amiodaron strikt halbjaehrlich)",
            "reason": "Amiodaron kann schwere Hypo- oder Hyperthyreosen induzieren; Dosisanpassung bei L-Thyroxin.",
            "triggers": [d.capitalize() for d in active_drugs if any(k in d.lower() for k in thyroid_drugs)]
        })

    # 4. Blutbild & Gerinnung (Hb, Thrombozyten, ggf. Quick/INR oder Anti-Xa)
    blood_drugs = ["aspirin", "clopidogrel", "apixaban", "rivaroxaban", "edoxaban", "dabigatran", "ibuprofen", "diclofenac"]
    if has_any(blood_drugs):
        checklist.append({
            "parameter": "Kleines Blutbild (Hb, Erythrozyten, Thrombozyten)",
            "urgency": "Standard",
            "interval": "Alle 6–12 Monate (bei Zeichen von Muedigkeit/Blassheit sofort)",
            "reason": "Frueherkennung okkulter gastrointestinaler Blutungen unter Thrombozytenaggregationshemmern, NSAR oder DOAKs.",
            "triggers": [d.capitalize() for d in active_drugs if any(k in d.lower() for k in blood_drugs)]
        })

    # 5. EKG (QTc-Zeit)
    qt_drugs = ["ciprofloxacin", "amiodaron", "sotalol", "citalopram", "escitalopram", "haloperidol", "clarithromycin"]
    matched_qt = [d.capitalize() for d in active_drugs if any(k in d.lower() for k in qt_drugs)]
    if len(matched_qt) >= 2 or has_any(["amiodaron", "sotalol"]):
        checklist.append({
            "parameter": "12-Kanal-EKG (QTc-Intervall)",
            "urgency": "Hoch" if len(matched_qt) >= 2 else "Standard",
            "interval": "Vor Beginn der Kombination und nach 1–2 Wochen",
            "reason": "Erfassung einer pathologischen QTc-Zeit-Verlaengerung (> 500 ms) zur Praevention von Torsade-de-Pointes-Arrhythmien.",
            "triggers": matched_qt
        })

    return checklist

# --- Rueckwaertskompatibilitaet fuer aeltere Testmodule (z.B. test_cache.py) ---

def check_cache(drug_a, drug_b):
    """Alias fuer fetch_exact_cache."""
    return fetch_exact_cache(drug_a, drug_b)

def save_to_cache(drug_a, drug_b, data_or_severity, system=None, effect=None, mechanism="", advice="", source="Manuell eingetragen"):
    """Unterstuetzt Dictionary- oder Einzelargumente und prueft/migriert Spalten on-the-fly."""
    if isinstance(data_or_severity, dict):
        d = data_or_severity
        sev = d.get("severity", "Moderat")
        sys_val = d.get("system", "Allgemein")
        eff = d.get("effect", "")
        mech = d.get("mechanism", "")
        adv = d.get("advice", "")
        src = d.get("source", source)
    else:
        sev = data_or_severity
        sys_val = system or "Allgemein"
        eff = effect or ""
        mech = mechanism or ""
        adv = advice or ""
        src = source

    conn = get_db_connection()
    cursor = conn.cursor()

    # Spaltenueberpruefung und Live-Migration
    cursor.execute("PRAGMA table_info(interactions)")
    existing_cols = {row[1] for row in cursor.fetchall()}

    for col in ["advice", "mechanism", "source"]:
        if col not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE interactions ADD COLUMN {col} TEXT")
                existing_cols.add(col)
            except Exception:
                pass

    if "advice" in existing_cols:
        cursor.execute("""
            INSERT OR REPLACE INTO interactions (drug_a, drug_b, severity, system, effect, mechanism, advice, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (drug_a.lower().strip(), drug_b.lower().strip(), sev, sys_val, eff, mech, adv, src))
    else:
        # Fallback falls alter Tabellenstand blockiert
        cursor.execute("""
            INSERT OR REPLACE INTO interactions (drug_a, drug_b, severity, system, effect)
            VALUES (?, ?, ?, ?, ?)
        """, (drug_a.lower().strip(), drug_b.lower().strip(), sev, sys_val, eff))

    conn.commit()
    conn.close()

def get_total_cached_count():
    """Gibt die Gesamtanzahl gespeicherter Interaktionen zurueck."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM interactions")
    count = cursor.fetchone()[0]
    conn.close()
    return count