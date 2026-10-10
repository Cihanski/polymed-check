"""
seed_phytomed.py
Einspeisung von Phytopharmaka, Nahrungsmitteln und Phyto-Phyto-Interaktionen.
"""

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "interactions.db")

PHYTO_ITEMS = [
    {
        "name": "Grapefruit / Grapefruitsaft 🍊",
        "atc_code": "PHYTO_GRAPEFRUIT",
        "drug_class": "Nahrungsmittel (CYP3A4-Inhibitor)",
        "organ_system": "Gastrointestinal / Leber",
        "metabolism": "Irreversible Hemmung von intestinalem CYP3A4 & P-gp"
    },
    {
        "name": "Johanniskraut (Hypericum perforatum) 🌿",
        "atc_code": "PHYTO_JOHANNISKRAUT",
        "drug_class": "Phytopharmakon (CYP/P-gp-Induktor)",
        "organ_system": "Leber / Zentralnervensystem",
        "metabolism": "Starke Induktion von CYP3A4, CYP2C9, CYP2C19 & P-gp"
    },
    {
        "name": "Ginkgo biloba Extrakt 🍃",
        "atc_code": "PHYTO_GINKGO",
        "drug_class": "Phytopharmakon (PAF-Inhibitor)",
        "organ_system": "Blutgerinnung",
        "metabolism": "Hemmung des Platelet-Activating Factor (PAF)"
    },
    {
        "name": "Knoblauchextrakt (hochdosiert / Allium sativum) 🧄",
        "atc_code": "PHYTO_GARLIC",
        "drug_class": "Nahrungsergänzungsmittel (Thrombozytenaggregationshemmer)",
        "organ_system": "Blutgerinnung",
        "metabolism": "Hemmung der Thromboxan-Synthese"
    },
    {
        "name": "Lakritze / Süßholzwurzel 🍬",
        "atc_code": "PHYTO_LAKRITZE",
        "drug_class": "Nahrungsmittel (11b-HSD2-Inhibitor)",
        "organ_system": "Elektrolyte & Blutdruck",
        "metabolism": "Hemmung von 11beta-HSD2 (Cortisol-Akkumulation)"
    },
    {
        "name": "Sennesblätter / Faulbaum (Anthranoid-Laxanzien) 🍂",
        "atc_code": "PHYTO_SENNA",
        "drug_class": "Pflanzliches Abführmittel (Laxans)",
        "organ_system": "Elektrolyte & Darm",
        "metabolism": "Sekretagoge Kalium- und Wassersekretion im Kolon"
    },
    {
        "name": "Milchprodukte & Calciumreiches Wasser 🥛",
        "atc_code": "PHYTO_CALCIUM",
        "drug_class": "Nahrungsmittel / Chelatbildner",
        "organ_system": "Resorption Gastrointestinal",
        "metabolism": "Komplexierung mehrwertiger Kationen (Ca2+)"
    },
    {
        "name": "Cannabidiol (CBD-Öl / Hanfextrakte) 🌿",
        "atc_code": "PHYTO_CBD",
        "drug_class": "Cannabinoid / Enzym-Inhibitor",
        "organ_system": "ZNS & Leber",
        "metabolism": "Inhibition von CYP3A4, CYP2C19 & CYP2D6"
    },
    {
        "name": "Grüntee-Extrakt (hochdosiert EGCG) 🍵",
        "atc_code": "PHYTO_GREENTEA",
        "drug_class": "Nahrungsbestandteil (Transporter-Inhibitor)",
        "organ_system": "Resorption",
        "metabolism": "Hemmung von OATP1A2, OATP2B1 & P-gp"
    }
]

