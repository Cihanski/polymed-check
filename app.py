import os
os.environ["FONTTOOLS_DONT_USE_CYTHON"] = "1"

import streamlit as st
import requests
import re
from itertools import combinations
from datetime import datetime

# Sicherer Import fuer FPDF (faengt Windows-Sicherheitsblockaden / DLL-Fehler ab)
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
    }
    .metric-title {
        margin: 0 0 8px 0; 
        color: #1e293b; 
        font-size: 0.95rem; 
        font-weight: 600;
    }
    .metric-desc {
        margin: 8px 0 0 0; 
        color: #64748b; 
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
        color: #991b1b;
        border: 1px solid #fecaca;
    }
    .badge-medium {
        background-color: #fef3c7;
        color: #92400e;
        border: 1px solid #fde68a;
    }
    .badge-organ {
        background-color: #e0f2fe;
        color: #075985;
        border: 1px solid #bae6fd;
    }
    .badge-db {
        background-color: #f3e8ff;
        color: #6b21a8;
        border: 1px solid #e9d5ff;
    }
    .badge-class {
        background-color: #e0e7ff;
        color: #3730a3;
        border: 1px solid #c7d2fe;
    }
    .badge-phyto {
        background-color: #dcfce7;
        color: #166534;
        border: 1px solid #bbf7d0;
    }
    .badge-fda {
        background-color: #ecfdf5;
        color: #065f46;
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
        color: #166534;
    }
    .combo-box {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 16px;
        font-size: 0.90rem;
        color: #334155;
    }
    .profile-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .monitoring-card {
        background-color: #f0f9ff;
        border: 1px solid #bae6fd;
        border-left: 6px solid #0284c7;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 20px;
    }
    .synergy-card {
        background-color: #fff1f2;
        border: 1px solid #fecdd3;
        border-left: 6px solid #e11d48;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 16px;
    }
    .disclaimer-banner {
        background-color: #eff6ff;
        border-left: 4px solid #3b82f6;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 20px;
        color: #1e3a8a;
        font-size: 0.9rem;
    }
    .disclaimer-box {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 16px;
        font-size: 0.88rem;
        color: #475569;
        margin-top: 30px;
    }
