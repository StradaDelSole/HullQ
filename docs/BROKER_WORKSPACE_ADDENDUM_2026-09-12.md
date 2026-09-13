# HullQ Broker Workspace — Ergänzungsvorschläge (Addendum)

**Datum:** 2026-09-12
**Bezug:** Ergänzt `HULLQ Broker Workspace – verbindliche Produktdirection` (Owner Decision, unverändert gültig)
**Zweck:** Konkrete Feature-/Qualitätsergänzungen, keine strategische Änderung der Owner-Entscheidung.

---

## 1. Stärkste Ergänzung: "Warum wurde mein Listing nicht gefunden?"

Eine Diagnose-Funktion, die nur mit HullQs deterministischer Fail-Closed-Suche möglich ist — kein Konkurrent kann das ohne dieselbe Architektur nachbauen.

**Konzept:** Pro Listing zeigt HullQ dem Broker eine einfache, konkrete Auswertung:

> "Dein Listing wurde diese Woche bei 14 Suchanfragen ausgeschlossen, weil `draft` als UNKNOWN markiert ist — 9 dieser Anfragen hatten ein Tiefgangs-Limit."

**Warum das wirkt:** Verwandelt die Datenqualitäts-Anforderung von einer abstrakten Bitte ("bitte alle Felder ausfüllen") in eine direkte, für den Broker nachvollziehbare Umsatz-Kausalkette. Gleichzeitig ein Value-Add für den Broker UND ein natürlicher Anreiz, genau die Feldqualität zu liefern, auf der die gesamte Suche beruht — eine sich selbst verstärkende Feedback-Schleife zwischen Produktnutzen und Datenqualität.

**Einordnung:** Late-Stage-Feature (setzt reales Suchvolumen voraus), aber als Konzept jetzt schon ins Domain-Modell einpreisbar (Suchanfragen-Ausschlussgründe müssten ohnehin geloggt werden, sobald echte Suche läuft).

---

## 2. Zwei Punkte aus der Boats-Group-Beschwerde-Recherche, die im aktuellen Dokument fehlen

### 2.1 Broker-Branding
Im aktuellen Broker-Workspace-Dokument nirgends erwähnt, obwohl es der stärkste Einzelfund der Konkurrenzrecherche war: Boats Group entfernt aktiv Broker-Logos/Wasserzeichen von eingestellten Fotos (siehe `hullq-boatsgroup-complaints`, Punkt B2).

**Vorschlag als explizites Requirement:** Broker-Logo/Branding sichtbar auf Fotos und Listing-Seite zulassen und fördern, nicht nur ein generisches "Listed via HullQ". Günstig umzusetzen, hoher Vertrauens-Signalwert, direkter Kontrast zum dokumentierten Incumbent-Verhalten.

### 2.2 Lock-in-freies Export-Versprechen
Bereits früher als Prinzip festgehalten ("dein Inventar bleibt deins, jederzeit exportierbar"), aber nicht im aktuellen Broker-Workspace-Dokument als Requirement verankert.

**Vorschlag:** Als eigenes REQ-BROKER-Requirement aufnehmen (CSV/JSON-Export jederzeit verfügbar), nicht nur als früherer Gedanke unverbindlich im Hintergrund stehen lassen.

---

## 3. Weitere konkrete Feature-Ideen

### 3.1 CSV-/Bulk-Import für Umsteiger
Ein Broker mit z.B. 40 bestehenden YachtWorld-Listings wird diese nicht einzeln von Hand neu eintippen. Ein einfacher Import (auch wenn zunächst nur Grunddaten übernommen werden und der Broker den Rest manuell ergänzt) senkt die Einstiegshürde erheblich. Passt zum bestehenden "easy to enter HullQ"-Prinzip.

### 3.2 Wöchentlicher Engagement-Bericht, auch ohne Lead
Adressiert das "bezahlt, aber wirkungslos"-Gefühl aus der Beschwerde-Recherche (Punkt B8). Auch in der kostenlosen Startphase automatisiert versendbar:

> "Dein Oceanis-30.1-Listing wurde diese Woche 34x angesehen, 8x als Suchtreffer angezeigt."

Baut Vertrauen auf, bevor der erste Lead überhaupt entsteht.

### 3.3 Aggregierte, anonymisierte Nachfrage-Einblicke pro Konfiguration
Sobald ausreichend Suchvolumen vorhanden ist: einem Broker zeigen, wie oft nach Booten mit ähnlicher Konfiguration wie seinem Listing gesucht wird — auch ohne direkten Treffer. Ein Bindungsfaktor unabhängig von einzelnen Leads.

### 3.4 Vorschau-Modus vor Veröffentlichung
Zeigt nicht nur, wie das Listing öffentlich aussehen wird, sondern auch, wie es in typischen/repräsentativen Suchanfragen abschneiden würde. Verbindet Formular-UX direkt mit dem Kernversprechen der Suche, statt beides getrennt zu behandeln.

---

## 4. Technische Qualitätsidee: Offline-tolerantes Entwurfsverhalten

Broker erfassen Daten häufig direkt auf der Werft oder am Steg, wo WLAN/Mobilfunk unzuverlässig ist. Ein Formular, das lokal zwischenspeichert und bei Verbindungsabbruch nichts verliert (echte Offline-Toleranz, nicht nur serverseitiges Autosave bei bestehender Verbindung), ist ein kleiner technischer Mehraufwand mit großem, im Alltag spürbarem Effekt — und eine Stelle, an der die wenigsten Konkurrenzsysteme sauber funktionieren.

---

## 5. Einordnung dieser Ergänzungen

Alle Punkte in diesem Addendum sind als **Ergänzungen innerhalb der bestehenden Owner-Direction** gedacht, nicht als Änderung von deren Umfang, Priorität oder Zeitplan. Abschnitt 1 und 3.3 setzen reales Suchvolumen voraus und sind entsprechend späte Bausteine im Workstream; Abschnitt 2, 3.1, 3.2, 3.4 und 4 sind bereits im Kern-Loop (Listing Creation, Lead-Transparenz) sinnvoll integrierbar.
