import os
os.environ["FONTTOOLS_DONT_USE_CYTHON"] = "1"

import streamlit as st
import streamlit.components.v1 as components
import requests
import re
from itertools import combinations
from datetime import datetime

# Sicherer Import fuer FPDF
FPDF_AVAILABLE = False
try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except (ImportError, Exception):
    FPDF_AVAILABLE = False

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
    save_to_cache, 
    get_total_cached_count, 
    get_total_class_rules_count, 
    get_all_cached_drugs
)
from drug_translator import translate_to_inn, resolve_drug_to_inns, get_autocomplete_catalog

st.set_page_config(
    page_title="MediCheck – Weltweiter Medikations- & Interaktions-Check",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    .metric-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        color: #1e293b !important;
    }
    .metric-title {
        margin: 0 0 8px 0; 
        color: #1e293b !important; 
        font-size: 0.95rem; 
        font-weight: 600;
    }
    .metric-desc {
        margin: 8px 0 0 0; 
        color: #64748b !important; 
        font-size: 0.85rem;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-right: 8px;
    }
    .badge-high {
        background-color: #fee2e2;
        color: #991b1b !important;
        border: 1px solid #fecaca;
    }
    .badge-medium {
        background-color: #fef3c7;
        color: #92400e !important;
        border: 1px solid #fde68a;
    }
    .badge-organ {
        background-color: #e0f2fe;
        color: #075985 !important;
        border: 1px solid #bae6fd;
    }
    .badge-db {
        background-color: #f3e8ff;
        color: #6b21a8 !important;
        border: 1px solid #e9d5ff;
    }
    .badge-class {
        background-color: #e0e7ff;
        color: #3730a3 !important;
        border: 1px solid #c7d2fe;
    }
    .badge-phyto {
        background-color: #dcfce7;
        color: #166534 !important;
        border: 1px solid #bbf7d0;
    }
    .badge-fda {
        background-color: #ecfdf5;
        color: #065f46 !important;
        border: 1px solid #a7f3d0;
    }
    .interaction-card {
        background-color: #ffffff;
        border-left: 5px solid #cbd5e1;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        border-top: 1px solid #f1f5f9;
        border-right: 1px solid #f1f5f9;
        border-bottom: 1px solid #f1f5f9;
        color: #1e293b !important;
    }
    .interaction-card.high {
        border-left-color: #ef4444;
    }
    .interaction-card.medium {
        border-left-color: #f59e0b;
    }
    .advice-box {
        background-color: #f0fdf4;
        border-left: 4px solid #22c55e;
        border-radius: 4px;
        padding: 8px 12px;
        margin-top: 8px;
        font-size: 0.90rem;
        color: #166534 !important;
    }
    .combo-box {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 16px;
        font-size: 0.90rem;
        color: #334155 !important;
    }
    .profile-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        color: #1e293b !important;
    }
    .priscus-card {
        background-color: #fefce8;
        border: 1px solid #fef08a;
        border-left: 6px solid #ca8a04;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 16px;
        color: #1e293b !important;
    }
    .renal-card {
        background-color: #fff7ed;
        border: 1px solid #fed7aa;
        border-left: 6px solid #ea580c;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 16px;
        color: #1e293b !important;
    }
    .schedule-card {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-left: 6px solid #2563eb;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 16px;
        color: #0f172a !important;
    }
    .schedule-card strong {
        color: #0f172a !important;
    }
    .schedule-card li {
        color: #334155 !important;
    }
    .monitoring-card {
        background-color: #f0f9ff;
        border: 1px solid #bae6fd;
        border-left: 6px solid #0284c7;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 20px;
        color: #1e293b !important;
    }
    .synergy-card {
        background-color: #fff1f2;
        border: 1px solid #fecdd3;
        border-left: 6px solid #e11d48;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 16px;
        color: #1e293b !important;
    }
    .disclaimer-banner {
        background-color: #eff6ff;
        border-left: 4px solid #3b82f6;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 20px;
        color: #1e3a8a !important;
        font-size: 0.9rem;
    }
    .disclaimer-box {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 16px;
        font-size: 0.88rem;
        color: #475569 !important;
        margin-top: 30px;
    }

    /* ----------------- NATIVES PRINT-CSS (DIN A4 OPTIMIERT) ----------------- */
    @media print {
        header, footer, [data-testid="stSidebar"], [data-testid="stHeader"], [data-testid="stToolbar"] {
            display: none !important;
        }
        .stButton, .stDownloadButton, [data-testid="stExpander"] {
            display: none !important;
        }
        [data-testid="stMultiSelect"] {
            display: none !important;
        }
        body, .stApp {
            background-color: #ffffff !important;
            color: #000000 !important;
            padding: 0 !important;
            margin: 0 !important;
        }
        .main .block-container {
            max-width: 100% !important;
            padding: 10mm 15mm !important;
        }
        .metric-card, .interaction-card, .schedule-card, .monitoring-card, .synergy-card, .priscus-card, .renal-card {
            box-shadow: none !important;
            border: 1px solid #94a3b8 !important;
            break-inside: avoid !important;
            page-break-inside: avoid !important;
            -webkit-print-color-adjust: exact !important;
            print-color-adjust: exact !important;
        }
        .disclaimer-banner {
            border: 1px solid #94a3b8 !important;
        }
    }
