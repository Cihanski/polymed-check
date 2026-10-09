import streamlit as st
from itertools import combinations
from fpdf import FPDF
from datetime import datetime

# --- 1. Seitenkonfiguration & Custom Styling ---
st.set_page_config(
    page_title="MediCheck – Polymedikations- & Interaktions-Visualisierer",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Sauberes CSS (ohne .main zu überschreiben)
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
    .disclaimer-box {
        background-color: #f8fafc;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 14px;
        font-size: 0.85rem;
        color: #475569;
        margin-top: 30px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Wissensdatenbank ---
DRUGS_DB = {
    "Ibuprofen": {"klasse": "NSAR (Schmerzmittel / Entzündungshemmer)"},
    "Ramipril": {"klasse": "ACE-Hemmer (Blutdrucksenker)"},
    "HCT (Hydrochlorothiazid)": {"klasse": "Thiaziddiuretikum (Entwässerungstablette)"},
    "Pantoprazol": {"klasse": "Protonenpumpeninhibitor / PPI (Magenschutz)"},
    "Metformin": {"klasse": "Biguanid (Antidiabetikum)"},
    "ASS (Acetylsalicylsäure)": {"klasse": "Thrombozytenaggregationshemmer (Blutverdünner)"},
    "Apixaban (Eliquis)": {"klasse": "DOAK / Direkter Faktor-Xa-Hemmer (starker Blutverdünner)"},
    "Phenprocoumon (Marcumar)": {"klasse": "Vitamin-K-Antagonist (klassischer Blutverdünner)"},
    "Simvastatin": {"klasse": "Statin (Cholesterinsenker)"},
    "Amlodipin": {"klasse": "Kalziumkanalblocker (Blutdrucksenker)"},
    "Citalopram": {"klasse": "SSRI (Antidepressivum)"},
    "Ginkgo Biloba": {"klasse": "Pflanzliches Präparat / Durchblutungsförderer"}
}

INTERACTIONS_DB = {
    frozenset(["Ibuprofen", "ASS (Acetylsalicylsäure)"]): {
        "severity": "Hoch",
        "system": "Magen-Darm-Trakt & Hämostase",
        "effect": "Massiv erhöhtes Risiko für Magengeschwüre, Magenblutungen und Aufhebung des Herzschutzes von ASS.",
        "mechanism": "Beide Wirkstoffe greifen die Magenschleimhaut an. Zudem blockiert Ibuprofen den Zugang von ASS an den Blutplättchen, wodurch die gerinnungshemmende Schutzwirkung von ASS verpufft."
    },
    frozenset(["Ibuprofen", "Apixaban (Eliquis)"]): {
        "severity": "Hoch",
        "system": "Hämostase & Magen-Darm-Trakt",
        "effect": "Kritisch erhöhtes Risiko schwerer gastrointestinaler Blutungen.",
        "mechanism": "NSAR (Ibuprofen) schädigen die Magenschleimhautoberfläche, während Apixaban die Gerinnungskaskade hemmt. Blutungen können nicht adäquat gestillt werden."
    },
    frozenset(["ASS (Acetylsalicylsäure)", "Apixaban (Eliquis)"]): {
        "severity": "Hoch",
        "system": "Hämostase (Blutgerinnung)",
        "effect": "Drastisch gesteigertes Blutungsrisiko (z. B. Hirn- oder Magenblutungen).",
        "mechanism": "Doppelte Gerinnungshemmung: Plättchenfunktionshemmung (ASS) trifft auf direkte Blockade der plasmatischen Gerinnung (Apixaban)."
    },
    frozenset(["Phenprocoumon (Marcumar)", "ASS (Acetylsalicylsäure)"]): {
        "severity": "Hoch",
        "system": "Hämostase (Blutgerinnung)",
        "effect": "Schwere Blutungsneigung, spontane Hämatome und innere Blutungen.",
        "mechanism": "Kombination aus Vitamin-K-Syntheseblockade und irreversibler Plättchenhemmung."
    },
    frozenset(["ASS (Acetylsalicylsäure)", "Ginkgo Biloba"]): {
        "severity": "Moderat",
        "system": "Hämostase (Blutgerinnung)",
        "effect": "Erhöhte Neigung zu Hämatomen, Nasenbluten und Nachblutungen.",
        "mechanism": "Ginkgo-Extrakte enthalten Ginkgolide, die den PAF (Plättchenaktivierungsfaktor) inhibieren und so die thrombozytenhemmende Wirkung von ASS verstärken."
    },
    frozenset(["Citalopram", "ASS (Acetylsalicylsäure)"]): {
        "severity": "Moderat",
        "system": "Hämostase & Thrombozyten",
        "effect": "Erhöhte Blutungsneigung im oberen Magen-Darm-Trakt.",
        "mechanism": "SSRI (Citalopram) senken den Serotoningehalt in den Blutplättchen, was deren Aggregationsfähigkeit verringert."
    },
    frozenset(["Ibuprofen", "Ramipril"]): {
        "severity": "Hoch",
        "system": "Nierenfunktion & Blutdruck",
        "effect": "Akute Verschlechterung der Nierenfiltration & Abschwächung der Blutdrucksenkung.",
        "mechanism": "Ramipril erweitert die ableitenden Gefäße der Niere, Ibuprofen verengt die zuleitenden Gefäße. Der Filtrationsdruck bricht ein."
    },
    frozenset(["Ibuprofen", "HCT (Hydrochlorothiazid)"]): {
        "severity": "Moderat",
        "system": "Niere & Flüssigkeitshaushalt",
        "effect": "Verminderte entwässernde Wirkung und Anstieg des Blutdrucks.",
        "mechanism": "NSAR führen durch Prostaglandinhemmung zu Natrium- und Wasserretention in der Niere."
    },
    frozenset(["Ramipril", "HCT (Hydrochlorothiazid)"]): {
        "severity": "Moderat",
        "system": "Kreislauf & Elektrolyte",
        "effect": "Gefahr eines plötzlichen Blutdruckabfalls zu Beginn sowie Kaliumverschiebungen.",
        "mechanism": "Therapeutisch gängige Kombination, erfordert jedoch zu Beginn engmaschige Laborkontrollen."
    },
    frozenset(["Pantoprazol", "Metformin"]): {
        "severity": "Moderat",
        "system": "Magen-Darm & Resorption",
        "effect": "Langfristig Gefahr eines Vitamin-B12-Mangels.",
        "mechanism": "Sowohl Pantoprazol als auch Metformin hemmen die Resorption von Vitamin B12 im Magen-Darm-Trakt."
    },
    frozenset(["Simvastatin", "Amlodipin"]): {
        "severity": "Moderat",
        "system": "Muskulatur & CYP3A4-Enzym",
        "effect": "Erhöhtes Risiko für Myopathien bis hin zur Rhabdomyolyse.",
        "mechanism": "Amlodipin hemmt den CYP3A4-vermittelten Abbau von Simvastatin, wodurch der Plasmaspiegel steigt."
    },
    frozenset(["Ramipril", "Metformin"]): {
        "severity": "Moderat",
        "system": "Blutzucker-Regulation",
        "effect": "Gefahr unbemerkter Hypoglykämien.",
        "mechanism": "ACE-Hemmer können die periphere Insulinsensitivität erhöhen."
    },
    frozenset(["Ibuprofen", "Metformin"]): {
        "severity": "Moderat",
        "system": "Niere & Laktathaushalt",
        "effect": "Gefahr einer Laktatazidose bei Nierenfunktionseinschränkung.",
        "mechanism": "Verringerte renale Ausscheidung von Metformin bei NSAR-induzierter Nierenbelastung."
    }
}

# --- 3. PDF-Generierungsfunktion (Fehlerfrei formatiert) ---
def create_pdf_report(drugs, interactions, is_triple):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    width = pdf.epw
    
    # Titelzeile
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(width, 10, "MediCheck - Medikations- & Interaktionsbericht", new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.set_font("Helvetica", size=9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(width, 6, f"Erstellt am: {datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')} | Dokument zur Besprechung mit Ihrem Arzt", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    # 1. Medikamente
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(20, 20, 20)
    pdf.cell(width, 8, "1. Aktuell erfasste Medikamente:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    for d in drugs:
        klasse = DRUGS_DB.get(d, {}).get("klasse", "")
        pdf.cell(width, 6, f"- {d} ({klasse})", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    
    # Sonderwarnung Triple Whammy
    if is_triple:
        pdf.set_fill_color(254, 226, 226)
        pdf.set_text_color(153, 27, 27)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(width, 8, " ACHTUNG: Akutes Triple-Whammy-Risiko erkannt!", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=9)
        pdf.multi_cell(width, 5, " Die Kombination aus Ramipril + Diuretikum (HCT) + Ibuprofen gefaehrdet die Nierenfunktion erheblich. Dringende aerztliche Absprache erforderlich.", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        pdf.set_text_color(20, 20, 20)
    
    # 2. Gefundene Wechselwirkungen
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(width, 8, f"2. Gefundene Wechselwirkungen ({len(interactions)} Konflikte):", new_x="LMARGIN", new_y="NEXT")
    
    if len(interactions) == 0:
        pdf.set_font("Helvetica", size=10)
        pdf.cell(width, 6, "Keine dokumentierten kritischen Wechselwirkungen in dieser Kombination.", new_x="LMARGIN", new_y="NEXT")
    else:
        for idx, item in enumerate(interactions, start=1):
            d1, d2 = item["pair"]
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(width, 6, f"{idx}. {d1} + {d2} [Risiko: {item['severity']} | System: {item['system']}]", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", size=9)
            pdf.multi_cell(width, 5, f"Klinischer Effekt: {item['effect']}", new_x="LMARGIN", new_y="NEXT")
            pdf.multi_cell(width, 5, f"Mechanismus: {item['mechanism']}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)
            
    # 3. Fragen an den Arzt
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(width, 8, "3. Vorschlaege fuer das Arztgespraech:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=9)
    fragen_text = (
        "- 'Gibt es fuer Schmerzmittel wie Ibuprofen magen- und nierenschonendere Alternativen?'\n"
        "- 'Sollten meine Nieren-, Elektrolyt- oder Blutzuckerwerte zeitnah kontrolliert werden?'\n"
        "- 'Koennen Einnahmezeiten zeitlich versetzt werden, um Wechselwirkungen zu reduzieren?'"
    )
    pdf.multi_cell(width, 5, fragen_text, new_x="LMARGIN", new_y="NEXT")
    
    # Disclaimer
    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(120, 120, 120)
    disclaimer_text = (
        "Haftungsausschluss: Dieser Ausdruck dient ausschliesslich zur Vorbereitung auf das aerztliche Beratungsgespraech. "
        "Er stellt keine medizinische Diagnose oder Therapieempfehlung dar. "
        "Veraenderungen der Medikation duerfen keinesfalls eigenmaechtig durchgefuehrt werden."
    )
    pdf.multi_cell(width, 4, disclaimer_text, new_x="LMARGIN", new_y="NEXT")
    
    return bytes(pdf.output())

# --- 4. App-Header & Einführung ---
st.title("💊 MediCheck – Interaktions-Visualisierer")
st.markdown("Erkennen Sie gefährliche Kreuzreaktionen, Doppelverordnungen und Organbelastungen in Sekundenschnelle.")

# --- 5. Interaktive Medikamentenauswahl ---
selected_drugs = st.multiselect(
    label="Wählen Sie die gleichzeitig eingenommenen Medikamente aus:",
    options=list(DRUGS_DB.keys()),
    default=["Ramipril", "HCT (Hydrochlorothiazid)", "Ibuprofen"],
    help="Tippen oder wählen Sie beliebig viele Substanzen aus."
)

# --- 6. Analyse-Logik ---
detected_interactions = []
if len(selected_drugs) >= 2:
    for drug_a, drug_b in combinations(selected_drugs, 2):
        pair = frozenset([drug_a, drug_b])
        if pair in INTERACTIONS_DB:
            data = INTERACTIONS_DB[pair]
            detected_interactions.append({
                "pair": (drug_a, drug_b),
                **data
            })

is_triple_whammy = all(
    drug in selected_drugs for drug in ["Ramipril", "HCT (Hydrochlorothiazid)", "Ibuprofen"]
)

# --- 7. Gesamt-Risiko Score (Ampel) ---
has_high = any(item["severity"] == "Hoch" for item in detected_interactions) or is_triple_whammy
has_medium = any(item["severity"] == "Moderat" for item in detected_interactions)

col1, col2, col3 = st.columns([1.3, 1, 1])

with col1:
    if len(selected_drugs) < 2:
        status_color = "#64748b"
        status_text = "Mindestens 2 Wirkstoffe wählen"
        status_desc = "Fügen Sie Substanzen hinzu, um die Analyse zu starten."
    elif has_high:
        status_color = "#dc2626"
        status_text = "🔴 Hohes Interaktionsrisiko"
        status_desc = "Kritische Konflikte gefunden. Dringend ärztlich abklären!"
    elif has_medium:
        status_color = "#d97706"
        status_text = "🟡 Überwachung empfohlen"
        status_desc = "Relevante Wechselwirkungen gefunden. Dosisanpassung ratsam."
    else:
        status_color = "#16a34a"
        status_text = "🟢 Keine bekannten Konflikte"
        status_desc = "Für diese Kombination liegen keine schweren Warnungen vor."

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
        <div class="metric-title">Ausgewählte Wirkstoffe</div>
        <h2 style="margin:0; color: #0284c7;">{len(selected_drugs)}</h2>
        <div class="metric-desc">Substanzen im aktuellen Plan</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Erkannte Konflikte</div>
        <h2 style="margin:0; color: {'#dc2626' if len(detected_interactions) > 0 else '#16a34a'};">{len(detected_interactions)}</h2>
        <div class="metric-desc">Paarweise Interaktionen</div>
    </div>
    """, unsafe_allow_html=True)

# Triple Whammy Notiz
if is_triple_whammy:
    st.error("⚠️ **Akutes Triple-Whammy-Syndrom erkannt:** Die Kombination aus **Ramipril + Diuretikum (HCT) + Ibuprofen** führt zu einem drastischen Einbruch der Nierenfiltration!")

# --- 8. PDF-Download Button ---
if len(selected_drugs) >= 2:
    pdf_bytes = create_pdf_report(selected_drugs, detected_interactions, is_triple_whammy)
    st.download_button(
        label="📄 Vorbereitungsbogen für den Arztbesuch als PDF herunterladen",
        data=pdf_bytes,
        file_name="MediCheck_Arzt_Bericht.pdf",
        mime="application/pdf",
        use_container_width=True
    )

# --- 9. Detail-Ergebnisse & Interaktionskarten ---
st.subheader("Detaillierte Analyse der Wechselwirkungen")

if len(detected_interactions) > 0:
    for item in detected_interactions:
        d1, d2 = item["pair"]
        is_high = item["severity"] == "Hoch"
        badge_class = "badge-high" if is_high else "badge-medium"
        card_class = "high" if is_high else "medium"

        st.markdown(f"""
        <div class="interaction-card {card_class}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                <h4 style="margin: 0; color: #0f172a;">{d1} &nbsp;⚡&nbsp; {d2}</h4>
                <div>
                    <span class="status-badge {badge_class}">{item['severity']}es Risiko</span>
                    <span class="status-badge badge-organ">System: {item['system']}</span>
                </div>
            </div>
            <p style="margin: 6px 0; font-weight: 500; color: #334155;"><strong>Klinischer Effekt:</strong> {item['effect']}</p>
            <p style="margin: 6px 0 0 0; color: #64748b; font-size: 0.92rem;"><strong>Biologischer Mechanismus:</strong> {item['mechanism']}</p>
        </div>
        """, unsafe_allow_html=True)
elif len(selected_drugs) >= 2:
    st.info("Für die ausgewählten Medikamente wurden keine dokumentierten kritischen Wechselwirkungen in der Wissensdatenbank gefunden.")
else:
    st.write("Wählen Sie mindestens zwei Medikamente aus, um den Abgleich zu starten.")

# --- 10. Medizinischer Disclaimer ---
st.markdown("""
<div class="disclaimer-box">
    <strong>⚠️ Medizinischer Haftungsausschluss:</strong><br>
    Dieses Portal dient ausschließlich zu Demonstrations-, Informations- und Bildungszwecken. 
    Es stellt keine medizinische Diagnostik oder Therapieempfehlung dar und ersetzt keinesfalls die fachkundige Beratung durch einen Arzt oder Apotheker. 
    Veränderungen an bestehenden Verordnungen dürfen keinesfalls eigenmächtig vorgenommen werden.
</div>
""", unsafe_allow_html=True)