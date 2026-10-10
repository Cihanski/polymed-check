"""
run_system_tests.py
Automatisierte Validierung der 3-Stufen-Prüfkaskade und Multi-Drug-Synergien.
"""

from cache_manager import (
    check_cache,
    check_class_rules,
    check_multidrug_synergies,
    get_atc_code
)

def run_tests():
    print("=" * 70)
    print("🧪 STARTE SYSTEM-VALIDIERUNG: MEDICHECK PRÜFKASKADE")
    print("=" * 70)

    # Test 1: Namens-Normalisierung & ATC-Erkennung
    print("\n[Test 1] ATC-Code-Erkennung und Priorisierung:")
    test_substances = [
        "Candesartan",
        "Naproxen",
        "Ramipril",
        "Clarithromycin",
        "Simvastatin"
    ]
    for sub in test_substances:
        code = get_atc_code(sub)
        status = f"✅ Gefunden ({code})" if code else "❌ FEHLT"
        print(f"  - {sub:<16} -> {status}")

    # Test 2: ATC-Klassenregel (NSAR + Sartan)
    print("\n[Test 2] ATC-Klassenregel: Naproxen + Candesartan")
    res_pair = check_class_rules("Naproxen", "Candesartan")
    if res_pair:
        print(f"  ✅ Treffer: {res_pair['effect']}")
        print(f"     Schweregrad: {res_pair['severity']} | Quelle: {res_pair['source']}")
    else:
        print("  ❌ FEHLER: Klassenregel hat nicht angeschlagen!")

    # Test 3: Multi-Drug-Synergie (Kumulative QT-Verlängerung)
    print("\n[Test 3] Multi-Drug-Detektor: QT-Zeit-Verlängerung (3 Substanzen)")
    qt_group = ["Ciprofloxacin", "Citalopram", "Amiodarone"]
    synergies = check_multidrug_synergies(qt_group)
    qt_found = any(s["type"] == "Kardiale QT-Verlängerung" for s in synergies)
    if qt_found:
        print(f"  ✅ Treffer: Kumulatives QT-Risiko für {len(qt_group)} Substanzen erkannt.")
    else:
        print("  ❌ FEHLER: QT-Synergie nicht erkannt!")

    # Test 4: Anticholinerge Last (ACB-Synergie)
    print("\n[Test 4] Multi-Drug-Detektor: Anticholinerge Last")
    acb_group = ["Amitriptyline", "Oxybutynin"]
    synergies_acb = check_multidrug_synergies(acb_group)
    acb_found = any(s["type"] == "Anticholinerge Last" for s in synergies_acb)
    if acb_found:
        print(f"  ✅ Treffer: Anticholinerge Last für {len(acb_group)} Substanzen erkannt.")
    else:
        print("  ❌ FEHLER: Anticholinerge Last nicht erkannt!")

    print("\n" + "=" * 70)
    print("🏁 SYSTEM-TEST ABGESCHLOSSEN")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()