# Regeln gegen Arzneistoffe (Target = ATC)
PHYTO_ATC_RULES = [
    # Grapefruit
    {"phyto_code": "PHYTO_GRAPEFRUIT", "target_atc": "C10AA", "severity": "Hoch", "system": "Muskulatur & Leber",
     "effect": "Massiver Anstieg der Statin-Blutspiegel (bis zu 12-fach). Hohes Risiko für Myopathie und Rhabdomyolyse.",
     "mechanism": "Furanocumarine inaktivieren irreversibel intestinales CYP3A4."},
    {"phyto_code": "PHYTO_GRAPEFRUIT", "target_atc": "C08CA", "severity": "Hoch", "system": "Kreislauf & Blutdruck",
     "effect": "Starke Blutdruckabfälle, Schwindel, Tachykardie und periphere Ödeme.",
     "mechanism": "Verhinderter first-pass CYP3A4-Abbau der Dihydropyridine."},
    {"phyto_code": "PHYTO_GRAPEFRUIT", "target_atc": "N06AB", "severity": "Moderat", "system": "ZNS",
     "effect": "Erhöhte SSRI-Spiegel mit verstärkten Nebenwirkungen (Tremor, Sedierung).",
     "mechanism": "Kompetitive Hemmung des CYP3A4-Abbaus."},
    {"phyto_code": "PHYTO_GRAPEFRUIT", "target_atc": "L04AD", "severity": "Hoch", "system": "Nierenfunktion",
     "effect": "Toxische Immunsuppressiva-Spitzen mit akuter Nephrotoxizität.",
     "mechanism": "Duale Hemmung von enteralem CYP3A4 und P-Glykoprotein."},

    # Johanniskraut
    {"phyto_code": "PHYTO_JOHANNISKRAUT", "target_atc": "L04A", "severity": "Hoch", "system": "Transplantation",
     "effect": "Akuter Wirkungsverlust mit lebensgefährlichem Risiko für Transplantatabstoßung.",
     "mechanism": "Hyperforin induziert CYP3A4 und P-gp massiv."},
    {"phyto_code": "PHYTO_JOHANNISKRAUT", "target_atc": "B01AF", "severity": "Hoch", "system": "Blutgerinnung",
     "effect": "Wirkverlust der DOAKs mit Risiko für Thrombosen und Schlaganfälle.",
     "mechanism": "Beschleunigte Elimination über induziertes CYP3A4 und P-gp."},
    {"phyto_code": "PHYTO_JOHANNISKRAUT", "target_atc": "G03A", "severity": "Hoch", "system": "Hormonhaushalt",
     "effect": "Verlust des Empfängnisschutzes bei oralen Kontrazeptiva.",
     "mechanism": "Beschleunigter hepatischer Östrogen- und Gestagenabbau."},
    {"phyto_code": "PHYTO_JOHANNISKRAUT", "target_atc": "N06A", "severity": "Hoch", "system": "ZNS",
     "effect": "Gefahr eines lebensbedrohlichen Serotoninsyndroms.",
     "mechanism": "Additive Hemmung der serotonergen Wiederaufnahme."},

    # Ginkgo
    {"phyto_code": "PHYTO_GINKGO", "target_atc": "B01", "severity": "Hoch", "system": "Hämostase",
     "effect": "Signifikant erhöhtes Risiko spontaner Blutungen.",
     "mechanism": "Ginkgolide hemmen den Platelet-Activating Factor (PAF) additiv zur Antikoagulation."},
    {"phyto_code": "PHYTO_GINKGO", "target_atc": "M01A", "severity": "Moderat", "system": "Magen & Gerinnung",
     "effect": "Gesteigerte Blutungsneigung und mukosale Schädigung.",
     "mechanism": "Kombinierte Hemmung von COX-1 und PAF-Rezeptor."},

    # Knoblauch
    {"phyto_code": "PHYTO_GARLIC", "target_atc": "B01", "severity": "Hoch", "system": "Hämostase",
     "effect": "Potenzierung des Blutungsrisikos unter Antikoagulanzien/Thrombozytenaggregationshemmern.",
     "mechanism": "Additive Thrombozyteninhibition durch Schwefelverbindungen (Ajoen/Allicin)."},

    # Lakritze
    {"phyto_code": "PHYTO_LAKRITZE", "target_atc": "C03", "severity": "Hoch", "system": "Elektrolyte",
     "effect": "Schwere Hypokaliämie und Arrhythmierisiko.",
     "mechanism": "Glycyrrhizin hemmt 11beta-HSD2 und potenziert renale Kaliumverluste."},
    {"phyto_code": "PHYTO_LAKRITZE", "target_atc": "C01A", "severity": "Hoch", "system": "Herzrhythmus",
     "effect": "Toxische Glykosid-Wirkung mit ventrikulären Rhythmusstörungen.",
     "mechanism": "Hypokaliämie sensibilisiert das Myokard für Digitalisglykoside."},

    # Sennesblätter / Faulbaum
    {"phyto_code": "PHYTO_SENNA", "target_atc": "C01A", "severity": "Hoch", "system": "Herzrhythmus",
     "effect": "Gesteigerte Toxizität von Digitalisglykosiden.",
     "mechanism": "Chronische enterale Kaliumverluste führen zu myokardialer Überempfindlichkeit."},
    {"phyto_code": "PHYTO_SENNA", "target_atc": "C03", "severity": "Moderat", "system": "Elektrolyte",
     "effect": "Verstärkter Kaliumverlust durch additive diuretische und laxierende Effekte.",
     "mechanism": "Kombinierte renale und intestinale Kaliumsekretion."},

    # Calcium / Milch
    {"phyto_code": "PHYTO_CALCIUM", "target_atc": "J01MA", "severity": "Hoch", "system": "Resorption",
     "effect": "Therapieversagen von Fluorchinolonen (bis zu 90% Resorptionsverlust).",
     "mechanism": "Unlösliche Chelatkomplex-Bildung mit Ca2+-Ionen."},
    {"phyto_code": "PHYTO_CALCIUM", "target_atc": "J01AA", "severity": "Hoch", "system": "Resorption",
     "effect": "Therapieversagen bei Tetracyclinen.",
     "mechanism": "Chelatkomplexierung verhindert enterale Aufnahme."},
    {"phyto_code": "PHYTO_CALCIUM", "target_atc": "H03AA", "severity": "Moderat", "system": "Schilddrüse",
     "effect": "Verminderte L-Thyroxin-Resorption.",
     "mechanism": "Adsorption an unlösliche Calciumsalze."},

    # Cannabidiol
    {"phyto_code": "PHYTO_CBD", "target_atc": "N03A", "severity": "Hoch", "system": "ZNS",
     "effect": "Exzessive Sedierung und Ataxie bei Antiepileptika (z. B. Clobazam).",
     "mechanism": "Hemmung von CYP2C19 und CYP3A4 verzögert Metabolitenabbau."}
]

