import streamlit as st
import requests
from itertools import combinations
from fpdf import FPDF
from datetime import datetime
from cache_manager import (
    check_cache, 
    check_class_rules, 
    check_multidrug_synergies,
    save_to_cache, 
    get_total_cached_count, 
    get_total_class_rules_count, 
    get_all_cached_drugs
)
from drug_translator import translate_to_inn, get_autocomplete_catalog

# --- 1. Seitenkonfiguration & Custom Styling ---
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

# --- 2. Live-Abfrage an openFDA ---
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
    """3-Stufen-Prüfkaskade."""
    cached = check_cache(drug_a, drug_b)
    if cached:
        return cached

    class_match = check_class_rules(drug_a, drug_b)
    if class_match:
        return class_match

    fda_result = fetch_fda_interaction(drug_a, drug_b)
    if fda_result:
        save_to_cache(drug_a, drug_b, fda_result)
        return fda_result

    return None

# --- 3. PDF-Generierungsfunktion ---
def create_pdf_report(drugs, interactions, is_triple, synergies):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    width = pdf.epw
    
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(width, 10, "MediCheck - Medikations- & Gespraechsleitfaden", new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(width, 6, f"Erstellt am: {datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')} | Zur Vorbereitung auf das Arztgespraech", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(width, 8, "1. Erfasste Praeparate & Wirkstoffe:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    for d in drugs:
        inn = translate_to_inn(d)
        inn_info = f" [Wirkstoff: {inn.capitalize()}]" if inn.lower() != d.lower() else ""
        pdf.cell(width, 6, f"- {d}{inn_info}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    if is_triple or synergies:
        pdf.set_fill_color(254, 226, 226)
        pdf.set_text_color(153, 27, 27)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(width, 8, " WARNUNG: Kumulative Mehrfach-Risiken (Multi-Drug Synergien):", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=9)
        
        if is_triple:
            pdf.multi_cell(width, 5, "- Triple-Whammy-Kombination: Renale Dekompensation durch RAAS-Hemmer + Diuretikum + NSAR.", fill=True, new_x="LMARGIN", new_y="NEXT")
        
        for syn in synergies:
            pdf.multi_cell(width, 5, f"- {syn['title']}: {syn['effect']}", fill=True, new_x="LMARGIN", new_y="NEXT")
        
        pdf.ln(4)
        pdf.set_text_color(20, 20, 20)
    
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(width, 8, f"2. Gefundene Einzelpaar-Wechselwirkungen ({len(interactions)} Befunde):", new_x="LMARGIN", new_y="NEXT")
    
    if len(interactions) == 0:
        pdf.set_font("Helvetica", size=10)
        pdf.cell(width, 6, "In den hinterlegten Referenzdatenbanken sind keine kritischen Konflikte dokumentiert.", new_x="LMARGIN", new_y="NEXT")
    else:
        for idx, item in enumerate(interactions, start=1):
            d1, d2 = item["pair"]
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(width, 6, f"{idx}. {d1} + {d2} [Risiko: {item['severity']} | {item['system']}]", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", size=9)
            pdf.multi_cell(width, 5, f"Effekt: {item['effect']}", new_x="LMARGIN", new_y="NEXT")
            pdf.multi_cell(width, 5, f"Details: {item['mechanism']}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(width, 8, "3. Leitfragen fuer das Arztgespraech:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    fragen_text = (
        "- 'Gibt es fuer die verordneten Praeparate schonendere Alternativen fuer mich?'\n"
        "- 'Sollten relevante Laborparameter (z. B. Kreatinin/GFR, Kalium, EKG/QT-Intervall) kontrolliert werden?'\n"
        "- 'Koennen die Einnahmezeitpunkte angepasst werden, um Wechselwirkungen zu minimieren?'"
    )
    pdf.multi_cell(width, 5, fragen_text, new_x="LMARGIN", new_y="NEXT")
    
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    pdf.multi_cell(width, 4, "Haftungsausschluss: Dieses Dokument dient ausschliesslich zur Gespraechsvorbereitung. Es stellt keine Therapieempfehlung dar. Medikamente niemals eigenmaechtig absetzen.", new_x="LMARGIN", new_y="NEXT")
    
    return bytes(pdf.output())

# --- 4. App-Header & Disclaimer-Banner ---
total_db = get_total_cached_count()
total_classes = get_total_class_rules_count()

base_catalog = set(get_autocomplete_catalog())
cached_drugs = set(get_all_cached_drugs())
all_available_options = sorted(list(base_catalog.union(cached_drugs)))

st.title("💊 MediCheck – Globaler Medikations-Check")

st.markdown("""
<div class="disclaimer-banner">
    ℹ️ <strong>Wichtiger Hinweis:</strong> Dieses Informationsportal dient ausschließlich als Orientierungs- und Vorbereitungshilfe für das persönliche Gespräch mit Ihrem Arzt oder Apotheker. Es stellt keine medizinische Diagnose oder Therapieempfehlung dar. Verändern oder beenden Sie die Einnahme verordneter Arzneimittel keinesfalls eigenmächtig.
</div>
""", unsafe_allow_html=True)

st.caption(f"Arzneistoffkatalog: **{len(all_available_options):,} Substanzen** (WHO-ATC-Index). Motor: **{total_classes} ATC-Klassenregeln** + **{total_db} Einzelwechselwirkungen**.")

# --- 5. Die smarte Suchleiste ---
default_selection = [
    "Delix (Ramipril)",
    "HCT-Hexal (Hydrochlorothiazid)",
    "Ibuprofen (z. B. Nurofen, Ibutop, Ibu-Hexal)"
]
valid_defaults = [d for d in default_selection if d in all_available_options]

selected_drugs = st.multiselect(
    label="Tippen Sie den Namen oder Anfangsbuchstaben ein (z. B. 'Flu', 'Aspirin', 'Cipro', 'Met'):",
    options=all_available_options,
    default=valid_defaults,
    placeholder="Buchstaben eingeben (z. B. 'Flu', 'Asp', 'Pan')...",
    help="Tippen Sie einfach Buchstaben ein. Die Liste durchsucht in Echtzeit den gesamten europäischen Arzneistoffkatalog."
)

# --- 6. Automatische Analyse ---
detected_interactions = []
if len(selected_drugs) >= 2:
    with st.spinner("Analysiere Wechselwirkungen..."):
        for drug_a, drug_b in combinations(selected_drugs, 2):
            result = find_interaction_smart(drug_a, drug_b)
            if result:
                detected_interactions.append({
                    "pair": (drug_a, drug_b),
                    **result
                })

# Multi-Drug Synergien & Triple Whammy
multidrug_synergies = check_multidrug_synergies(selected_drugs) if len(selected_drugs) >= 2 else []

normalized_drugs = [translate_to_inn(d) for d in selected_drugs]
has_raas = any(d in normalized_drugs for d in ["ramipril", "candesartan", "enalapril", "valsartan", "lisinopril"])
has_diuretic = any(d in normalized_drugs for d in ["hydrochlorothiazide", "torsemide", "furosemide", "spironolactone"])
has_nsar = any(d in normalized_drugs for d in ["ibuprofen", "diclofenac", "naproxen", "etoricoxib"])
is_triple_whammy = has_raas and has_diuretic and has_nsar

# --- 7. Ampel-Dashboard ---
has_high = any(item["severity"] == "Hoch" for item in detected_interactions) or is_triple_whammy or any(s["severity"] == "Hoch" for s in multidrug_synergies)
has_medium = any(item["severity"] == "Moderat" for item in detected_interactions) or len(multidrug_synergies) > 0

col1, col2, col3 = st.columns([1.3, 1, 1])

with col1:
    if len(selected_drugs) < 2:
        status_color = "#64748b"
        status_text = "Mindestens 2 Wirkstoffe wählen"
        status_desc = "Wählen Sie Substanzen aus, um die automatische Analyse zu starten."
    elif has_high:
        status_color = "#dc2626"
        status_text = "🔴 Hohe Relevanz fürs Arztgespräch"
        status_desc = "Kritische Konflikte erkannt. Dringend beim nächsten Arzttermin vorlegen!"
    elif has_medium:
        status_color = "#d97706"
        status_text = "🟡 Monitoring / Überwachung empfohlen"
        status_desc = "Dokumentierte Wechselwirkungen oder Synergien gefunden."
    else:
        status_color = "#16a34a"
        status_text = "🟢 Keine dokumentierten Konflikte"
        status_desc = "In den hinterlegten Datenbanken ist kein bekannter Konflikt verzeichnet (ersetzt keine ärztliche Prüfung)."

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
        <div class="metric-title">Ausgewählte Medikamente</div>
        <h2 style="margin:0; color: #0284c7;">{len(selected_drugs)}</h2>
        <div class="metric-desc">Substanzen im aktuellen Check</div>
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
        <div class="metric-desc">Konflikte & Synergien</div>
    </div>
    """, unsafe_allow_html=True)

# Warnbanner für Triple Whammy
if is_triple_whammy:
    st.error("⚠️ **Akutes Triple-Whammy-Risiko:** Blutdrucksenker + Entwässerungsmittel + NSAR-Schmerzmittel drosseln die Nierenfunktion akut. Sprechen Sie dies zeitnah beim Arzt an!")

# Warnkarten für Multi-Drug-Synergien
for syn in multidrug_synergies:
    st.markdown(f"""
    <div class="synergy-card">
        <h4 style="margin: 0 0 6px 0; color: #9f1239;">⚡ {syn['title']}</h4>
        <p style="margin: 4px 0; font-size: 0.95rem; color: #1e293b;"><strong>Beteiligte Medikamente:</strong> {', '.join(syn['drugs'])}</p>
        <p style="margin: 4px 0; font-size: 0.92rem; color: #334155;"><strong>Klinischer Effekt:</strong> {syn['effect']}</p>
        <p style="margin: 4px 0 0 0; font-size: 0.88rem; color: #64748b;"><strong>Mechanismus:</strong> {syn['mechanism']}</p>
    </div>
    """, unsafe_allow_html=True)

# --- 8. PDF Download ---
if len(selected_drugs) >= 2:
    pdf_bytes = create_pdf_report(selected_drugs, detected_interactions, is_triple_whammy, multidrug_synergies)
    st.download_button(
        label="📄 Gesprächsleitfaden für das nächste Arztgespräch als PDF herunterladen",
        data=pdf_bytes,
        file_name="MediCheck_Arzt_Gespraechsleitfaden.pdf",
        mime="application/pdf",
        use_container_width=True
    )

# --- 9. Detaillierte Befunde ---
st.subheader("Detaillierte Analyse der Paar-Wechselwirkungen")

if len(detected_interactions) > 0:
    for item in detected_interactions:
        d1, d2 = item["pair"]
        is_high = item["severity"] == "Hoch"
        badge_class = "badge-high" if is_high else "badge-medium"
        card_class = "high" if is_high else "medium"
        
        src = item.get("source", "DB")
        if src == "ATC-Klassenregel":
            source_badge_class = "badge-class"
        elif "openFDA" in src:
            source_badge_class = "badge-fda"
        else:
            source_badge_class = "badge-db"

        st.markdown(f"""
        <div class="interaction-card {card_class}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <h4 style="margin: 0; color: #0f172a;">{d1} &nbsp;⚡&nbsp; {d2}</h4>
                <div>
                    <span class="status-badge {badge_class}">{item['severity']}</span>
                    <span class="status-badge badge-organ">{item['system']}</span>
                    <span class="status-badge {source_badge_class}">{src}</span>
                </div>
            </div>
            <p style="margin: 6px 0; font-weight: 500; color: #334155;"><strong>Klinischer Befund:</strong> {item['effect']}</p>
            <p style="margin: 6px 0 0 0; color: #64748b; font-size: 0.92rem;"><strong>Hintergrund / Auszug:</strong> {item['mechanism']}</p>
        </div>
        """, unsafe_allow_html=True)
elif len(selected_drugs) >= 2:
    st.info("In den hinterlegten Datenbanken wurden für diese Wirkstoffkombination keine dokumentierten kritischen Wechselwirkungen gefunden.")
else:
    st.write("Wählen Sie mindestens zwei Medikamente aus, um den Abgleich zu starten.")

# --- 10. Haftungsausschluss Footer ---
st.markdown("""
<div class="disclaimer-box">
    <strong>⚠️ Rechtlicher Hinweis & Haftungsausschluss:</strong><br>
    Dieses Informationsportal dient ausschließlich als Orientierungs- und Vorbereitungshilfe für das Arzt- oder Apothekergespräch. 
    Es ersetzt unter keinen Umständen die professionelle medizinische Begutachtung, Diagnose oder Therapie. 
    Verändern oder beenden Sie die Einnahme verordneter Arzneimittel keinesfalls eigenmächtig.
</div>
""", unsafe_allow_html=True)