</style>
""", unsafe_allow_html=True)


def clean_text_for_pdf(text):
    if not text:
        return ""
    replacements = {
        "ä": "ae", "ö": "oe", "ü": "ue",
        "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
        "ß": "ss",
        "–": "-", "—": "-",
        "’": "'", "‘": "'",
        "“": '"', "”": '"',
        "•": "-", "…": "..."
    }
    cleaned = text
    for original, repl in replacements.items():
        cleaned = cleaned.replace(original, repl)

    cleaned_chars = []
    for char in cleaned:
        code = ord(char)
        if 32 <= code <= 126 or 160 <= code <= 255 or code == 10:
            cleaned_chars.append(char)
        else:
            cleaned_chars.append(" ")
            
    res = "".join(cleaned_chars)
    return re.sub(r' +', ' ', res).strip()


def get_practical_advice(effect_text, mechanism_text, system_name):
    comb_text = f"{effect_text} {mechanism_text} {system_name}".lower()
    
    if "chelat" in comb_text or "calcium" in comb_text or "resorption" in comb_text or "eisen" in comb_text or "magnesium" in comb_text:
        return "⏰ Einnahme-Tipp: Mindestens 2 bis 3 Stunden zeitlichen Abstand zwischen den Mahlzeiten/Mineralstoffen und der Medikamenteneinnahme einhalten."
    if "cyp3a4" in comb_text and ("grapefruit" in comb_text or "hypericum" in comb_text or "johanniskraut" in comb_text):
        return "⚠️ Wichtiger Hinweis: Grapefruit/Johanniskraut waehrend der gesamten Dauer der medikamentoesen Therapie vollstaendig meiden."
    if "blutung" in comb_text or "haemostase" in comb_text:
        return "🩸 Vorsichtsmassnahme: Auf vermehrte Blutungszeichen (Zahnfleischbluten, Haematome, dunklen Stuhl) achten und vor operativen Eingriffen aerztlich absprechen."
    if "hypokaliaemie" in comb_text or "hyperkaliaemie" in comb_text or "kalium" in comb_text or "diureti" in comb_text:
        return "🧪 Monitoring: Regelmaessige elektrolytische Laborkontrolle (insbesondere Serum-Kalium und Kreatinin) durch den behandelnden Arzt empfohlen."
    if "qt" in comb_text or "torsade" in comb_text:
        return "🫀 Kardiologischer Hinweis: Ein Kontroll-EKG zur Bestimmung der QTc-Zeit sollte aerztlich evaluiert werden."
    
    return None


def get_aggregated_monitoring(active_drugs, detected_interactions, synergies):
    params = set()
    all_codes = []
    for d in active_drugs:
        all_codes.extend(get_all_atc_codes(d))

    combined_text = " ".join([f"{item.get('effect', '')} {item.get('mechanism', '')} {item.get('system', '')}" for item in detected_interactions]).lower()
    for syn in synergies:
        combined_text += f" {syn.get('effect', '')} {syn.get('mechanism', '')}"

    if (any(c.startswith("C09") or c.startswith("C03") or c.startswith("M01A") for c in all_codes) or 
        "kalium" in combined_text or "niere" in combined_text or "whammy" in combined_text or "hyperkaliaemie" in combined_text or "hypokaliaemie" in combined_text):
        params.add("Nierenwerte & Elektrolyte: Serum-Kalium, Serum-Natrium, Kreatinin und eGFR")

    if any(syn.get("type") == "Kardiale QT-Verlaengerung" for syn in synergies) or "qt" in combined_text or "torsade" in combined_text or any(c.startswith("C01B") for c in all_codes):
        params.add("Kardiologische Diagnostik: 12-Kanal-Ruhe-EKG (Messung der frequenzkorrigierten QTc-Zeit)")

    if any(c.startswith("B01") for c in all_codes) or "blutung" in combined_text or "haemostase" in combined_text:
        params.add("Haemostase & Haematologie: Kleines Blutbild (Hb, Thrombozytenzahl), ggf. Gerinnungsstatus (INR/Quick)")

    if "statin" in combined_text or "rhabdomyolyse" in combined_text or any(c.startswith("C10AA") for c in all_codes) or "cyp3a4" in combined_text:
        params.add("Hepatische Parameter & Muskelenzyme: ALAT (GPT), ASAT (GOT), Creatin-Kinase (CK bei Myalgien)")

    if any(c.startswith("H03AA") for c in all_codes) and ("chelat" in combined_text or "resorption" in combined_text or any(c in ["PHYTO_IRON", "PHYTO_CALCIUM"] for c in all_codes)):
        params.add("Endokrines Monitoring: TSH-Basalwert und freies T4 (fT4) zur Resorptionskontrolle")

    if any(c.startswith("C01AA") for c in all_codes) and ("digitalis" in combined_text or "digoxin" in combined_text or "p-gp" in combined_text):
        params.add("Therapeutisches Drug Monitoring (TDM): Serum-Digoxin-Talspiegel (Serumkonzentration)")

    return sorted(list(params))


@st.cache_data(ttl=3600)
def load_cached_catalog():
    base_catalog = set(get_autocomplete_catalog())
    cached_drugs = set(get_all_cached_drugs())
    return sorted(list(base_catalog.union(cached_drugs)))


def fetch_fda_interaction(drug_a, drug_b):
    inn_a = translate_to_inn(drug_a)
    inn_b = translate_to_inn(drug_b)
    
    if not inn_a or not inn_b or inn_a == inn_b:
        return None

    url = "https://api.fda.gov/drug/label.json"
    for primary, secondary in [(inn_a, inn_b), (inn_b, inn_a)]:
        params = {
            "search": f'openfda.generic_name:"{primary}"',
            "limit": 1
        }
        try:
            resp = requests.get(url, params=params, timeout=4)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    label = results[0]
                    text_blocks = label.get("drug_interactions", []) + label.get("warnings", [])
                    full_text = " ".join(text_blocks)
                    
                    if secondary.lower() in full_text.lower():
                        sentences = full_text.split(".")
                        matched = [s.strip() for s in sentences if secondary.lower() in s.lower()]
                        detail_text = ". ".join(matched[:2]) + "." if matched else "Wechselwirkung in FDA-Fachinformation dokumentiert."
                        
                        return {
                            "severity": "Moderat",
                            "system": "FDA-Dokumentation",
                            "effect": f"Wechselwirkung zwischen {drug_a} und {drug_b} in Fachinformation vermerkt.",
                            "mechanism": detail_text[:400],
                            "source": "openFDA Live-API"
                        }
        except Exception:
            pass

    return None


def find_interaction_smart(drug_a, drug_b):
    cached = check_cache(drug_a, drug_b)
    if cached:
        return cached

    phyto_match = check_phytomed_rules(drug_a, drug_b)
    if phyto_match:
        return phyto_match

    class_match = check_class_rules(drug_a, drug_b)
    if class_match:
        return class_match

    fda_result = fetch_fda_interaction(drug_a, drug_b)
    if fda_result:
        save_to_cache(drug_a, drug_b, fda_result)
        return fda_result

    return None


def generate_text_report(selected_drugs, active_substances, drug_settings, interactions, is_triple, synergies, monitoring_params, priscus_alerts, renal_alerts, schedule):
    lines = []
    lines.append("=" * 70)
    lines.append("MediCheck - Medikations- & Gespraechsleitfaden")
    lines.append(f"Erstellt am: {datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')}")
    lines.append("=" * 70 + "\n")
    
    lines.append("1. Erfasste Praeparate & aufgeschluesselte Wirkstoffe:")
    for d in selected_drugs:
        inns = resolve_drug_to_inns(d)
        inn_info = f" [Fixkombination: {' + '.join([i.capitalize() for i in inns])}]" if len(inns) > 1 else ""
        setting_info = f" ({drug_settings[d]})" if d in drug_settings else ""
        lines.append(f"- {d}{inn_info}{setting_info}")
    lines.append("")

    if schedule:
        lines.append("2. Empfohlener Einnahme-Tageszeitplan:")
        for time_slot, items in schedule.items():
            lines.append(f"[{time_slot}]")
            for item in items:
                lines.append(f"  * {item['drug'].capitalize()} - {item['note']}")
        lines.append("")

    if is_triple or synergies or priscus_alerts or renal_alerts:
        lines.append("WARNUNG: Klinische Risiken & Sonderpopulationen:")
        if is_triple:
            lines.append("- Triple-Whammy: RAAS-Hemmer + Diuretikum + NSAR (systemisch) -> Akute Nierenbelastung")
        for syn in synergies:
            lines.append(f"- {syn['title']}: {syn['effect']}")
        for p in priscus_alerts:
            lines.append(f"- Priscus 2.0 PIM ({p['drug'].capitalize()}): {p['risk']} Alternative: {p['alternative']}")
        for r in renal_alerts:
            lines.append(f"- Nierenfunktion ({r['drug'].capitalize()}): {r['message']}")
        lines.append("")

    lines.append(f"3. Gefundene Einzelwechselwirkungen ({len(interactions)} Befunde):")
    if not interactions:
        lines.append("Keine kritischen Konflikte dokumentiert.")
    else:
        for idx, item in enumerate(interactions, start=1):
            d1, d2 = item["pair"]
            lines.append(f"{idx}. {d1.capitalize()} + {d2.capitalize()} [{item['severity']} | {item['system']}]")
            lines.append(f"   Effekt: {item['effect']}")
            lines.append(f"   Details: {item['mechanism']}")
    lines.append("")

    if monitoring_params:
        lines.append("4. Empfohlene Laborkontrollen & Diagnostik:")
        for param in monitoring_params:
            lines.append(f"* {param}")
        lines.append("")

    lines.append("5. Leitfragen fuer das Arztgespraech:")
    lines.append("- Gibt es schonendere Alternativen?")
    lines.append("- Sollten die empfohlenen Laborparameter kontrolliert werden?")
    lines.append("- Passen die Einnahmezeiten zum Tagesablauf?")
    lines.append("\nHaftungsausschluss: Dient ausschliesslich zur Gespraechsvorbereitung. Keine Therapieempfehlung.")
    return "\n".join(lines).encode("utf-8")


def create_pdf_report(selected_drugs, active_substances, drug_settings, interactions, is_triple, synergies, monitoring_params, priscus_alerts, renal_alerts, schedule):
    if not FPDF_AVAILABLE:
        return generate_text_report(selected_drugs, active_substances, drug_settings, interactions, is_triple, synergies, monitoring_params, priscus_alerts, renal_alerts, schedule)

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    width = pdf.epw
    
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(width, 10, clean_text_for_pdf("MediCheck - Medikations- & Gespraechsleitfaden"), new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(width, 6, clean_text_for_pdf(f"Erstellt am: {datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')} | Zur Vorbereitung auf das Arztgespraech"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(width, 8, clean_text_for_pdf("1. Erfasste Praeparate:"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    for d in selected_drugs:
        inns = resolve_drug_to_inns(d)
        inn_info = f" [Fixkombination: {' + '.join([i.capitalize() for i in inns])}]" if len(inns) > 1 else ""
        setting_info = f" ({drug_settings[d]})" if d in drug_settings else ""
        pdf.cell(width, 6, clean_text_for_pdf(f"- {d}{inn_info}{setting_info}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    if schedule:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(37, 99, 235)
        pdf.cell(width, 8, clean_text_for_pdf("2. Empfohlener Einnahme-Tageszeitplan:"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=9)
        pdf.set_text_color(20, 20, 20)
        for time_slot, items in schedule.items():
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(width, 6, clean_text_for_pdf(f"[{time_slot}]"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", size=9)
            for item in items:
                pdf.multi_cell(width, 5, clean_text_for_pdf(f"* {item['drug'].capitalize()} - {item['note']}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
        pdf.ln(3)
    
    if is_triple or synergies or priscus_alerts or renal_alerts:
        pdf.set_fill_color(254, 226, 226)
        pdf.set_text_color(153, 27, 27)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(width, 8, clean_text_for_pdf(" WARNUNG: Klinische Risiken & Sonderpopulationen:"), fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=9)
        
        if is_triple:
            pdf.multi_cell(width, 5, clean_text_for_pdf("- Triple-Whammy: Renale Dekompensation durch RAAS-Hemmer + Diuretikum + NSAR (systemisch)."), fill=True, new_x="LMARGIN", new_y="NEXT")
        
        for syn in synergies:
            pdf.multi_cell(width, 5, clean_text_for_pdf(f"- {syn['title']}: {syn['effect']}"), fill=True, new_x="LMARGIN", new_y="NEXT")
            
        for p in priscus_alerts:
            pdf.multi_cell(width, 5, clean_text_for_pdf(f"- Priscus 2.0 PIM ({p['drug'].capitalize()}): {p['risk']} Alternative: {p['alternative']}"), fill=True, new_x="LMARGIN", new_y="NEXT")

        for r in renal_alerts:
            pdf.multi_cell(width, 5, clean_text_for_pdf(f"- Nierenfunktion ({r['drug'].capitalize()}): {r['message']}"), fill=True, new_x="LMARGIN", new_y="NEXT")
        
        pdf.ln(4)
        pdf.set_text_color(20, 20, 20)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(width, 8, clean_text_for_pdf("3. Einzelwechselwirkungen ({len(interactions)} Befunde):"), new_x="LMARGIN", new_y="NEXT")
    
    if len(interactions) == 0:
        pdf.set_font("Helvetica", size=10)
        pdf.cell(width, 6, clean_text_for_pdf("Keine dokumentierten Konflikte gefunden."), new_x="LMARGIN", new_y="NEXT")
    else:
        for idx, item in enumerate(interactions, start=1):
            d1, d2 = item["pair"]
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(width, 6, clean_text_for_pdf(f"{idx}. {d1.capitalize()} + {d2.capitalize()} [{item['severity']} | {item['system']}]"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", size=9)
            pdf.multi_cell(width, 5, clean_text_for_pdf(f"Effekt: {item['effect']}"), new_x="LMARGIN", new_y="NEXT")
            pdf.multi_cell(width, 5, clean_text_for_pdf(f"Details: {item['mechanism']}"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            
    if monitoring_params:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(2, 132, 199)
        pdf.cell(width, 8, clean_text_for_pdf("4. Empfohlene Laborkontrollen & Diagnostik:"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=9)
        pdf.set_text_color(20, 20, 20)
        for param in monitoring_params:
            pdf.multi_cell(width, 5, clean_text_for_pdf(f"* {param}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(width, 8, clean_text_for_pdf("5. Leitfragen fuer das Arztgespraech:"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    fragen_text = (
        "- 'Gibt es fuer die verordneten Praeparate schonendere Alternativen?'\n"
        "- 'Sollten die empfohlenen Laborparameter kontrolliert werden?'\n"
        "- 'Passt der Einnahmezeitplan optimal zu meinen Lebensgewohnheiten?'"
    )
    pdf.multi_cell(width, 5, clean_text_for_pdf(fragen_text), new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(width, 4, clean_text_for_pdf("Haftungsausschluss: Dient ausschliesslich zur Gespraechsvorbereitung. Keine Therapieempfehlung."), new_x="LMARGIN", new_y="NEXT")
    
    return bytes(pdf.output())


total_db = get_total_cached_count()
total_rules = get_total_class_rules_count()
all_available_options = load_cached_catalog()

st.title("💊 MediCheck – Globaler Medikations- & Interaktions-Check")

st.markdown("""
<div class="disclaimer-banner">
    ℹ️ <strong>Wichtiger Hinweis:</strong> Dieses Informationsportal dient ausschließlich als Orientierungs- und Vorbereitungshilfe für das persönliche Gespräch mit Ihrem Arzt oder Apotheker. Es stellt keine medizinische Diagnose oder Therapieempfehlung dar. Verändern oder beenden Sie die Einnahme verordneter Arzneimittel keinesfalls eigenmächtig.
