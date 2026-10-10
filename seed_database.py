"""
seed_database.py
Befüllt die SQLite-Datenbank interactions.db mit den wichtigsten klinischen
Interaktionen der am häufigsten verordneten Medikamente in Deutschland.
"""

from cache_manager import save_to_cache, get_total_cached_count

# Das kuratierte Praxis-Set: Die wichtigsten klinischen Risikopaare
CORE_DATA = [
    # --- Blutverdünnung & Blutungsrisiken ---
    {
        "pair": ("Ibuprofen", "ASS"),
        "severity": "Hoch",
        "system": "Magen-Darm-Trakt & Hämostase",
        "effect": "Massiv erhöhtes Risiko für Magengeschwüre, Blutungen und Aufhebung des Herzschutzes von ASS.",
        "mechanism": "Beide Wirkstoffe hemmen Cyclooxygenasen und schädigen die Magenschleimhaut. Ibuprofen blockiert zudem sterisch die Bindungsstelle für ASS an Thrombozyten."
    },
    {
        "pair": ("Ibuprofen", "Apixaban"),
        "severity": "Hoch",
        "system": "Hämostase & Magen-Darm-Trakt",
        "effect": "Kritisch erhöhtes Risiko schwerer gastrointestinaler Blutungen.",
        "mechanism": "NSAR verursachen Schleimhautläsionen im Verdauungstrakt; Apixaban hemmt Faktor Xa, wodurch die Blutgerinnung massiv unterdrückt wird."
    },
    {
        "pair": ("ASS", "Apixaban"),
        "severity": "Hoch",
        "system": "Hämostase (Blutgerinnung)",
        "effect": "Drastisch gesteigerte Blutungsneigung (z. B. Magen- oder Hirnblutungen).",
        "mechanism": "Additive Wirkung: Thrombozytenaggregationshemmung trifft auf direkte Hemmung der plasmatischen Gerinnungskaskade."
    },
    {
        "pair": ("Phenprocoumon", "ASS"),
        "severity": "Hoch",
        "system": "Hämostase (Blutgerinnung)",
        "effect": "Schwere Blutungsneigung, spontane Hämatome und innere Blutungen.",
        "mechanism": "Kombination aus Vitamin-K-Syntheseblockade von Gerinnungsfaktoren und irreversibler Plättchenhemmung."
    },
    {
        "pair": ("Phenprocoumon", "Ibuprofen"),
        "severity": "Hoch",
        "system": "Magen-Darm & Hämostase",
        "effect": "Schwere Magen-Darm-Blutungen und unberechenbare INR-Schwankungen.",
        "mechanism": "NSAR verdrängen Cumarine teilweise aus der Plasmaproteinbindung und schädigen gleichzeitig die Magenbarriere."
    },
    {
        "pair": ("ASS", "Ginkgo Biloba"),
        "severity": "Moderat",
        "system": "Hämostase (Blutgerinnung)",
        "effect": "Erhöhte Neigung zu Hämatomen, Nasenbluten und Nachblutungen.",
        "mechanism": "Ginkgolide hemmen den Plättchenaktivierungsfaktor (PAF) und verstärken die thrombozytenhemmende Wirkung von ASS additiv."
    },
    {
        "pair": ("Citalopram", "ASS"),
        "severity": "Moderat",
        "system": "Hämostase & Thrombozyten",
        "effect": "Erhöhte Blutungsneigung im oberen Magen-Darm-Trakt.",
        "mechanism": "SSRI blockieren die Wiederaufnahme von Serotonin in Thrombozyten, was deren Aggregationsfähigkeit bei Gefäßverletzungen schwächt."
    },
    {
        "pair": ("Citalopram", "Ibuprofen"),
        "severity": "Moderat",
        "system": "Magen-Darm-Trakt & Hämostase",
        "effect": "Deutlich erhöhtes Risiko für gastrointestinale Schleimhautblutungen.",
        "mechanism": "Synergistischer Schädigungsmechanismus an der Magenschleimhaut bei gleichzeitiger Störung der plättchenvermittelten Blutstillung."
    },

    # --- Niere & Herz-Kreislauf (Triple Whammy Komponenten) ---
    {
        "pair": ("Ibuprofen", "Ramipril"),
        "severity": "Hoch",
        "system": "Nierenfunktion & Blutdruck",
        "effect": "Akute Verschlechterung der Nierenfiltration & Abschwächung der Blutdrucksenkung.",
        "mechanism": "Ramipril erweitert das abführende Gefäß der Nierenknäuelchen (Vas efferens), Ibuprofen drosselt über Prostaglandinhemmung das zuführende Gefäß (Vas afferens). Der Filtrationsdruck bricht ein."
    },
    {
        "pair": ("Ibuprofen", "Candesartan"),
        "severity": "Hoch",
        "system": "Nierenfunktion & Blutdruck",
        "effect": "Gefahr des akuten Nierenversagens und Wirkungsverlust des Blutdrucksenkers.",
        "mechanism": "Analoger Mechanismus zum ACE-Hemmer: AT1-Blockade am Vas efferens kombiniert mit afferenter Vasokonstriktion durch NSAR."
    },
    {
        "pair": ("Ibuprofen", "HCT"),
        "severity": "Moderat",
        "system": "Niere & Flüssigkeitshaushalt",
        "effect": "Verminderte Diurese (Entwässerung) und Anstieg des Blutdrucks.",
        "mechanism": "NSAR führen durch intrarenale Prostaglandinhemmung zu Natrium- und Wasserretention, was dem Thiazid-Effekt direkt entgegenwirkt."
    },
    {
        "pair": ("Ibuprofen", "Torasemid"),
        "severity": "Moderat",
        "system": "Niere & Volumenhaushalt",
        "effect": "Abschwächung der Schleifendiuretikum-Wirkung und Nierenbelastung.",
        "mechanism": "Kompensation des renalen Blutflusses wird gehemmt; verringerte fraktionelle Natrium-Ausscheidung."
    },
    {
        "pair": ("Ramipril", "HCT"),
        "severity": "Moderat",
        "system": "Kreislauf & Elektrolyte",
        "effect": "Risiko eines initialen Blutdruckabfalls sowie Störungen im Kaliumhaushalt.",
        "mechanism": "Gängige Kombination, erfordert jedoch zu Beginn engmaschiges Monitoring von Serumkreatinin und Elektrolyten."
    },
    {
        "pair": ("Ramipril", "Spironolacton"),
        "severity": "Hoch",
        "system": "Elektrolythaushalt (Kalium)",
        "effect": "Gefahr einer lebensbedrohlichen Hyperkaliämie (Herzrhythmusstörungen).",
        "mechanism": "Beide Wirkstoffe halten Kalium im Körper zurück: ACE-Hemmer über Aldosteronsenkung, Spironolacton als kaliumsparendes Diuretikum."
    },

    # --- Herzrhythmus & Puls ---
    {
        "pair": ("Metoprolol", "Amlodipin"),
        "severity": "Moderat",
        "system": "Herz-Kreislauf & Reizleitung",
        "effect": "Gefahr von ausgeprägter Hypotonie (niedriger Blutdruck) und Bradykardie (verlangsamter Puls).",
        "mechanism": "Additive kardiodepressive Effekte: Betablockade trifft auf periphere Vasodilatation."
    },
    {
        "pair": ("Citalopram", "Pantoprazol"),
        "severity": "Moderat",
        "system": "Herzrhythmus (QT-Zeit)",
        "effect": "Erhöhtes Risiko für Herzrhythmusstörungen (QT-Verlängerung).",
        "mechanism": "Pantoprazol kann den Plasmaspiegel von Citalopram über Enzymhemmung leicht steigern; beide Substanzen besitzen ein eigenständiges Potenzial zur Verlängerung des QT-Intervalls."
    },

    # --- Stoffwechsel, Leber & Muskeln ---
    {
        "pair": ("Simvastatin", "Amlodipin"),
        "severity": "Moderat",
        "system": "Muskulatur & CYP3A4-Enzym",
        "effect": "Erhöhtes Risiko für Muskelschmerzen bis hin zum Muskelzerfall (Rhabdomyolyse).",
        "mechanism": "Amlodipin inhibiert das Leberenzym CYP3A4, wodurch der Abbau von Simvastatin verlangsamt wird und dessen Blutspiegel ansteigt (Maximaldosis beachten: 20 mg)."
    },
    {
        "pair": ("Atorvastatin", "Clarithromycin"),
        "severity": "Hoch",
        "system": "Leber & Skelettmuskulatur",
        "effect": "Gefahr schwerer Myopathien und Rhabdomyolyse.",
        "mechanism": "Starke CYP3A4-Inhibition durch das Makrolid-Antibiotikum führt zu toxischen Statin-Spiegeln."
    },
    {
        "pair": ("Pantoprazol", "Metformin"),
        "severity": "Moderat",
        "system": "Magen-Darm & Resorption",
        "effect": "Langfristig erhöhtes Risiko für Vitamin-B12-Mangel und periphere Neuropathien.",
        "mechanism": "Magensäureblockade vermindert die Freisetzung von Vitamin B12 aus der Nahrung; Metformin behindert zusätzlich dessen calciumabhängige Aufnahme im Dünndarm."
    },
    {
        "pair": ("Ramipril", "Metformin"),
        "severity": "Moderat",
        "system": "Blutzucker-Regulation",
        "effect": "Gefahr unerwarteter Unterzuckerungen (Hypoglykämien).",
        "mechanism": "ACE-Hemmer können die periphere Insulinsensitivität erhöhen und die endogene Glukoseproduktion drosseln."
    },
    {
        "pair": ("Ibuprofen", "Metformin"),
        "severity": "Moderat",
        "system": "Niere & Laktathaushalt",
        "effect": "Gefahr einer Laktatazidose bei Einschränkung der Nierenfiltration.",
        "mechanism": "Metformin wird unverändert über die Nieren ausgeschieden. Drosselt Ibuprofen die GFR, akkumuliert Metformin im Organismus."
    }
]

def run_seed():
    print("=" * 60)
    print("🚀 Starte Vorbefüllung (Seeding) von interactions.db ...")
    print("=" * 60)
    
    vorher = get_total_cached_count()
    print(f"Bestehende Einträge vor dem Lauf: {vorher}")
    
    hinzugefuegt = 0
    for item in CORE_DATA:
        d1, d2 = item["pair"]
        save_to_cache(d1, d2, {
            "severity": item["severity"],
            "system": item["system"],
            "effect": item["effect"],
            "mechanism": item["mechanism"],
            "source": "Klinische Core-DB (SQLite)"
        })
        hinzugefuegt += 1
        print(f" -> Gespeichert: {d1} + {d2} [{item['severity']}]")
        
    nachher = get_total_cached_count()
    print("=" * 60)
    print(f"✅ Seeding abgeschlossen!")
    print(f"Einträge verarbeitet: {hinzugefuegt}")
    print(f"Gesamtbestand in interactions.db: {nachher}")
    print("=" * 60)

if __name__ == "__main__":
    run_seed()