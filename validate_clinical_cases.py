"""
validate_clinical_cases.py
Automatisierte Validierung kritischer klinischer Interaktionsszenarien
fuer MediCheck (Pharmakokinetik, Haemostase, Elektrolyte, Resorption, ZNS).
"""

from cache_manager import (
    get_all_atc_codes,
    check_cache,
    check_phytomed_rules,
    check_class_rules
)


def find_interaction_test(drug_a, drug_b):
    """Simuliert die Kern-Pruefkaskade ohne externen openFDA-Netzwerk-Call."""
    cached = check_cache(drug_a, drug_b)
    if cached:
        return cached

    phyto_match = check_phytomed_rules(drug_a, drug_b)
    if phyto_match:
        return phyto_match

    class_match = check_class_rules(drug_a, drug_b)
    if class_match:
        return class_match

    return None


TEST_CASES = [
    (
        "Grapefruit / Grapefruitsaft 🍊",
        "Simvastatin",
        "Hoch",
        "CYP3A4-Inhibition -> Rhabdomyolyse"
    ),
    (
        "Grapefruit / Grapefruitsaft 🍊",
        "Amlodipine",
        "Hoch",
        "CYP3A4-Inhibition -> Vasodilatation / Hypotonie"
    ),
    (
        "Johanniskraut (Hypericum perforatum) 🌿",
        "Ciclosporin",
        "Hoch",
        "CYP3A4/P-gp-Induktion -> Transplantatabstossung"
    ),
    (
        "Johanniskraut (Hypericum perforatum) 🌿",
        "Citalopram",
        "Hoch",
        "Serotonerger Synergismus -> Serotoninsyndrom"
    ),
    (
        "Johanniskraut (Hypericum perforatum) 🌿",
        "Rivaroxaban",
        "Hoch",
        "P-gp/CYP-Induktion -> Thromboembolierisiko"
    ),
    (
        "Ginkgo biloba Extrakt 🍃",
        "Knoblauchextrakt (hochdosiert / Allium sativum) 🧄",
        "Moderat",
        "Phyto-Phyto: Additive Haemostasehemmung"
    ),
    (
        "Lakritze / Suessholzwurzel 🍬",
        "Torasemide",
        "Hoch",
        "11b-HSD2-Blockade + Diuretikum -> Schwere Hypokaliaemie"
    ),
    (
        "Lakritze / Suessholzwurzel 🍬",
        "Sennesblaetter / Faulbaum (Anthranoid-Laxanzien) 🍂",
        "Hoch",
        "Phyto-Phyto: Kumulativer Kaliumverlust"
    ),
    (
        "Milchprodukte & Calciumreiches Wasser 🥛",
        "Ciprofloxacin",
        "Hoch",
        "Chelatkomplexierung -> Resorptionsausfall"
    ),
    (
        "Milchprodukte & Calciumreiches Wasser 🥛",
        "Doxycycline",
        "Hoch",
        "Tetracyclin-Chelatierung -> Resorptionsblockade"
    ),
    (
        "Cannabidiol (CBD-Oel / Hanfextrakte) 🌿",
        "Clobazam",
        "Hoch",
        "CYP2C19/3A4-Hemmung -> Toxische Sedierung"
    ),
    (
        "Ramipril",
        "Spironolactone",
        "Hoch",
        "Duale RAAS-Hemmung -> Hyperkaliaemie"
    ),
    (
        "Ibuprofen",
        "Phenprocoumon",
        "Hoch",
        "NSAR + VKA -> Magenblutungsrisiko"
    ),
    # Neue klinische Haertungsfaelle:
    (
        "Morphine",
        "Diazepam",
        "Hoch",
        "Opioid + Benzodiazepin -> Letale Atemdepression (FDA Black Box)"
    ),
    (
        "Digoxin",
        "Verapamil",
        "Hoch",
        "P-gp-Inhibition -> Kardiale Digitalis-Toxizitaet"
    ),
    (
        "Eisenpraeparate / Eisentabletten (Fe2+/Fe3+) 🩸",
        "Levothyroxine sodium",
        "Hoch",
        "Eisen-Chelatierung -> Hypothyreose durch Resorptionsverlust"
    ),
    (
        "Sertraline",
        "Rivaroxaban",
        "Moderat",
        "SSRI + DOAK -> Gastrointestinales Blutungsrisiko (Thrombozytenentleerung)"
    )
]


def run_tests():
    print("=" * 80)
    print("🧪 Starte erweiterte pharmakologische Härtungstests (17 Fälle)...")
    print("=" * 80)

    passed = 0
    failed = 0

    for idx, (drug_a, drug_b, exp_sev, desc) in enumerate(TEST_CASES, start=1):
        res = find_interaction_test(drug_a, drug_b)

        codes_a = get_all_atc_codes(drug_a)
        codes_b = get_all_atc_codes(drug_b)

        c_a_str = codes_a[0] if codes_a else "NICHT GEFUNDEN"
        c_b_str = codes_b[0] if codes_b else "NICHT GEFUNDEN"

        if res and res.get("severity") == exp_sev:
            passed += 1
            status = "✅ PASS"
            print(f"[{idx:02d}] {status} | {drug_a} + {drug_b}")
            print(f"     -> Befund: {res['severity']} | Quelle: {res['source']}")
            print(f"     -> Fokus:  {desc}")
        else:
            failed += 1
            status = "❌ FAIL"
            act_sev = res.get("severity") if res else "Kein Treffer (None)"
            print(f"[{idx:02d}] {status} | {drug_a} + {drug_b}")
            print(f"     -> Erwartet: {exp_sev} | Erhalten: {act_sev}")
            print(f"     -> Codes:    {drug_a} -> {c_a_str} | {drug_b} -> {c_b_str}")
            print(f"     -> Fokus:    {desc}")
        print("-" * 80)

    print(f"Ergebnis: {passed}/{len(TEST_CASES)} Tests bestanden.")
    if failed == 0:
        print("🎯 Alle 17 klinischen Kernszenarien werden fehlerfrei erkannt!")
    else:
        print(f"⚠️ {failed} Szenario/Szenarien müssen im Regelwerk oder ATC-Mapping nachjustiert werden.")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()