</div>
""", unsafe_allow_html=True)

st.caption(f"Arzneistoffkatalog: **{len(all_available_options):,} Substanzen & Nahrungsmittel**. Regelwerk: **{total_rules} aktive Klassen- & Phyto-Regeln** + **{total_db} Einzelwechselwirkungen**.")

# ----------------- Patientenprofil -----------------
with st.expander("👤 Patientenprofil & Sonderpopulationen (Optional: Alter & Nierenfunktion)", expanded=False):
    col_pat1, col_pat2 = st.columns(2)
    with col_pat1:
        patient_age = st.number_input("Patientenalter (Jahre):", min_value=1, max_value=120, value=68, step=1)
        is_elderly = patient_age >= 65
        if is_elderly:
            st.caption("👴 Altersgruppe $\\ge 65$ Jahre: Prüfung gegen **Priscus 2.0 (PIM)** aktiv.")
    with col_pat2:
        egfr_value = st.slider("Geschätzte Nierenfunktion (eGFR in ml/min/1.73 m²):", min_value=10, max_value=120, value=90, step=5)
        if egfr_value < 30:
            st.caption("🔴 **Schwere Niereninsuffizienz** (Stadium G4/G5)")
        elif egfr_value < 60:
            st.caption("🟡 **Moderate Niereninsuffizienz** (Stadium G3)")
        else:
            st.caption("🟢 **Normale bis leicht eingeschränkte Nierenfunktion** (Stadium G1/G2)")

default_selection = [
    "Milchprodukte & Calciumreiches Wasser 🥛",
    "Ciprofloxacin"
]
valid_defaults = [d for d in default_selection if d in all_available_options]

selected_drugs = st.multiselect(
    label="Wählen oder suchen Sie Wirkstoffe, Phytopharmaka oder Lebensmittel:",
    options=all_available_options,
    default=valid_defaults,
    placeholder="Buchstaben eingeben (z. B. 'Diazepam', 'Metformin', 'Spironolactone', 'Co-Diovan')...",
    help="Erkennt Einzelwirkstoffe, Markennamen und spaltet Fixkombinationen automatisch auf."
)

# ----------------- Aufspaltung von Kombinationspraeparaten -----------------
active_substances = []
combo_details = {}

for drug in selected_drugs:
    resolved = resolve_drug_to_inns(drug)
    if len(resolved) > 1:
        combo_details[drug] = resolved
    for r in resolved:
        if r not in active_substances:
            active_substances.append(r)

if combo_details:
    combo_info_html = "".join([
        f"<li><strong>{d}:</strong> Aufgespalten in <em>{' + '.join([c.capitalize() for c in comps])}</em></li>"
        for d, comps in combo_details.items()
    ])
    st.markdown(f"""
    <div class="combo-box">
        🧩 <strong>Fixkombination(en) erkannt:</strong>
        <ul style="margin: 4px 0 0 0; padding-left: 20px;">
            {combo_info_html}
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ----------------- Differenzierung: Darreichung & Dosis -----------------
drug_settings = {}
has_configurable_drugs = any(
    any(k in d.lower() for k in ["diclofenac", "ibuprofen", "acetylsalicyl", "aspirin", "hydrocortison"])
    for d in active_substances
)

