import pytest
from drug_translator import translate_to_inn
from cache_manager import (
    fetch_exact_cache,
    check_phyto_and_cation_rules,
    check_class_level_rules,
    check_multidrug_synergies,
    check_priscus_pim,
    check_renal_risks,
    generate_intake_schedule
)


def test_cache_exact_lookup():
    """Prueft, ob ein direkt in SQLite hinterlegtes Interaktionspaar gefunden wird."""
    res = fetch_exact_cache("Ramipril", "Ibuprofen")
    if not res:
        res = fetch_exact_cache("ramipril", "ibuprofen")
    assert res is not None
    assert res["severity"] in ["Hoch", "Moderat"]


def test_phyto_chelation_rule():
    """Prueft Chelatbildung zwischen Ciprofloxacin und Kationen (Calcium/Milch)."""
    res = check_phyto_and_cation_rules("Ciprofloxacin", "Calcium")
    assert res is not None
    assert res["severity"] == "Hoch"
    assert "Chelat" in res["system"] or "Resorption" in res["system"]


def test_class_rules_opioid_benzo():
    """Prueft die Klassenregel fuer ZNS-/Atemdepression (Opioid + Benzodiazepin)."""
    res = check_class_level_rules("Tilidin", "Diazepam")
    assert res is not None
    assert res["severity"] == "Hoch"
    assert "Atemdepression" in res["effect"] or "ZNS" in res["system"]


def test_class_rules_digoxin_verapamil():
    """Prueft die pharmakokinetische P-gp-Interaktion zwischen Digoxin und Verapamil."""
    res = check_class_level_rules("Digoxin", "Verapamil")
    assert res is not None
    assert res["severity"] == "Hoch"
    assert "P-Glykoprotein" in res["mechanism"] or "Digoxin" in res["effect"]


def test_synergy_anticholinergic_burden():
    """Prueft additive anticholinerge Last bei mehreren anticholinergen Substanzen."""
    raw_drugs = ["Amitriptylin", "Oxybutynin"]
    drugs = [translate_to_inn(d) or d.lower() for d in raw_drugs]
    syn = check_multidrug_synergies(drugs)
    types = [s["type"] for s in syn]
    assert "Anticholinerge Last" in types


def test_synergy_qt_prolongation():
    """Prueft kumulative QT-Verlaengerung mit INN-Normalisierung."""
    raw_drugs = ["Ciprofloxacin", "Amiodaron"]
    drugs = [translate_to_inn(d) or d.lower() for d in raw_drugs]
    syn = check_multidrug_synergies(drugs)
    types = [s["type"] for s in syn]
    assert "Kardiale QT-Verlaengerung" in types


def test_synergy_cns_depression():
    """Prueft kumulative ZNS-/Atemdepression im Multidrug-Synergie-Modul."""
    raw_drugs = ["Morphin", "Lorazepam"]
    drugs = [translate_to_inn(d) or d.lower() for d in raw_drugs]
    syn = check_multidrug_synergies(drugs)
    types = [s["type"] for s in syn]
    assert "Kumulative ZNS-Depression" in types


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


def test_translator_brand_to_inn():
    """Prueft die korrekte Aufloesung von Handelsnamen in INN-Wirkstoffnamen (de/en tolerant)."""
    res = translate_to_inn("Pantozol")
    assert res in ["pantoprazol", "pantoprazole"]
    res_asp = translate_to_inn("Aspirin")
    assert res_asp in ["acetylsalicylsaeure", "aspirin", "acetylsalicylic acid"]


def test_translator_fixed_dose_combination():
    """Prueft das automatische Splitten oder Erkennen von Fixkombinationen."""
    components = translate_to_inn("Ramipril Plus")
    if isinstance(components, list):
        assert any("ramipril" in c.lower() for c in components)
    else:
        assert "ramipril" in components.lower()


def test_priscus_pim_detection():
    """Prueft die Basis-PIM-Erkennung fuer geriatrische Patienten."""
    alerts = check_priscus_pim(["Diazepam", "Pantoprazol"])
    assert len(alerts) >= 1
    assert alerts[0]["drug"].lower() == "diazepam"


