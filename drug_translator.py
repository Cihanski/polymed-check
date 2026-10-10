"""
drug_translator.py
Automatisierte Normalisierung von Markennamen, Handelsnamen und Generika auf INN.
Nutzt lokale Heuristiken, bekannte Kern-Markennamen und die offizielle RxNorm API.
"""

import re
import requests
import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "interactions.db")

# 1. Bekannte deutsche & internationale Kern-Markennamen (fuer Autocomplete-Vorauswahl)
BRAND_TO_INN = {
    # Kardiovaskulaer & Blutdruck
    "xarelto": "rivaroxaban",
    "eliquis": "apixaban",
    "pradaxa": "dabigatran",
    "lixiana": "edoxaban",
    "marcumar": "phenprocoumon",
    "falithrom": "phenprocoumon",
    "aspirin": "acetylsalicylic acid",
    "aspirin protect": "acetylsalicylic acid",
    "plavix": "clopidogrel",
    "beloc-zok": "metoprolol",
    "delix": "ramipril",
    "norvasc": "amlodipine",
    "crestor": "rosuvastatin",
    "sortis": "atorvastatin",
    "lipitor": "atorvastatin",
    "zocor": "simvastatin",

    # Schmerz & Entzuendung
    "voltaren": "diclofenac",
    "ibuflam": "ibuprofen",
    "dolormin": "ibuprofen",
    "novalgin": "metamizole",
    "novaminsulfon": "metamizole",
    "tilidin": "tilidine",
    "valoron": "tilidine",
    "targin": "oxycodone",
    "subutex": "buprenorphine",
    "mst mundipharma": "morphine",

    # Magen & Endokrinologie
    "pantozol": "pantoprazole",
    "antra": "omeprazole",
    "nexium": "esomeprazole",
    "l-thyroxin henning": "levothyroxine sodium",
    "eythyrox": "levothyroxine sodium",
    "januvia": "sitagliptin",
    "jardiance": "empagliflozin",
    "forxiga": "dapagliflozin",
    "ozempic": "semaglutide",

    # ZNS & Psychiatrie
    "tavor": "lorazepam",
    "valium": "diazepam",
    "cipralex": "escitalopram",
    "zoloft": "sertraline",
    "trevilor": "venlafaxine",
    "lyrica": "pregabalin",
    "neurontin": "gabapentin",

    # Antiinfektiva & Immunologie
    "ciprobay": "ciprofloxacin",
    "clont": "metronidazole",
    "sandimmun": "ciclosporin",
    "prograf": "tacrolimus"
}

# Deutsche Generika-Herstellerkuerzel zum Herausfiltern via Regex
GENERIC_SUFFIXES = [
    r"\bratiopharm\b", r"\bhexal\b", r"\bstada\b", r"\b1a pharma\b",
    r"\b1 a pharma\b", r"\bal\b", r"\bheumann\b", r"\bzenon\b",
    r"\bbasics\b", r"\babZ\b", r"\baxcount\b"
]


def clean_generic_brand_name(name):
    """
    Entfernt Hersteller-Kuerzel wie 'ratiopharm', 'HEXAL' oder Dosisangaben,
    um direkt den INN freizulegen (z. B. 'Ramipril-ratiopharm 5mg' -> 'Ramipril').
    """
    cleaned = name
    cleaned = re.sub(r"\b\d+\s*(mg|g|ug|µg|ml)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = cleaned.replace("-", " ")

    for suffix in GENERIC_SUFFIXES:
        cleaned = re.sub(suffix, "", cleaned, flags=re.IGNORECASE)

    return re.sub(r"\s+", " ", cleaned).strip()


def query_rxnorm_api(brand_name):
    """
    Fragt die offizielle U.S. NLM RxNorm API ab, um ueber die Relation
    'allrelated' gezielt den aktiven Inhaltsstoff (Ingredient / IN) aufzuloesen.
    """
    clean_term = clean_generic_brand_name(brand_name)
    if not clean_term or len(clean_term) < 3:
        return None

    try:
        # 1. RxCUI des Markennamens abfragen
        find_url = f"https://rxnav.nlm.nih.gov/REST/rxcui.json?name={clean_term}"
        resp = requests.get(find_url, timeout=3)
        if resp.status_code != 200:
            return None

        id_group = resp.json().get("idGroup", {})
        rxnorm_ids = id_group.get("rxnormId", [])
        if not rxnorm_ids:
            return None

        rxcui = rxnorm_ids[0]

        # 2. Den verknuepften Inhaltsstoff (Ingredient / IN) aufloesen
        rel_url = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/allrelated.json"
        rel_resp = requests.get(rel_url, timeout=3)
        if rel_resp.status_code == 200:
            rel_group = rel_resp.json().get("allRelatedGroup", {})
            for concept_group in rel_group.get("conceptGroup", []):
                if concept_group.get("tty") == "IN":  # IN = Ingredient
                    concept_props = concept_group.get("conceptProperties", [])
                    if concept_props:
                        return concept_props[0].get("name", "").lower().strip()

    except Exception:
        pass

    return None


def translate_to_inn(name):
    """
    Normalisiert einen Namen auf den internationalen Freinamen (INN):
    1. Bereinigung von Klammerzusaetzen wie 'Xarelto (Rivaroxaban)'
    2. Bereinigung von Generika-Zusaetzen
    3. Lokale Markennamen-Tabelle
    4. RxNorm API Fallback mit 'allrelated' (Ingredient)
    """
    if not name:
        return ""

    raw_clean = name.strip()

    if raw_clean.startswith("PHYTO_") or any(em in raw_clean for em in ["🍊", "🥛", "🌿", "🩸", "🍬", "🍂", "🍃", "🧄", "⚡", "🍵"]):
        return raw_clean

    if "(" in raw_clean and ")" in raw_clean:
        inside = raw_clean[raw_clean.find("(") + 1:raw_clean.find(")")].strip()
        if inside:
            return inside.lower()

    raw_lower = raw_clean.lower()

    if raw_lower in BRAND_TO_INN:
        return BRAND_TO_INN[raw_lower]

    cleaned = clean_generic_brand_name(raw_clean).lower()
    if cleaned in BRAND_TO_INN:
        return BRAND_TO_INN[cleaned]

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM "drugs" WHERE name = ? COLLATE NOCASE', (cleaned,))
        row = cursor.fetchone()
        if row:
            return row[0].lower()

    api_match = query_rxnorm_api(raw_clean)
    if api_match:
        BRAND_TO_INN[raw_lower] = api_match
        return api_match

    return cleaned


def get_autocomplete_catalog():
    """
    Generiert den Gesamtkatalog fuer das Streamlit-Dropdown:
    - Alle bekannten Markennamen mit Klarnamen-Hinweis: z. B. 'Xarelto (Rivaroxaban)'
    - Alle Freinamen (INNs) aus der Datenbank
    """
    catalog = set()

    for brand, inn in BRAND_TO_INN.items():
        catalog.add(f"{brand.capitalize()} ({inn.capitalize()})")

    try:
        with sqlite3.connect(DB_FILE) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT name FROM "drugs"')
            for row in cursor.fetchall():
                if row[0]:
                    catalog.add(row[0])
    except Exception:
        pass

    return sorted(list(catalog))