if has_configurable_drugs:
    with st.expander("⚙️ Klinische Präzisierung: Darreichungsform & Dosierung", expanded=True):
        st.caption("Einige Präparate haben je nach Darreichung (z. B. Schmerzgel vs. Tablette) oder Dosis drastisch unterschiedliche Risikoprofile.")
        cols = st.columns(min(len(active_substances), 3))
        col_idx = 0
        for d in active_substances:
            d_low = d.lower()
            if "diclofenac" in d_low or "ibuprofen" in d_low:
                with cols[col_idx % len(cols)]:
                    mode = st.radio(
                        f"**{d.capitalize()}**:",
                        options=["Oral (Tablette / systemisch)", "Topisch (Gel / Salbe / lokal)"],
                        index=0,
                        key=f"mode_{d}"
                    )
                    drug_settings[d] = mode
                    col_idx += 1
            elif "acetylsalicyl" in d_low or "aspirin" in d_low:
                with cols[col_idx % len(cols)]:
                    mode = st.radio(
                        f"**{d.capitalize()}**:",
                        options=["Niedrigdosis (100 mg – Thrombozytenhemmung)", "Schmerzdosis (≥ 500 mg – NSAR-Wirkung)"],
                        index=0,
                        key=f"mode_{d}"
                    )
                    drug_settings[d] = mode
                    col_idx += 1
            elif "hydrocortison" in d_low or "prednisolon" in d_low:
                with cols[col_idx % len(cols)]:
                    mode = st.radio(
                        f"**{d.capitalize()}**:",
                        options=["Oral (Tablette / systemisch)", "Topisch (Creme / Spray / lokal)"],
                        index=0,
                        key=f"mode_{d}"
                    )
                    drug_settings[d] = mode
                    col_idx += 1

