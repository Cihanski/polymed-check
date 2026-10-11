import pytest
from cache_manager import (
    check_cache,
    check_phytomed_rules,
    check_class_rules,
    check_multidrug_synergies,
    check_priscus_pim,
    check_renal_risks,
    generate_intake_schedule,
    get_all_atc_codes,
    get_drug_pharmacology,
    save_to_cache
)
from drug_translator import translate_to_inn, resolve_drug_to_inns


# ============================================================================
# 1. BESTEHENDE KERN-TESTS
# ============================================================================

def test_cache_exact_lookup():
    """Prüft direkten Cache-Treffer."""
    save_to_cache("ciprofloxacin", "milchprodukte", {
        "severity": "Hoch",
        "system": "Resorption",
        "effect": "Chelatbildung hemmt Resorption.",
        "mechanism": "Kationen binden Chelatoren.",
        "source": "Test-Cache"
    })
    res = check_cache("ciprofloxacin", "milchprodukte")
    assert res is not None
    assert res["severity"] == "Hoch"


def test_phyto_chelation_rule():
    """Prüft Chelatbildung über Kationen/Phyto-Regelwerk."""
    res = check_phytomed_rules("Milchprodukte & Calciumreiches Wasser 🥛", "Ciprofloxacin")
    assert res is not None
    assert "Resorption" in res["system"] or "Chelat" in res["effect"] or res["severity"] == "Hoch"


def test_class_rules_opioid_benzo():
    """Prüft synergistische Atemdepression (Opioid + Benzo)."""
    res = check_class_rules("Morphin", "Diazepam")
    assert res is not None
    assert res["severity"] == "Hoch"
    assert "Atemdepression" in res["effect"]


def test_class_rules_digoxin_verapamil():
    """Prüft P-gp-Interaktion Digoxin + Verapamil."""
    res = check_class_rules("Digoxin", "Verapamil")
    assert res is not None
    assert res["severity"] == "Hoch"


def test_synergy_anticholinergic_burden():
    """Prüft Erkennung kumulativer anticholinerger Last."""
    drugs = ["Amitriptylin", "Oxybutynin"]
    syn = check_multidrug_synergies(drugs)
    types = [s["type"] for s in syn]
    assert "Anticholinerge Last" in types


def test_synergy_qt_prolongation():
    """Prüft kumulative QT-Verlängerung mit INN-Normalisierung."""
    raw_drugs = ["Ciprofloxacin", "Amiodaron"]
    # App-Workflow: Substanzen werden zuerst zu INN übersetzt
    drugs = [translate_to_inn(d) or d.lower() for d in raw_drugs]
    syn = check_multidrug_synergies(drugs)
    types = [s["type"] for s in syn]
    assert "Kardiale QT-Verlaengerung" in types


def test_synergy_cns_depression():
    """Prüft ZNS- & Atemdepression über mehrere Sedativa."""
    drugs = ["Morphin", "Diazepam"]
    syn = check_multidrug_synergies(drugs)
    types = [s["type"] for s in syn]
    assert "Kumulative ZNS-Depression" in types


def test_translator_brand_to_inn():
    """Prüft Handelsnamen-Auflösung auf INN."""
    assert translate_to_inn("Aspirin") == "acetylsalicylic acid"
    assert translate_to_inn("Xarelto") == "rivaroxaban"
    assert translate_to_inn("Pantozol") == "pantoprazole"


def test_translator_fixed_dose_combination():
    """Prüft Aufspaltung von Kombinationspräparaten."""
    inns = resolve_drug_to_inns("Co-Diovan")
    assert len(inns) >= 2
    assert "valsartan" in inns
    assert "hydrochlorothiazide" in inns


# ============================================================================
# 2. SONDERPOPULATIONEN & KLINISCHE LOGIKEN
# ============================================================================

