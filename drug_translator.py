"""
drug_translator.py
Verwaltet den Autocomplete-Katalog und übersetzt deutsche Handelsnamen/Wirkstoffe
in standardisierte internationale Freinamen (INN / openFDA generic names).
"""

import re

# Umfassendes Mapping: Handelsname oder deutscher Wirkstoff -> Internationaler Freiname (INN)
GERMAN_BRAND_AND_NAME_MAP = {
    # --- Schmerzmittel, NSAR & Entzündungshemmer ---
    "Aspirin (Acetylsalicylsäure)": "aspirin",
    "Aspirin Protect 100mg": "aspirin",
    "ASS ratiopharm": "aspirin",
    "Godamed": "aspirin",
    "Ibuprofen (z. B. Nurofen, Ibutop, Ibu-Hexal)": "ibuprofen",
    "Voltaren (Diclofenac)": "diclofenac",
    "Diclac Dolo": "diclofenac",
    "Paracetamol (Ben-u-ron)": "acetaminophen",
    "Novalgin / Novaminsulfon (Metamizol)": "metamizole",
    "Aleve (Naproxen)": "naproxen",
    "Arcoxia (Etoricoxib)": "etoricoxib",
    "Celebrex (Celecoxib)": "celecoxib",
    "Tilidin comp.": "tilidine",
    "Tramal / Tramadol": "tramadol",
    "Oxygesic (Oxycodon)": "oxycodone",
    "MST Mundipharma (Morphin)": "morphine",
    "Fentanyl Pflaster": "fentanyl",

    # --- Blutverdünner & Gerinnungshemmer ---
    "Eliquis (Apixaban)": "apixaban",
    "Xarelto (Rivaroxaban)": "rivaroxaban",
    "Lixiana (Edoxaban)": "edoxaban",
    "Pradaxa (Dabigatran)": "dabigatran",
    "Marcumar / Falithrom (Phenprocoumon)": "phenprocoumon",
    "Plavix / Iscover (Clopidogrel)": "clopidogrel",
    "Brilique (Ticagrelor)": "ticagrelor",
    "Effient (Prasugrel)": "prasugrel",
    "Clexane (Enoxaparin)": "enoxaparin",

    # --- Herz-Kreislauf, Blutdruck & Diuretika ---
    "Delix (Ramipril)": "ramipril",
    "Ena-hexal (Enalapril)": "enalapril",
    "Lisinopril": "lisinopril",
    "Blopress (Candesartan)": "candesartan",
    "Cozaar (Losartan)": "losartan",
    "Diovan (Valsartan)": "valsartan",
    "Norvasc (Amlodipin)": "amlodipine",
    "Bayotensin (Nitrendipin)": "nitrendipine",
    "Beloc-zok (Metoprolol)": "metoprolol",
    "Concor (Bisoprolol)": "bisoprolol",
    "Nebilet (Nebivolol)": "nebivolol",
    "Carvedilol": "carvedilol",
    "HCT-Hexal (Hydrochlorothiazid)": "hydrochlorothiazide",
    "Torem (Torasemid)": "torsemide",
    "Lasix (Furosemid)": "furosemide",
    "Aldactone (Spironolacton)": "spironolactone",
    "Inspra (Eplerenon)": "eplerenone",

    # --- Antibiotika & Antiinfektiva ---
    "Amoxicillin": "amoxicillin",
    "Augmentan (Amoxicillin/Clavulansäure)": "amoxicillin",
    "Cefuroxim": "cefuroxime",
    "Ciproflox / Ciprobay (Ciprofloxacin)": "ciprofloxacin",
    "Tavanic (Levofloxacin)": "levofloxacin",
    "Avalox (Moxifloxacin)": "moxifloxacin",
    "Klacid (Clarithromycin)": "clarithromycin",
    "Zithromax (Azithromycin)": "azithromycin",
    "Doxycyclin": "doxycycline",
    "Cotrim / Eusaprim (Cotrimoxazol)": "trimethoprim",
    "Fosfomycin Aristo": "fosfomycin",
    "Sobelin (Clindamycin)": "clindamycin",
    "Metronidazol": "metronidazole",

    # --- Onkologie, Immunsuppression & Krebsmedikamente ---
    "Methotrexat (MTX / Lantarel)": "methotrexate",
    "Imurek (Azathioprin)": "azathioprine",
    "Sandimmun (Ciclosporin)": "cyclosporine",
    "Prograf / Advagraf (Tacrolimus)": "tacrolimus",
    "CellCept (Mycophenolatmofetil)": "mycophenolate",
    "Tamoxifen Hexal": "tamoxifen",
    "Arimidex (Anastrozol)": "anastrozole",
    "Femara (Letrozol)": "letrozole",
    "Glivec (Imatinib)": "imatinib",
    "Xeloda (Capecitabin)": "capecitabine",
    "Endoxan (Cyclophosphamid)": "cyclophosphamide",
    "Ibrance (Palbociclib)": "palbociclib",

    # --- Magenschutz (PPI) & Magen-Darm ---
    "Pantozol (Pantoprazol)": "pantoprazole",
    "Antra / Gastracid (Omeprazol)": "omeprazole",
    "Nexium (Esomeprazol)": "esomeprazole",
    "Agopton (Lansoprazol)": "lansoprazole",
    "Iberogast": "iberogast",
    "MCP / Paspertin (Metoclopramid)": "metoclopramide",

    # --- Diabetes & Stoffwechsel ---
    "Glucophage (Metformin)": "metformin",
    "Jardiance (Empagliflozin)": "empagliflozin",
    "Forxiga (Dapagliflozin)": "dapagliflozin",
    "Januvia (Sitagliptin)": "sitagliptin",
    "Ozempic (Semaglutid)": "semaglutide",
    "Trulicity (Dulaglutid)": "dulaglutide",
    "Lantus (Insulin glargin)": "insulin glargine",
    "Novorapid (Insulin aspart)": "insulin aspart",

    # --- Cholesterinsenker (Statine & Co.) ---
    "Sortis (Atorvastatin)": "atorvastatin",
    "Zocor (Simvastatin)": "simvastatin",
    "Crestor (Rosuvastatin)": "rosuvastatin",
    "Pravasin (Pravastatin)": "pravastatin",
    "Ezetrol (Ezetimib)": "ezetimibe",

    # --- ZNS, Psyche, Neurologie & Schlaf ---
    "Cipramil (Citalopram)": "citalopram",
    "Cipralex (Escitalopram)": "escitalopram",
    "Zoloft (Sertralin)": "sertraline",
    "Trevilor (Venlafaxin)": "venlafaxine",
    "Cymbalta (Duloxetin)": "duloxetine",
    "Mirtazapin": "mirtazapine",
    "Quilonum / Hypnorex (Lithium)": "lithium",
    "Tavor (Lorazepam)": "lorazepam",
    "Valium (Diazepam)": "diazepam",
    "Xanor (Alprazolam)": "alprazolam",
    "Lyrica (Pregabalin)": "pregabalin",
    "Neurontin (Gabapentin)": "gabapentin",
    "Levodopa / Benserazid (Madopar)": "levodopa",

    # --- Pflanzliche Präparate & OTC ---
    "Tebonin / Ginkobil (Ginkgo Biloba)": "ginkgo",
    "Laif 900 (Johanniskraut)": "st. john's wort",
    "Baldrian Dispert": "valerian"
}

