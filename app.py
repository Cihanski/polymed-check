import streamlit as st
from itertools import combinations

# --- 1. Seitenkonfiguration & Custom Styling ---
st.set_page_config(
    page_title="Polymedikations- & Interaktions-Check",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Modernes CSS für Kärtchen, Badges und saubere Typografie
st.markdown("""
<style>
    .main {
        background-color: #f8fafc;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .metric-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 0.85rem;
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
        background: white;
        border-left: 5px solid #cbd5e1;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
    }
    .interaction-card.high {
        border-left-color: #ef4444;
    }
    .interaction-card.medium {
        border-left-color: #f59e0b;
    }
    .disclaimer-box {
        background-color: #f1f5f9;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        padding: 14px;
        font-size: 0.85rem;
        color: #475569;
        margin-top: 30px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Wissensdatenbank (Wirkstoffe & Paarkonflikte) ---
DRUGS_DB = {
    "Ibuprofen": {"klasse": "NSAR (Schmerzmittel / Entzündungshemmer)"},
    "Ramipril": {"klasse": "ACE-Hemmer (Blutdrucksenker)"},
    "Metformin": {"klasse": "Biguanid (Antidiabetikum)"},
    "ASS (Acetylsalicylsäure)": {"klasse": "Thrombozytenaggregationshemmer (Blutverdünner)"},
    "Simvastatin": {"klasse": "Statin (Cholesterinsenker)"},
    "Ginkgo Biloba": {"klasse": "Pflanzliches Präparat / Durchblutungsförderer"}
}

INTERACTIONS_DB = {
    frozenset(["Ibuprofen", "Ramipril"]): {
        "severity": "Hoch",
        "system": "Nierenfunktion & Blutdruck",
        "effect": "Abschwächung der Blutdrucksenkung & akute Nierenfunktionsstörung.",
        "mechanism": "Ramipril erweitert die ableitenden Blutgefäße der Niere, während Ibuprofen die zuleitenden Gefäße verengt (Prostaglandin-Hemmung). Dies kann zu einem plötzlichen Abfall des Filtrationsdrucks in den Nieren führen."
    },
    frozenset(["Ibuprofen", "ASS (Acetylsalicylsäure)"]): {
        "severity": "Hoch",
        "system": "Magen-Darm-Trakt & Hämostase",
        "effect": "Massiv erhöhtes Risiko für Magengeschwüre und Magen-Darm-Blutungen.",
        "mechanism": "Beide Wirkstoffe greifen die schützende Magenschleimhaut an und blockieren gleichzeitig die Blutgerinnungsplättchen additiv."
    },
    frozenset(["ASS (Acetylsalicylsäure)", "Ginkgo Biloba"]): {
        "severity": "Moderat",
        "system": "Hämostase (Blutgerinnung)",
        "effect": "Erhöhte Neigung zu Hämatomen, Nasenbluten und postoperativen Blutungen.",
        "mechanism": "Ginkgo-Extrakte enthalten Ginkgolide, die den PAF (Plättchenaktivierungsfaktor) inhibieren, was den thrombozytenhemmenden Effekt von ASS verstärkt."
    },
    frozenset(["Ramipril", "Metformin"]): {
        "severity": "Moderat",
        "system": "Blutzucker-Regulation",
        "effect": "Gefahr unbemerkter Unterzuckerungen (Hypoglykämien).",
        "mechanism": "ACE-Hemmer können die Insulinsensitivität des Gewebes erhöhen, wodurch die blutzuckersenkende Wirkung von Metformin unerwartet stark ausfällt."
    },
    frozenset(["Ibuprofen", "Metformin"]): {
        "severity": "Moderat",
        "system": "Laktat-Stoffwechsel & Niere",
        "effect": "Gefahr einer Laktatazidose bei Nierenbelastung.",
        "mechanism": "Eine temporäre Einschränkung der Nierenfunktion durch Ibuprofen verringert die renale Ausscheidung von Metformin, was die Anreicherung im Körper begünstigt."
    }
}

# --- 3. App-Header & Einführung ---
st.title("💊 Polymedikations- & Interaktions-Check")
st.markdown("Analysieren Sie Mehrfachmedikationen auf pharmakologische Kreuzreaktionen und Organsystem-Belastungen.")

# --- 4. Interaktive Medikamentenauswahl ---
selected_drugs = st.multiselect(
    label="Wählen Sie die gleichzeitig eingenommenen Wirkstoffe aus:",
    options=list(DRUGS_DB.keys()),
    default=["Ibuprofen", "Ramipril"],
    help="Tippen oder wählen Sie mehrere Medikamente aus der Liste."
)

# --- 5. Analyse-Logik ---
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

# --- 6. Gesamt-Risiko Score (Ampel) ---
has_high = any(item["severity"] == "Hoch" for item in detected_interactions)
has_medium = any(item["severity"] == "Moderat" for item in detected_interactions)

col1, col2, col3 = st.columns([1.2, 1, 1])

with col1:
    if len(selected_drugs) < 2:
        status_color = "#64748b"
        status_text = "Mindestens 2 Wirkstoffe wählen"
        status_desc = "Fügen Sie Medikamente hinzu, um Wechselwirkungen zu scannen."
    elif has_high:
        status_color = "#dc2626"
        status_text = "🔴 Hohes Interaktionsrisiko"
        status_desc = "Kritische pharmakologische Konflikte gefunden. Ärztliche Rücksprache dringend erforderlich."
    elif has_medium:
        status_color = "#d97706"
        status_text = "🟡 Überwachung empfohlen"
        status_desc = "Bekannte Wechselwirkungen erfordern Dosisanpassung oder Symptom-Monitoring."
    else:
        status_color = "#16a34a"
        status_text = "🟢 Keine bekannten kritischen Konflikte"
        status_desc = "In dieser Konstellation wurden keine schweren Wechselwirkungen gefunden."

    st.markdown(f"""
    <div class="metric-card" style="border-top: 4px solid {status_color};">
        <h4 style="margin:0 0 8px 0; color: #1e293b;">Gesamt-Risiko-Status</h4>
        <h3 style="margin:0; color: {status_color};">{status_text}</h3>
        <p style="margin: 8px 0 0 0; color: #64748b; font-size: 0.9rem;">{status_desc}</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <h4 style="margin:0 0 8px 0; color: #1e293b;">Ausgewählte Wirkstoffe</h4>
        <h2 style="margin:0; color: #0284c7;">{len(selected_drugs)}</h2>
        <p style="margin: 8px 0 0 0; color: #64748b; font-size: 0.9rem;">Aktive Substanzen im Panel</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <h4 style="margin:0 0 8px 0; color: #1e293b;">Gefundene Interaktionen</h4>
        <h2 style="margin:0; color: {'#dc2626' if len(detected_interactions) > 0 else '#16a34a'};">{len(detected_interactions)}</h2>
        <p style="margin: 8px 0 0 0; color: #64748b; font-size: 0.9rem;">Paarweise Konflikte erkannt</p>
    </div>
    """, unsafe_allow_html=True)

# --- 7. Detail-Ergebnisse & Interaktionskarten ---
st.subheader("Detaillierte Interaktions-Übersicht")

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
    st.info("Für die ausgewählte Wirkstoffkombination wurden in der hinterlegten Datenbank keine Interaktionen identifiziert.")
else:
    st.write("Wählen Sie mindestens zwei Wirkstoffe aus, um den Abgleich zu starten.")

# --- 8. Medizinischer Disclaimer ---
st.markdown("""
<div class="disclaimer-box">
    <strong>⚠️ Medizinischer Haftungsausschluss:</strong><br>
    Dieses Programm dient ausschließlich zu Demonstrations-, Ausbildungs- und Informationszwecken. 
    Es ersetzt unter keinen Umständen die professionelle Beratung, Diagnose oder Behandlung durch einen approbierten Arzt oder Apotheker. 
    Setzen Sie verordnete Medikamente niemals eigenmächtig ab oder ändern Sie eigenständig die Dosierung.
</div>
""", unsafe_allow_html=True)