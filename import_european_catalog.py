"""
import_european_catalog.py
Spielt den standardisierten europäischen Wirkstoffkatalog (WHO-ATC-Nomenklatur)
sowie biochemische Interaktions- und Inhibitions-Korrelationen in interactions.db ein.
"""

import sqlite3

DB_FILE = "interactions.db"

# 1. Europäischer Arzneistoffkatalog (WHO-ATC orientiert)
EUROPEAN_DRUGS = [
    # --- A: Alimentäres System & Stoffwechsel ---
    ("Pantoprazol", "A02BC02", "Protonenpumpenhemmer (PPI)", "Magen-Darm", "CYP2C19-Substrat"),
    ("Omeprazol", "A02BC01", "Protonenpumpenhemmer (PPI)", "Magen-Darm", "CYP2C19-Inhibitor"),
    ("Esomeprazol", "A02BC05", "Protonenpumpenhemmer (PPI)", "Magen-Darm", "CYP2C19-Inhibitor"),
    ("Metformin", "A10BA02", "Biguanid (Antidiabetikum)", "Niere/Stoffwechsel", "Renal eliminiert"),
    ("Empagliflozin", "A10BK03", "SGLT2-Inhibitor", "Niere/Kreislauf", "Glukosurisch"),
    ("Dapagliflozin", "A10BK01", "SGLT2-Inhibitor", "Niere/Kreislauf", "Glukosurisch"),
    ("Sitagliptin", "A10BH01", "DPP-4-Inhibitor", "Stoffwechsel", "Renal eliminiert"),
    ("Semaglutid", "A10BJ06", "GLP-1-Rezeptoragonist", "Magen-Darm/Stoffwechsel", "Peptid-Abbau"),

    # --- B: Blut & blutbildende Organe (Hämostase) ---
    ("Acetylsalicylsäure", "B01AC06", "Thrombozytenaggregationshemmer", "Blutgerinnung", "COX-1-Inhibitor"),
    ("Apixaban", "B01AF02", "DOAK (Faktor-Xa-Hemmer)", "Blutgerinnung", "CYP3A4/P-gp-Substrat"),
    ("Rivaroxaban", "B01AF01", "DOAK (Faktor-Xa-Hemmer)", "Blutgerinnung", "CYP3A4/P-gp-Substrat"),
    ("Edoxaban", "B01AF03", "DOAK (Faktor-Xa-Hemmer)", "Blutgerinnung", "P-gp-Substrat"),
    ("Dabigatran", "B01AE07", "Direkter Thrombininhibitor", "Blutgerinnung/Niere", "P-gp-Substrat"),
    ("Phenprocoumon", "B01AA04", "Vitamin-K-Antagonist (Cumarin)", "Blutgerinnung/Leber", "CYP2C9-Substrat"),
    ("Clopidogrel", "B01AC04", "P2Y12-Rezeptor-Inhibitor", "Blutgerinnung", "CYP2C19-Prodrug"),
    ("Ticagrelor", "B01AC24", "P2Y12-Rezeptor-Inhibitor", "Blutgerinnung", "CYP3A4-Substrat"),

    # --- C: Kardiovaskuläres System ---
    ("Ramipril", "C09AA05", "ACE-Hemmer", "Niere/Blutdruck", "Prodrug / renal eliminiert"),
    ("Enalapril", "C09AA02", "ACE-Hemmer", "Niere/Blutdruck", "Renal eliminiert"),
    ("Lisinopril", "C09AA03", "ACE-Hemmer", "Niere/Blutdruck", "Renal eliminiert"),
    ("Candesartan", "C09CA06", "AT1-Rezeptorantagonist (Sartan)", "Niere/Blutdruck", "Geringe Metabolisierung"),
    ("Valsartan", "C09CA03", "AT1-Rezeptorantagonist (Sartan)", "Niere/Blutdruck", "Geringe Metabolisierung"),
    ("Losartan", "C09CA01", "AT1-Rezeptorantagonist (Sartan)", "Niere/Blutdruck", "CYP2C9/3A4-Substrat"),
    ("Amlodipin", "C08CA01", "Calciumkanalblocker (Dihydropyridin)", "Kreislauf/Gefäße", "CYP3A4-Inhibitor (schwach)"),
    ("Metoprolol", "C07AB02", "Selektiver Beta-1-Blocker", "Herz/Reizleitung", "CYP2D6-Substrat"),
    ("Bisoprolol", "C07AB07", "Selektiver Beta-1-Blocker", "Herz/Reizleitung", "Renal/Hepatisch 50/50"),
    ("Carvedilol", "C07AG02", "Alpha-/Beta-Blocker", "Herz/Kreislauf", "CYP2D6/2C9-Substrat"),
    ("Hydrochlorothiazid", "C03AA03", "Thiaziddiuretikum", "Niere/Elektrolyte", "Renal eliminiert"),
    ("Torasemid", "C03CA04", "Schleifendiuretikum", "Niere/Elektrolyte", "CYP2C9-Substrat"),
    ("Furosemid", "C03CA01", "Schleifendiuretikum", "Niere/Elektrolyte", "Renal eliminiert"),
    ("Spironolacton", "C03DA01", "Aldosteronantagonist", "Niere/Elektrolyte (K+)", "Hepatisch metabolisiert"),
    ("Simvastatin", "C10AA01", "HMG-CoA-Reduktasehemmer (Statin)", "Leber/Muskel", "CYP3A4-Substrat"),
    ("Atorvastatin", "C10AA05", "HMG-CoA-Reduktasehemmer (Statin)", "Leber/Muskel", "CYP3A4-Substrat"),
    ("Rosuvastatin", "C10AA07", "HMG-CoA-Reduktasehemmer (Statin)", "Leber/Muskel", "CYP2C9 (minimal)"),

    # --- J: Antiinfektiva zur systemischen Anwendung ---
    ("Flucloxacillin", "J01CF05", "Isoxazolylpenicillin (Staphylokokken)", "Leber/Knochenmark", "CYP3A4-Induktor (schwach)"),
    ("Amoxicillin", "J01CA04", "Aminopenicillin", "Magen-Darm/Niere", "Renal eliminiert"),
    ("Cefuroxim", "J01DC02", "Cephalosporin der 2. Generation", "Niere", "Renal eliminiert"),
    ("Ciprofloxacin", "J01MA02", "Fluorchinolon (Gyrasehemmer)", "ZNS/Sehnen/Herz", "CYP1A2-Inhibitor (stark)"),
    ("Levofloxacin", "J01MA12", "Fluorchinolon", "Herz (QT-Intervall)", "Renal eliminiert"),
    ("Clarithromycin", "J01FA09", "Makrolid-Antibiotikum", "Herz/Leber", "CYP3A4-Inhibitor (stark)"),
    ("Azithromycin", "J01FA10", "Makrolid-Antibiotikum", "Herz (QT-Intervall)", "Geringe CYP-Interaktion"),
    ("Doxycyclin", "J01AA02", "Tetracyclin-Antibiotikum", "Magen-Darm/Zähne", "Metallsalz-Chelatbildner"),
    ("Fluconazol", "J02AC01", "Triazol-Antimykotikum", "Leber/Enzyme", "CYP2C9/CYP3A4-Inhibitor (stark)"),
    ("Cotrimoxazol", "J01EE01", "Sulfonamid + Trimethoprim", "Niere/Knochenmark", "CYP2C9-Inhibitor"),

    # --- M: Muskel- und Skelettsystem (NSAR / Gicht) ---
    ("Ibuprofen", "M01AE01", "Nichtsteroidales Antirheumatikum (NSAR)", "Magen/Niere/Blut", "COX-1/2-Inhibitor"),
    ("Diclofenac", "M01AB05", "Nichtsteroidales Antirheumatikum (NSAR)", "Magen/Herz/Niere", "CYP2C9-Substrat"),
    ("Naproxen", "M01AE02", "Nichtsteroidales Antirheumatikum (NSAR)", "Magen/Niere", "COX-1/2-Inhibitor"),
    ("Etoricoxib", "M01AH05", "Selektiver COX-2-Inhibitor", "Herz-Kreislauf/Niere", "CYP3A4-Substrat"),
    ("Allopurinol", "M04AA01", "Xanthinoxidasehemmer", "Stoffwechsel/Haut", "Purin-Analogon"),

    # --- N: Nervensystem (Analgetika, Psyche, Neurologie) ---
    ("Paracetamol", "N02BE01", "Nicht-Opioid-Analgetikum", "Leber", "CYP2E1-Metabolisierung"),
    ("Metamizol", "N02BB02", "Pyrazolonderivat-Analgetikum", "Knochenmark/Blutdruck", "CYP2B6/3A4-Induktor"),
    ("Tilidin", "N02AX01", "Opioid-Analgetikum", "ZNS/Atmung", "CYP3A4/2C19-Prodrug"),
    ("Tramadol", "N02AX02", "Opioid-Analgetikum / SNRI", "ZNS/Serotonin", "CYP2D6-Substrat"),
    ("Citalopram", "N06AB04", "SSRI (Antidepressivum)", "ZNS/Herz (QT)", "CYP2C19-Substrat"),
    ("Escitalopram", "N06AB10", "SSRI (Antidepressivum)", "ZNS/Herz (QT)", "CYP2C19-Substrat"),
    ("Sertralin", "N06AB06", "SSRI (Antidepressivum)", "ZNS/Thrombozyten", "CYP2B6/2C19-Substrat"),
    ("Venlafaxin", "N06AX16", "SNRI (Antidepressivum)", "ZNS/Blutdruck", "CYP2D6-Substrat"),
    ("Lithium", "N05AN01", "Stimmungsstabilisierer", "Niere/Schilddrüse", "Renal eliminiert (Na+-Kanal)"),
    ("Lorazepam", "N05BA06", "Benzodiazepin", "ZNS/Sedierung", "Glukuronidierung (kein CYP)"),

    # --- L: Antineoplastische & immunmodulierende Mittel (Onkologie/Rheuma) ---
    ("Methotrexat", "L01BA01", "Folsäure-Antagonist (Immunsuppressivum)", "Knochenmark/Leber/Niere", "Renal tubulär eliminiert"),
    ("Azathioprin", "L04AX01", "Purin-Antagonist (Immunsuppressivum)", "Knochenmark/Leber", "TPMT/Xanthinoxidase-Substrat"),
    ("Tacrolimus", "L04AD02", "Calcineurin-Inhibitor", "Niere/Immunsystem", "CYP3A4/P-gp-Substrat"),
    ("Ciclosporin", "L04AD01", "Calcineurin-Inhibitor", "Niere/Immunsystem", "CYP3A4/P-gp-Inhibitor")
]

