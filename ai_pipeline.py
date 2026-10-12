import os


def generate_clinical_summary(patient_age, egfr_value, active_substances,
                              detected_interactions, synergies, priscus_alerts, renal_alerts):
    """
    Generiert eine praegnante aerztliche Fallzusammenfassung via Google Gemini.
    Liefert einen evidenzbasierten Fliesstext fuer die Visite oder das Medikationsgespraech.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        # Lokaler deterministischer Fallback, wenn kein API-Key konfiguriert ist
        high_alerts = len([i for i in detected_interactions if i.get("severity") == "Hoch"])
        return (
            f"Klinische Kurzsynthese (Regelwerk): Bei dem {patient_age}-jaehrigen Patienten "
            f"(eGFR: {egfr_value} ml/min) bestehen unter {len(active_substances)} Wirkstoffen "
            f"{high_alerts} kritische Interaktionsrisiken sowie {len(synergies)} kumulative Synergien. "
            f"Eine Priorisierung der Nieren- und Sturzrisikofaktoren vor Weiterverordnung wird empfohlen."
        )

    try:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = f"""Du bist ein klinischer Pharmakologe und AMTS-Experte (Arzneimitteltherapiesicherheit).
Erstelle eine praegnante, professionelle Zusammenfassung (maximal 3 bis 4 Saetze) fuer den behandelnden Arzt oder Apotheker.

Patientendaten:
- Alter: {patient_age} Jahre ({'geriatrisch >=65' if patient_age >= 65 else 'nicht geriatrisch'})
- eGFR: {egfr_value} ml/min/1.73m2
- Verordnete Wirkstoffe: {', '.join(active_substances)}

Identifizierte Risiken:
- Kritische Wechselwirkungen: {len(detected_interactions)}
- Multidrug-Synergien (z.B. QTc/ZNS): {len(synergies)}
- PRISCUS 2.0 PIM-Kriterien: {len(priscus_alerts)}
- Renale Kontraindikationen/Warnungen: {len(renal_alerts)}

Fasse das Hauptgefaehrdungspotenzial zusammen und formuliere eine klare aerztliche Handlungsempfehlung zur Risikominimierung."""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        return f"KI-Zusammenfassung derzeit nicht verfuegbar ({str(e)}). Bitte manuelle Befundtriage nutzen."