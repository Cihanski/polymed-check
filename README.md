\# 💊 MediCheck – Klinischer Medikations- \& Interaktions-Check



\*\*MediCheck\*\* ist ein evidenzbasiertes Analysewerkzeug zur Erkennung von Arzneimittelwechselwirkungen, kumulativen Risiken (Multi-Drug Synergien), Phytopharmaka- und Nahrungsmittelkonflikten sowie Resorptionsstörungen.



Das System kombiniert einen lokalen SQLite-Kern, ein dynamisches WHO-ATC- und Phyto-Regelwerk sowie eine Fallback-Anbindung an die offizielle \*\*openFDA API\*\*.



\---



\## 🌟 Kernfunktionen



\* \*\*4-Stufen-Prüfkaskade:\*\*

&#x20; 1. \*\*SQLite-Cache:\*\* Sofortige Rückgabe validierter Paare ohne Netzwerklatenz.

&#x20; 2. \*\*Phyto- \& Food-Engine:\*\* Identifikation kritischer Interaktionen mit Phytopharmaka, Mineralstoffen und Nahrungsmitteln (z. B. Johanniskraut, Grapefruitsaft, Ginkgo, Knoblauch, Lakritze, Calcium/Milchprodukte, Eisen, Magnesium, CBD).

&#x20; 3. \*\*WHO-ATC Klassenregeln:\*\* Erkennung übergeordneter pharmakodynamischer Klassenkonflikte (z. B. RAAS-Blocker + kaliumsparende Diuretika, Antikoagulation + NSAR, Opioide + Benzodiazepine, Digoxin + P-gp-Inhibitoren).

&#x20; 4. \*\*openFDA Live-Fallback:\*\* Dynamische Extraktion relevanter Warnhinweise aus US-FDA-Fachinformationen bei seltenen Kombinationen.

\* \*\*Klinische Differenzierung (Darreichungsform \& Dosis):\*\*

&#x20; \* Unterscheidung zwischen topischer (z. B. Diclofenac-Gel, \~6 % systemische Bioverfügbarkeit) und oraler Applikation zur Vermeidung von Alert Fatigue.

&#x20; \* Differenzierung zwischen Thrombozytenaggregationshemmung (ASS 100 mg) und analgetischer NSAR-Hochdosis (ASS ≥ 500 mg).

\* \*\*Multi-Drug Synergien \& Organtoxizität:\*\*

&#x20; \* \*\*Triple-Whammy-Erkennung:\*\* Akutes Nephrotoxizitätsrisiko bei RAAS-Inhibitor + Diuretikum + oralem NSAR.

&#x20; \* \*\*Anticholinerge Last:\*\* Kumulatives Delir- und Sturzrisiko bei multiplen anticholinergen Wirkstoffen.

&#x20; \* \*\*QTc-Verlängerung:\*\* Synergistische Hemmung myokardialer Kaliumkanäle (hERG) mit Risiko für Torsade-de-Pointes-Arrhythmien.

&#x20; \* \*\*ZNS- \& Atemdepression:\*\* Kumulative Dämpfung über GABAerge Transmission und mu-Opioid-Signalwege.

\* \*\*Strukturierter PDF-Gesprächsleitfaden:\*\*

&#x20; \* Robuster Latin-1/FPDF-Export ohne Unicode-Artefakte.

&#x20; \* Generierung zielgerichteter Leitfragen und Einnahmeabstandshinweise (z. B. 2–3 Stunden Abstand bei Chelatbildnern wie Eisen, Magnesium, Milch) für das Arztgespräch.



\---



\## 🏗️ Systemarchitektur

