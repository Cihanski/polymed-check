import os
import json
import itertools
from ai_pipeline import generate_clinical_summary
import streamlit as st
import streamlit.components.v1 as components
from fpdf import FPDF

from pdf_generator import generate_full_clinical_pdf
from drug_translator import translate_to_inn
from bmp_parser import parse_medication_text
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

# --- CSS / Dark Mode Theme Overrides ---
st.markdown("""
<style>
    /* Globales Dark Theme */
    .metric-card {
        background-color: #0f172a !important;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #1e293b;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.3);
        margin-bottom: 20px;
        color: #f1f5f9 !important;
    }
    .metric-title {
        margin: 0 0 8px 0; 
        color: #94a3b8 !important; 
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
        background-color: #450a0a !important;
        color: #fca5a5 !important;
        border: 1px solid #991b1b;
    }
    .badge-medium {
        background-color: #451a03 !important;
        color: #fcd34d !important;
        border: 1px solid #b45309;
    }
    .badge-organ {
        background-color: #082f49 !important;
        color: #7dd3fc !important;
        border: 1px solid #0369a1;
    }
    .badge-db {
        background-color: #3b0764 !important;
        color: #d8b4fe !important;
        border: 1px solid #7e22ce;
    }
    .badge-class {
        background-color: #1e1b4b !important;
        color: #a5b4fc !important;
        border: 1px solid #4338ca;
    }
    .badge-phyto {
        background-color: #052e16 !important;
        color: #86efac !important;
        border: 1px solid #15803d;
    }
    .badge-fda {
        background-color: #064e3b !important;
        color: #6ee7b7 !important;
        border: 1px solid #047857;
    }
    .interaction-card {
        background-color: #0f172a !important;
        border-left: 5px solid #475569;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
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
        background-color: #022c22 !important;
        border-left: 4px solid #10b981;
        border-radius: 4px;
        padding: 8px 12px;
        margin-top: 8px;
        font-size: 0.90rem;
        color: #a7f3d0 !important;
    }
    .combo-box {
        background-color: #0f172a !important;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 16px;
        font-size: 0.90rem;
        color: #cbd5e1 !important;
    }
    .profile-card {
        background-color: #0f172a !important;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 14px 18px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        color: #f1f5f9 !important;
    }
    .priscus-card {
        background-color: #422006 !important;
        border: 1px solid #854d0e;
        border-left: 6px solid #eab308;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 16px;
        color: #fef08a !important;
    }
    .renal-card {
        background-color: #431407 !important;
        border: 1px solid #9a3412;
        border-left: 6px solid #f97316;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 16px;
        color: #fed7aa !important;
    }
    .schedule-card {
        background-color: #0f172a !important;
        border: 1px solid #1e293b;
        border-left: 6px solid #3b82f6;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 16px;
        color: #f1f5f9 !important;
    }
    .monitoring-card {
        background-color: #082f49 !important;
        border: 1px solid #0369a1;
        border-left: 6px solid #38bdf8;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 20px;
        color: #e0f2fe !important;
    }
    .synergy-card {
        background-color: #4c0519 !important;
        border: 1px solid #9f1239;
        border-left: 6px solid #f43f5e;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 16px;
        color: #ffe4e6 !important;
    }
    .disclaimer-banner {
        background-color: #0f172a !important;
        border-left: 4px solid #38bdf8;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 20px;
        color: #bae6fd !important;
        font-size: 0.9rem;
    }
    .disclaimer-box {
        background-color: #0b0f19 !important;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 16px;
        font-size: 0.88rem;
        color: #64748b !important;
        margin-top: 30px;
    }
</style>
""", unsafe_allow_html=True)


def check_substance_pair(drug_a, drug_b):
    """Fuehrt alle Pruefstufen fuer ein Wirkstoffpaar aus."""
    # 1. SQLite Exakt
    res = fetch_exact_cache(drug_a, drug_b)
    if res:
        return res

    # 2. Kation / Phyto
    res = check_phyto_and_cation_rules(drug_a, drug_b)
    if res:
        return res

    # 3. ATC-Klassenregeln
    res = check_class_level_rules(drug_a, drug_b)
    if res:
        return res

    # 4. openFDA Fallback
    res = fetch_fda_interaction(drug_a, drug_b)
    if res:
        return res

    return None


