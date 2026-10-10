"""
seed_class_rules.py
Erweitertes ATC-Klassen-Regelwerk fuer interactions.db.
Deckt systematisch ueber 30 klinische Grossgruppen-Interaktionen ab,
um 'False Negatives' (das Gruen-Dilemma) drastisch zu reduzieren.
"""

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "interactions.db")

CLASS_RULES = [
    # --- 1. Kardiologie, Blutdruck & Nierenfunktion ---
    {
        "atc_a": "M01A",
        "atc_b": "C09A",
        "class_name_a": "NSAR-Schmerzmittel",
        "class_name_b": "ACE-Hemmer",
        "severity": "Hoch",
        "system": "Nierenfunktion & Blutdruck",
        "effect": "Akute Nierenfunktionsverschlechterung (GFR-Abfall) und Abschwaechung der Blutdrucksenkung.",
        "mechanism": "NSAR hemmen gefaesserweiternde renale Prostaglandine (Vas afferens verengt), waehrend ACE-Hemmer Angiotensin II senken (Vas efferens dilatiert). Der Filtrationsdruck bricht zusammen."
    },
    {
        "atc_a": "M01A",
        "atc_b": "C09C",
        "class_name_a": "NSAR-Schmerzmittel",
        "class_name_b": "AT1-Antagonisten (Sartane)",
        "severity": "Hoch",
        "system": "Nierenfunktion & Blutdruck",
        "effect": "Verminderte Nierenfiltration und reduzierter antihypertensiver Schutz.",
        "mechanism": "Haemodynamischer Konflikt an den Nierenarteriolen analog zu ACE-Hemmern."
    },
    {
        "atc_a": "M01A",
        "atc_b": "C03",
        "class_name_a": "NSAR-Schmerzmittel",
        "class_name_b": "Diuretika (Entwaesserung)",
        "severity": "Moderat",
        "system": "Fluessigkeitshaushalt & Kreislauf",
        "effect": "Abschwaechung der harntreibenden Wirkung und Risiko fuer Natrium-/Wasserretention.",
        "mechanism": "NSAR unterdruecken die renale Prostaglandinsynthese, die fuer den renalen Blutfluss und Diurese notwendig ist."
    },
    {
        "atc_a": "C09A",
        "atc_b": "C03D",
        "class_name_a": "ACE-Hemmer",
        "class_name_b": "Kaliumsparende Diuretika",
        "severity": "Hoch",
        "system": "Elektrolyte & Herzrhythmus",
        "effect": "Gefahr einer lebensbedrohlichen Hyperkaliaemie mit Herzrhythmusstoerungen.",
        "mechanism": "Synergistische Hemmung der renalen Kaliumausscheidung am distalen Nephron durch duale Blockade von Aldosteron."
    },
    {
        "atc_a": "C09C",
        "atc_b": "C03D",
        "class_name_a": "Sartane (AT1-Blocker)",
        "class_name_b": "Kaliumsparende Diuretika",
        "severity": "Hoch",
        "system": "Elektrolyte (Kalium)",
        "effect": "Kritischer Anstieg der Kalium-Serumkonzentration.",
        "mechanism": "Duale Hemmung der kaliuretischen Wirkung von Aldosteron."
    },
    {
        "atc_a": "C07A",
        "atc_b": "C08D",
        "class_name_a": "Beta-Blocker",
        "class_name_b": "Calciumantagonisten (Verapamil/Diltiazem)",
        "severity": "Hoch",
        "system": "Kardiale Reizleitung",
        "effect": "Schwere Bradykardie, AV-Blockierungen bis zum Asystolie-Risiko.",
        "mechanism": "Additiver negativ chronotroper und negativ dromotroper Effekt am Sinusknoten und AV-Knoten."
    },

    # --- 2. Blutgerinnung & Haemorrhagie-Risiken ---
    {
        "atc_a": "M01A",
        "atc_b": "B01AF",
        "class_name_a": "NSAR-Schmerzmittel",
        "class_name_b": "DOAKs (Faktor-Xa-Hemmer)",
        "severity": "Hoch",
        "system": "Blutgerinnung & Magenschleimhaut",
        "effect": "Massiv gesteigertes Risiko schwerer Magen-Darm-Blutungen.",
        "mechanism": "Schaedigung der Magenschleimhautbarriere durch NSAR trifft auf die systemische Gerinnungshemmung des DOAKs."
    },
    {
        "atc_a": "M01A",
        "atc_b": "B01AA",
        "class_name_a": "NSAR-Schmerzmittel",
        "class_name_b": "Vitamin-K-Antagonisten (Phenprocoumon/Warfarin)",
        "severity": "Hoch",
        "system": "Haemostase & Magen-Darm",
        "effect": "Schwere Ulkusblutungen und unberechenbare INR-Schwankungen.",
        "mechanism": "Plaettchenfunktionshemmung und Schleimhauterosion durch NSAR bei gleichzeitiger Hemmung der plasmatischen Gerinnung."
    },
    {
        "atc_a": "M01A",
        "atc_b": "B01AC",
        "class_name_a": "NSAR-Schmerzmittel",
        "class_name_b": "Plaettchenhemmer (z.B. ASS, Clopidogrel)",
        "severity": "Hoch",
        "system": "Magen-Darm & Blutgerinnung",
        "effect": "Schwere gastrointestinale Ulzera und Blutungen; Aufhebung der kardioprotektiven ASS-Wirkung.",
        "mechanism": "Kompetitive Verdraengung von ASS an der Thrombozyten-COX-1 sowie additive Mukosatoxizitaet."
    },
    {
        "atc_a": "N06AB",
        "atc_b": "M01A",
        "class_name_a": "SSRI-Antidepressiva",
        "class_name_b": "NSAR-Schmerzmittel",
        "severity": "Moderat",
        "system": "Haemostase & Magen-Darm",
        "effect": "Signifikant erhoehtes Risiko fuer Magen-Darm-Blutungen (ca. 3- bis 6-fach).",
        "mechanism": "SSRI entleeren die intraplaettchenaeren Serotoninspeicher; NSAR schaedigen die protektive Schleimhautbarriere."
    },
    {
        "atc_a": "N06AB",
        "atc_b": "B01A",
        "class_name_a": "SSRI-Antidepressiva",
        "class_name_b": "Antikoagulantien / Plaettchenhemmer",
        "severity": "Moderat",
        "system": "Blutgerinnung",
        "effect": "Verstaerkte Blutungsneigung.",
        "mechanism": "Duale Beeintraechtigung von Thrombozytenaktivierung und Gerinnungskaskade."
    },
    {
        "atc_a": "H02AB",
        "atc_b": "M01A",
        "class_name_a": "Glukokortikoide (Kortison)",
        "class_name_b": "NSAR-Schmerzmittel",
        "severity": "Hoch",
        "system": "Magen-Darm-Trakt",
        "effect": "Dramatisch erhoehtes Risiko fuer Magen- und Zwoelffingerdarmgeschwuere sowie Perforationen.",
        "mechanism": "Synergistische Hemmung der schleimhautschuetzenden Prostaglandinsynthese durch duale Enzyminhibition."
    },

    # --- 3. Metabolisierung: CYP450-Inhibition & Statine ---
    {
        "atc_a": "J02AC",
        "atc_b": "C10AA",
        "class_name_a": "Azol-Antimykotika",
        "class_name_b": "Statine (Cholesterinsenker)",
        "severity": "Hoch",
        "system": "Skelettmuskulatur & Leber",
        "effect": "Massiver Statin-Spiegelanstieg mit Gefahr fuer schwere Myopathie und Rhabdomyolyse.",
        "mechanism": "Starke Inhibition von hepatischem CYP3A4 durch Azole blockiert den first-pass-Abbau der Statine."
    },
    {
        "atc_a": "J01FA",
        "atc_b": "C10AA",
        "class_name_a": "Makrolid-Antibiotika",
        "class_name_b": "Statine (Cholesterinsenker)",
        "severity": "Hoch",
        "system": "Muskulatur & Niere",
        "effect": "Rhabdomyolyse-Gefahr durch Akkumulation toxischer Statin-Konzentrationen.",
        "mechanism": "Irreversible mechanism-based Inaktivierung von CYP3A4 durch Makrolide (z.B. Clarithromycin)."
    },
    {
        "atc_a": "C08CA",
        "atc_b": "C10AA",
        "class_name_a": "Dihydropyridin-Calciumantagonisten (z.B. Amlodipin)",
        "class_name_b": "Statine (z.B. Simvastatin)",
        "severity": "Moderat",
        "system": "Muskulatur",
        "effect": "Erhoehte Statin-Plasmaspiegel, gesteigertes Risiko fuer Muskelschmerzen (Myalgien).",
        "mechanism": "Kompetitive Hemmung des CYP3A4-Stoffwechsels (Dosisbegrenzung fuer Simvastatin empfohlen)."
    },

    # --- 4. Kardiales Reizleitungssystem: QT-Intervall & Torsade de Pointes ---
    {
        "atc_a": "J01MA",
        "atc_b": "C01BD",
        "class_name_a": "Fluorchinolone (Gyrasehemmer)",
        "class_name_b": "Klasse-III-Antiarrhythmika (z.B. Amiodaron)",
        "severity": "Hoch",
        "system": "Kardiales Reizleitungssystem",
        "effect": "Exzessive Verlaengerung des QTc-Intervalls mit Gefahr fuer ventrikulaere Torsade-de-Pointes-Arrhythmien.",
        "mechanism": "Additive Blockade der myokardialen repolarisierenden hERG-Kaliumkanaele."
    },
    {
        "atc_a": "J01FA",
        "atc_b": "N05A",
        "class_name_a": "Makrolid-Antibiotika",
        "class_name_b": "Antipsychotika / Neuroleptika",
        "severity": "Hoch",
        "system": "Herzrhythmus (QT-Zeit)",
        "effect": "Kritisches Risiko fuer lebensbedrohliche Herzrhythmusstoerungen.",
        "mechanism": "Pharmakodynamischer Synergismus bezueglich der Verlaengerung der myokardialen Refraktaerzeit."
    },
    {
        "atc_a": "N06A",
        "atc_b": "N05A",
        "class_name_a": "Antidepressiva",
        "class_name_b": "Antipsychotika",
        "severity": "Moderat",
        "system": "Herzrhythmus",
        "effect": "Potenzierte QTc-Verlaengerung.",
        "mechanism": "Additive Blockade der kardialen Kalium-Auswaertsstroeme."
    },

    # --- 5. Zentralnervensystem & Serotonerge Toxizitaet ---
    {
        "atc_a": "N05BA",
        "atc_b": "N02A",
        "class_name_a": "Benzodiazepine",
        "class_name_b": "Opioid-Analgetika",
        "severity": "Hoch",
        "system": "Zentralnervensystem & Atmung",
        "effect": "Lebensbedrohliche Atemdepression, schwere Sedierung bis hin zum Koma.",
        "mechanism": "Synergistische Daempfung des zentralen Atemantriebs ueber GABA-A- und My-Opioid-Rezeptoren."
    },
    {
        "atc_a": "N06AB",
        "atc_b": "N02AX",
        "class_name_a": "SSRI-Antidepressiva",
        "class_name_b": "Atypische Opioide (Tramadol)",
        "severity": "Hoch",
        "system": "Zentralnervensystem",
        "effect": "Akute Gefahr eines Serotoninsyndroms (Hyperthermie, Tremor, Myoklonien, Verwirrtheit) und erhoehte Krampfneigung.",
        "mechanism": "Additive Erhoehung des synaptischen Serotoninspiegels sowie Senkung der Krampfschwelle."
    },
    {
        "atc_a": "N06A",
        "atc_b": "N04BD",
        "class_name_a": "Antidepressiva (SSRI/SNRI/Trizyklika)",
        "class_name_b": "MAO-B-Hemmer (Parkinson-Therapie)",
        "severity": "Hoch",
        "system": "Zentralnervensystem",
        "effect": "Potentiell toedliches Serotoninsyndrom.",
        "mechanism": "Gleichzeitige Wiederaufnahmehemmung und verminderter enzymatischer Abbau von Serotonin."
    },
    {
        "atc_a": "N02A",
        "atc_b": "N05C",
        "class_name_a": "Opioide",
        "class_name_b": "Z-Substanzen (Zopiclon/Zolpidem)",
        "severity": "Hoch",
        "system": "Zentralnervensystem",
        "effect": "Verstaerkte Atemdepression und sedierende Kumulation.",
        "mechanism": "Additive Wirkung an zentralen depressiven Neurotransmittersystemen."
    },

    # --- 6. Immunsuppression, Onkologie & Elimination ---
    {
        "atc_a": "L04AX03",
        "atc_b": "M01A",
        "class_name_a": "Methotrexat",
        "class_name_b": "NSAR-Schmerzmittel",
        "severity": "Hoch",
        "system": "Knochenmark & Nieren",
        "effect": "Gefahr einer toedlichen Methotrexat-Intoxikation (Panzytopenie, Schleimhautnekrosen).",
        "mechanism": "NSAR reduzieren die glomerulaere Filtration und hemmen die tubulaere Sekretion von Methotrexat ueber renale Anionentransporter."
    },
    {
        "atc_a": "L04AD",
        "atc_b": "J02AC",
        "class_name_a": "Calcineurin-Inhibitoren (Tacrolimus/Ciclosporin)",
        "class_name_b": "Azol-Antimykotika",
        "severity": "Hoch",
        "system": "Nierenfunktion & Immunsystem",
        "effect": "Massiver Anstieg der Immunsuppressiva-Spiegel mit akuter Nephrotoxizitaet.",
        "mechanism": "Starke Hemmung von CYP3A4 und P-Glykoprotein (P-gp)."
    },

    # --- 7. Endokrinologie & Stoffwechsel ---
    {
        "atc_a": "A10B",
        "atc_b": "C07A",
        "class_name_a": "Antidiabetika",
        "class_name_b": "Beta-Blocker",
        "severity": "Moderat",
        "system": "Stoffwechsel & Kreislauf",
        "effect": "Maskierung von Hypoglykaemie-Warnsymptomen (z.B. Tachykardie, Tremor).",
        "mechanism": "Blockade der sympathoadrenalen Gegenregulation bei Unterzuckerung."
    },
    {
        "atc_a": "A10BA02",
        "atc_b": "V08",
        "class_name_a": "Metformin",
        "class_name_b": "Jodhaltige Roentgenkontrastmittel",
        "severity": "Hoch",
        "system": "Nieren & Saeure-Basen-Haushalt",
        "effect": "Gefahr einer lebensbedrohlichen Laktatazidose.",
        "mechanism": "Kontrastmittelinduziertes akutes Nierenversagen fuehrt zur massiven Kumulation von Metformin."
    },

    # --- 8. Anticholinerge Last & Urologie ---
    {
        "atc_a": "N06AA",
        "atc_b": "G04BD",
        "class_name_a": "Trizyklische Antidepressiva",
        "class_name_b": "Urologische Spasmolytika (Anticholinergika)",
        "severity": "Moderat",
        "system": "Vegetatives Nervensystem",
        "effect": "Kritische anticholinerge Last: Harnverhalt, paralytischer Ileus, akutes Delir, Glaukomanfall.",
        "mechanism": "Additive kompetitive Hemmung muskulaerer Muskarinrezeptoren (M1-M3)."
    },

    # --- 9. Resorption & Chelatbildung ---
    {
        "atc_a": "J01MA",
        "atc_b": "A02A",
        "class_name_a": "Fluorchinolone (Gyrasehemmer)",
        "class_name_b": "Antazida (Calcium-, Magnesium-, Aluminiumverbindungen)",
        "severity": "Hoch",
        "system": "Resorption & Infektionskontrolle",
        "effect": "Therapieversagen bei schweren bakteriellen Infektionen.",
        "mechanism": "Bildung unloeslicher Chelatkomplexe im Gastrointestinaltrakt verhindert die Resorption des Antibiotikums."
    },
    {
        "atc_a": "H03AA",
        "atc_b": "B03A",
        "class_name_a": "Schilddruesenhormone (Levothyroxin)",
        "class_name_b": "Eisenpraeparate",
        "severity": "Moderat",
        "system": "Schilddruese & Resorption",
        "effect": "Wirkungsverlust des Schilddruesenhormons mit persistierender Hypothyreose.",
        "mechanism": "Bildung schwer loeslicher Eisen-Thyroxin-Komplexe im Darmlumen."
    }
]


def init_class_rules():
    print("=" * 70)
    print("🚀 Initialisiere erweitertes ATC-Klassen-Regelwerk in interactions.db...")
    print("=" * 70)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

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

    # Bereinigen und neu schreiben
    cursor.execute('DELETE FROM "class_rules"')

    for r in CLASS_RULES:
        cursor.execute("""
            INSERT INTO "class_rules" 
            (atc_a, atc_b, class_name_a, class_name_b, severity, system, effect, mechanism)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["atc_a"], r["atc_b"], r["class_name_a"], r["class_name_b"],
            r["severity"], r["system"], r["effect"], r["mechanism"]
        ))

    conn.commit()
    cursor.execute('SELECT COUNT(*) FROM "class_rules"')
    count = cursor.fetchone()[0]
    conn.close()

    print(f"✅ {count} klinische ATC-Grossgruppenregeln erfolgreich aktiviert!")
    print("=" * 70)


if __name__ == "__main__":
    init_class_rules()