def test_priscus_pim_detection():
    """Prüft Erkennung potenziell inadäquater Medikation im Alter (PIM)."""
    alerts = check_priscus_pim(["Diazepam", "Metformin"])
    assert len(alerts) == 1
    assert alerts[0]["drug"].lower() == "diazepam"
    assert "Hangover" in alerts[0]["risk"] or "Stuerze" in alerts[0]["risk"]
    assert "Lorazepam" in alerts[0]["alternative"]

    alerts_ami = check_priscus_pim(["Amitriptyline"])
    assert len(alerts_ami) == 1
    assert "Delir" in alerts_ami[0]["risk"] or "anticholinerg" in alerts_ami[0]["reason"].lower()

    alerts_safe = check_priscus_pim(["Ramipril", "Paracetamol"])
    assert len(alerts_safe) == 0


def test_renal_risk_severe_cutoff():
    """Prüft Dosisgrenzen und Kontraindikationen bei eGFR < 30 ml/min."""
    alerts = check_renal_risks(["Metformin"], egfr=25)
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "Hoch"
    assert "Laktatazidose" in alerts[0]["message"]
    assert alerts[0]["cutoff"] == 30

    alerts_spiro = check_renal_risks(["Spironolactone"], egfr=20)
    assert len(alerts_spiro) == 1
    assert alerts_spiro[0]["severity"] == "Hoch"
    assert "Hyperkaliaemie" in alerts_spiro[0]["message"]


def test_renal_risk_moderate_cutoff():
    """Prüft Warnhinweise bei moderater Niereninsuffizienz (eGFR 30-59 ml/min)."""
    alerts = check_renal_risks(["Metformin"], egfr=40)
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "Moderat"
    assert "1000 mg" in alerts[0]["message"]

    alerts_normal = check_renal_risks(["Metformin", "Spironolactone", "Allopurinol"], egfr=85)
    assert len(alerts_normal) == 0


def test_intake_schedule_chelator_separation():
    """Prüft Trennung von Chelatbildnern und Schilddrüsenhormonen."""
    drugs = [
        "L-Thyroxin Henning",
        "Eisenpraeparate / Eisentabletten (Fe2+/Fe3+) 🩸"
    ]
    schedule = generate_intake_schedule(drugs)

    morning_fasting = schedule.get("Morgens (nüchtern / 30 Min. vor dem Frühstück)", [])
    assert any("thyrox" in item["drug"].lower() for item in morning_fasting)

    lunch = schedule.get("Mittags (mit Mahlzeit / 2-3h Abstand zu Mineralstoffen)", [])
    assert any("eisen" in item["drug"].lower() for item in lunch)


def test_intake_schedule_statin_evening():
    """Prüft Zuordnung von Statinen zum Abend."""
    drugs = ["Simvastatin"]
    schedule = generate_intake_schedule(drugs)
    evening = schedule.get("Abends (zum Abendessen)", [])
    assert any("simvastatin" in item["drug"].lower() for item in evening)


def test_intake_schedule_diuretic_morning():
    """Prüft Zuordnung von Schleifendiuretika zum Morgen."""
    drugs = ["Torasemide"]
    schedule = generate_intake_schedule(drugs)
    breakfast = schedule.get("Morgens (zum Frühstück)", [])
    assert any("torasemid" in item["drug"].lower() for item in breakfast)

def test_synergy_serotonin_syndrome():
    """Prueft Erkennung des Serotonin-Syndroms bei SSRI + Opioid/Triptan."""
    raw_drugs = ["Sertralin", "Tramadol"]
    drugs = [translate_to_inn(d) or d.lower() for d in raw_drugs]
    syn = check_multidrug_synergies(drugs)
    types = [s["type"] for s in syn]
    assert "Serotonin-Syndrom" in types
    
    match = next(s for s in syn if s["type"] == "Serotonin-Syndrom")
    assert match["severity"] == "Hoch"


def test_synergy_doac_bleeding_risk():
    """Prueft DOAK-Spiegelerhoehung via P-gp/CYP3A4-Hemmung."""
    raw_drugs = ["Apixaban", "Clarithromycin"]
    drugs = [translate_to_inn(d) or d.lower() for d in raw_drugs]
    syn = check_multidrug_synergies(drugs)
    types = [s["type"] for s in syn]
    assert "DOAK-Interaktion" in types
    
    match = next(s for s in syn if s["type"] == "DOAK-Interaktion")
    assert match["severity"] == "Hoch"