# ----------------- Wechselwirkungsanalyse -----------------
detected_interactions = []
if len(active_substances) >= 2:
    with st.spinner("Analysiere Wechselwirkungen..."):
        for drug_a, drug_b in combinations(active_substances, 2):
            result = find_interaction_smart(drug_a, drug_b)
            if result:
                item_copy = dict(result)
                setting_a = drug_settings.get(drug_a, "")
                setting_b = drug_settings.get(drug_b, "")
                
                if "Topisch" in setting_a or "Topisch" in setting_b:
                    if item_copy["severity"] == "Hoch" and any(sys_kw in item_copy.get("system", "").lower() for sys_kw in ["niere", "magen", "kreislauf"]):
                        item_copy["severity"] = "Moderat"
                        item_copy["effect"] = f"[Lokale Anwendung gewählt] {item_copy['effect']} Durch die topische Anwendung ist die systemische Resorption minimal (~6%), was das Organrisiko klinisch senkt."
                
                detected_interactions.append({
                    "pair": (drug_a, drug_b),
                    **item_copy
                })

multidrug_synergies = check_multidrug_synergies(active_substances) if len(active_substances) >= 2 else []

priscus_alerts = check_priscus_pim(active_substances) if is_elderly else []
renal_alerts = check_renal_risks(active_substances, egfr_value)
intake_schedule = generate_intake_schedule(active_substances) if len(active_substances) > 0 else {}