def test_priscus_expanded_catalog():
    """Prueft die erweiterte PRISCUS 2.0 PIM-Erkennung: Indometacin, Oxybutynin und Metoclopramid."""
    drugs = ["Indometacin", "Oxybutynin", "Metoclopramid"]
    alerts = check_priscus_pim(drugs)
    assert len(alerts) == 3
    alert_drugs = [a["drug"].lower() for a in alerts]
    assert "indometacin" in alert_drugs
    assert "oxybutynin" in alert_drugs
    assert "metoclopramid" in alert_drugs

    mcp_alert = next(a for a in alerts if a["drug"].lower() == "metoclopramid")
    assert "Dyskinesien" in mcp_alert["risk"] or "Dopamin" in mcp_alert["reason"]


def test_renal_risk_severe_cutoff():
    """Prueft die Erkennung von Kontraindikationen bei schwerer Niereninsuffizienz (eGFR < 30 ml/min)."""
    alerts = check_renal_risks(["Metformin", "Spironolacton"], egfr_value=25)
    assert len(alerts) == 2
    for a in alerts:
        assert a["severity"] == "Hoch"


def test_renal_risk_moderate_cutoff():
    """Prueft Dosisreduktionswarnungen bei moderater Einschraenkung (eGFR 40 ml/min)."""
    alerts = check_renal_risks(["Metformin"], egfr_value=40)
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "Moderat"


def test_intake_schedule_chelator_separation():
    """Prueft die automatische zeitliche Entzerrung von Kationen/Chelatbildnern."""
    schedule = generate_intake_schedule(["L-Thyroxin", "Eisen"])
    assert "Morgens (Nuechtern)" in schedule
    assert "Mittags" in schedule
    assert any("L-Thyroxin" in s or "l-thyroxin" in s.lower() for s in schedule["Morgens (Nuechtern)"])
    assert any("Eisen" in s or "eisen" in s.lower() for s in schedule["Mittags"])


def test_intake_schedule_statin_evening():
    """Prueft die chronopharmakologische Zuordnung von Statinen auf den Abend."""
    schedule = generate_intake_schedule(["Simvastatin"])
    assert "Abends" in schedule


def test_intake_schedule_diuretic_morning():
    """Prueft die Verlegung von Diuretika auf den Morgen zur Vermeidung von Nykturie."""
    schedule = generate_intake_schedule(["Torasemid"])
    assert "Morgens (Zum Fruehstueck)" in schedule

from bmp_parser import parse_medication_text, parse_bmp_xml


def test_bmp_xml_parser():
    """Prueft das Extrahieren von Wirkstoffen aus BMP-XML-Strukturen."""
    sample_xml = """<MP v="024" U="uuid">
        <S>
            <M p="12345678" w="Ramipril" d="5mg"/>
            <M p="87654321" a="Pantozol" d="40mg"/>
        </S>
    </MP>"""
    results = parse_bmp_xml(sample_xml)
    assert "Ramipril" in results
    assert "Pantozol" in results


def test_medication_freetext_parser():
    """Prueft die Bereinigung klinischer Freitextzeilen inklusive Dosierungen."""
    clinical_text = """
    1. Metformin 1000 mg 1-0-1-0
    2. Simvastatin 20mg 0-0-1-0
    3. Torasemid 10 mg morgens
    """
    parsed = parse_medication_text(clinical_text)
    assert any("metformin" in p.lower() for p in parsed)
    assert any("simvastatin" in p.lower() for p in parsed)
    assert any("torasemid" in p.lower() for p in parsed)

from cache_manager import generate_lab_monitoring_checklist


def test_lab_monitoring_checklist_generation():
    """Prueft die Erstellung von Labormonitoring-Empfehlungen fuer RAAS und QTc-Risiken."""
    drugs = ["Ramipril", "Ciprofloxacin", "Amiodaron"]
    checklist = generate_lab_monitoring_checklist(drugs, egfr_value=45)
    
    params = [c["parameter"] for c in checklist]
    assert any("Serum-Kalium" in p for p in params)
    assert any("EKG" in p for p in params)
    assert any("Schilddruese" in p for p in params)

    qt_item = next(c for c in checklist if "EKG" in c["parameter"])
    assert qt_item["urgency"] == "Hoch"