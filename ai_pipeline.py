import os


def generate_clinical_summary(patient_age, egfr_value, active_substances,
                              detected_interactions, synergies, priscus_alerts, renal_alerts):
    """
    Generiert eine praegnante aerztliche Fallzusammenfassung via Google Gemini.
    Faengt fehlende oder inkompatible SDK-Installationen sauber ab und faellt
    auf die deterministische Regelwerk-Synthese zurueck.
    """
    def fallback_text():
        high_alerts = len([i for i in detected_interactions if i.get("severity") == "Hoch"])
        high_syn = len([s for s in synergies if s.get("severity") == "Hoch"])
        pim_count = len(priscus_alerts)
        ren_count = len(renal_alerts)
        
        reasons = []
        if high_syn:
            reasons.append("kumulative Synergien (z. B. QTc-Verlaengerung)")
        if high_alerts:
            reasons.append("kritische Paarinteraktionen")
        if ren_count:
            reasons.append("renale Dosisanpassungen/Kontraindikationen")
        if pim_count:
            reasons.append("geriatrische PIM-Kriterien")

        grund_str = ", ".join(reasons) if reasons else "keine akuten Hochrisiko-Konflikte"

        return (
            f"Klinische Kurzsynthese (Regelwerk): Bei dem {patient_age}-jaehrigen Patienten "
            f"(eGFR: {egfr_value} ml/min) bestehen unter {len(active_substances)} Wirkstoffen "
            f"folgende Risikofaktoren: {grund_str}. "
            f"Eine engmaschige Kontrolle der Vitalparameter sowie der empfohlenen Laborwerte vor Weiterverordnung wird dringend angeraten."
        )

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return fallback_text()

    prompt = f"""Du bist ein klinischer Pharmakologe und AMTS-Experte.
Erstelle eine praegnante, professionelle Zusammenfassung (maximal 3 bis 4 Saetze) fuer den behandelnden Arzt oder Apotheker.

Patientendaten:
- Alter: {patient_age} Jahre ({'geriatrisch >=65' if patient_age >= 65 else 'nicht geriatrisch'})
- eGFR: {egfr_value} ml/min/1.73m2
- Verordnete Wirkstoffe: {', '.join(active_substances)}

Identifizierte Risiken:
- Kritische Wechselwirkungen: {len(detected_interactions)}
- Multidrug-Synergien (z. B. QTc-Verlaengerung): {len(synergies)}
- PRISCUS 2.0 PIM-Kriterien: {len(priscus_alerts)}
- Renale Kontraindikationen/Warnungen: {len(renal_alerts)}

Fasse das Hauptgefaehrdungspotenzial zusammen und formuliere eine klare aerztliche Handlungsempfehlung zur Risikominimierung."""

    # 1. Versuch: Neues Google GenAI SDK (google-genai)
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        if response and response.text:
            return response.text.strip()
    except Exception:
        pass

    # 2. Versuch: Legacy SDK (google-generativeai) falls auf Cloud vorhanden
    try:
        import google.generativeai as legacy_genai
        legacy_genai.configure(api_key=api_key)
        model = legacy_genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        if response and response.text:
            return response.text.strip()
    except Exception:
        pass

    # Sicherer Fallback bei jeglichem Fehler
    return fallback_text()