# Regeln für Pflanze + Pflanze (Target = Phyto-Code)
PHYTO_PHYTO_RULES = [
    {
        "phyto_a": "PHYTO_GINKGO",
        "phyto_b": "PHYTO_GARLIC",
        "severity": "Moderat",
        "system": "Blutgerinnung",
        "effect": "[Phyto-Kombination] Additive Thrombozytenaggregationshemmung mit gesteigerter Blutungsneigung.",
        "mechanism": "Duale Hemmung: Ginkgolide blockieren PAF, während Allicin/Ajoen die Thromboxan-Bildung hemmen."
    },
    {
        "phyto_a": "PHYTO_LAKRITZE",
        "phyto_b": "PHYTO_SENNA",
        "severity": "Hoch",
        "system": "Elektrolyte & Kreislauf",
        "effect": "[Phyto-Kombination] Akuter Kaliumverlust (schwere Hypokaliämie) und Muskelschwäche.",
        "mechanism": "Synergismus: Renale Kaliumausscheidung (Lakritze) plus intestinaler Kaliumverlust (Anthranoid-Laxans)."
    },
    {
        "phyto_a": "PHYTO_JOHANNISKRAUT",
        "phyto_b": "PHYTO_CBD",
        "severity": "Moderat",
        "system": "Lebermetabolismus",
        "effect": "[Phyto-Kombination] Kinetischer Antagonismus an Cytochrom-P450-Enzymen.",
        "mechanism": "Johanniskraut induziert CYP3A4, während CBD dasselbe Isoenzym inhibiert. Blutspiegel begleitender Substanzen werden unvorhersehbar."
    }
]


def init_phytomed():
    print("=" * 70)
    print("🌿 Aktualisiere Phytomedizin-, Nahrungsmittel- & Phyto-Phyto-Engine...")
    print("=" * 70)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

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
    cursor.execute('DELETE FROM "phytomed_rules"')

    # 1. Phyto-zu-ATC Regeln
    for r in PHYTO_ATC_RULES:
        cursor.execute("""
            INSERT INTO "phytomed_rules" (phyto_code, target_atc, severity, system, effect, mechanism)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (r["phyto_code"], r["target_atc"], r["severity"], r["system"], r["effect"], r["mechanism"]))

    # 2. Phyto-zu-Phyto Regeln in dieselbe Tabelle
    for r in PHYTO_PHYTO_RULES:
        cursor.execute("""
            INSERT INTO "phytomed_rules" (phyto_code, target_atc, severity, system, effect, mechanism)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (r["phyto_a"], r["phyto_b"], r["severity"], r["system"], r["effect"], r["mechanism"]))

    # 3. Phyto-Items in 'drugs' eintragen
    for item in PHYTO_ITEMS:
        cursor.execute("""
            INSERT OR REPLACE INTO "drugs" (name, atc_code, drug_class, organ_system, metabolism)
            VALUES (?, ?, ?, ?, ?)
        """, (item["name"], item["atc_code"], item["drug_class"], item["organ_system"], item["metabolism"]))

    conn.commit()
    cursor.execute('SELECT COUNT(*) FROM "phytomed_rules"')
    rules_count = cursor.fetchone()[0]
    conn.close()

    print(f"✅ {len(PHYTO_ITEMS)} Phyto-/Nahrungsmittel im Autocomplete hinterlegt.")
    print(f"✅ {rules_count} Phyto- und Phyto-Phyto-Regeln aktiv!")
    print("=" * 70)


if __name__ == "__main__":
    init_phytomed()