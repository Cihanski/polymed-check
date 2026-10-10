def get_atc_code(drug_name):
    """
    Ermittelt robust den ATC-Code oder Phyto-Code eines Eintrags.
    Entfernt Emojis, Klammern und Whitespace vor dem Lookup.
    """
    if not drug_name:
        return None

    clean = drug_name.strip()
    
    # 1. Schneller Direktabgleich in 'drugs'
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT atc_code FROM "drugs" WHERE name = ? COLLATE NOCASE', (clean,))
        row = cursor.fetchone()
        if row:
            return row[0]

    # Bereinige Emojis für Phyto-Items
    import re
    clean_no_emoji = re.sub(r'[\U00010000-\U0010ffff]', '', clean).strip()
    
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT atc_code FROM "drugs" WHERE name LIKE ? COLLATE NOCASE', (f"{clean_no_emoji}%",))
        row = cursor.fetchone()
        if row:
            return row[0]

    # Falls Klammern vorhanden sind (z. B. "Delix (Ramipril)")
    if "(" in clean and ")" in clean:
        inside = clean[clean.find("(") + 1:clean.find(")")].strip()
        clean_candidates = [inside, clean.split("(")[0].strip()]
    else:
        clean_candidates = [clean]

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        for cand in clean_candidates:
            cand_clean = re.sub(r'[\U00010000-\U0010ffff]', '', cand).strip()
            cursor.execute("""
                SELECT atc_code FROM "drugs" 
                WHERE name = ? COLLATE NOCASE 
                ORDER BY 
                    CASE 
                        WHEN atc_code LIKE 'PHYTO_%' THEN 0
                        WHEN atc_code LIKE 'M01%' THEN 1
                        WHEN atc_code LIKE 'C%' THEN 1
                        WHEN atc_code LIKE 'J%' THEN 1
                        WHEN atc_code LIKE 'N%' THEN 1
                        ELSE 2
                    END,
                    LENGTH(name) ASC
            """, (cand_clean,))
            rows = cursor.fetchall()
            if rows:
                return rows[0][0]

            cursor.execute("""
                SELECT atc_code FROM "drugs" 
                WHERE name LIKE ? 
                ORDER BY 
                    CASE 
                        WHEN atc_code LIKE 'PHYTO_%' THEN 0
                        WHEN atc_code LIKE 'M01%' THEN 1
                        WHEN atc_code LIKE 'C%' THEN 1
                        WHEN atc_code LIKE 'J%' THEN 1
                        WHEN atc_code LIKE 'N%' THEN 1
                        ELSE 2
                    END,
                    LENGTH(name) ASC
            """, (f"{cand_clean}%",))
            rows = cursor.fetchall()
            if rows:
                return rows[0][0]

    return None


def check_phytomed_rules(drug_a, drug_b):
    """
    Prüft Interaktionen zwischen Phytopharmaka/Nahrungsmitteln und Arzneistoffen
    sowie reine Phyto-Phyto-Interaktionen.
    """
    atc_a = get_atc_code(drug_a)
    atc_b = get_atc_code(drug_b)

    if not atc_a or not atc_b:
        return None

    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT phyto_code, target_atc, severity, system, effect, mechanism 
            FROM "phytomed_rules"
        """)
        rules = cursor.fetchall()

    for p_code, t_atc, sev, sys_name, eff, mech in rules:
        # Fall 1: A ist Phyto, B matcht (entweder via ATC-Präfix oder exakter Phyto-Code)
        match_ab = (atc_a == p_code) and (atc_b.startswith(t_atc) or atc_b == t_atc)
        # Fall 2: B ist Phyto, A matcht
        match_ba = (atc_b == p_code) and (atc_a.startswith(t_atc) or atc_a == t_atc)

        if match_ab or match_ba:
            return {
                "severity": sev,
                "system": sys_name,
                "effect": eff,
                "mechanism": mech,
                "source": "Phyto-Regelwerk"
            }

    return None