def render_interaction_network(active_substances, detected_interactions, synergies):
    """Erzeugt ein standfest zentriertes 2-Spalten Split-Panel im Dark-Design."""
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
            "margin": {"top": 8, "bottom": 8, "left": 14, "right": 14},
            "borderRadius": 8,
            "color": {
                "background": bg_color,
                "border": border_color,
                "highlight": {"background": "#0284c7", "border": "#38bdf8"}
            },
            "font": {
                "color": "#ffffff",
                "size": 13,
                "face": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                "bold": True
            },
            "borderWidth": 2,
            "shadow": {"enabled": True, "color": glow_color, "size": 10, "x": 0, "y": 3}
        })

    edge_details_map = {}
    first_edge_id = None
    for idx, item in enumerate(detected_interactions):
        d1, d2 = item["pair"]
        sev = item.get("severity", "Moderat")
        is_high = sev == "Hoch"
        edge_id = f"edge_{idx}"
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
            "width": 3.5 if is_high else 2.5,
            "dashes": [6, 6] if not is_high else False,
            "smooth": {"type": "curvedCW", "roundness": 0.15}
        })

    nodes_json = json.dumps(nodes)
    edges_json = json.dumps(edges)
    edge_details_json = json.dumps(edge_details_map)
    default_edge_id = json.dumps(first_edge_id)
    has_conflicts = len(detected_interactions) > 0

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
          min-height: 420px;
        }}
        #radar-container {{
          flex: 1.5;
          display: flex;
          flex-direction: column;
          border: 1px solid #1e293b;
          border-radius: 12px;
          background-color: #090d16;
          box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
          overflow: hidden;
          position: relative;
        }}
        #network {{
          width: 100%;
          height: 365px;
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
          height: 45px;
          padding: 0 16px;
          background-color: #030712;
          border-top: 1px solid #1e293b;
          font-size: 12px;
          color: #cbd5e1;
        }}
        .dot {{
          width: 10px;
          height: 10px;
          border-radius: 50%;
          display: inline-block;
          margin-right: 6px;
        }}
        #detail-panel {{
          flex: 1.3;
          border: 1px solid #334155;
          border-radius: 12px;
          background: #0f172a;
          box-shadow: 0 10px 25px rgba(0, 0, 0, 0.4);
          padding: 22px 24px;
          display: flex;
          flex-direction: column;
          justify-content: flex-start;
          min-height: 420px;
          overflow-y: auto;
        }}
        .panel-badge {{
          align-self: flex-start;
          font-size: 11px;
          font-weight: 700;
          padding: 4px 12px;
          border-radius: 9999px;
          text-transform: uppercase;
          margin-bottom: 12px;
        }}
        .badge-red {{ background: #7f1d1d; color: #fecaca; border: 1px solid #ef4444; }}
        .badge-yellow {{ background: #78350f; color: #fef3c7; border: 1px solid #f59e0b; }}
        .badge-green {{ background: #064e3b; color: #a7f3d0; border: 1px solid #10b981; }}
        .badge-blue {{ background: #0c4a6e; color: #bae6fd; border: 1px solid #0284c7; }}
        .panel-title {{
          font-size: 18px;
          font-weight: 700;
          color: #ffffff;
          margin: 0 0 10px 0;
          line-height: 1.3;
        }}
        .panel-desc {{
          font-size: 13.5px;
          line-height: 1.6;
          color: #e2e8f0;
          margin: 0 0 16px 0;
        }}
        .panel-hint {{
          font-size: 12px;
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
            <span><span class="dot" style="background:#ef4444; box-shadow:0 0 6px #ef4444;"></span><strong>Hohes Risiko</strong></span>
            <span><span class="dot" style="background:#f59e0b; box-shadow:0 0 6px #f59e0b;"></span><strong>Moderates Risiko</strong></span>
            <span><span class="dot" style="background:#10b981; box-shadow:0 0 6px #10b981;"></span><strong>Kein Risiko</strong></span>
          </div>
        </div>

        <div id="detail-panel">
          <span id="p-badge" class="panel-badge {'badge-blue' if has_conflicts else 'badge-green'}">{'Klinische Inspektion' if has_conflicts else 'Unbedenkliche Kombination'}</span>
          <h3 id="p-title" class="panel-title">{'Interaktions-Radar' if has_conflicts else 'Keine dokumentierten Konflikte'}</h3>
          <p id="p-desc" class="panel-desc">{'Klicken Sie links auf eine Linie oder ein Medikament, um den genauen Wirkungsmechanismus und Organ-Konflikt einzublenden.' if has_conflicts else 'In den geprüften Fachinformationen und Datenbanken sind zwischen den ausgewählten Wirkstoffen keine relevanten Interaktionen verzeichnet. Die Kombination gilt als verträglich.'}</p>
          <div class="panel-hint">💡 <em>Knoten sind standfest zentriert und können interaktiv verschoben werden.</em></div>
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
            stabilization: {{
              enabled: true,
              iterations: 150,
              updateInterval: 25
            }},
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

        // Standfest-Logik: Physik nach Stabilisierung anhalten & zentrieren
        network.once('stabilizationIterationsDone', function() {{
          network.setOptions({{ physics: false }});
          network.fit({{
            animation: {{
              duration: 400,
              easingFunction: 'easeInOutQuad'
            }}
          }});
          
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
            pDesc.innerText = "Dieser Wirkstoff ist im Netzwerk aktiv. Klicken Sie auf eine Verbindungslinie für detaillierte Wechselwirkungen.";
          }}
        }});
      </script>
    </body>
    </html>
    """
    components.html(html_code, height=450)


# --- SIDEBAR: Filter, Patientenprofil & BMP-Import ---
st.sidebar.title("⚙️ Klinische Parameter")

# 1. BMP / Freitext Import
with st.sidebar.expander("📋 Medikationsplan / Freitext importieren", expanded=False):
    import_text = st.text_area(
        "BMP-XML oder Textliste einfügen:",
        placeholder="Z. B.:\nRamipril 5mg 1-0-0\nMetformin 1000mg 1-0-1\nSimvastatin 40mg abends",
        height=100
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
                st.warning("Keine Wirkstoffe im eingegebenen Text erkannt.")

# 2. Patientenprofil
st.sidebar.markdown("### 👤 Patientenprofil")
patient_age = st.sidebar.slider("Alter des Patienten (Jahre):", min_value=18, max_value=100, value=72, step=1)
egfr_value = st.sidebar.slider("Geschätzte eGFR (ml/min/1.73m²):", min_value=10, max_value=120, value=42, step=1)

is_geriatric = patient_age >= 65
if is_geriatric:
    st.sidebar.warning("⚠️ Geriatrischer Patient (≥ 65 Jahre) – PRISCUS 2.0 PIM-Filter aktiv")

if egfr_value < 30:
    st.sidebar.error("🔴 Schwere Niereninsuffizienz (eGFR < 30 ml/min)")
elif egfr_value < 60:
    st.sidebar.warning("🟠 Moderate Niereninsuffizienz (eGFR 30–59 ml/min)")

# 3. Wirkstoffauswahl
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

# --- HAUPTANSICHT ---
st.title("💊 MediCheck")
st.caption("Evidenzbasierte Polypharmazie-Analyse • PRISCUS 2.0 • eGFR-Dosisanpassung • Chronopharmakologie")

st.markdown("""
<div class="disclaimer-banner">
    🛡️ <strong>Klinischer Leitfaden:</strong> Vollautomatische Triagierung von 1:1-Substanzpaaren, ATC-Klassenkonflikten, PRISCUS 2.0 PIM-Kriterien und pharmakodynamischen Multidrug-Synergien.
</div>
""", unsafe_allow_html=True)

# Substanzen normalisieren und Fixkombinationen auflösen
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

# Interaktionen ermitteln
detected_interactions = []
if len(active_substances) >= 2:
    for da, db in itertools.combinations(active_substances, 2):
        res = check_substance_pair(da, db)
        if res:
            detected_interactions.append(res)

# Synergien, Priscus, Nierenrisiken & Labor-Monitoring
synergies = check_multidrug_synergies(active_substances)
priscus_alerts = check_priscus_pim(active_substances) if is_geriatric else []
renal_alerts = check_renal_risks(active_substances, egfr_value)
schedule = generate_intake_schedule(active_substances)
lab_checklist = generate_lab_monitoring_checklist(active_substances, egfr_value)

# --- KPI-Kacheln ---
col1, col2, col3, col4 = st.columns(4)
high_count = sum(1 for i in detected_interactions if i.get("severity") == "Hoch") + sum(1 for s in synergies if s.get("severity") == "Hoch")
mod_count = sum(1 for i in detected_interactions if i.get("severity") == "Moderat")

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-title">Geprüfte Substanzen</p>
        <h2 style="margin:0; color:#38bdf8;">{len(active_substances)}</h2>
        <p class="metric-desc">Wirkstoffe aktiv</p>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-title">Hohes Risiko</p>
        <h2 style="margin:0; color:#ef4444;">{high_count}</h2>
        <p class="metric-desc">Kritische Konflikte</p>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-title">Moderates Risiko</p>
        <h2 style="margin:0; color:#f59e0b;">{mod_count}</h2>
        <p class="metric-desc">Kombinationshinweise</p>
    </div>
    """, unsafe_allow_html=True)

with col4:
    pim_renal_total = len(priscus_alerts) + len(renal_alerts)
    st.markdown(f"""
    <div class="metric-card">
        <p class="metric-title">PIM / Nierenwarnungen</p>
        <h2 style="margin:0; color:#fb923c;">{pim_renal_total}</h2>
        <p class="metric-desc">Geriatrisch / eGFR</p>
    </div>
    """, unsafe_allow_html=True)

# --- KI-KLINISCHE KURZSYNTHESE ---
with st.expander("🤖 KI-Klinische Kurzsynthese (Arzt-Briefing)", expanded=True):
    col_ai_btn, col_ai_txt = st.columns([1, 4])
    with col_ai_btn:
        generate_ai = st.button("Synthese erstellen", use_container_width=True)
    with col_ai_txt:
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
            st.caption("Klicken Sie auf 'Synthese erstellen', um eine 3-sätzige strukturierte Risikobewertung für den Visitenbericht zu generieren.")

# --- VIS.JS RADAR PANEL ---
st.markdown("### 🕸️ Interaktives Interaktions-Radar")
render_interaction_network(active_substances, detected_interactions, synergies)

st.markdown("---")

# --- MULTIDRUG-SYNERGIEN ---
if synergies:
    st.markdown("### ⚡ Multidrug-Synergien (Kombinatorische Risiken)")
    for syn in synergies:
        st.markdown(f"""
        <div class="synergy-card">
            <span class="status-badge badge-high">{syn['severity']}</span>
            <span class="status-badge badge-class">{syn['type']}</span>
            <h4 style="margin:10px 0 6px 0; color:#fff;">{syn['title']}</h4>
            <p style="margin:0 0 6px 0;"><strong>Beteiligte Substanzen:</strong> {", ".join([s.capitalize() for s in syn['drugs']])}</p>
            <p style="margin:0 0 6px 0;">{syn['effect']}</p>
            <p style="margin:0; font-size:0.88rem; color:#fca5a5;"><em>Mechanismus: {syn['mechanism']}</em></p>
        </div>
        """, unsafe_allow_html=True)

# --- PRISCUS 2.0 ALERTS ---
if priscus_alerts:
    st.markdown("### 👵 PRISCUS 2.0 – Potenziell Inadäquate Medikation (PIM)")
    for pim in priscus_alerts:
        st.markdown(f"""
        <div class="priscus-card">
            <span class="status-badge badge-medium">PRISCUS 2.0 PIM</span>
            <h4 style="margin:10px 0 6px 0; color:#fef08a;">{pim['drug'].capitalize()}</h4>
            <p style="margin:0 0 6px 0;"><strong>Risiko im Alter:</strong> {pim['risk']}</p>
            <p style="margin:0 0 6px 0;"><strong>Begründung:</strong> {pim['reason']}</p>
            <p style="margin:0; color:#fde047;"><strong>Leitlinien-Alternative:</strong> {pim['alternative']}</p>
        </div>
        """, unsafe_allow_html=True)

# --- NIERENRISIKEN (eGFR) ---
if renal_alerts:
    st.markdown("### 🫘 Nierenfunktions-Warnungen (eGFR-Dosisanpassung)")
    for ren in renal_alerts:
        st.markdown(f"""
        <div class="renal-card">
            <span class="status-badge badge-high">{ren['severity']}</span>
            <h4 style="margin:10px 0 6px 0; color:#fed7aa;">{ren['title']}</h4>
            <p style="margin:0 0 6px 0;">{ren['message']}</p>
            <p style="margin:0; color:#ffedd5;"><strong>Empfohlene Maßnahme:</strong> {ren['action']}</p>
        </div>
        """, unsafe_allow_html=True)

# --- PAARWEISE INTERAKTIONEN ---
st.markdown("### 📑 Dokumentierte Paar-Wechselwirkungen")
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
            <h4 style="margin:10px 0 6px 0; color:#fff;">{d1.capitalize()} + {d2.capitalize()}</h4>
            <p style="margin:0 0 8px 0; font-size:0.95rem;">{item.get('effect', '')}</p>
            {f'<p style="margin:0 0 8px 0; font-size:0.88rem; color:#94a3b8;"><em>Mechanismus: {item["mechanism"]}</em></p>' if item.get("mechanism") else ''}
            {f'<div class="advice-box">💡 <strong>Handlungsempfehlung:</strong> {item["advice"]}</div>' if item.get("advice") else ''}
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("Keine paarweisen Wechselwirkungen zwischen den ausgewählten Wirkstoffen dokumentiert.")

# --- LABORMONITORING CHECKLISTE ---
if lab_checklist:
    st.markdown("### 🧪 Leitliniengestützte Labormonitoring-Empfehlungen")
    for lab in lab_checklist:
        is_urgent = lab["urgency"] == "Hoch"
        badge_class = "badge-high" if is_urgent else "badge-organ"
        st.markdown(f"""
        <div class="monitoring-card">
            <span class="status-badge {badge_class}">{lab['urgency']}e Priorität</span>
            <span class="status-badge badge-db">Intervall: {lab['interval']}</span>
            <h4 style="margin:8px 0 6px 0; color:#ffffff;">🔬 {lab['parameter']}</h4>
            <p style="margin:0 0 6px 0; font-size:0.92rem; color:#cbd5e1;"><strong>Indikation / Auslöser:</strong> {', '.join(lab['triggers'])}</p>
            <p style="margin:0; font-size:0.90rem; color:#94a3b8;"><strong>Klinische Begründung:</strong> {lab['reason']}</p>
        </div>
        """, unsafe_allow_html=True)

# --- CHRONOPHARMAKOLOGISCHER EINNAHMEPLAN ---
st.markdown("### ⏰ Chronopharmakologischer Einnahmezeitplan")
if schedule:
    for slot, items in schedule.items():
        st.markdown(f"""
        <div class="schedule-card">
            <h4 style="margin:0 0 8px 0; color:#38bdf8;">🕒 {slot}</h4>
            <ul style="margin:0; padding-left:20px;">
                {''.join([f'<li style="margin-bottom:4px;">{it}</li>' for it in items])}
            </ul>
        </div>
        """, unsafe_allow_html=True)
else:
    st.write("Keine Medikamente zur Zeitplan-Erstellung ausgewählt.")

# --- EXPORT & REPORTING ---
st.markdown("---")
st.markdown("### 📥 Medikationsdossier & Export")


def generate_pdf_report():
    return generate_full_clinical_pdf(
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


col_exp1, col_exp2 = st.columns(2)
with col_exp1:
    try:
        pdf_bytes = generate_pdf_report()
        st.download_button(
            label="📄 PDF-Arztbrief herunterladen",
            data=bytes(pdf_bytes),
            file_name="medicheck_interaktionsbericht.pdf",
            mime="application/pdf",
            use_container_width=True
        )
    except Exception as e:
        st.warning(f"PDF-Generierung vorübergehend nicht verfügbar: {e}")

with col_exp2:
    summary_text = f"MediCheck Befund:\nPatient: {patient_age} J., eGFR: {egfr_value}\nSubstanzen: {', '.join(active_substances)}\nInteraktionen: {len(detected_interactions)}\nSynergien: {len(synergies)}\nPIM: {len(priscus_alerts)}"
    st.download_button(
        label="📋 Text-Zusammenfassung kopieren",
        data=summary_text,
        file_name="medicheck_befund.txt",
        mime="text/plain",
        use_container_width=True
    )

st.markdown("""
<div class="disclaimer-box">
    <strong>Haftungsausschluss & Medizinischer Hinweis:</strong> MediCheck dient der softwaregestützten Entscheidungsunterstützung (Clinical Decision Support) für medizinisches Fachpersonal und ersetzt keine ärztliche oder apothekerliche Begutachtung. Alle Angaben ohne Gewähr.
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
with st.sidebar.expander("⚖️ Rechtliches & Datenschutz"):
    st.markdown("""
    **Haftungsausschluss:** MediCheck ist ein rein wissenschaftliches Informations- und Recherchewerkzeug zur Entscheidungsunterstützung. Es ist **kein** zertifiziertes Medizinprodukt im Sinne der EU-MDR.

    **Datenschutz (DSGVO):** Es werden keinerlei personenbezogene Daten, Patientennamen oder Behandlungsakten erhoben oder auf Servern gespeichert. Die Analyse erfolgt zustandslos im Arbeitsspeicher.

    **Kontakt:** Cihan Baydaroglu, Berlin
    """)