</style>
""", unsafe_allow_html=True)


def clean_text_for_pdf(text):
    """Entfernt Emojis und codiert sicher fuer FPDF Latin-1."""
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
    """Generiert praxisnahe Handlungsempfehlungen basierend auf dem Wirkmechanismus."""
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
    """Aggregiert notwendige Kontrollparameter ueber alle aktiven Substanzen."""
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
    """Laedt den gesamten Katalog in den Cache."""
    base_catalog = set(get_autocomplete_catalog())
    cached_drugs = set(get_all_cached_drugs())
    return sorted(list(base_catalog.union(cached_drugs)))


def fetch_fda_interaction(drug_a, drug_b):
    """Fallback: openFDA drug label API."""
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
    """4-Stufen-Pruefkaskade: Cache -> Phyto/Nahrung -> ATC-Klassen -> openFDA."""
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


def generate_text_report(selected_drugs, active_substances, drug_settings, interactions, is_triple, synergies, monitoring_params):
    """Fallback-Report als formatierter Text, falls FPDF blockiert wird."""
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

    if is_triple or synergies:
        lines.append("WARNUNG: Kumulative Mehrfach-Risiken (Multi-Drug Synergien):")
        if is_triple:
            lines.append("- Triple-Whammy: RAAS-Hemmer + Diuretikum + NSAR (systemisch) -> Akute Nierenbelastung")
        for syn in synergies:
            lines.append(f"- {syn['title']}: {syn['effect']}")
        lines.append("")

    lines.append(f"2. Gefundene Einzelwechselwirkungen ({len(interactions)} Befunde):")
    if not interactions:
        lines.append("Keine kritischen Konflikte dokumentiert.")
    else:
        for idx, item in enumerate(interactions, start=1):
            d1, d2 = item["pair"]
            lines.append(f"{idx}. {d1.capitalize()} + {d2.capitalize()} [{item['severity']} | {item['system']}]")
            lines.append(f"   Effekt: {item['effect']}")
            lines.append(f"   Details: {item['mechanism']}")
            advice = get_practical_advice(item.get("effect", ""), item.get("mechanism", ""), item.get("system", ""))
            if advice:
                lines.append(f"   Empfehlung: {advice}")
    lines.append("")

    if monitoring_params:
        lines.append("3. Empfohlene Laborkontrollen & Diagnostik:")
        for param in monitoring_params:
            lines.append(f"* {param}")
        lines.append("")

    lines.append("4. Leitfragen fuer das Arztgespraech:")
    lines.append("- Gibt es schonendere Alternativen?")
    lines.append("- Sollten die empfohlenen Laborparameter kontrolliert werden?")
    lines.append("- Koennen Einnahmeabstaende angepasst werden?")
    lines.append("\nHaftungsausschluss: Dient ausschliesslich zur Gespraechsvorbereitung. Keine Therapieempfehlung.")
    return "\n".join(lines).encode("utf-8")


def create_pdf_report(selected_drugs, active_substances, drug_settings, interactions, is_triple, synergies, monitoring_params):
    """Erzeugt einen sauberen PDF-Report (faellt bei DLL-Blockaden auf Text zurueck)."""
    if not FPDF_AVAILABLE:
        return generate_text_report(selected_drugs, active_substances, drug_settings, interactions, is_triple, synergies, monitoring_params)

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
    pdf.cell(width, 8, clean_text_for_pdf("1. Erfasste Praeparate & aufgeschluesselte Wirkstoffe:"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    for d in selected_drugs:
        inns = resolve_drug_to_inns(d)
        if len(inns) > 1:
            inn_info = f" [Fixkombination: {' + '.join([i.capitalize() for i in inns])}]"
        else:
            inn = inns[0]
            inn_info = f" [Wirkstoff: {inn.capitalize()}]" if inn.lower() != d.lower() and not d.startswith("PHYTO_") else ""
        
        setting_info = f" ({drug_settings[d]})" if d in drug_settings else ""
        pdf.cell(width, 6, clean_text_for_pdf(f"- {d}{inn_info}{setting_info}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    if is_triple or synergies:
        pdf.set_fill_color(254, 226, 226)
        pdf.set_text_color(153, 27, 27)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(width, 8, clean_text_for_pdf(" WARNUNG: Kumulative Mehrfach-Risiken (Multi-Drug Synergien):"), fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=9)
        
        if is_triple:
            pdf.multi_cell(width, 5, clean_text_for_pdf("- Triple-Whammy-Kombination: Renale Dekompensation durch RAAS-Hemmer + Diuretikum + NSAR (systemisch)."), fill=True, new_x="LMARGIN", new_y="NEXT")
        
        for syn in synergies:
            pdf.multi_cell(width, 5, clean_text_for_pdf(f"- {syn['title']}: {syn['effect']}"), fill=True, new_x="LMARGIN", new_y="NEXT")
        
        pdf.ln(4)
        pdf.set_text_color(20, 20, 20)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(width, 8, clean_text_for_pdf(f"2. Gefundene Einzelwechselwirkungen ({len(interactions)} Befunde):"), new_x="LMARGIN", new_y="NEXT")
    
    if len(interactions) == 0:
        pdf.set_font("Helvetica", size=10)
        pdf.cell(width, 6, clean_text_for_pdf("In den hinterlegten Referenzdatenbanken sind keine kritischen Konflikte dokumentiert."), new_x="LMARGIN", new_y="NEXT")
    else:
        for idx, item in enumerate(interactions, start=1):
            d1, d2 = item["pair"]
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(width, 6, clean_text_for_pdf(f"{idx}. {d1.capitalize()} + {d2.capitalize()} [Risiko: {item['severity']} | {item['system']}]"), new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", size=9)
            pdf.multi_cell(width, 5, clean_text_for_pdf(f"Effekt: {item['effect']}"), new_x="LMARGIN", new_y="NEXT")
            pdf.multi_cell(width, 5, clean_text_for_pdf(f"Details: {item['mechanism']}"), new_x="LMARGIN", new_y="NEXT")
            
            advice = get_practical_advice(item.get("effect", ""), item.get("mechanism", ""), item.get("system", ""))
            if advice:
                pdf.set_text_color(22, 101, 52)
                pdf.multi_cell(width, 5, clean_text_for_pdf(f"Empfehlung: {advice}"), new_x="LMARGIN", new_y="NEXT")
                pdf.set_text_color(20, 20, 20)
            pdf.ln(2)
            
    if monitoring_params:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(2, 132, 199)
        pdf.cell(width, 8, clean_text_for_pdf("3. Empfohlene Laborkontrollen & Diagnostik:"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=9)
        pdf.set_text_color(20, 20, 20)
        for param in monitoring_params:
            pdf.multi_cell(width, 5, clean_text_for_pdf(f"* {param}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(width, 8, clean_text_for_pdf("4. Leitfragen fuer das Arztgespraech:"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    fragen_text = (
        "- 'Gibt es fuer die verordneten Praeparate schonendere Alternativen?'\n"
        "- 'Sollten die oben aufgefuehrten Laborwerte (z. B. Elektrolyte, Nierenfunktion, EKG) kontrolliert werden?'\n"
        "- 'Koennen Einnahmezeitpunkte oder Abstaende angepasst werden (z. B. bei Chelatbildnern wie Milch/Mineralstoffen)?'"
    )
    pdf.multi_cell(width, 5, clean_text_for_pdf(fragen_text), new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(width, 4, clean_text_for_pdf("Haftungsausschluss: Dieses Dokument dient ausschliesslich zur Gespraechsvorbereitung. Es stellt keine Therapieempfehlung dar. Medikamente niemals eigenmaechtig absetzen."), new_x="LMARGIN", new_y="NEXT")
    
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

default_selection = [
    "Milchprodukte & Calciumreiches Wasser 🥛",
    "Ciprofloxacin"
]
valid_defaults = [d for d in default_selection if d in all_available_options]

selected_drugs = st.multiselect(
    label="Wählen oder suchen Sie Wirkstoffe, Phytopharmaka oder Lebensmittel:",
    options=all_available_options,
    default=valid_defaults,
    placeholder="Buchstaben eingeben (z. B. 'Co-Diovan', 'Ramipril plus HCT', 'Vimovo', 'Diclofenac')...",
    help="Erkennt Einzelwirkstoffe, Markennamen und spaltet Fixkombinationen (z. B. Co-Diovan) automatisch auf."
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

has_high = any(item["severity"] == "Hoch" for item in detected_interactions) or is_triple_whammy or any(s["severity"] == "Hoch" for s in multidrug_synergies)
has_medium = any(item["severity"] == "Moderat" for item in detected_interactions) or len(multidrug_synergies) > 0

col1, col2, col3 = st.columns([1.3, 1, 1])

with col1:
    if len(active_substances) < 2:
        status_color = "#64748b"
        status_text = "Mindestens 2 Einträge wählen"
        status_desc = "Wählen Sie Substanzen aus, um die Analyse zu starten."
    elif has_high:
        status_color = "#dc2626"
        status_text = "🔴 Hohe Relevanz fürs Arztgespräch"
        status_desc = "Kritische Konflikte erkannt. Dringend ärztlich besprechen!"
    elif has_medium:
        status_color = "#d97706"
        status_text = "🟡 Monitoring empfohlen"
        status_desc = "Relevante Wechselwirkungen oder Resorptionskonflikte gefunden."
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
    total_findings = len(detected_interactions) + len(multidrug_synergies) + (1 if is_triple_whammy else 0)
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Erkannte Befunde</div>
        <h2 style="margin:0; color: {'#dc2626' if total_findings > 0 else '#16a34a'};">
            {total_findings}
        </h2>
        <div class="metric-desc">Konflikte, Resorption & Synergien</div>
    </div>
    """, unsafe_allow_html=True)