# 2. Biochemische Interaktions- & Inhibitions-Matrix
INTERACTION_MATRIX = [
    # Flucloxacillin-Spezifika (Europäischer Standard)
    {
        "pair": ("Flucloxacillin", "Paracetamol"),
        "severity": "Moderat",
        "system": "Stoffwechsel & Säure-Basen-Haushalt",
        "effect": "Risiko einer schweren metabolischen Azidose mit vergrößerter Anionenlücke (HAGMA).",
        "mechanism": "Flucloxacillin hemmt die Pyroglutamatsynthese bei gleichzeitiger Glutathionverarmung durch Paracetamol. Führt zur Kumulation von 5-Oxoprolin (besonders bei älteren Patienten und Niereninsuffizienz).",
        "source": "Europäische Fachinformation (EMA)"
    },
    {
        "pair": ("Flucloxacillin", "Methotrexat"),
        "severity": "Hoch",
        "system": "Knochenmark & Nierenfunktion",
        "effect": "Verzögerte Ausscheidung und lebensbedrohliche Toxizität von Methotrexat (Panzytopenie).",
        "mechanism": "Penicilline wie Flucloxacillin hemmen kompetitiv die tubuläre Sekretion von Methotrexat in den Nierentubuli.",
        "source": "Klinische Pharmakologie"
    },

    # Enzym-Inhibitionen (CYP3A4 / CYP2C9 / CYP1A2)
    {
        "pair": ("Fluconazol", "Simvastatin"),
        "severity": "Hoch",
        "system": "Skelettmuskulatur & Leber",
        "effect": "Massiv erhöhtes Risiko für Myopathie bis hin zur tödlichen Rhabdomyolyse.",
        "mechanism": "Fluconazol ist ein starker Inhibitor von CYP3A4 und CYP2C9. Der first-pass-Abbau von Simvastatin wird blockiert; die Bioverfügbarkeit steigt um das 5- bis 10-Fache.",
        "source": "Enzym-Matrix (CYP3A4-Inhibition)"
    },
    {
        "pair": ("Fluconazol", "Phenprocoumon"),
        "severity": "Hoch",
        "system": "Blutgerinnung (INR-Entgleisung)",
        "effect": "Unkontrollierbarer Anstieg des INR-Werts mit akuter innerer Blutungsgefahr.",
        "mechanism": "Fluconazol inhibiert CYP2C9, das Hauptabbauenzym des biologisch aktiven S-Enantiomers von Cumarinen.",
        "source": "Enzym-Matrix (CYP2C9-Inhibition)"
    },
    {
        "pair": ("Clarithromycin", "Simvastatin"),
        "severity": "Hoch",
        "system": "Muskulatur & Nierenfunktion",
        "effect": "Gefahr des akuten Nierenversagens infolge Rhabdomyolyse. Kombination ist kontraindiziert.",
        "mechanism": "Starke irreversible Mechanism-based Inhibition von intestinalem und hepatischem CYP3A4 durch das Makrolid.",
        "source": "Enzym-Matrix (CYP3A4-Inhibition)"
    },
    {
        "pair": ("Ciprofloxacin", "Citalopram"),
        "severity": "Hoch",
        "system": "Herzrhythmus (QTc-Intervall)",
        "effect": "Gefahr lebensbedrohlicher ventrikulärer Arrhythmien (Torsade de Pointes).",
        "mechanism": "Additive Verlängerung der kardialen Repolarisationsphase (hERG-Kanal-Blockade) plus partielle Inhibition des Abbaus über CYP1A2.",
        "source": "Kardiovaskuläre Pharmakologie"
    },

    # Onkologie & Immunologie
    {
        "pair": ("Allopurinol", "Azathioprin"),
        "severity": "Hoch",
        "system": "Hämatopoese (Knochenmark)",
        "effect": "Schwere, teils tödliche Knochenmarksdepression (Agranulozytose).",
        "mechanism": "Allopurinol hemmt die Xanthinoxidase, wodurch Azathioprin nicht mehr zum inaktiven Metaboliten oxidiert werden kann. 6-Thioguanin-Nukleotide akkumulieren massiv.",
        "source": "Metabolismus-Matrix"
    },
    {
        "pair": ("Ibuprofen", "Methotrexat"),
        "severity": "Hoch",
        "system": "Knochenmark & Niere",
        "effect": "Akkumulation toxischer Methotrexat-Spiegel mit Schleimhautulzerationen und Panzytopenie.",
        "mechanism": "NSAR senken die renale Durchblutung (Prostaglandinsynthese-Hemmung) und konkurrieren um tubuläre Anionentransporter (OAT1/OAT3).",
        "source": "Renale Clearance-Matrix"
    },

    # Renale Elimination & Elektrolyte
    {
        "pair": ("Ramipril", "Lithium"),
        "severity": "Hoch",
        "system": "Zentralnervensystem & Niere",
        "effect": "Akute Lithiumintoxikation (Tremor, Ataxie, Verwirrtheit, Krampfanfälle).",
        "mechanism": "ACE-Hemmer induzieren über Natriumausscheidung eine kompensatorische proximale Rückresorption von Natrium – und damit auch von Lithium.",
        "source": "Elektrolyt-Clearance"
    },
    {
        "pair": ("Ibuprofen", "Lithium"),
        "severity": "Hoch",
        "system": "ZNS & Renale Clearance",
        "effect": "Steiler Anstieg des Lithium-Serumspiegels um 30–60 % innerhalb weniger Tage.",
        "mechanism": "Hemmung renaler gefäßerweiternder Prostaglandine durch NSAR vermindert die glomeruläre Filtrationsrate von Lithium.",
        "source": "Elektrolyt-Clearance"
    },
    {
        "pair": ("Ramipril", "Spironolacton"),
        "severity": "Hoch",
        "system": "Elektrolythaushalt (Kalium)",
        "effect": "Akute, lebensgefährliche Hyperkaliämie mit Herzstillstand-Risiko.",
        "mechanism": "Doppelte Aldosteron-Suppression: Verminderte Synthese trifft auf direkte Rezeptorblockade am distalen Tubulus.",
        "source": "Kardiovaskuläre Matrix"
    },

    # Triple-Whammy-Kernelemente
    {
        "pair": ("Ramipril", "Hydrochlorothiazid"),
        "severity": "Moderat",
        "system": "Kreislauf & Elektrolyte",
        "effect": "Initialer Blutdruckabfall, Elektrolytverschiebungen (Natrium/Kalium).",
        "mechanism": "Synergistische Blutdrucksenkung: RAAS-Blockade kompensiert reflektorische Reninfreisetzung des Diuretikums.",
        "source": "Kardiovaskuläre Matrix"
    },
    {
        "pair": ("Ramipril", "Ibuprofen"),
        "severity": "Hoch",
        "system": "Glomeruläre Filtration (Niere)",
        "effect": "Akuter Abfall der glomerulären Filtrationsrate (GFR) und Abschwächung der Antihypertension.",
        "mechanism": "Vas afferens verengt (NSAR-Prostaglandinmangel) + Vas efferens dilatiert (ACE-Hemmer-Angiotensin-II-Mangel) -> Intraglomerulärer Druck bricht zusammen.",
        "source": "Renale Hämodynamik"
    },
    {
        "pair": ("Hydrochlorothiazid", "Ibuprofen"),
        "severity": "Moderat",
        "system": "Niere & Volumenstatus",
        "effect": "Wirkungsverlust der Entwässerung und Blutdruckanstieg.",
        "mechanism": "NSAR induzieren renale Natrium- und Wasserretention.",
        "source": "Renale Hämodynamik"
    },

    # Gerinnungs- und Magenkaskaden
    {
        "pair": ("Acetylsalicylsäure", "Ibuprofen"),
        "severity": "Hoch",
        "system": "Thrombozyten & Magenschleimhaut",
        "effect": "Verlust des kardiovaskulären Schutzes von ASS sowie erhöhtes Ulkusrisiko.",
        "mechanism": "Ibuprofen blockiert sterisch den Zugang von ASS zum katalytischen Zentrum der Thrombozyten-COX-1 (Serin 529).",
        "source": "Plättchenpharmakologie"
    },
    {
        "pair": ("Acetylsalicylsäure", "Apixaban"),
        "severity": "Hoch",
        "system": "Hämostase (Blutgerinnung)",
        "effect": "Drastische Zunahme schwerer gastrointestinaler und intrakranieller Blutungen.",
        "mechanism": "Kombination aus primärer Hämostasehemmung (Plättchenaggregationshemmung) und sekundärer plasmatischer Antikoagulation.",
        "source": "Hämostaseologie"
    },
    {
        "pair": ("Phenprocoumon", "Acetylsalicylsäure"),
        "severity": "Hoch",
        "system": "Hämostase (Blutgerinnung)",
        "effect": "Hohe Rate spontaner Weichteil- und Schleimhautblutungen.",
        "mechanism": "Duale Gerinnungsblockade: Cumarin hemmt Synthese der Faktoren II, VII, IX, X; ASS blockiert Thrombozyten irreversibel.",
        "source": "Hämostaseologie"
    }
]


