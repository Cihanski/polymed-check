\# 💊 MediCheck – Clinical Decision Support \& Interaction Radar



\[!\[MediCheck CI Pipeline](https://github.com/Cihanski/polymed-check/actions/workflows/ci.yml/badge.svg)](https://github.com/Cihanski/polymed-check/actions/workflows/ci.yml)



\*\*MediCheck\*\* ist ein evidenzbasiertes, klinisches Entscheidungsunterstützungssystem (Clinical Decision Support System, CDSS) zur Analyse komplexer Polymedikationsregime, arzneimittelbezogener Probleme (DRPs) und lebensmittelbedingter Interaktionen.



Das System kombiniert einen mehrstufigen Analyse-Pipeline-Ansatz mit leitlinienbasierter Geriatrie- und Nephrologie-Prüfung (\*\*Priscus 2.0\*\*, \*\*eGFR-Schwellenwerte\*\*, \*\*Triple-Whammy-Erkennung\*\*) sowie einem interaktiven Netzwerk-Radar zur visuellen Risikobewertung.



\---



\## 🎯 Kernfunktionen



\- \*\*Multi-Stage Interaction Engine:\*\*

&#x20; 1. \*Stufe 1:\* SQLite-Volltext-Cache mit verifizierten pharmakologischen Interaktionspaaren.

&#x20; 2. \*Stufe 2:\* Kationen- \& Phytotherapie-Regelwerk (Chelatbildung mit $Ca^{2+}$, $Fe^{2+/3+}$, $Mg^{2+}$; CYP3A4-Induktion durch Johanniskraut/Grapefruit).

&#x20; 3. \*Stufe 3:\* WHO-ATC-Klassenabgleich für breite Substanzgruppen (z. B. ACE-Hemmer, Sartane, Schleifendiuretika, NSAR).

&#x20; 4. \*Stufe 4:\* Live-Fallback auf die \*\*openFDA Drug Label API\*\* bei bisher nicht lokal annotierten Wirkstoffen.



\- \*\*Klinische Sonderlogiken \& Risikopopulationen:\*\*

&#x20; - \*\*Priscus 2.0 PIM-Check:\*\* Automatische Erkennung potenziell inadäquater Medikation bei Patienten $\\ge 65$ Jahren inklusive evidenzbasierter Therapiealternativen.

&#x20; - \*\*Renale Dosisanpassung (eGFR):\*\* Frühzeitige Warnungen und Kontraindikationsprüfung bei eingeschränkter Nierenfunktion (z. B. Metformin bei $\\text{eGFR} < 30\\,\\text{ml/min}$, Spironolacton-Hyperkaliämierisiko).

&#x20; - \*\*Triple-Whammy-Erkennung:\*\* Alarmierung bei gleichzeitiger Gabe von RAAS-Hemmern, Diuretika und systemischen NSAR.



\- \*\*Interaktives Visual Network Radar:\*\*

&#x20; - 2-Spalten-Split-Dashboard auf Basis von Vis.js Canvas ohne C-Abhängigkeiten.

&#x20; - Farblich kodierte Risikoknoten und Verbindungslinien mit Direkt-Inspektor.

&#x20; - Zero-Conflict-State für unbedenkliche Kombinationen.



\- \*\*Chronopharmakologischer Einnahmeplaner \& Labor-Ampel:\*\*

&#x20; - Automatische zeitliche Separierung kritischer Substanzen (z. B. L-Thyroxin morgens nüchtern, Eisen/Calcium mittags).

&#x20; - Priorisierte Labor- und Diagnostik-Empfehlungen für das Arztgespräch (z. B. Serum-Kalium, Kreatinin, EKG/QTc, Leberenzyme).



\- \*\*Patienten- \& Arztberichte:\*\*

&#x20; - Export als druckoptimiertes Dokument via nativer Browser-Print-CSS oder formatierter PDF-Download.



\---



\## 🏗️ Systemarchitektur

