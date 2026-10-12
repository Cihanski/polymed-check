import os
import json
import itertools
import streamlit as st
import streamlit.components.v1 as components

from drug_translator import translate_to_inn
from bmp_parser import parse_medication_text
from pdf_generator import generate_full_clinical_pdf
from ai_pipeline import generate_clinical_summary
from cache_manager import (
    fetch_exact_cache,
    check_phyto_and_cation_rules,
    check_class_level_rules,
    check_multidrug_synergies,
    check_priscus_pim,
    check_renal_risks,
    generate_intake_schedule,
    generate_lab_monitoring_checklist,
    get_drug_pharmacology,
    fetch_fda_interaction
)

# --- Seitenkonfiguration ---
st.set_page_config(
    page_title="MediCheck | Interaktions-Radar",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS / Barrierefreies Dark Theme (Senioren- & B2B-tauglich) ---
st.markdown("""
<style>
    /* 1. Barrierefreie Typografie & Lesbarkeit */
    p, li, .stMarkdown {
        font-size: 1.05rem !important;
        line-height: 1.65 !important;
    }

    /* 2. Grosse, taktile Registerkarten (Tabs) */
    button[data-baseweb="tab"] {
        font-size: 1.15rem !important;
        font-weight: 700 !important;
        padding: 14px 26px !important;
        color: #cbd5e1 !important;
        border-radius: 10px 10px 0 0 !important;
        margin-right: 6px !important;
        background-color: #0f172a !important;
        border: 1px solid #334155 !important;
        border-bottom: none !important;
        transition: all 0.2s ease-in-out;
    }

    button[data-baseweb="tab"]:hover {
        color: #ffffff !important;
        background-color: #1e293b !important;
    }

    button[data-baseweb="tab"][aria-selected="true"] {
        color: #38bdf8 !important;
        background-color: #1e293b !important;
        border: 1px solid #38bdf8 !important;
        border-bottom: 3px solid #38bdf8 !important;
        box-shadow: 0 -2px 10px rgba(56, 189, 248, 0.15);
    }

    /* 3. WCAG-gerechte Buttons mit mindestens 48px Hoehe */
    .stButton > button {
        font-size: 1.05rem !important;
        font-weight: 700 !important;
        padding: 12px 22px !important;
        min-height: 48px !important;
        border-radius: 8px !important;
        transition: background 0.2s ease;
    }

    /* 4. Metrik-Kacheln */
    .metric-card {
        background-color: #0f172a !important;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3);
        color: #f1f5f9 !important;
    }
    .metric-title {
        margin: 0 0 6px 0; 
        color: #94a3b8 !important; 
        font-size: 0.92rem; 
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .metric-desc {
        margin: 6px 0 0 0; 
        color: #94a3b8 !important; 
        font-size: 0.88rem;
    }

    /* 5. Status-Badges mit hohem Kontrast */
    .status-badge {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 9999px;
        font-size: 0.88rem;
        font-weight: 700;
        margin-right: 8px;
        letter-spacing: 0.02em;
    }
    .badge-high {
        background-color: #7f1d1d !important;
        color: #fee2e2 !important;
        border: 1.5px solid #ef4444;
    }
    .badge-medium {
        background-color: #78350f !important;
        color: #fef3c7 !important;
        border: 1.5px solid #f59e0b;
    }
    .badge-organ {
        background-color: #0c4a6e !important;
        color: #e0f2fe !important;
        border: 1.5px solid #38bdf8;
    }
    .badge-db {
        background-color: #581c87 !important;
        color: #f3e8ff !important;
        border: 1.5px solid #c084fc;
    }
    .badge-class {
        background-color: #312e81 !important;
        color: #e0e7ff !important;
        border: 1.5px solid #818cf8;
    }

    /* 6. Risikokarten */
    .interaction-card {
        background-color: #0f172a !important;
        border-left: 6px solid #475569;
        border-radius: 10px;
        padding: 18px 22px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.25);
        border-top: 1px solid #1e293b;
        border-right: 1px solid #1e293b;
        border-bottom: 1px solid #1e293b;
        color: #f1f5f9 !important;
    }
    .interaction-card.high {
        border-left-color: #ef4444 !important;
    }
    .interaction-card.medium {
        border-left-color: #f59e0b !important;
    }
    .advice-box {
        background-color: #064e3b !important;
        border-left: 5px solid #34d399;
        border-radius: 6px;
        padding: 10px 16px;
        margin-top: 12px;
        font-size: 0.98rem;
        color: #d1fae5 !important;
        font-weight: 500;
    }
    .priscus-card {
        background-color: #422006 !important;
        border: 1.5px solid #ca8a04;
        border-left: 6px solid #facc15;
        border-radius: 10px;
        padding: 18px 22px;
        margin-bottom: 16px;
        color: #fef9c3 !important;
    }
    .renal-card {
        background-color: #431407 !important;
        border: 1.5px solid #ea580c;
        border-left: 6px solid #fb923c;
        border-radius: 10px;
        padding: 18px 22px;
        margin-bottom: 16px;
        color: #ffedd5 !important;
    }
    .schedule-card {
        background-color: #0f172a !important;
        border: 1.5px solid #1e3a8a;
        border-left: 6px solid #38bdf8;
        border-radius: 10px;
        padding: 18px 22px;
        margin-bottom: 16px;
        color: #f1f5f9 !important;
    }
    .monitoring-card {
        background-color: #082f49 !important;
        border: 1.5px solid #0284c7;
        border-left: 6px solid #38bdf8;
        border-radius: 10px;
        padding: 18px 22px;
        margin-bottom: 16px;
        color: #f0f9ff !important;
    }
    .synergy-card {
        background-color: #4c0519 !important;
        border: 1.5px solid #e11d48;
        border-left: 6px solid #fb7185;
        border-radius: 10px;
        padding: 18px 22px;
        margin-bottom: 16px;
        color: #ffe4e6 !important;
    }
    .disclaimer-banner {
        background-color: #0f172a !important;
        border-left: 5px solid #38bdf8;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 18px;
        color: #e0f2fe !important;
        font-size: 0.95rem;
    }
    .citation-note {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-top: 6px;
        font-style: italic;
    }
</style>
""", unsafe_allow_html=True)


def check_substance_pair(drug_a, drug_b):
    """Fuehrt alle Pruefstufen fuer ein Wirkstoffpaar aus."""
    res = fetch_exact_cache(drug_a, drug_b)
    if res:
        return res
    res = check_phyto_and_cation_rules(drug_a, drug_b)
    if res:
        return res
    res = check_class_level_rules(drug_a, drug_b)
    if res:
        return res
    res = fetch_fda_interaction(drug_a, drug_b)
    if res:
        return res
    return None


def render_interaction_network(active_substances, detected_interactions, synergies):
    """Erzeugt das standfest zentrierte 2-Spalten Split-Panel im barrierefreien Dark-Design."""
    nodes = []
    edges = []

    high_risk_drugs = set()
    mod_risk_drugs = set()

    for item in detected_interactions:
        d1, d2 = item["pair"]
        sev = item.get("severity", "Moderat")
        if sev == "Hoch":
            high_risk_drugs.add(d1)
            high_risk_drugs.add(d2)
        else:
            mod_risk_drugs.add(d1)
            mod_risk_drugs.add(d2)

    for syn in synergies:
        for d in syn.get("drugs", []):
            if syn.get("severity") == "Hoch":
                high_risk_drugs.add(d)
            else:
                mod_risk_drugs.add(d)

    for d in active_substances:
        clean_name = d.replace(" 🍊", "").replace(" 🥛", "").replace(" 🌿", "").replace(" 🩸", "").replace(" 🍬", "").replace(" 🍂", "").replace(" 🍃", "").replace(" 🧄", "").capitalize()
        pharm = get_drug_pharmacology(d)
        
        sub_class = "Wirkstoff"
        d_low = d.lower()
        if "ramipril" in d_low: sub_class = "ACE-Hemmer"
        elif "torasemid" in d_low or "furosemid" in d_low: sub_class = "Diuretikum"
        elif "ibuprofen" in d_low or "diclofenac" in d_low: sub_class = "NSAR"
        elif "simvastatin" in d_low: sub_class = "Statin"
        elif "metformin" in d_low: sub_class = "Biguanid"
        elif "ciprofloxacin" in d_low: sub_class = "Antibiotikum"
        elif "amiodaron" in d_low: sub_class = "Antiarrhythmikum"
        elif pharm and pharm.get("drug_class") and "WHO-ATC" not in pharm.get("drug_class"):
            sub_class = pharm["drug_class"][:14]

        if d in high_risk_drugs:
            bg_color = "#dc2626"
            border_color = "#f87171"
            glow_color = "rgba(220, 38, 38, 0.45)"
        elif d in mod_risk_drugs:
            bg_color = "#d97706"
            border_color = "#fbbf24"
            glow_color = "rgba(217, 119, 6, 0.45)"
        else:
            bg_color = "#059669"
            border_color = "#34d399"
            glow_color = "rgba(5, 150, 105, 0.35)"

        nodes.append({
            "id": d,
            "label": f"💊 {clean_name}\n({sub_class})",
            "shape": "box",
            "margin": {"top": 10, "bottom": 10, "left": 16, "right": 16},
            "borderRadius": 8,
            "color": {
                "background": bg_color,
                "border": border_color,
                "highlight": {"background": "#0284c7", "border": "#38bdf8"}
            },
            "font": {
                "color": "#ffffff",
                "size": 14,
                "face": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                "bold": True
            },
            "borderWidth": 2,
            "shadow": {"enabled": True, "color": glow_color, "size": 10, "x": 0, "y": 3}
        })

    edge_details_map = {}
    first_edge_id = None
    edge_idx = 0

    for item in detected_interactions:
        d1, d2 = item["pair"]
        sev = item.get("severity", "Moderat")
        is_high = sev == "Hoch"
        edge_id = f"edge_{edge_idx}"
        edge_idx += 1
        if first_edge_id is None:
            first_edge_id = edge_id

        edge_details_map[edge_id] = {
            "pair": f"{d1.capitalize()} + {d2.capitalize()}",
            "severity": sev,
            "system": item.get("system", "Allgemein"),
            "effect": item.get("effect", ""),
            "mechanism": item.get("mechanism", "")
        }

        edges.append({
            "id": edge_id,
            "from": d1,
            "to": d2,
            "color": {
                "color": "#ef4444" if is_high else "#f59e0b",
                "highlight": "#38bdf8"
            },
            "width": 3.8 if is_high else 2.8,
            "dashes": [6, 6] if not is_high else False,
            "smooth": {"type": "curvedCW", "roundness": 0.15}
        })

    drawn_pairs = set(tuple(sorted([item["pair"][0], item["pair"][1]])) for item in detected_interactions)
    for syn in synergies:
        syn_drugs = syn.get("drugs", [])
        if len(syn_drugs) >= 2:
            for s1, s2 in itertools.combinations(syn_drugs, 2):
                pair_key = tuple(sorted([s1, s2]))
                if pair_key not in drawn_pairs:
                    drawn_pairs.add(pair_key)
                    is_high = syn.get("severity") == "Hoch"
                    edge_id = f"edge_{edge_idx}"
                    edge_idx += 1
                    if first_edge_id is None:
                        first_edge_id = edge_id

                    edge_details_map[edge_id] = {
                        "pair": f"{s1.capitalize()} + {s2.capitalize()}",
                        "severity": syn.get("severity", "Hoch"),
                        "system": syn.get("type", "Synergie"),
                        "effect": syn.get("title", "") + ": " + syn.get("effect", ""),
                        "mechanism": syn.get("mechanism", "")
                    }

                    edges.append({
                        "id": edge_id,
                        "from": s1,
                        "to": s2,
                        "color": {
                            "color": "#ef4444" if is_high else "#f59e0b",
                            "highlight": "#38bdf8"
                        },
                        "width": 3.8 if is_high else 2.8,
                        "dashes": [4, 4] if not is_high else False,
                        "smooth": {"type": "curvedCW", "roundness": 0.2}
                    })

    nodes_json = json.dumps(nodes)
    edges_json = json.dumps(edges)
    edge_details_json = json.dumps(edge_details_map)
    default_edge_id = json.dumps(first_edge_id)
    has_conflicts = len(edges) > 0

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
      <style>
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          padding: 0;
          background-color: transparent;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
          user-select: none;
        }}
        #dashboard-split {{
          display: flex;
          gap: 16px;
          width: 100%;
          min-height: 430px;
        }}
        #radar-container {{
          flex: 1.5;
          display: flex;
          flex-direction: column;
          border: 1.5px solid #334155;
          border-radius: 12px;
          background-color: #090d16;
          box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
          overflow: hidden;
          position: relative;
        }}
        #network {{
          width: 100%;
          height: 380px;
          background-color: #090d16;
          background-image: 
            radial-gradient(circle at 50% 50%, rgba(30, 41, 59, 0.35) 0%, rgba(9, 13, 22, 1) 100%),
            linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
          background-size: 100% 100%, 28px 28px, 28px 28px;
        }}
        .legend-bar {{
          display: flex;
          justify-content: space-around;
          align-items: center;
          height: 48px;
          padding: 0 16px;
          background-color: #030712;
          border-top: 1px solid #1e293b;
          font-size: 13px;
          font-weight: 600;
          color: #e2e8f0;
        }}
        .dot {{
          width: 11px;
          height: 11px;
          border-radius: 50%;
          display: inline-block;
          margin-right: 8px;
        }}
        #detail-panel {{
          flex: 1.3;
          border: 1.5px solid #334155;
          border-radius: 12px;
          background: #0f172a;
          box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
          padding: 24px 26px;
          display: flex;
          flex-direction: column;
          justify-content: flex-start;
          min-height: 430px;
          overflow-y: auto;
        }}
        .panel-badge {{
          align-self: flex-start;
          font-size: 12px;
          font-weight: 700;
          padding: 5px 14px;
          border-radius: 9999px;
          text-transform: uppercase;
          margin-bottom: 12px;
          letter-spacing: 0.03em;
        }}
        .badge-red {{ background: #7f1d1d; color: #fee2e2; border: 1.5px solid #ef4444; }}
        .badge-yellow {{ background: #78350f; color: #fef3c7; border: 1.5px solid #f59e0b; }}
        .badge-green {{ background: #064e3b; color: #d1fae5; border: 1.5px solid #10b981; }}
        .badge-blue {{ background: #0c4a6e; color: #e0f2fe; border: 1.5px solid #0284c7; }}
        .panel-title {{
          font-size: 19px;
          font-weight: 700;
          color: #ffffff;
          margin: 0 0 10px 0;
          line-height: 1.35;
        }}
        .panel-desc {{
          font-size: 14.5px;
          line-height: 1.65;
          color: #f1f5f9;
          margin: 0 0 16px 0;
        }}
        .panel-hint {{
          font-size: 12.5px;
          color: #94a3b8;
          border-top: 1px solid #1e293b;
          padding-top: 12px;
          margin-top: auto;
        }}
      </style>
    </head>
    <body>
      <div id="dashboard-split">
        <div id="radar-container">
          <div id="network"></div>
          <div class="legend-bar">
            <span><span class="dot" style="background:#ef4444; box-shadow:0 0 8px #ef4444;"></span><strong>Hohes Risiko</strong></span>
            <span><span class="dot" style="background:#f59e0b; box-shadow:0 0 8px #f59e0b;"></span><strong>Moderates Risiko</strong></span>
            <span><span class="dot" style="background:#10b981; box-shadow:0 0 8px #10b981;"></span><strong>Kein Risiko</strong></span>
          </div>
        </div>

        <div id="detail-panel">
          <span id="p-badge" class="panel-badge {'badge-red' if has_conflicts else 'badge-green'}">{'Klinischer Konflikt erkannt' if has_conflicts else 'Unbedenkliche Kombination'}</span>
          <h3 id="p-title" class="panel-title">{'Interaktions-Radar' if has_conflicts else 'Keine dokumentierten Konflikte'}</h3>
          <p id="p-desc" class="panel-desc">{'Klicken Sie links auf eine Verbindungslinie oder ein Medikament, um den exakten Wirkungsmechanismus einzublenden.' if has_conflicts else 'In den geprueften Fachinformationen und Leitlinien sind zwischen den ausgewaehlten Wirkstoffen keine relevanten Interaktionen verzeichnet.'}</p>
          <div class="panel-hint">💡 <em>Knoten koennen barrierefrei mit der Maus verschoben werden.</em></div>
        </div>
      </div>

      <script type="text/javascript">
        var nodes = new vis.DataSet({nodes_json});
        var edges = new vis.DataSet({edges_json});
        var edgeMap = {edge_details_json};
        var defaultEdge = {default_edge_id};
        var hasConflicts = {'true' if has_conflicts else 'false'};

        var container = document.getElementById('network');
        var pBadge = document.getElementById('p-badge');
        var pTitle = document.getElementById('p-title');
        var pDesc = document.getElementById('p-desc');

        var data = {{ nodes: nodes, edges: edges }};
        var options = {{
          physics: {{
            enabled: true,
            stabilization: {{ iterations: 150, updateInterval: 25 }},
            barnesHut: {{
              gravitationalConstant: -3000,
              centralGravity: 0.8,
              springLength: 95,
              springConstant: 0.08,
              damping: 0.4,
              avoidOverlap: 1
            }}
          }},
          interaction: {{
            hover: true,
            zoomView: true,
            dragView: true,
            dragNodes: true
          }}
        }};

        var network = new vis.Network(container, data, options);

        network.once('stabilizationIterationsDone', function() {{
          network.setOptions({{ physics: false }});
          network.fit({{ animation: {{ duration: 400, easingFunction: 'easeInOutQuad' }} }});
          if (hasConflicts && defaultEdge && edgeMap[defaultEdge]) {{
            showEdgeDetails(edgeMap[defaultEdge]);
          }}
        }});

        function showEdgeDetails(detail) {{
          var isHigh = detail.severity === "Hoch";
          pBadge.className = "panel-badge " + (isHigh ? "badge-red" : "badge-yellow");
          pBadge.innerText = detail.severity + " • " + detail.system;
          pTitle.innerText = detail.pair;
          pDesc.innerText = detail.effect + (detail.mechanism ? " " + detail.mechanism : "");
        }}

        network.on("click", function(params) {{
          if (params.edges.length > 0) {{
            var edgeId = params.edges[0];
            var detail = edgeMap[edgeId];
            if (detail) {{
              showEdgeDetails(detail);
              return;
            }}
          }}
          if (params.nodes.length > 0) {{
            var nodeId = params.nodes[0];
            pBadge.className = "panel-badge badge-blue";
            pBadge.innerText = "Wirkstoff-Fokus";
            pTitle.innerText = nodeId.toUpperCase();
            pDesc.innerText = "Dieser Wirkstoff ist im Profil aktiv. Klicken Sie auf eine Verbindungslinie fuer detaillierte Wechselwirkungen.";
          }}
        }});
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=450)


# --- SIDEBAR: Parameter, Patientenprofil & BMP-Import ---
st.sidebar.title("⚙️ Klinische Parameter")

# 1. Fall-ID & Audit Trail
patient_id = st.sidebar.text_input("Patienten-ID / Fall-Kürzel (optional):", value="P-2026-001", help="Wird auf dem exportierten Arztbrief fuer das Praxissystem ausgewiesen.")

# 2. BMP / Freitext Import
with st.sidebar.expander("📋 Medikationsplan / Freitext importieren", expanded=False):
    import_text = st.text_area(
        "BMP-XML oder Textliste einfügen:",
        placeholder="Z. B.:\nRamipril 5mg 1-0-0\nMetformin 1000mg 1-0-1\nSimvastatin 40mg abends",
        height=95
    )
    if st.button("Substanzen übernehmen", use_container_width=True):
        if import_text:
            parsed_drugs = parse_medication_text(import_text)
            if parsed_drugs:
                current_selection = st.session_state.get("selected_drugs", [])
                updated = list(dict.fromkeys(current_selection + parsed_drugs))
                st.session_state["selected_drugs"] = updated
                st.success(f"{len(parsed_drugs)} Substanz(en) erkannt!")
                st.rerun()
            else:
                st.warning("Keine Wirkstoffe erkannt.")

# 3. Barrierefreie Zahleneingaben (Tastatur- & Button-tauglich statt Slider)
st.sidebar.markdown("### 👤 Vitalparameter & Labor")

patient_age = st.sidebar.number_input(
    "Alter des Patienten (Jahre):",
    min_value=18,
    max_value=115,
    value=72,
    step=1,
    help="Ab 65 Jahren greifen automatisch die PRISCUS 2.0 PIM-Kriterien fuer potenziell inadäquate Medikation."
)

egfr_value = st.sidebar.number_input(
    "Geschätzte eGFR (ml/min/1.73m²):",
    min_value=5,
    max_value=140,
    value=42,
    step=1,
    help="Kreatinin-basierte Nierenfiltrationsrate zur Dosisanpassung und Kontraindikations-Prüfung."
)

is_geriatric = patient_age >= 65
if is_geriatric:
    st.sidebar.warning("⚠️ Geriatrischer Patient (≥ 65 Jahre) – PRISCUS 2.0 Filter aktiv")

if egfr_value < 30:
    st.sidebar.error("🔴 Schwere Niereninsuffizienz (eGFR < 30 ml/min)")
elif egfr_value < 60:
    st.sidebar.warning("🟠 Moderate Niereninsuffizienz (eGFR 30–59 ml/min)")

# 4. Wirkstoffauswahl
st.sidebar.markdown("### 💊 Medikationsliste")
available_drugs_catalog = [
    "Ramipril", "Ibuprofen", "Torasemid", "Metformin", "Simvastatin", "Ciprofloxacin",
    "Pantoprazol", "Aspirin", "Amiodaron", "Diazepam", "Lorazepam", "Tilidin", "Tramadol",
    "Morphin", "Sertralin", "Citalopram", "Apixaban", "Rivaroxaban", "Clarithromycin",
    "Verapamil", "Digoxin", "Amitriptylin", "Oxybutynin", "Indometacin", "Metoclopramid",
    "L-Thyroxin", "Calcium", "Eisen", "Spironolacton", "Johanniskraut"
]

if "selected_drugs" not in st.session_state:
    st.session_state["selected_drugs"] = ["Ramipril", "Ibuprofen", "Torasemid"]

selected_drugs = st.sidebar.multiselect(
    "Aktive Wirkstoffe:",
    options=sorted(list(set(available_drugs_catalog + st.session_state["selected_drugs"]))),
    default=st.session_state["selected_drugs"]
)
st.session_state["selected_drugs"] = selected_drugs

# Rechtlicher Footer in der Sidebar
st.sidebar.markdown("---")
with st.sidebar.expander("⚖️ Rechtliches & Datenschutz"):
    st.markdown("""
    **Haftungsausschluss:** MediCheck ist ein rein wissenschaftliches Informations- und Entscheidungsunterstützungs-Werkzeug (Clinical Decision Support) für medizinisches Fachpersonal und kein zertifiziertes Medizinprodukt im Sinne der EU-MDR.
    
    **Datenschutz (DSGVO):** Es werden keinerlei personenbezogene Klarnamen oder Patientenakten serverseitig gespeichert.
    """)

# --- DATEN-VERARBEITUNG ---
active_substances = []
for d in selected_drugs:
    inn = translate_to_inn(d)
    if isinstance(inn, list):
        active_substances.extend(inn)
    elif inn:
        active_substances.append(inn)
    else:
        active_substances.append(d.lower())

active_substances = list(dict.fromkeys(active_substances))

detected_interactions = []
if len(active_substances) >= 2:
    for da, db in itertools.combinations(active_substances, 2):
        res = check_substance_pair(da, db)
        if res:
            detected_interactions.append(res)

synergies = check_multidrug_synergies(active_substances)
priscus_alerts = check_priscus_pim(active_substances) if is_geriatric else []
renal_alerts = check_renal_risks(active_substances, egfr_value)
schedule = generate_intake_schedule(active_substances)
lab_checklist = generate_lab_monitoring_checklist(active_substances, egfr_value)

# --- HEADER & KPI-DASHBOARD ---
st.title("💊 MediCheck | AMTS-Cockpit")
st.caption(f"Evidenzbasierte Polypharmazie-Analyse • Fall: **{patient_id}** • PRISCUS 2.0 • eGFR-Dosisanpassung • Chronopharmakologie")

high_count = sum(1 for i in detected_interactions if i.get("severity") == "Hoch") + sum(1 for s in synergies if s.get("severity") == "Hoch")
mod_count = sum(1 for i in detected_interactions if i.get("severity") == "Moderat")
pim_renal_total = len(priscus_alerts) + len(renal_alerts)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
with kpi1:
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-title">Geprüfte Substanzen</p>
        <h2 style="margin:0; font-size: 2.2rem; color:#38bdf8;">{len(active_substances)}</h2>
        <p class="metric-desc">Wirkstoffe aktiv</p>
    </div>
    """, unsafe_allow_html=True)
with kpi2:
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-title">Hohes Risiko</p>
        <h2 style="margin:0; font-size: 2.2rem; color:#ef4444;">{high_count}</h2>
        <p class="metric-desc">Kritische Konflikte</p>
    </div>
    """, unsafe_allow_html=True)
with kpi3:
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-title">Moderates Risiko</p>
        <h2 style="margin:0; font-size: 2.2rem; color:#f59e0b;">{mod_count}</h2>
        <p class="metric-desc">Kombinationshinweise</p>
    </div>
    """, unsafe_allow_html=True)
with kpi4:
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-title">PIM / Nierenwarnungen</p>
        <h2 style="margin:0; font-size: 2.2rem; color:#fb923c;">{pim_renal_total}</h2>
        <p class="metric-desc">Geriatrisch / eGFR</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- BARRIEREFREIE REITER-NAVIGATION ---
tab_radar, tab_risks, tab_plan, tab_export = st.tabs([
    "🕸️ 1. Interaktions-Radar & Triage",
    f"⚠️ 2. Klinische Risiken ({high_count + pim_renal_total})",
    "🧪 3. Labor & Einnahmeplan",
    "📥 4. Dossier & Export"
])

# ==================== TAB 1: RADAR & TRIAGE ====================
with tab_radar:
    with st.expander("🤖 Klinische Kurzsynthese (Arzt-Briefing)", expanded=True):
        col_btn, col_txt = st.columns([1, 3.5])
        with col_btn:
            generate_ai = st.button("Synthese erstellen", use_container_width=True)
        with col_txt:
            if generate_ai or "ai_narrative" in st.session_state:
                if generate_ai:
                    with st.spinner("Pharmakologische Gesamtsynthese wird erstellt..."):
                        st.session_state["ai_narrative"] = generate_clinical_summary(
                            patient_age=patient_age,
                            egfr_value=egfr_value,
                            active_substances=active_substances,
                            detected_interactions=detected_interactions,
                            synergies=synergies,
                            priscus_alerts=priscus_alerts,
                            renal_alerts=renal_alerts
                        )
                st.info(st.session_state.get("ai_narrative", ""))
            else:
                st.write("Generiert ein 3-sätziges klinisches Briefing zur Risikominimierung für das Arzt- oder Patientengespräch.")

    st.markdown("#### 🕸️ Interaktives Interaktions-Netzwerk")
    render_interaction_network(active_substances, detected_interactions, synergies)

    st.markdown("#### 📑 Dokumentierte Paar-Wechselwirkungen")
    if detected_interactions:
        for item in detected_interactions:
            d1, d2 = item["pair"]
            sev = item.get("severity", "Moderat")
            is_high = sev == "Hoch"
            card_class = "high" if is_high else "medium"
            badge_class = "badge-high" if is_high else "badge-medium"
            st.markdown(f"""
            <div class="interaction-card {card_class}">
                <span class="status-badge {badge_class}">{sev}</span>
                <span class="status-badge badge-organ">{item.get('system', 'Allgemein')}</span>
                <span class="status-badge badge-db">{item.get('source', 'Lokal verifiziert')}</span>
                <h3 style="margin:10px 0 6px 0; color:#fff; font-size: 1.25rem;">{d1.capitalize()} + {d2.capitalize()}</h3>
                <p style="margin:0 0 6px 0; font-size:1.02rem;">{item.get('effect', '')}</p>
                {f'<p style="margin:0 0 6px 0; font-size:0.92rem; color:#94a3b8;"><em>Mechanismus: {item["mechanism"]}</em></p>' if item.get("mechanism") else ''}
                {f'<div class="advice-box">💡 <strong>Handlungsempfehlung:</strong> {item["advice"]}</div>' if item.get("advice") else ''}
                <div class="citation-note">Evidenzquelle: Fachinformationen der Hersteller / openFDA Drug Interaction Reference</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("Keine paarweisen Wechselwirkungen zwischen den ausgewählten Wirkstoffen dokumentiert.")

# ==================== TAB 2: KLINISCHE RISIKEN ====================
with tab_risks:
    has_any_risk = bool(synergies or priscus_alerts or renal_alerts)

    if not has_any_risk:
        st.success("Keine akuten Multidrug-Synergien, PRISCUS-Kriterien oder Nierenrisiken identifiziert.")

    if synergies:
        st.markdown("#### ⚡ Multidrug-Synergien (Kombinatorische Risiken)")
        for syn in synergies:
            st.markdown(f"""
            <div class="synergy-card">
                <span class="status-badge badge-high">{syn['severity']}</span>
                <span class="status-badge badge-class">{syn['type']}</span>
                <h3 style="margin:10px 0 6px 0; color:#fff; font-size: 1.25rem;">{syn['title']}</h3>
                <p style="margin:0 0 4px 0;"><strong>Beteiligte Substanzen:</strong> {", ".join([s.capitalize() for s in syn['drugs']])}</p>
                <p style="margin:0 0 4px 0;">{syn['effect']}</p>
                <p style="margin:0; font-size:0.92rem; color:#fca5a5;"><em>Mechanismus: {syn['mechanism']}</em></p>
                <div class="citation-note">Leitlinie: AMTS-Konsensus & DKG-Leitlinie kardiovaskuläre Pharmakotherapie</div>
            </div>
            """, unsafe_allow_html=True)

    if priscus_alerts:
        st.markdown("#### 👵 PRISCUS 2.0 – Potenziell Inadäquate Medikation im Alter (PIM)")
        for pim in priscus_alerts:
            st.markdown(f"""
            <div class="priscus-card">
                <span class="status-badge badge-medium">PRISCUS 2.0 PIM</span>
                <h3 style="margin:10px 0 6px 0; color:#fef08a; font-size: 1.25rem;">{pim['drug'].capitalize()}</h3>
                <p style="margin:0 0 4px 0;"><strong>Risiko im Alter:</strong> {pim['risk']}</p>
                <p style="margin:0 0 4px 0;"><strong>Begründung:</strong> {pim['reason']}</p>
                <p style="margin:0; font-weight:700; color:#fde047;"><strong>Leitlinien-Alternative:</strong> {pim['alternative']}</p>
                <div class="citation-note">Quelle: PRISCUS 2.0 Leitlinie (BMBF-gefördert, 2023)</div>
            </div>
            """, unsafe_allow_html=True)

    if renal_alerts:
        st.markdown("#### 🫘 Nierenfunktions-Warnungen (eGFR-Dosisanpassung)")
        for ren in renal_alerts:
            st.markdown(f"""
            <div class="renal-card">
                <span class="status-badge badge-high">{ren['severity']}</span>
                <h3 style="margin:10px 0 6px 0; color:#fed7aa; font-size: 1.25rem;">{ren['title']}</h3>
                <p style="margin:0 0 4px 0;">{ren['message']}</p>
                <p style="margin:0; font-weight:700; color:#ffedd5;"><strong>Empfohlene Maßnahme:</strong> {ren['action']}</p>
                <div class="citation-note">Referenz: Dosing in Renal Disease (KDIGO Guidelines 2024)</div>
            </div>
            """, unsafe_allow_html=True)

# ==================== TAB 3: LABOR & EINNAHMEPLAN ====================
with tab_plan:
    col_lab, col_sched = st.columns([1, 1])

    with col_lab:
        st.markdown("#### 🧪 Leitliniengestützte Laborkontrollen")
        if lab_checklist:
            for lab in lab_checklist:
                is_urgent = lab["urgency"] == "Hoch"
                badge_class = "badge-high" if is_urgent else "badge-organ"
                st.markdown(f"""
                <div class="monitoring-card">
                    <span class="status-badge {badge_class}">{lab['urgency']}e Priorität</span>
                    <span class="status-badge badge-db">{lab['interval']}</span>
                    <h3 style="margin:10px 0 6px 0; color:#ffffff; font-size: 1.2rem;">🔬 {lab['parameter']}</h3>
                    <p style="margin:0 0 4px 0; font-size:0.95rem; color:#cbd5e1;"><strong>Auslöser:</strong> {', '.join(lab['triggers'])}</p>
                    <p style="margin:0; font-size:0.92rem; color:#94a3b8;"><strong>Begründung:</strong> {lab['reason']}</p>
                    <div class="citation-note">Leitlinie: Fachinformationen & AkdÄ-Monitoring-Empfehlungen</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Keine spezifischen Laborkontrollen für das aktuelle Wirkstoffprofil erforderlich.")

    with col_sched:
        st.markdown("#### ⏰ Chronopharmakologischer Einnahmeplan")
        if schedule:
            for slot, items in schedule.items():
                st.markdown(f"""
                <div class="schedule-card">
                    <h3 style="margin:0 0 8px 0; color:#38bdf8; font-size: 1.2rem;">🕒 {slot}</h3>
                    <ul style="margin:0; padding-left:20px;">
                        {''.join([f'<li style="margin-bottom:4px; font-size:0.98rem;">{it}</li>' for it in items])}
                    </ul>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("Keine Medikamente zur Zeitplan-Erstellung ausgewählt.")

# ==================== TAB 4: DOSSIER & EXPORT ====================
with tab_export:
    st.markdown("#### 📥 Klinischer Report & Medikationsdossier")
    st.write(f"Generieren Sie einen druckfertigen DIN-A4-Arztbrief für **Fall-ID {patient_id}** zur Übernahme in Ihr Praxis- oder Apothekenverwaltungssystem.")

    col_btn_pdf, col_btn_txt = st.columns(2)

    with col_btn_pdf:
        try:
            pdf_bytes = generate_full_clinical_pdf(
                patient_age=patient_age,
                egfr_value=egfr_value,
                active_substances=active_substances,
                detected_interactions=detected_interactions,
                synergies=synergies,
                priscus_alerts=priscus_alerts,
                renal_alerts=renal_alerts,
                schedule=schedule,
                lab_checklist=lab_checklist
            )
            st.download_button(
                label="📄 PDF-Arztbrief herunterladen (DIN-A4)",
                data=pdf_bytes,
                file_name=f"medicheck_befund_{patient_id}_{patient_age}J_eGFR{egfr_value}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"PDF-Generierungsfehler: {e}")

    with col_btn_txt:
        summary_text = (
            f"MediCheck AMTS-Befund\n"
            f"Fall-ID: {patient_id} | Patient: {patient_age} Jahre | eGFR: {egfr_value} ml/min\n"
            f"Wirkstoffe ({len(active_substances)}): {', '.join([s.capitalize() for s in active_substances])}\n"
            f"Interaktionen: {len(detected_interactions)} | Synergien: {len(synergies)} | PIM: {len(priscus_alerts)}\n\n"
            f"Befundübersicht:\n"
            + "\n".join([f"- [{i.get('severity')}] {i['pair'][0].capitalize()} + {i['pair'][1].capitalize()}: {i.get('effect')}" for i in detected_interactions])
        )
        st.download_button(
            label="📋 Text-Befund in Zwischenablage exportieren",
            data=summary_text,
            file_name=f"medicheck_{patient_id}.txt",
            mime="text/plain",
            use_container_width=True
        )

st.markdown("""
<div class="disclaimer-box">
    <strong>Haftungsausschluss & Medizinischer Hinweis:</strong> MediCheck dient der softwaregestützten Entscheidungsunterstützung (Clinical Decision Support) für medizinisches Fachpersonal und ersetzt keine ärztliche oder apothekerliche Begutachtung. Alle Angaben ohne Gewähr.
</div>
""", unsafe_allow_html=True)