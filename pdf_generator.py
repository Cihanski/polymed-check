from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos


class MediCheckReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(15, 23, 42)  # Slate-900
        self.cell(
            self.epw, 8,
            "MediCheck - Klinischer Medikationsbericht & Interaktionsdossier",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L"
        )
        self.set_font("Helvetica", size=9)
        self.set_text_color(100, 116, 139)  # Slate-500
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.cell(
            self.epw, 5,
            f"Erstellt am: {now_str} | Evidenzbasierte klinische Entscheidungsunterstuetzung",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L"
        )
        self.line(self.l_margin, self.get_y() + 2, self.l_margin + self.epw, self.get_y() + 2)
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(
            self.epw * 0.75, 5,
            "Dieser Bericht ersetzt keine aerztliche Begutachtung. Alle Angaben ohne Gewaehr.",
            new_x=XPos.RIGHT, new_y=YPos.TOP, align="L"
        )
        self.cell(
            self.epw * 0.25, 5,
            f"Seite {self.page_no()}",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R"
        )


def clean_text(text):
    """Sichert die Textkodierung fuer Standard-PDF-Schriften ab."""
    if not text:
        return ""
    replacements = {
        "ä": "ae", "ö": "oe", "ü": "ue",
        "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
        "ß": "ss", "•": "-", "–": "-", "—": "-"
    }
    cleaned = str(text)
    for orig, rep in replacements.items():
        cleaned = cleaned.replace(orig, rep)
    return cleaned.encode("latin-1", "replace").decode("latin-1")


def generate_full_clinical_pdf(patient_age, egfr_value, active_substances,
                                detected_interactions, synergies, priscus_alerts,
                                renal_alerts, schedule, lab_checklist):
    """
    Generiert ein vollstaendiges, strukturiertes DIN-A4 PDF-Dokument.
    """
    pdf = MediCheckReportPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    w_full = pdf.epw

    # 1. Patienten- und Fallstammdaten
    pdf.set_fill_color(241, 245, 249)  # Slate-100
    pdf.rect(pdf.l_margin, pdf.get_y(), w_full, 20, "F")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 41, 59)
    half_w = w_full / 2.0
    pdf.cell(
        half_w, 6,
        clean_text(f"Patientenalter: {patient_age} Jahre (Geriatrisch: {'Ja' if patient_age >= 65 else 'Nein'})"),
        new_x=XPos.RIGHT, new_y=YPos.TOP
    )
    pdf.cell(
        half_w, 6,
        clean_text(f"eGFR-Nierenfunktion: {egfr_value} ml/min/1.73m2"),
        new_x=XPos.LMARGIN, new_y=YPos.NEXT
    )

    pdf.set_font("Helvetica", size=9)
    substances_str = ", ".join([s.capitalize() for s in active_substances])
    pdf.multi_cell(
        w_full, 5,
        clean_text(f"Aktive Wirkstoffe ({len(active_substances)}): {substances_str}"),
        new_x=XPos.LMARGIN, new_y=YPos.NEXT
    )
    pdf.ln(5)

    # 2. Akute Warnungen (PIM / Nierenrisiken)
    if renal_alerts or priscus_alerts:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(185, 28, 28)  # Rot
        pdf.cell(w_full, 6, "1. Dosisanpassungen & Geriatrische PIM-Kriterien (PRISCUS 2.0)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(15, 23, 42)

        for ren in renal_alerts:
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(w_full, 5, clean_text(f"[NIERE] {ren['title']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=8.5)
            pdf.multi_cell(w_full, 4.5, clean_text(f"Befund: {ren['message']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.multi_cell(w_full, 4.5, clean_text(f"Massnahme: {ren['action']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1.5)

        for pim in priscus_alerts:
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(w_full, 5, clean_text(f"[PRISCUS 2.0 PIM] {pim['drug'].capitalize()}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=8.5)
            pdf.multi_cell(w_full, 4.5, clean_text(f"Risiko: {pim['risk']} ({pim['reason']})"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.multi_cell(w_full, 4.5, clean_text(f"Alternative: {pim['alternative']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1.5)

        pdf.ln(3)

    # 3. Multidrug-Synergien
    if synergies:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(194, 65, 12)  # Orange
        pdf.cell(w_full, 6, "2. Multidrug-Synergien & Kumulative Risiken", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(15, 23, 42)

        for syn in synergies:
            pdf.set_font("Helvetica", "B", 9)
            syn_drugs = ", ".join([d.capitalize() for d in syn.get("drugs", [])])
            pdf.cell(w_full, 5, clean_text(f"[{syn['severity']}] {syn['title']} ({syn_drugs})"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=8.5)
            pdf.multi_cell(w_full, 4.5, clean_text(f"Effekt: {syn['effect']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.multi_cell(w_full, 4.5, clean_text(f"Mechanismus: {syn['mechanism']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1.5)

        pdf.ln(3)

    # 4. Dokumentierte Paar-Interaktionen
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w_full, 6, clean_text(f"3. Paarweise Interaktionen ({len(detected_interactions)} Befunde)"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if detected_interactions:
        for item in detected_interactions:
            d1, d2 = item["pair"]
            sev = item.get("severity", "Moderat")
            pdf.set_font("Helvetica", "B", 9)
            pdf.cell(w_full, 5, clean_text(f"[{sev}] {d1.capitalize()} + {d2.capitalize()} ({item.get('system', 'Allgemein')})"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", size=8.5)
            pdf.multi_cell(w_full, 4.5, clean_text(f"Klinische Wirkung: {item.get('effect', '')}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            if item.get("advice"):
                pdf.multi_cell(w_full, 4.5, clean_text(f"Handlungsempfehlung: {item.get('advice', '')}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(2)
    else:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(w_full, 5, clean_text("Keine relevanten paarweisen Wechselwirkungen verzeichnet."), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(3)

    # 5. Chronopharmakologischer Einnahmeplan
    if schedule:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(w_full, 6, "4. Empfohlener Einnahmezeitplan (Chronopharmakologie)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", size=8.5)
        for slot, items in schedule.items():
            pdf.cell(w_full, 5, clean_text(f"- {slot}: {', '.join(items)}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(3)

    # 6. Labormonitoring
    if lab_checklist:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(w_full, 6, "5. Leitliniengestuetzte Laborkontrollen", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", size=8.5)
        for lab in lab_checklist:
            pdf.cell(w_full, 5, clean_text(f"- {lab['parameter']} [{lab['urgency']}e Prioritaet]: {lab['interval']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.multi_cell(w_full, 4.5, clean_text(f"  Begruendung: {lab['reason']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    return bytes(pdf.output())