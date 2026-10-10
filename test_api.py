import requests

def get_drug_interactions(drug_name):
    """
    Fragt die offizielle openFDA-API nach den im Beipackzettel
    hinterlegten Arzneimittel-Wechselwirkungen (drug_interactions) ab.
    """
    url = "https://api.fda.gov/drug/label.json"
    
    # Suchparameter: Wir suchen nach dem Wirkstoff im Feld 'generic_name'
    params = {
        "search": f'openfda.generic_name:"{drug_name}"',
        "limit": 1
    }
    
    print(f"📡 Sende Anfrage an openFDA für: '{drug_name}' ...")
    response = requests.get(url, params=params)
    
    # 200 bedeutet: Erfolgreich gefunden
    if response.status_code == 200:
        data = response.json()
        results = data.get("results", [])
        if results:
            label_data = results[0]
            
            # Das Feld 'drug_interactions' enthält den offiziellen Warntext
            interactions = label_data.get("drug_interactions", ["Keine spezifischen Wechselwirkungstexte hinterlegt."])
            
            print("\n✅ Treffer gefunden! Offizieller FDA-Interaktionstext (Auszug):")
            print("=" * 60)
            # Wir zeigen die ersten 600 Zeichen des Textes
            print(interactions[0][:600] + " ...\n[Gekürzt]")
            print("=" * 60)
            return interactions[0]
    elif response.status_code == 404:
        print(f"❌ Kein Datensatz für '{drug_name}' bei der FDA gefunden.")
    else:
        print(f"⚠️ Fehler bei der Abfrage. HTTP-Status: {response.status_code}")
    
    return None

# Testaufruf für zwei Wirkstoffe
if __name__ == "__main__":
    get_drug_interactions("ibuprofen")
    get_drug_interactions("ramipril")