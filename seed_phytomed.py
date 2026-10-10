"""
seed_phytomed.py
Automatische Einspeisung von Phytopharmaka, Nahrungsergänzungsmitteln
und Nahrungsmittel-Interaktoren in interactions.db.
Verknüpft diese automatisiert über ATC-Klassen (z. B. Grapefruit -> CYP3A4-Substrate wie Statine, SSRI, Antihypertensiva).
"""

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "interactions.db")

# 1. Nicht-Arzneistoff-Katalog für die Autocomplete-Suche
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
        "name": "Lakritze / Süßholzwurzel 🍬",
        "atc_code": "PHYTO_LAKRITZE",
        "drug_class": "Nahrungsmittel (11b-HSD2-Inhibitor)",
        "organ_system": "Elektrolyte & Blutdruck",
        "metabolism": "Hemmung von 11beta-HSD2 (Cortisol-Akkumulation)"
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

# 2. Regelwerk: Verknüpft die Phyto-Stoffe automatisch mit ganzen ATC-Klassen
PHYTO_RULES = [
    # --- GRAPEFRUIT ---
    {
        "phyto_code": "PHYTO_GRAPEFRUIT",
        "target_atc": "C10AA",  # Statine (Simvastatin, Atorvastatin)
        "severity": "Hoch",
        "system": "Muskulatur & Leber",
        "effect": "Massiver Anstieg der Statin-Blutspiegel (bis zu 12-fach). Hohes Risiko für Myopathie und Rhabdomyolyse.",
        "mechanism": "Furanocumarine in Grapefruit inaktivieren irreversibel das Darmwandenzym CYP3A4, wodurch der first-pass-Abbau wegfällt."
    },
    {
        "phyto_code": "PHYTO_GRAPEFRUIT",
        "target_atc": "C08CA",  # Calciumkanalblocker (Amlodipin, Felodipin, Nifedipin)
        "severity": "Hoch",
        "system": "Kreislauf & Blutdruck",
        "effect": "Starke Blutdruckabfälle, Schwindel, Tachykardie und periphere Ödeme.",
        "mechanism": "Verhinderter CYP3A4-Abbau führt zu stark erhöhter Bioverfügbarkeit der Dihydropyridine."
    },
    {
        "phyto_code": "PHYTO_GRAPEFRUIT",
        "target_atc": "N06AB",  # SSRI Antidepressiva (Sertralin etc.)
        "severity": "Moderat",
        "system": "Zentralnervensystem",
        "effect": "Erhöhte Wirkspiegel des Antidepressivums. Verstärkte Nebenwirkungen (Tremor, Schwindel, Übelkeit, Sedierung).",
        "mechanism": "Kompetitive Hemmung des CYP3A4-vermittelten Abbaus von Sertralin und verwandten Antidepressiva."
    },
    {
        "phyto_code": "PHYTO_GRAPEFRUIT",
        "target_atc": "L04AD",  # Calcineurin-Inhibitoren (Tacrolimus, Ciclosporin)
        "severity": "Hoch",
        "system": "Nierenfunktion & Immunsystem",
        "effect": "Toxische Spiegelspitzen des Immunsuppressivums mit akuter Nephrotoxizität.",
        "mechanism": "Duale Hemmung von enteralem CYP3A4 und P-Glykoprotein."
    },

    # --- JOHANNISKRAUT ---
    {
        "phyto_code": "PHYTO_JOHANNISKRAUT",
        "target_atc": "L04A",  # Immunsuppressiva
        "severity": "Hoch",
        "system": "Immunsystem & Transplantation",
        "effect": "Akuter Wirkungsverlust mit lebensgefährlichem Risiko für Transplantatabstoßung.",
        "mechanism": "Hyperforin aktiviert den PXR-Rezeptor und induziert CYP3A4 und P-Glykoprotein massiv. Die Wirkstoffe werden vorzeitig eliminiert."
    },
    {
        "phyto_code": "PHYTO_JOHANNISKRAUT",
        "target_atc": "B01AF",  # DOAKs (Faktor-Xa-Hemmer: Rivaroxaban, Apixaban)
        "severity": "Hoch",
        "system": "Blutgerinnung",
        "effect": "Wirkverlust des Gerinnungshemmers mit Risiko für Schlaganfälle und Thrombosen.",
        "mechanism": "Beschleunigte Elimination über induziertes CYP3A4 und Efflux-Transporter P-Glykoprotein."
    },
    {
        "phyto_code": "PHYTO_JOHANNISKRAUT",
        "target_atc": "G03A",  # Hormonelle Kontrazeptiva ("Anti-Baby-Pille")
        "severity": "Hoch",
        "system": "Hormonhaushalt",
        "effect": "Verlust des Empfängnisschutzes (Zwischenblutungen, ungewollte Schwangerschaft).",
        "mechanism": "Beschleunigter hepatischer Abbau von Östrogenen und Gestagenen durch CYP3A4-Induktion."
    },
    {
        "phyto_code": "PHYTO_JOHANNISKRAUT",
        "target_atc": "N06A",  # Antidepressiva (SSRI, SNRI, Trizyklika)
        "severity": "Hoch",
        "system": "Zentralnervensystem",
        "effect": "Gefahr eines lebensbedrohlichen Serotoninsyndroms (Hyperthermie, Tremor, Myoklonien, Delir).",
        "mechanism": "Pharmakodynamischer Synergismus: Additive Hemmung der Serotonin-Wiederaufnahme am synaptischen Spalt."
    },

    # --- GINKGO BILOBA ---
    {
        "phyto_code": "PHYTO_GINKGO",
        "target_atc": "B01",  # Alle Antithrombotika / Antikoagulanzien / Thrombozytenhemmer
        "severity": "Hoch",
        "system": "Hämostase & Blutgerinnung",
        "effect": "Signifikant erhöhtes Risiko spontaner Blutungen (inkl. Hirnblutungen und Magen-Darm-Blutungen).",
        "mechanism": "Ginkgolide hemmen den Platelet-Activating Factor (PAF) und verstärken die Blutungsneigung additiv."
    },
    {
        "phyto_code": "PHYTO_GINKGO",
        "target_atc": "M01A",  # NSAR-Schmerzmittel (Ibuprofen, Diclofenac etc.)
        "severity": "Moderat",
        "system": "Blutgerinnung & Magenschleimhaut",
        "effect": "Gesteigerte Blutungsneigung und mukosale Mikroläsionen.",
        "mechanism": "Kombinierte Hemmung von COX-1 (NSAR) und PAF-Rezeptor (Ginkgo)."
    },

    # --- LAKRITZE ---
    {
        "phyto_code": "PHYTO_LAKRITZE",
        "target_atc": "C03",  # Diuretika (Schleifendiuretika, Thiazide)
        "severity": "Hoch",
        "system": "Elektrolyte & Herzrhythmus",
        "effect": "Schwere, therapieresistente Hypokaliämie und Arrhythmierisiko.",
        "mechanism": "Glycyrrhizin blockiert 11beta-HSD2, Cortisol stimuliert Mineralokortikoid-Rezeptoren. Dies potenziert renale Kaliumverluste durch Diuretika."
    },
    {
        "phyto_code": "PHYTO_LAKRITZE",
        "target_atc": "C01A",  # Herzglykoside (Digoxin, Digitoxin)
        "severity": "Hoch",
        "system": "Kardiale Reizleitung",
        "effect": "Toxische Glykosid-Wirkung mit lebensgefährlichen ventrikulären Herzrhythmusstörungen.",
        "mechanism": "Hypokaliämie durch Lakritze sensibilisiert das Myokard massiv für Digitalisglykoside."
    },

    # --- CALCIUM / MILCHPRODUKTE ---
    {
        "phyto_code": "PHYTO_CALCIUM",
        "target_atc": "J01MA",  # Fluorchinolone (Ciprofloxacin, Moxifloxacin)
        "severity": "Hoch",
        "system": "Resorption / Infektionsschutz",
        "effect": "Massives Therapieversagen der Antibiotika-Behandlung (Resorptionsabfall bis zu 90%).",
        "mechanism": "Bildung stabiler, nicht-resorbierbarer Chelat-Komplexe mit zweiwertigen Calcium-Ionen im Darmlumen."
    },
    {
        "phyto_code": "PHYTO_CALCIUM",
        "target_atc": "J01AA",  # Tetracycline (Doxycyclin)
        "severity": "Hoch",
        "system": "Resorption",
        "effect": "Therapieversagen bei bakteriellen Infektionen.",
        "mechanism": "Chelatkomplex-Bildung verhindert die enterale Absorption."
    },
    {
        "phyto_code": "PHYTO_CALCIUM",
        "target_atc": "H03AA",  # Schilddrüsenhormone (Levothyroxin)
        "severity": "Moderat",
        "system": "Schilddrüse & Stoffwechsel",
        "effect": "Verminderte Hormonresorption mit persistierender Schilddrüsenunterfunktion.",
        "mechanism": "Adsorption von Thyroxin an unlösliche Calciumsalze im Magen-Darm-Trakt."
    },

    # --- CANNABIDIOL (CBD) ---
    {
        "phyto_code": "PHYTO_CBD",
        "target_atc": "N03A",  # Antiepileptika (Clobazam etc.)
        "severity": "Hoch",
        "system": "Zentralnervensystem",
        "effect": "Exzessive Sedierung, Ataxie und Atemdämpfung durch Akkumulation aktiver Metaboliten.",
        "mechanism": "CBD inhibiert CYP2C19 und CYP3A4, wodurch der Abbau von N-Desmethylclobazam blockiert wird."
    }
]

