# HullQ — Verbindliche Owner-Entscheidung: Sail + Power, jeweils mit vollständiger spezialisierter Technical Search

**Entschieden:** 22. Oktober 2026 (Europe/Vienna)  
**Status:** **OWNER-ACCEPTED STRATEGIC PRODUCT DIRECTION** — Zielbild verbindlich; Implementierung, Go-live und neue Slice-Auswahl nicht bereits erfolgt  
**Projekt:** StradaDelSole/HullQ  
**Tracking:** [Owner-Decision Issue #366](https://github.com/StradaDelSole/HullQ/issues/366)  
**Baseline für Dokumentationsvorschlag:** main 7927ab7dbddac6e3c142c2f4847db5bd2d5cf700; Projektstatus-/0088-Dokumente können historisch ältere Statuswerte enthalten  
**Zweck:** Kanonisch nachvollziehbarer Strategiebeschluss und eigenständig mit Claude überprüfbare Umsetzungsgrundlage.

> **OWNER-BESCHLUSS (22.10.2026):** HullQ wird ein gemeinsamer, qualitativ hochwertiger Yachtmarktplatz für **Segelboote/Segelyachten und Motorboote/Motoryachten**. Beide Bereiche erhalten auf Dauer eine **eigenständige, fachlich anspruchsvolle technische Suche mit derselben methodischen Präzision, Nachvollziehbarkeit, Quellen- und Datenwahrheitsqualität**. Das Sail-Produkt wird zuerst zu einer nutzbaren, stabilen Referenz ausgebaut; anschließend werden die tragfähigen gemeinsamen Grundlagen für ein vollständig ausgearbeitetes Power-Produkt verwendet. Die erforderliche zusätzliche persönliche Entwicklungszeit, auch mehrere Wochen, ist für den Owner kein Grund, Motorboote fachlich nur zweitklassig zu behandeln. **Broker Excellence und Buyer/Technical Excellence sind gleichrangige strategische Säulen.**

## 1. Entscheidung und eindeutige Grenzen

### Verbindlich entschieden

1. **Zielmarkt:** Yacht-/Boots-Listings für **Sail UND Power**; die langfristige strategische Segelboot-Exklusivität ist aufgehoben.
2. **Endzustand:** Nicht C-light als dauerhafte Architektur, nicht bloß ein Motorboot-Kleinanzeigenanhang, sondern eine fachlich leistungsfähige **Power Technical Discovery** in vergleichbarer Tiefe und Qualität wie Sail. „Vergleichbar“ heißt **gleicher Standard**, nicht blind identische Filter.
3. **Ein gemeinsamer professioneller Marktplatz:** Broker mit gemischtem Bestand sind vollwertige Kunden. Beide Kategorien teilen Organisationen, Rollen, Listing-/Medien-Workflows, berechtigte Import-/Exportpfade, Leads, Attribution, Reporting, Rechte, Monitoring und Operations, soweit fachlich passend und geprüft.
4. **Differenzierung:** HullQ ist nicht nur Technical Search. Mindestens gleichrangig sind die aus dem Konkurrenz-/Beschwerde-Research und akzeptierten Produktanforderungen gewonnenen **brokerseitigen USPs**: geringer Aufwand, keine künstliche Bindung, starke Brokeridentität, nachvollziehbare Leadqualität und Geschäftswirkung, faire Vermarktungs-/Rankingregeln.
5. **Echte Fachlichkeit:** Motorboote bekommen ein eigenes belastbares Modell für Rumpf-/Fahrverhalten, Antrieb, Motorisierungen, Varianten, Verbrauch, Reichweite, Ausstattung sowie tatsächliche konkrete Gebrauchtbootzustände.
6. **Qualität statt bloßer Funktionalität:** Kein Feld, Filter, Score oder Badge darf eine gesicherte technische Eigenschaft behaupten, wenn Quellen, Konfiguration oder konkrete angebotene Yacht das nicht tragen.

### Nicht entschieden oder ausdrücklich nicht automatisch autorisiert

- Kein neuer Slice, keine Slice-Nummer, keine Implementierung, keine automatische Zusammenlegung in main durch diesen Text.
- Kein Terminversprechen, kein „beide Produktbereiche müssen vor dem allerersten Sail-Pilot gleichzeitig fertig sein“.
- Keine stillschweigende Änderung bereits akzeptierter Arbeitsabfolgen, von SLICE-0088, seiner Review-Situation oder dem Owner START_SLICE.bat / FINISH_SLICE.bat-Prozess.
- Keine Zulassung realer externer Broker-Uploads/-Feeds/-Piloten vor den bestehenden Sicherheits-, Rechte- und Production-Readiness-STOP/GO-Gates, insbesondere Issue #355.
- Keine unlimitierte automatische Erweiterung auf PWC/Jetskis, sonstige Kleinstwasserfahrzeuge oder spezielle kommerzielle Schiffssegmente; der präzise erste Power-Marktzuschnitt wird in einer eigenen Taxonomieentscheidung festgelegt. **Motorsegler und Mischantriebe dürfen nicht anhand oberflächlicher Labels geraten werden.**
- Keine Behauptung, alle Konkurrenten seien tatsächlich schlechter oder HullQ liefere heute bereits die künftigen Power-Funktionen.

## 2. Entscheidungsbegründung — was sich aus der Diskussion verändert hat

Frühere Position: Sail-only bzw. Sail-first erschien wegen Differenzierung und Entwicklungsfokus risikoärmer. Der Owner hat zurecht auf die **Opportunitätskosten verlorener Broker** hingewiesen: Wer nur einen Teil seines Portfolios auf HullQ anbieten kann, könnte gerade während der Gründungsphase absagen und später schwer zurückzugewinnen sein. Die reine Kontaktaufnahme mit einem Broker verursacht nicht automatisch weniger Aufwand, nur weil wir dessen Power-Bestand ausschließen. Zusätzliche Listings verursachen auf bestehender Infrastruktur zunächst nicht zwingend hohe marginale Speicher-/Transferkosten; operativer Aufwand und Einnahmen müssen dennoch getrennt validiert werden.

Ein zweiter Korrekturpunkt: **Sail Technical Search ist nur ein USP von mindestens zwei großen USP-Familien.** Die zweite, gleichberechtigte Familie ist die bessere, fairere und transparentere **Broker-Plattform**. Diese Vorteile sind überwiegend bootstypunabhängig. Es wäre wirtschaftlich fragwürdig, gemischte Broker dauerhaft von ihnen auszuschließen, wenn die Fachlogik technologisch sinnvoll auf Power erweitert werden kann.

Daraus wurden zunächst C-light (Power-Listings mit Basissuche, vertiefte Sail-Technical Search) und dann eine noch weitergehende Richtung diskutiert. **Der Owner hat sich ausdrücklich für die vollständige, technisch hochwertige Sail+Power-Zielarchitektur entschieden.** C-light bleibt höchstens eine transparente **Zwischenstufe**; es ist nicht das Zielprodukt.

Wichtig: Diese Entscheidung ist eine **Owner-Priorität**, keine mathematisch erwiesene Umsatzprognose. Marktgröße, zahlungsbereite Broker, Käuferakquise und tatsächliche Datenverfügbarkeit müssen weiterhin gemessen werden. Die eigene Arbeitszeit wird nicht als entscheidendes monetäres Verhinderungsargument behandelt, aber Kalender-/Launch-Abhängigkeiten, Datenrechte, Sicherheitsprüfungen, Support, Hosting, Teamkapazität und Betriebsrisiken verschwinden dadurch nicht.

## 3. Gleichrangige Produkt-Säulen und nachzuhaltende Broker-USPs

### Säule A — Buyer/Technical Excellence für Sail UND Power

- Anforderungen statt nur Marke/Modell: harte, zusammen kombinierbare Filter auf **derselben geeigneten Konfiguration**.
- Trennung von **BoatDesign/Modell/Generation/Variante**, konkreter werkseitiger Option und dem **aktuellen PhysicalBoat** mit Umbauten/abweichender Ausstattung.
- Herkunft, Qualifikation und Konfliktbearbeitung jedes technisch wichtigen Fakts; **UNKNOWN**, **CONFLICT**, **CONFIRMED_MATCH**, **CONFIRMED_NON_MATCH** oder **INSUFFICIENT_DATA** nur nach akzeptierten Semantiken.
- Vergleich, nachvollziehbares Matching, angemessene Sensitivität/Unsicherheit, verständliche Begründungen und am Markt tatsächlich auffindbare Angebote. Nicht alle davon sind heute vollständig umgesetzt; Status pro Slice nachführen.
- Eigene fachliche Search-Dimensionen und verständliche Oberflächen für Sail bzw. Power.

### Säule B — Broker Excellence für Sail UND Power

Aus den akzeptierten Owner- und Research-Unterlagen, insbesondere Broker Workspace Product Direction (2026-09-13), Broker Workspace Addendum (2026-09-12), Product Success & Customer Priority (2026-09-11) und Boats Group Feature Adoption Gap Register (2026-10-16):

| Broker-Vorteil / Prinzip | Zielzustand für beide Kategorien | Status-/Wahrheitsgrenze |
|---|---|---|
| Einfacher Einstieg und reduzierte Doppelerfassung | Schneller Draft, Wiederverwendung rechtlich/fachlich zulässiger Informationen, Bulk Import und später rechtmäßig beauftragte Synchronisierung | Import 0083 ist kein fertiger Auto-Sync; Power-Klassifikation fehlt |
| Eigentum/Kontrolle und kein künstlicher Lock-in | Broker kann autorisierte eigene Daten exportieren; klare Quellen- und Lizenzgrenzen | SLICE-0088 war zuletzt REVIEW; XLSB Writer gesondert deferred (#362) |
| Broker-Sichtbarkeit und Branding | Broker/Organisation sichtbar; rechtmäßige Logos/Wasserzeichen nicht allein wegen Branding entfernt | Nur soweit Quelle, Rechte, Privacy und Medienfreigabe passen |
| Transparente Leads | Herkunft, Kampagne, konkretes Listing, Bearbeitung, Zuweisung, Ausgang und Antwortstatus verständlich | Nur tatsächlich erfasste Ereignisse, keine erfundenen Drittplattform-Leads |
| Ehrliches Listing-/Performance-Reporting | Aktivität, Views, Suchtreffer, Leads, Zeitraum und Null-Lead-Phasen nachvollziehbar | Periodische Berichte REQ-BROKER-028 noch verpflichtender Gap (#357) |
| Besserer Broker-Workflow | Inventar, Medien, Status, Verkauf, Nachverfolgung leichter und weniger fehleranfällig | UX/Benchmark plus reale Broker-Validierung notwendig |
| Fairer, unabhängiger Such- und Vermarktungsmechanismus | Kein Pay-to-win, keine gekauften organischen technischen Treffer, Quellen-/Verifizierungsstatus nicht mit Bezahlung verwechseln | Bestehende organische Neutralität bleibt Pflicht |
| Listing-Eignungs- und Vollständigkeitsfeedback | Fehlende Angaben und technische Auffindbarkeitsgründe verständlich machen | Tatsächliche Nutzer-Suchen/Analytics erst nach echten Datenmengen; kein erfundener Impact |
| Bestands- und Partnerfreiheit | Kein Exklusivzwang, kein bewusst erschwerter Austritt; klare kontrollierbare Datenrechte | Keine fremden Inventare/Bilder/Feeds ohne Freigabe oder Nutzungsrecht |

**Normatives Ziel:** Broker Excellence ist **kein Power-Notbehelf** und nicht weniger wichtig als Technical Search. Eine spätere Power-Einführung ohne diese Qualitätsprinzipien wäre unvereinbar mit der Owner-Richtung.

### Kein unbewiesener Wettbewerbssieg

Die Research-Funde sind produktstrategische Hinweise, keine pauschalen Tatsachen über jede große Listingplattform. Vergleichsrelevante Aussagen zu Konkurrenzangeboten, Brokerbeschwerden und Preisen vor externer Kommunikation mit datierten Primärquellen nachprüfen. Im bestehenden Launch-Benchmark wurden einige Brokeraufgaben als DEFICIENT oder NOT_COMPARABLE eingestuft; kein pauschaler „HullQ ist bereits besser“-Claim.

## 4. Technische Zielarchitektur

**Ein gemeinsames System; zwei Fachmodule; eine Broker- und Listingwahrheit.**

1. **Shared Identity & Marketplace Kernel:** Publisher/Organisation, Owner-Direct-Rechte wo akzeptiert, PhysicalBoat, MarketEpisode, NativeListing, Offer, Broker Media, Lead, Lifecycle, Freshness, Audit und Schutz der Quellrechte.
2. **Shared Truth & Search Primitives:** Typisierte Datenquellen und Anspruchsarten, zeitliche/konfigurationsbezogene Qualifikation, FieldResolution, UNKNOWN/CONFLICT, deterministische AND-Prädikate, reproduzierbare Klassifikation, Begründungs-/Evidence-Read-Model.
3. **Sailing Domain:** eigene Design-/Variantenschemata und bewiesene Segelbootkriterien (Rigg, Kiel, Ruder, Verdrängung, Segelplan usw.).
4. **Power Domain:** eigene Design-/Variantenschemata und bewiesene Motorbootkriterien (Rumpf-/Fahrverhalten, Antrieb/Motorpaket, Treibstoff, Leistung, Geschwindigkeits-/Verbrauchs-/Reichweitenprofile, Stabilisierung usw.).
5. **Shared Listing Discovery:** allgemeine veröffentlichte Bestandsübersicht und Basisfilter für Sail + Power, getrennt von zusätzlicher domänenspezifischer technischer Suche.
6. **Shared Broker Application:** gleicher Workspace und fachlich passend differenzierte Editoren, Import, Export, Prepublication Search-fit, Media, Leads, Reporting und Rechte.

**Entscheidend:** Den akzeptierten Sail-Code nicht gedankenlos kopieren oder alles in eine gigantische generische Enum umformen. Vor Änderungen **lesende Architektur-Reconciliation**: Tatsächlich wiederverwendbare Mechanik identifizieren und nur die nötigen Grenzen abstrahieren. Sail-Regressionen verhindern und jedes neue Power-Feature mit eigenen fachlichen Tests beweisen.

### Konkrete heute sichtbare Voraussetzungen (aus Repo-Stand beim Beschluss)

- PhysicalBoat kann design-unresolved existieren, aber die akzeptierte technische native Suche verwendet designverknüpfte Kandidaten (in src/hullq/persistence/inventory_search.py explizit boat_design_ref IS NOT NULL).
- Die NautiX-1.4-Importlogik (src/hullq/domain/import_nautix.py) akzeptiert bewusst nur Sailing-Kategorien; Power wurde bisher als außerhalb des Supply-Scope behandelt.
- Die gemeinsame Draft-Struktur enthält noch keinen verbindlichen Sail/Power-Typ.
- Eine eigenständige öffentliche allgemeine Browse-/Suchfläche für designlose Power-Listings ist nach aktueller Dateiprüfung noch nicht nachgewiesen; eine einzelne öffentliche Listing-Detailseite existiert.
- Der bestehende Broker-/Marktplatzkern und der Konfigurationssuchkern liefern bedeutende Grundlagen, **nicht** schon ein fertiges Power-Datenprodukt.
- Historische PROJECT_CONTEXT.md / docs/PRODUCT_SCOPE.md beschreiben noch „Sailboat-only“ bzw. einen Suchlayer ohne nativen Marktplatz. Spätere Owner-Entscheidungen haben die Marketplace-Strategie schon verändert; dieses neue Owner-Dokument überschreibt **zusätzlich nur die langfristige Sail-only-Vessel-Grenze**. Andere Normen bleiben bindend.

## 5. Power-Fachmodell: explizite Wahrheits- und Variantenanforderungen

**Vorschlag für spätere Fachdefinition, nicht bereits implementierter Feldvertrag:**

| Ebene | Beispiel | Zwingende Genauigkeitsregel |
|---|---|---|
| Vessel/Design/Familie | Modell, Generation, Rumpfform, Verdränger/Semigleiter/Gleiter | Marketingklassifikation ≠ automatisch physikalisch bestätigter Zustand |
| Factory configuration / motorization | Motoranzahl, Hersteller, Typ, Leistung, Welle/Z/Pod/Wasserjet/Außenborder | Werkseitige Optionen dürfen nicht als tatsächliche Bootsausstattung behauptet werden |
| PhysicalBoat aktuelle Konfiguration | Motortausch, Upgrade, Refit, aktuelle installierte Aggregate | Nur aktuelle, qualifizierte Publisher-/Quellenclaims; mit Provenienz/Datum |
| Betriebs- und Messbedingungen | Geschwindigkeit, Verbrauch und Reichweite bei definiertem Setup | Einheit, Geschwindigkeit, Last, Reserve, Wetter/See, Messmethode und Gültigkeit festhalten; nicht bedingungslos extrapolieren |
| Zustands-/Wartungsdaten | Motorstunden, Servicehistorie, Untersuchung | Anzeige/Quelle vom bestätigten technischen Zustand unterscheiden; keine unbelegte Prognose von Lebensdauer |
| Energie und Hybride | Diesel/Benzin, Elektrik, Hybrid, Kapazitäten | Fachlich typisierte Zustands- und Messgrößen statt fiktiver normalisierter Einheit |
| Käuferkriterien | z. B. Reichweite >= X sm bei >= Y kn | Nur positive Treffer bei gleicher geeigneter Power-Konfiguration **und** ausreichend belegtem Kontext der konkreten angebotenen Yacht |

Eine umfangreiche Power-Datenbasis benötigt ein **breites Modellidentitätsuniversum mit progressiver Verifizierung**. Ein schmales Demo-Korpus bleibt Forschungs-/Proof-of-Concept-Grundlage und darf nicht als Marktdeckung ausgegeben werden. Quellenrechte, Herstellerbroschüren, Varianten, historische Daten und Datenqualität müssen eigens untersucht werden.

## 6. Reihenfolge der Umsetzung – verpflichtendes Ziel, bewusst gestufter Weg

### Phase 0 — Laufende Arbeit ordnungsgemäß schließen

- SLICE-0088 in seinem vereinbarten Umfang fertig bewerten/akzeptieren/abschließen; keine heimliche Motorboot-Erweiterung in den offenen Export-Review.
- Vor erster externer realer Brokerverarbeitung die verbindliche Issue-#355-Härtung und alle passenden Production/Onboarding-Rechte-/Sicherheits-Gates nach akzeptiertem Prozess erfüllen.
- Bereits akzeptierte P0-Brokeranforderungen, insbesondere periodische auch Null-Leads umfassende Performanceberichte (#357), bleiben im vorgesehenen Launch-Gate.
- Keine unbegrenzte Zusage, Sail müsse *jeden denkbaren Filter* fertig haben. Nötig ist eine saubere, sinnvoll benutzbare, validierte Referenz.

### Phase 1 — Sailing-Produkt als Referenz stabilisieren

- Ganzheitlicher Käufer→Listing→Lead→Broker→Outcome-Weg, technische Suche, Broker-UX und Daten-/Medienwahrheit zuverlässig beweisen; Datenabdeckung und bislang offene Pflichtfunktionen nachziehen.
- Fachliche/technische Komponentengrenzen dokumentieren; messbare Benchmarks für Search-Qualität und Broker-Workflows erfassen.

### Phase 2 — Lesendes Dual-Domain-Design und Power-Korpussuche

- Aktuelles Repo/DB/API/Web gegen den Owner-Beschluss prüfen: Typ/Kategorie, Designmodell, konkrete Claims, Search Engine, Import NautiX/Spreadsheet, Export, Discovery, SEO, Locale, Berechtigungen.
- Vorhersagen über „wenige Wochen“ oder „N Slices“ vermeiden; echte Engineering-Delta-Analyse mit Test-/Migrations-/Review-Pfaden erstellen.
- Validierte Power-Quellen/Rechte und ein schwierig ausgewähltes Modell-/Motorisierung-Benchmark-Korpus bestimmen; Problemfälle inkludieren (gleiche Baureihe mit verschiedenen Motorsätzen, Motorumbau, echte/reduzierte Reichweite, Datenausfall).

### Phase 3 — Gemeinsame Vessel-Klassifikation und Native Browse

- Explizite Sail/Power/Motorsegler/unklar-Klassifikationssemantik inkl. Broker-Origin, UNKNOWN/CONFLICT, manueller Klärung; keine willkürliche Verifikation von Importlabels.
- Backward-kompatibler, abgesicherter Schema-/Migrations- und Exportvertrag; Rechte/ACL/tenant isolation/unbekannte Kategorien und importbedingte Updates testen.
- Verifizierbare allgemeine Browse-/Basis-Suche für native Listings, fünf vorhandene Locales, klare kategoriale Eingänge, Indexability/Canonical/SEO ohne Duplicate-/thin-content-Missbrauch.
- Klares Testinvariant: Nur zulässige Sail-Designkonfigurationen erreichen Sail-Technical-Confirmed-Match; Power darf nicht aufgrund von Hull/Model-Namen als Sail erscheinen.

### Phase 4 — Vollwertige Power Technical Search

- Fachdomäne mit Generationen, Varianten, Motorisierungskonfigurationen, aktuellen PhysicalBoat-Claims, technischer Source Registry/Bridges, UNKNOWN/CONFLICT und Suchkriterien entwickeln.
- Multi-Kriterium-Suche mit **derselben epistemischen Strenge** wie Sail; ernsthafte Power-Buyer-Scenarios und No-False-Positive-Tests; tatsächliche angebotsbezogene Evidence in Buyer Search und Broker Search-fit.
- Spezialisierte technische Oberflächen, Vergleiche und später Monitoring/Alerts in kontrollierten, überprüften Erweiterungen.

### Phase 5 — Power-Datenuniversum und nachgewiesener Marktplatzbetrieb

- Breites Bootstyp-/Modelluniversum mit ehrlicher Evidenzabdeckung; auf echte Käuferjobs optimiert, nicht allein Anzeigemenge.
- Gezielte Akquise von Brokersegmenten (Sail, Mixed, Power), Rückmeldungen/Arbeitsaufwand/Preisbereitschaft und tatsächliche Leads messen.
- Launch-Reihenfolge anhand **separater technischer und kommerzieller Gates** freigeben. Ein ggf. früher freigegebener Power-Listingmodus muss öffentlich auffindbar und klar als reduzierte Funktionsstufe bezeichnet werden, ohne den verbindlichen Endzustand auf C-light abzusenken.

**Diese Phasen sind Leitplanken, keine automatisch gestarteten nummerierten Slices.** Vor jedem neuen Slice: kurzer Owner-Überblick, ordnungsgemäße Reconciliation, unabhängige READY/Review, normale START-/FINISH-Prozedur; Owner wählt und akzeptiert Implementierung ausdrücklich.

## 7. Non-negotiable Qualitäts- und Sicherheitsschranken

- Keine Wahrheitserfindung: Design-, Varianten- und konkrete Bootsbehauptungen strikt separieren; UNKNOWN/CONFLICT bleiben sichtbar.
- Keine falschen bestätigten technischen Treffer bei fehlendem Kontext, widersprüchlichen Quellen, unzulässigen Messbedingungen oder Design-/PhysicalBoat-Mismatch.
- Kein Import fremder Medien, Drittbrokerdaten oder proprietärer Portalinhalte ohne Berechtigung und vereinbarte Datennutzung.
- Kein Power-Launch allein aufgrund ausreichenden Speichers; zusätzliche Rohdaten, Medien, Lead-/Moderations-/Supportpflichten benötigen operative Budget-/Limit-/Retention-Gates.
- Keine bezahlte Manipulation der organischen technischen Klassifikation; Werbung von organischem Match strikt getrennt.
- Kein Exklusivzwang und kein künstliches erschwerendes Export-/Exit-Verhalten gegenüber Brokern.
- Kein neues Power-Material darf die bisher akzeptierten Sail-Funktionalitäten, Datenschutz-/MFA-/Rollenregeln, Publishing-Lifecycle oder Monitoring/Backup/Incident-Readiness stillschweigend verändern.
- Produktversprechen extern nur gemäß tatsächlich gelieferten Fähigkeiten; künftige Power-Suche nicht vorzeitig als vollständig/gleichwertig ausgeben.

## 8. Brand-, Produkt- und Markteintrittsfolgen

**Übergeordnete Positionierung (Richtung, keine freigegebene Werbekampagne):**

> HullQ — a better yacht marketplace for buyers and brokers, built around trustworthy technical decisions, transparent operations and freedom of inventory.

Der Claim „Find boats by what they are“ passt weiterhin für Sail + Power. „Nice yacht. Wrong keel.“ bleibt ein gültiges **Sail-spezifisches** Motiv, kein Beweis allgemeiner Power-Spezifikation. „Built for sailing. Not everything that floats.“ oder „nur Segelboote“ **nicht als gesamte dauerhafte HullQ-Identität festschreiben**, denn dies widerspricht der neuen Owner-Entscheidung.

Etablierte Marktteilnehmer nicht persönlich angreifen oder pauschal Abzocke unterstellen. Die aus der Beschwerde-Recherche abgeleiteten Brokerprobleme konstruktiv, präzise und überprüfbar adressieren. Humor bleibt in Kampagnen möglich; operative Broker- und technische UIs bleiben sachlich.

**Zu PR #365 / Issue #364:** Der noch offene, ungemergte Marken-Draft darf diese Owner-Vessel-Scope-Entscheidung nicht überstimmen. Bei späterem Merge/Brand-Publishing prüfen und gegebenenfalls Sail-exklusive Richtungen zu domänenspezifischer Copy umklassifizieren.

## 9. Prüfpunkte für Claude / unabhängiges Architektur-Review

Claude soll **nicht erneut abstimmen, ob Sail-only schöner wäre**, sondern die bereits **getroffene Owner-Richtung** auf technische, regulatorische und wirtschaftliche Umsetzbarkeit prüfen, Risiken transparent machen und konkrete bessere Umsetzung vorschlagen.

1. Welche tatsächlichen Source-of-Truth-Modelle, Registry-/Search-Primitive und Brokerfunktionen auf aktuellem HEAD sind sauber gemeinsame Grundlagen, und was ist Sail-spezifisch?
2. Welche minimalen backward-kompatiblen Änderungen brauchen wir für funktionale Kategorie/Power-Supply und eine für beide Typen brauchbare echte native Listing Browse/Search?
3. Wie werden PowerDesign/Generation/Motorisierungs-Konfiguration und aktuelle PhysicalBoat-Motor-/Refit-Fakten mit belegtem Varianten- und Zeitbezug modelliert?
4. Welche eigenen Hard Filter sind beim Motorbootkauf wirklich entscheidend, ohne Datenlücken oder unklare Einheitensemantik zu verschleiern?
5. Wie würde bedingungsabhängige Geschwindigkeit/Verbrauch/Reichweite modelliert und im Search fail-closed beurteilt? Muss das ein Curve/OperatingPoint-Modell sein?
6. Wo bestehen echte Doppelcode-, Migration-, Import-/Export-, SEO-, Locale-, Berechtigung-/Privacy- und Sicherheitsrisiken? Bitte Dateien, Tests, Invarianten, DB-Migrationen nennen.
7. Welche Referenz- und Primärquellen können ein ausreichend breites Power-Modelluniversum **rechtssicher** und mit nachvollziehbarem Prüfaufwand tragen? Welche Felder bleiben vorerst UNKNOWN?
8. Wie wird die Arbeit am Power-Fachprodukt gestuft, **ohne** SLICE-0088, #355, #357, Freigaben und den ersten zulässigen Käufer-Broker-Test zu unterbrechen?
9. Welcher Teil von C-light kann bei einer späteren vollständigen Power Technical Search sinnvoll wiederverwendet werden, statt zu Wegwerfcode zu führen?
10. Wie testen wir die Gleichrangigkeit der Broker-USPs für Sail+Power sowie echten kommerziellen Mehrwert, statt nur größeren Listingbestand zu erzeugen?
11. Welche kritischen Annahmen dieses Owner-Plans sind derzeit im Code **nicht** verifiziert? Evidenz bitte als CODE/TEST/CONTRACT/HYPOTHESIS markieren.
12. Welche konkreten nächsten **docs-only** Architektur-/Readiness-Artefakte sollten wir nach regulärem Owner-Slice-Abschluss vorbereiten? Noch keine Implementierung/Branch-Neunummerierung ohne Owner-Auswahl.

**Erwarteter Review-Output:** Konkret prüfbare Gap-Matrix, Shared-vs-Domain-Boundary-Diagramm, Risiken, Abhängigkeiten, MVP/Release-Gates, nachvollziehbare Aufwandsszenarien und eine in kleine vertikale, testbare Schritte zerlegte Umsetzung – **unter Anerkennung der Owner-Richtung**, nicht als Gegenabstimmung.

## 10. Autorität, laufender Zustand und Dokumentenpflege

- Neue Owner-Vessel-Scope-Richtung **überstimmt frühere Aussagen**, dass HullQ langfristig ausschließlich Segelyachten bedient. Frühere historische Recherche und Sail-Anfangsumfang bleiben als Geschichte gültig.
- Spätere bereits akzeptierte native Broker-first + Owner-Direct Marketplace-Entscheidungen überstimmen weiterhin ältere „HullQ ist kein Marketplace“-Abschnitte in PROJECT_CONTEXT.md/PRODUCT_SCOPE.md. Dieses Dokument ändert **keine** anderen bereits akzeptierten Verantwortlichkeiten.
- docs/PRODUCT_EXECUTION_PLAN.md, docs/PROJECT_STATE.md, Broker Workspace Direction, Product Success & Customer Priority und Competitive Gap Register sind in ihrer operativen Reihenfolge/Quality Gate-Logik weiter controlling, soweit nicht konkret bei langfristiger Kategorie-/Product-Scope-Richtung durch diese Owner-Entscheidung superseded.
- **Repositorystatus bei Dokumenterstellung:** docs-only Owner-Decision auf eigenem Branch und Draft-PR zur unabhängigen Prüfung; **nicht** automatisch main oder bereits Code. Die verbindliche Owner-Anweisung ist erteilt; ihre kanonische Wirkung im Repository erfordert Review/Merge entsprechend bestehender Verfahren.
- Kein impliziter Start von SLICE-0089 oder Power-Implementierung; nächste Umsetzung nur nach regulärem Slice-Reassessment und ausdrücklicher Owner-Auswahl.

### Relevante Quellen und Verweise

- [Issue #366 – Sail + Power Owner Decision](https://github.com/StradaDelSole/HullQ/issues/366)
- [Issue #355 – Pre-pilot runtime safety](https://github.com/StradaDelSole/HullQ/issues/355)
- [Issue #356 – Wettbewerbs-/Feature-Gap-Register](https://github.com/StradaDelSole/HullQ/issues/356)
- [Issue #357 – Broker-Reporting](https://github.com/StradaDelSole/HullQ/issues/357)
- [SLICE-0088-Readiness](https://github.com/StradaDelSole/HullQ/blob/main/docs/slices/SLICE-0088-broker-inventory-portability-export.md)
- [Broker Workspace Product Direction](https://github.com/StradaDelSole/HullQ/blob/main/docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md)
- [Broker Research/Addendum](https://github.com/StradaDelSole/HullQ/blob/main/docs/BROKER_WORKSPACE_ADDENDUM_2026-09-12.md)
- [Boats Group Competitive Register](https://github.com/StradaDelSole/HullQ/blob/main/docs/governance/BOATS_GROUP_COMPETITIVE_CAPABILITY_REGISTER_2026-10-16.md)
- [Draft Branding PR #365](https://github.com/StradaDelSole/HullQ/pull/365)

**Kurzform für spätere Übergaben:**

> **Owner-accepted 2026-10-22:** HullQ ist strategisch ein gemeinsamer Sail+Power-Yachtmarktplatz mit gleichwertiger, domänenspezifischer Technical Search für beide Bootskategorien und gleichrangigen bootstypneutralen Broker-USPs. Sail wird zuerst als zuverlässige Referenz finalisiert, Power darauf als eigenständige Fachdomäne aufgebaut. Ein eventuell früher Power-Listingmodus ist nur Zwischenstufe. #355 / SLICE-0088 / P0 Broker Gates und reguläre Slice-/Owner-Freigabe gelten uneingeschränkt.