def setup_database_schema(conn):
    """Erstellt die Tabellen für Wirkstoffe und Interaktionen."""
    cursor = conn.cursor()

    # 1. Wirkstoffkatalog-Tabelle (ATC-Katalog)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS drugs (
            name TEXT PRIMARY KEY,
            atc_code TEXT NOT NULL,
            drug_class TEXT NOT NULL,
            organ_system TEXT NOT NULL,
            metabolism TEXT NOT NULL
        )
    """)

    # 2. Interaktionstabelle
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            pair_key TEXT PRIMARY KEY,
            drug_a TEXT NOT NULL,
            drug_b TEXT NOT NULL,
            severity TEXT NOT NULL,
            system TEXT NOT NULL,
            effect TEXT NOT NULL,
            mechanism TEXT NOT NULL,
            source TEXT DEFAULT 'Europäischer Katalog'
        )
    """)
    conn.commit()


def get_pair_key(d1, d2):
    """Generiert einen alphabetisch einheitlichen Primärschlüssel."""
    sorted_pair = sorted([d1.strip().lower(), d2.strip().lower()])
    return f"{sorted_pair[0]}___{sorted_pair[1]}"


def run_import():
    print("=" * 65)
    print("🚀 Starte Import des europäischen Arzneistoffkatalogs (WHO-ATC)...")
    print("=" * 65)

    conn = sqlite3.connect(DB_FILE)
    setup_database_schema(conn)
    cursor = conn.cursor()

    # 1. Wirkstoffe importieren
    drug_count = 0
    for name, atc, d_class, organ, metab in EUROPEAN_DRUGS:
        cursor.execute("""
            INSERT OR REPLACE INTO drugs (name, atc_code, drug_class, organ_system, metabolism)
            VALUES (?, ?, ?, ?, ?)
        """, (name, atc, d_class, organ, metab))
        drug_count += 1

    # 2. Interaktionen & Inhibitions-Matrix importieren
    interaction_count = 0
    for item in INTERACTION_MATRIX:
        d1, d2 = item["pair"]
        pair_key = get_pair_key(d1, d2)
        cursor.execute("""
            INSERT OR REPLACE INTO interactions 
            (pair_key, drug_a, drug_b, severity, system, effect, mechanism, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pair_key,
            d1,
            d2,
            item["severity"],
            item["system"],
            item["effect"],
            item["mechanism"],
            item["source"]
        ))
        interaction_count += 1

    conn.commit()

    # Status-Abfrage
    cursor.execute("SELECT COUNT(*) FROM drugs")
    total_drugs = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM interactions")
    total_interactions = cursor.fetchone()[0]

    conn.close()

    print(f"✅ Wirkstoffe eingespielt: {drug_count} (Gesamtbestand in 'drugs': {total_drugs})")
    print(f"✅ Interaktionen eingespielt: {interaction_count} (Gesamtbestand in 'interactions': {total_interactions})")
    print("=" * 65)
    print("🎉 Import erfolgreich abgeschlossen! interactions.db ist nun vollwertig bestückt.")


if __name__ == "__main__":
    run_import()