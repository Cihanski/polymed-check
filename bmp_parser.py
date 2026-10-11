import re
import xml.etree.ElementTree as ET
from drug_translator import translate_to_inn


def parse_bmp_xml(xml_content):
    """
    Parst den XML-Inhalt eines offiziellen Bundeseinheitlichen Medikationsplans (BMP).
    Liest Wirkstoffnamen (W) oder Handelsnamen (A) aus den Medikamenten-Tags (<M>).
    """
    drugs = []
    try:
        root = ET.fromstring(xml_content.strip())
        # Suche nach allen Medikationszeilen (<M> Tags)
        for med in root.iter("M"):
            # 'w' = Wirkstoffbezeichnung, 'a' = Handelsname
            substance = med.attrib.get("w") or med.attrib.get("a")
            if substance:
                cleaned = substance.strip()
                if cleaned and cleaned not in drugs:
                    drugs.append(cleaned)
    except Exception:
        pass
    return drugs


def parse_medication_text(raw_text):
    """
    Parst unstrukturierten Text, Freitext-Medikationslisten oder BMP-XML-Strings.
    Filtert Dosierungsangaben (z. B. 1-0-0, 5mg, Retard) heraus und extrahiert Wirkstoffnamen.
    """
    if not raw_text or not raw_text.strip():
        return []

    text = raw_text.strip()

    # Falls XML uebergeben wurde: XML-Parser nutzen
    if text.startswith("<") and "</" in text:
        xml_results = parse_bmp_xml(text)
        if xml_results:
            return xml_results

    extracted_substances = []
    lines = text.splitlines()

    # Regex-Muster fuer Dosierungen, Einheiten und Einnahmeschemata
    dosage_pattern = re.compile(
        r"(\b\d+([,\.]\d+)?\s*(mg|µg|ug|g|ml|ie|einh|tabl|tbl|stk)\b|"
        r"\b\d+-\d+-\d+(-\d+)?\b|"
        r"\b(morgens|mittags|abends|zur nacht|tgl|täglich|b\.b\.|retard|plus|comp)\b)",
        re.IGNORECASE
    )

    for line in lines:
        cleaned_line = line.strip()
        if not cleaned_line or cleaned_line.startswith("#") or cleaned_line.startswith("//"):
            continue

        # Trennung nach typischen Trennzeichen (Semikolon, Komma, Zeilenumbruch)
        parts = re.split(r"[;,]", cleaned_line)
        for part in parts:
            item = part.strip()
            if not item:
                continue

            # Dosierungsbestandteile entfernen
            item_no_dose = dosage_pattern.sub("", item).strip()

            # Satzzeichen am Rand entfernen
            item_no_dose = re.sub(r"^[\d\.\-\*\s]+", "", item_no_dose)
            item_no_dose = re.sub(r"[\(\)\[\]\{\}]", "", item_no_dose).strip()

            # Erstes relevantes Wort/Wortgruppe als Substanzkandidat
            words = item_no_dose.split()
            if words:
                candidate = words[0]
                # Zusätze wie "Plus" oder "Comp" wieder anhängen, falls Kombipräparat
                if len(words) > 1 and words[1].lower() in ["plus", "comp"]:
                    candidate = f"{words[0]} {words[1]}"

                if len(candidate) >= 3 and not candidate.isdigit():
                    norm = translate_to_inn(candidate)
                    if isinstance(norm, list):
                        for n in norm:
                            if n.capitalize() not in extracted_substances:
                                extracted_substances.append(n.capitalize())
                    elif norm:
                        val = norm.capitalize()
                        if val not in extracted_substances:
                            extracted_substances.append(val)
                    else:
                        cap = candidate.capitalize()
                        if cap not in extracted_substances:
                            extracted_substances.append(cap)

    return extracted_substances