if is_triple_whammy:
    st.error("⚠️ **Akutes Triple-Whammy-Risiko:** Blutdrucksenker + Entwässerungsmittel + orales NSAR drosseln die glomeruläre Nierenfunktion akut. Sprechen Sie dies zeitnah beim Arzt an!")

for syn in multidrug_synergies:
    st.markdown(f"""
    <div class="synergy-card">
        <h4 style="margin: 0 0 6px 0; color: #9f1239;">⚡ {syn['title']}</h4>
        <p style="margin: 4px 0; font-size: 0.95rem; color: #1e293b;"><strong>Beteiligte Medikamente:</strong> {', '.join([d.capitalize() for d in syn['drugs']])}</p>
        <p style="margin: 4px 0; font-size: 0.92rem; color: #334155;"><strong>Klinischer Effekt:</strong> {syn['effect']}</p>
        <p style="margin: 4px 0 0 0; font-size: 0.88rem; color: #64748b;"><strong>Mechanismus:</strong> {syn['mechanism']}</p>
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

if len(active_substances) >= 2:
    report_bytes = create_pdf_report(selected_drugs, active_substances, drug_settings, detected_interactions, is_triple_whammy, multidrug_synergies, monitoring_list)
    file_ext = "pdf" if FPDF_AVAILABLE else "txt"
    mime_type = "application/pdf" if FPDF_AVAILABLE else "text/plain"
    
    st.download_button(
        label="📄 Gesprächsleitfaden für das nächste Arztgespräch herunterladen",
        data=report_bytes,
        file_name=f"MediCheck_Arzt_Gespraechsleitfaden.{file_ext}",
        mime=mime_type,
        use_container_width=True
    )

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