normalized_drugs = [translate_to_inn(d) for d in active_substances]
has_raas = any(d in normalized_drugs for d in ["ramipril", "candesartan", "enalapril", "valsartan", "lisinopril"])
has_diuretic = any(d in normalized_drugs for d in ["hydrochlorothiazide", "torsemide", "furosemide", "spironolactone"])

has_systemic_nsar = False
for d in active_substances:
    inn = translate_to_inn(d)
    if inn in ["ibuprofen", "diclofenac", "naproxen", "etoricoxib"]:
        setting = drug_settings.get(d, "Oral")
        if "Topisch" not in setting:
            has_systemic_nsar = True

is_triple_whammy = has_raas and has_diuretic and has_systemic_nsar

has_high = (
    any(item["severity"] == "Hoch" for item in detected_interactions) or 
    is_triple_whammy or 
    any(s["severity"] == "Hoch" for s in multidrug_synergies) or
    any(r["severity"] == "Hoch" for r in renal_alerts)
)
has_medium = (
    any(item["severity"] == "Moderat" for item in detected_interactions) or 
    len(multidrug_synergies) > 0 or
    len(priscus_alerts) > 0 or
    len(renal_alerts) > 0
)

col1, col2, col3 = st.columns([1.3, 1, 1])

with col1:
    if len(active_substances) < 2 and not priscus_alerts and not renal_alerts:
        status_color = "#64748b"
        status_text = "Mindestens 2 Einträge wählen"
        status_desc = "Wählen Sie Substanzen aus, um die Analyse zu starten."
    elif has_high:
        status_color = "#dc2626"
        status_text = "🔴 Hohe Relevanz fürs Arztgespräch"
        status_desc = "Kritische Konflikte oder Kontraindikationen erkannt!"
    elif has_medium:
        status_color = "#d97706"
        status_text = "🟡 Monitoring & Anpassung empfohlen"
        status_desc = "Relevante Wechselwirkungen, PIM oder Nierenrisiken gefunden."
    else:
        status_color = "#16a34a"
        status_text = "🟢 Keine dokumentierten Konflikte"
        status_desc = "In den hinterlegten Datenbanken ist kein bekannter Konflikt verzeichnet."

    st.markdown(f"""
    <div class="metric-card" style="border-top: 4px solid {status_color};">
        <div class="metric-title">Gesamt-Risiko-Status</div>
        <h3 style="margin:0; color: {status_color};">{status_text}</h3>
        <div class="metric-desc">{status_desc}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Aktive Wirkstoffe</div>
        <h2 style="margin:0; color: #0284c7;">{len(active_substances)}</h2>
        <div class="metric-desc">Inkl. aufgespaltener Kombinationen</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    total_findings = len(detected_interactions) + len(multidrug_synergies) + len(priscus_alerts) + len(renal_alerts) + (1 if is_triple_whammy else 0)
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Erkannte Befunde</div>
        <h2 style="margin:0; color: {'#dc2626' if total_findings > 0 else '#16a34a'};">
            {total_findings}
        </h2>
        <div class="metric-desc">Konflikte, PIM, Nierenrisiken & Synergien</div>
    </div>
    """, unsafe_allow_html=True)