def init_phytomed():
    print("=" * 70)
    print("🌿 Initialisiere Phytomedizin- & Nahrungsmittel-Engine...")
    print("=" * 70)

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Tabelle für Phytoregeln anlegen
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

    for r in PHYTO_RULES:
        cursor.execute("""
            INSERT INTO "phytomed_rules" (phyto_code, target_atc, severity, system, effect, mechanism)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (r["phyto_code"], r["target_atc"], r["severity"], r["system"], r["effect"], r["mechanism"]))

    # Phyto-Items in 'drugs' eintragen, damit sie in der Suchleiste erscheinen
    for item in PHYTO_ITEMS:
        cursor.execute("""
            INSERT OR REPLACE INTO "drugs" (name, atc_code, drug_class, organ_system, metabolism)
            VALUES (?, ?, ?, ?, ?)
        """, (item["name"], item["atc_code"], item["drug_class"], item["organ_system"], item["metabolism"]))

    conn.commit()
    cursor.execute('SELECT COUNT(*) FROM "phytomed_rules"')
    rules_count = cursor.fetchone()[0]
    conn.close()

    print(f"✅ {len(PHYTO_ITEMS)} Phyto-/Nahrungsmittel in Autocomplete hinterlegt.")
    print(f"✅ {rules_count} automatische Phyto-Interaktionsregeln aktiviert!")
    print("=" * 70)

if __name__ == "__main__":
    init_phytomed()