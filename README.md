💊 MediCheck | Clinical Decision Support \& Interaction RadarMediCheck ist ein evidenzbasiertes, webgestütztes Entscheidungsunterstützungs-System (Clinical Decision Support Tool / CDSS) zur Analyse komplexer Arzneimitteltherapien bei Multimorbidität und Polypharmazie.Entwickelt für Apotheker (Erweiterte Medikationsberatung nach § 31a SGB V), Allgemeinmediziner und klinisches Fachpersonal, aggregiert die Anwendung Fachinformationen, Geriatrie-Kriterien (PRISCUS 2.0) und Nierenfunktionsprofile (eGFR) in einer barrierefreien, interaktiven Cockpit-Oberfläche.🎯 Kernfunktionen \& Klinischer NutzenModulKlinischer Funktionsumfang🕸️ Interaktions-Radar (Vis.js)Topologische 2D-Netzwerk-Visualisierung von 1:1-Interaktionen und kombinatorischen Klasseneffekten mit Ampel-Risikotriage (Hoch, Moderat, Verträglich).👵 PRISCUS 2.0 PIM-KatalogAutomatischer Abgleich geriatrischer Risikomedikamente ($\\ge 65$ Jahre) mit evidenzbasierten Leitlinien-Alternativen zur Sturz- und Delir-Prävention.🫘 eGFR-DosisanpassungTriage renaler Dosisreduktionen und toxischer Kontraindikationen bei chronischer Niereninsuffizienz (CKD-Stufen 3a–5).⚡ Multidrug-SynergienErkennung kumulativer Risiken wie kardialer QTc-Verlängerung (Torsade de Pointes), ZNS-Depression (Sedierung/Atemdepression), serotonergem Syndrom und anticholinerger Last.⏰ ChronopharmakologieAutomatisierte Erstellung eines tageszeitlichen Einnahmeplans (morgens nüchtern, zum Frühstück, abends zur Nacht) unter Beachtung von Chelatbildungsintervallen.🧪 Leitlinien-LabormatrixAutomatische Ableitung notwendiger Kontrollparameter (Serum-Kalium, Kreatinin, EKG, Leberwerte, TSH) mit konkreten Kontrollintervallen.📋 BMP- \& Freitext-ParserDirekter Import aus dem Bundeseinheitlichen Medikationsplan (BMP-XML nach § 31a SGB V) oder unstrukturierten Praxislisten mit Dosis-Bereinigung.📄 DIN-A4 PDF-Arztbrief1-Klick-Generierung druckfertiger AMTS-Befundberichte inklusive Patienten-Audit-Trail für Praxisverwaltungssysteme.🏗️ Systemarchitektur \& Datenfluss\[ Medikationsplan / BMP / Freitext ] 

&#x20;                │

&#x20;                ▼

&#x20;    \[ drug\_translator.py ] ──> Auflösung von Handelsnamen \& Fixkombinationen (INN)

&#x20;                │

&#x20;                ▼

┌─────────────────────────────────────────────────────────────┐

│                 Multi-Tier Interaction Engine               │

│                                                             │

│  Stufe 1: Lokaler SQLite-Cache (Fachinformationen)          │

│  Stufe 2: Deterministische Kationen- \& Phyto-Regeln         │

│  Stufe 3: WHO ATC-Klassenregeln (z. B. Opioide + Benzodiazepine)│

│  Stufe 4: openFDA API-Schnittstelle mit Write-Through-Cache │

└──────────────────────────────┬──────────────────────────────┘

&#x20;                              │

&#x20;      ┌───────────────────────┼────────────────────────┐

&#x20;      ▼                       ▼                        ▼

\[ PRISCUS 2.0 ]         \[ eGFR \& Renale Tox ]    \[ Labormonitoring ]

&#x20;      │                       │                        │

&#x20;      └───────────────────────┼────────────────────────┘

&#x20;                              │

&#x20;                ┌─────────────┴─────────────┐

&#x20;                ▼                           ▼

&#x20;     \[ Vis.js Radar Cockpit ]     \[ PDF-Dossier-Generator ]