if is_triple_whammy:
    st.error("⚠️ **Akutes Triple-Whammy-Risiko:** Blutdrucksenker + Entwässerungsmittel + orales NSAR drosseln die glomeruläre Nierenfunktion akut. Sprechen Sie dies zeitnah beim Arzt an!")

# Priscus 2.0 Warnungen
for p in priscus_alerts:
    st.markdown(f"""
    <div class="priscus-card">
        <h4 style="margin: 0 0 6px 0; color: #854d0e;">👴 Priscus 2.0 Warnung: Potenziell inadäquate Medikation im Alter ({p['drug'].capitalize()})</h4>
        <p style="margin: 4px 0; font-size: 0.92rem; color: #1e293b;"><strong>Risiko:</strong> {p['risk']}</p>
        <p style="margin: 4px 0; font-size: 0.88rem; color: #475569;"><strong>Hintergrund:</strong> {p['reason']}</p>
        <p style="margin: 4px 0 0 0; font-size: 0.90rem; color: #15803d;"><strong>Mögliche Alternative laut Leitlinie:</strong> {p['alternative']}</p>
    </div>
    """, unsafe_allow_html=True)

# Nierenfunktions-Warnungen
for r in renal_alerts:
    st.markdown(f"""
    <div class="renal-card">
        <h4 style="margin: 0 0 6px 0; color: #c2410c;">🫘 Nierenfunktion & Dosisanpassung: {r['drug'].capitalize()} (eGFR: {egfr_value} ml/min)</h4>
        <p style="margin: 4px 0; font-size: 0.92rem; color: #1e293b;"><strong>Klinischer Hinweis:</strong> {r['message']}</p>
        <p style="margin: 4px 0 0 0; font-size: 0.86rem; color: #7c2d12;">Schwellenwert für Dosisanpassung/Kontraindikation: &lt; {r['cutoff']} ml/min.</p>
    </div>
    """, unsafe_allow_html=True)

for syn in multidrug_synergies:
    st.markdown(f"""
    <div class="synergy-card">
        <h4 style="margin: 0 0 6px 0; color: #9f1239;">⚡ {syn['title']}</h4>
        <p style="margin: 4px 0; font-size: 0.95rem; color: #1e293b;"><strong>Beteiligte Medikamente:</strong> {', '.join([d.capitalize() for d in syn['drugs']])}</p>
        <p style="margin: 4px 0; font-size: 0.92rem; color: #334155;"><strong>Klinischer Effekt:</strong> {syn['effect']}</p>
        <p style="margin: 4px 0 0 0; font-size: 0.88rem; color: #64748b;"><strong>Mechanismus:</strong> {syn['mechanism']}</p>
    </div>
    """, unsafe_allow_html=True)

# ----------------- Einnahme-Tageszeitplaner -----------------
if intake_schedule:
    schedule_html = ""
    for time_slot, items in intake_schedule.items():
        schedule_html += f"<div style='margin-bottom: 12px;'><strong style='color: #1e293b; font-size: 0.96rem;'>⏱️ {time_slot}:</strong><ul style='margin: 4px 0 0 0; padding-left: 20px; font-size: 0.92rem; color: #334155;'>"
        for item in items:
            schedule_html += f"<li style='margin-bottom: 4px;'><strong style='color: #0f172a;'>{item['drug'].capitalize()}:</strong> <span style='color: #475569;'>{item['note']}</span></li>"
        schedule_html += "</ul></div>"

    st.markdown(f"""
    <div class="schedule-card">
        <h4 style="margin: 0 0 12px 0; color: #1e40af;">📅 Chronopharmakologischer Einnahmeplan (Tagesplaner)</h4>
        {schedule_html}
    </div>
    """, unsafe_allow_html=True)

