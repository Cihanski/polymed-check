import os
import json
import requests
from google import genai
from google.genai import types

# 1. Gemini Client initialisieren
# Setze hier deinen Key ein oder nutze os.environ.get("GEMINI_API_KEY")
api_key = os.environ.get("GEMINI_API_KEY", "DEIN_GEMINI_API_KEY_HIER")
client = genai.Client(api_key=api_key)

def fetch_fda_label(drug_name):
    """Holt die offiziellen Beipackzetteldaten von openFDA."""
    url = "https://api.fda.gov/drug/label.json"
    params = {"search": f'openfda.generic_name:"{drug_name}"', "limit": 1}
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        results = data.get("results", [])
        if results:
            label = results[0]
            # Wir prüfen drug_interactions, sonst warnings als Fallback
            text = label.get("drug_interactions", label.get("warnings", [""]))
            return text[0][:2500]  # Erste 2500 Zeichen reichen völlig
    return None

def analyze_interactions_with_ai(drug_a, drug_b, raw_text):
    """Nutzt Gemini mit Structured Outputs, um sauberes JSON zu erzeugen."""
    
    prompt = f"""
Du bist ein pharmazeutischer Analyse-Assistent.
Analysiere den folgenden Auszug aus dem offiziellen FDA-Beipackzettel für '{drug_a}'.
Prüfe speziell, ob und wie eine Wechselwirkung mit '{drug_b}' beschrieben wird.

FDA-Textauszug:
\"\"\"{raw_text}\"\"\"

Antworte IMMER im folgenden JSON-Format:
{{
  "found": true oder false,
  "severity": "Hoch" oder "Moderat" oder "Gering" oder "Unbekannt",
  "system": "Betroffenes Organsystem (z.B. Niere, Magen-Darm, Herz-Kreislauf)",
  "effect": "Klinischer Effekt in 1 klaren deutschen Satz",
  "mechanism_layman": "Laienverständliche Erklärung in 1-2 Sätzen (Warum passiert das?)"
}}
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1  # Sehr niedrig für maximale Faktentreue
        )
    )
    
    return json.loads(response.text)

# --- Testlauf ---
if __name__ == "__main__":
    drug_1 = "ramipril"
    drug_2 = "ibuprofen (NSAID)"
    
    print(f"1. Frage openFDA nach '{drug_1}' ab...")
    raw_data = fetch_fda_label(drug_1)
    
    if raw_data:
        print("2. FDA-Text erhalten. Sende zur Strukturierung an Gemini...\n")
        structured_result = analyze_interactions_with_ai(drug_1, drug_2, raw_data)
        
        print("✅ KI-Strukturierte Ausgabe (Fertig für dein Frontend):")
        print(json.dumps(structured_result, indent=2, ensure_ascii=False))
    else:
        print("Keine Daten bei openFDA gefunden.")