def get_autocomplete_catalog():
    """Gibt die sortierte Liste aller Präparate für das Suchfeld zurück."""
    return sorted(list(GERMAN_BRAND_AND_NAME_MAP.keys()))

STRIP_PATTERNS = [
    r"\bratiopharm\b", r"\bhexal\b", r"\b1a pharma\b", r"\bal\b", r"\btad\b", 
    r"\bzentiva\b", r"\bdura\b", r"\bheumann\b", r"\bprotect\b", r"\bakut\b", 
    r"\bforte\b", r"\bplus\b", r"\bcomp\b", r"\bmg\b", r"\b\d+\b"
]

def clean_input_string(raw_text: str) -> str:
    text = raw_text.lower().strip()
    text = re.sub(r"\(.*?\)", "", text)
    for pattern in STRIP_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    text = re.sub(r"[^\w\s-]", "", text)
    return text.strip()

def translate_to_inn(drug_input: str) -> str:
    if not drug_input:
        return ""

    if drug_input in GERMAN_BRAND_AND_NAME_MAP:
        return GERMAN_BRAND_AND_NAME_MAP[drug_input].lower()

    cleaned = clean_input_string(drug_input)

    for brand_key, inn in GERMAN_BRAND_AND_NAME_MAP.items():
        if cleaned == clean_input_string(brand_key):
            return inn.lower()

    for word in cleaned.split():
        for brand_key, inn in GERMAN_BRAND_AND_NAME_MAP.items():
            if word in clean_input_string(brand_key).split():
                return inn.lower()

    normalized = cleaned
    if normalized.endswith("prazol"):
        normalized = normalized[:-6] + "prazole"
    elif normalized.endswith("dipin"):
        normalized = normalized[:-5] + "dipine"
    return normalized