# ----------------- Labor- & Diagnostik-Ampel -----------------
monitoring_list = get_aggregated_monitoring(active_substances, detected_interactions, multidrug_synergies)
if monitoring_list:
    st.markdown(f"""
    <div class="monitoring-card">
        <h4 style="margin: 0 0 8px 0; color: #0369a1;">🔬 Empfohlene Laborkontrollen & Diagnostik für das Arztgespräch</h4>
        <p style="margin: 0 0 10px 0; font-size: 0.88rem; color: #0c4a6e;">
            Auf Basis der ausgewählten Medikation und Organrisiken sollten folgende Parameter ärztlich kontrolliert werden:
        </p>
        <ul style="margin: 0; padding-left: 20px; color: #1e293b; font-size: 0.92rem;">
            {''.join([f'<li style="margin-bottom: 4px;">{p}</li>' for p in monitoring_list])}
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ----------------- Pharmakologische Wirkstoff-Profile -----------------
if len(active_substances) > 0:
    with st.expander("🧬 Pharmakologische Wirkstoff-Profile (Elimination, Metabolisierung & Klasse)", expanded=False):
        st.caption("Kompakte pharmakologische Kenndaten zur renalen/hepatischen Belastung und Enzymwegen.")
        for d in active_substances:
            pharm = get_drug_pharmacology(d)
            if pharm:
                st.markdown(f"""
                <div class="profile-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                        <h4 style="margin: 0; color: #0f172a;">{pharm['name'].capitalize()}</h4>
                        <span class="status-badge badge-organ">ATC: {pharm['atc_code']}</span>
                    </div>
                    <p style="margin: 3px 0; font-size: 0.90rem; color: #334155;"><strong>Wirkstoffklasse:</strong> {pharm['drug_class']}</p>
                    <p style="margin: 3px 0; font-size: 0.90rem; color: #334155;"><strong>Primäres Organsystem:</strong> {pharm['organ_system']}</p>
                    <p style="margin: 3px 0 0 0; font-size: 0.88rem; color: #64748b;"><strong>Elimination & Metabolisierung:</strong> {pharm['metabolism']}</p>
                </div>
                """, unsafe_allow_html=True)

# ----------------- Export- & Druckbereich -----------------
if len(active_substances) >= 1:
    report_bytes = create_pdf_report(selected_drugs, active_substances, drug_settings, detected_interactions, is_triple_whammy, multidrug_synergies, monitoring_list, priscus_alerts, renal_alerts, intake_schedule)
    file_ext = "pdf" if FPDF_AVAILABLE else "txt"
    mime_type = "application/pdf" if FPDF_AVAILABLE else "text/plain"

    col_btn1, col_btn2 = st.columns([1.5, 1])

    with col_btn1:
        st.download_button(
            label="📄 Gesprächsleitfaden herunterladen (PDF / TXT)",
            data=report_bytes,
            file_name=f"MediCheck_Arzt_Gespraechsleitfaden.{file_ext}",
            mime=mime_type,
            use_container_width=True
        )

    with col_btn2:
        if st.button("🖨️ Bericht direkt drucken", use_container_width=True):
            components.html("<script>window.parent.print();</script>", height=0, width=0)

st.subheader("Detaillierte Analyse der Paar-Wechselwirkungen")

if len(detected_interactions) > 0:
    for item in detected_interactions:
        d1, d2 = item["pair"]
        is_high = item["severity"] == "Hoch"
        badge_class = "badge-high" if is_high else "badge-medium"
        card_class = "high" if is_high else "medium"
        
        src = item.get("source", "DB")
        if src == "Phyto-Regelwerk":
            source_badge_class = "badge-phyto"
        elif src == "ATC-Klassenregel":
            source_badge_class = "badge-class"
        elif "openFDA" in src:
            source_badge_class = "badge-fda"
        else:
            source_badge_class = "badge-db"

        advice = get_practical_advice(item.get("effect", ""), item.get("mechanism", ""), item.get("system", ""))
        advice_html = f'<div class="advice-box">{advice}</div>' if advice else ""

        st.markdown(f"""
        <div class="interaction-card {card_class}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <h4 style="margin: 0; color: #0f172a;">{d1.capitalize()} &nbsp;⚡&nbsp; {d2.capitalize()}</h4>
                <div>
                    <span class="status-badge {badge_class}">{item['severity']}</span>
                    <span class="status-badge badge-organ">{item['system']}</span>
                    <span class="status-badge {source_badge_class}">{src}</span>
                </div>
            </div>
            <p style="margin: 6px 0; font-weight: 500; color: #334155;"><strong>Klinischer Befund:</strong> {item['effect']}</p>
            <p style="margin: 6px 0 0 0; color: #64748b; font-size: 0.92rem;"><strong>Hintergrund / Auszug:</strong> {item['mechanism']}</p>
            {advice_html}
        </div>
        """, unsafe_allow_html=True)
elif len(active_substances) >= 2:
    st.info("In den hinterlegten Datenbanken wurden für diese Kombination keine dokumentierten kritischen Wechselwirkungen gefunden.")
else:
    st.write("Wählen Sie mindestens zwei Substanzen aus, um den Abgleich zu starten.")

st.markdown("""
<div class="disclaimer-box">
    <strong>⚠️ Rechtlicher Hinweis & Haftungsausschluss:</strong><br>
    Dieses Informationsportal dient ausschließlich als Orientierungs- und Vorbereitungshilfe für das Arzt- oder Apothekergespräch. 
    Es ersetzt unter keinen Umständen die professionelle medizinische Begutachtung, Diagnose oder Therapie. 
    Verändern oder beenden Sie die Einnahme verordneter Arzneimittel keinesfalls eigenmächtig.
</div>
""", unsafe_allow_html=True)