♿ Barrierefreiheit \& UX-Design (WCAG 2.1)Das Cockpit wurde speziell für kontrastreiches, fehlersicheres und ermüdungsfreies Arbeiten gestaltet:Geprüfter Dark-Mode-Kontrast: Text- und Badge-Kontraste erfüllen den WCAG AAA Standard ($\\ge 7:1$).Touch- \& Senioren-freundliche Klickflächen: Mindesthöhe von 48 px für alle primären Schalter und Registerkarten.Ersetzte Schieberegler: Schnelle Zahleneingabe für Alter und eGFR via Tastatur oder Stepper-Tasten verhindert Fehlbedienungen.Keine reinen Farb-Indikatoren: Risikostufen werden stets durch Text-Badges (\[HOCH], \[MODERAT]) und Evidenzquellen begleitet.⚖️ Regulatorische Einordnung \& ComplianceMedizinprodukte-Verordnung (EU-MDR 2017/745): MediCheck ist kein zertifiziertes Medizinprodukt (Software as a Medical Device / SaMD). Es fungiert als reines Information Retrieval \& Clinical Decision Support System für approbiertes medizinisches Fachpersonal. Das Tool trifft keine eigenständigen therapeutischen oder diagnostischen Entscheidungen.Datenschutz (DSGVO): Die Anwendung arbeitet zustandslos (stateless) im flüchtigen Arbeitsspeicher. Es werden serverseitig keine Klarnamen, IP-Adressen oder Behandlungsakten persistiert. Fall-Kürzel dienen ausschließlich der Zuordnung auf dem lokalen Ausdruck.🚀 Lokale Installation \& Schnellstart1. Repository klonen \& Umgebung einrichtengit clone https://github.com/cihanbaydaroglu/polymed-check.git

cd polymed-check



\# Virtuelle Umgebung erstellen

python -m venv venv

source venv/bin/activate  # Unter Windows: venv\\Scripts\\activate



\# Abhängigkeiten installieren

pip install -r requirements.txt

2\. Tests ausführenpython -m pytest -v

3\. Anwendung startenstreamlit run app.py

🧪 Qualitätssicherung \& TestsDie Testsuite in test\_interactions.py und test\_ai\_pipeline.py deckt 25 Prüfpfade ab:collected 25 items



test\_ai\_pipeline.py::test\_clinical\_summary\_fallback\_without\_key  PASSED

test\_ai\_pipeline.py::test\_clinical\_summary\_structure             PASSED

test\_ai\_pipeline.py::test\_gemini\_live\_inference                  SKIPPED (Optionale Live-Inferenz)

test\_interactions.py::test\_cache\_exact\_lookup                   PASSED

test\_interactions.py::test\_phyto\_chelation\_rule                 PASSED

test\_interactions.py::test\_class\_rules\_opioid\_benzo            PASSED

test\_interactions.py::test\_class\_rules\_digoxin\_verapamil        PASSED

test\_interactions.py::test\_synergy\_anticholinergic\_burden       PASSED

test\_interactions.py::test\_synergy\_qt\_prolongation              PASSED

test\_interactions.py::test\_synergy\_cns\_depression               PASSED

test\_interactions.py::test\_synergy\_serotonin\_syndrome           PASSED

test\_interactions.py::test\_synergy\_doac\_bleeding\_risk           PASSED

test\_interactions.py::test\_translator\_brand\_to\_inn              PASSED

test\_interactions.py::test\_translator\_fixed\_dose\_combination    PASSED

test\_interactions.py::test\_priscus\_pim\_detection                PASSED

test\_interactions.py::test\_priscus\_expanded\_catalog             PASSED

test\_interactions.py::test\_renal\_risk\_severe\_cutoff             PASSED

test\_interactions.py::test\_renal\_risk\_moderate\_cutoff           PASSED

test\_interactions.py::test\_intake\_schedule\_chelator\_separation  PASSED

test\_interactions.py::test\_intake\_schedule\_statin\_evening       PASSED

test\_interactions.py::test\_intake\_schedule\_diuretic\_morning     PASSED

test\_interactions.py::test\_bmp\_xml\_parser                       PASSED

test\_interactions.py::test\_medication\_freetext\_parser           PASSED

test\_interactions.py::test\_lab\_monitoring\_checklist\_generation PASSED

test\_interactions.py::test\_pdf\_report\_generation\_binary         PASSED



============================== 24 passed, 1 skipped in 7.84s ==============================

📄 Lizenz \& KontaktEntwickelt für evidenzbasierte Arzneimitteltherapiesicherheit.Autor: Cihan Baydaroglu, BerlinLizenz: MIT License

