<!-- SPDX-License-Identifier: Apache-2.0 -->

# OpenSpellGEOS: Deutsch (Deutschland)

## Installation

Schließen Sie PC/GEOS Ensemble, bevor Sie Wörterbuchdateien ersetzen. Entpacken Sie das Paket und kopieren Sie die Dateien .DCT, .THS, .HYP und .GDI nach Ensemble/USERDATA/DICTS. Wählen Sie in den Einstellungen (Preferences) Deutsch (Deutschland) aus und starten Sie Ensemble nach einem Sprachwechsel neu.

Bewahren Sie NOTICES.TXT und LICENSES bei weitergegebenen Kopien auf. Das vollständige Projektarchiv enthält die Werkzeuge zum Erstellen der Dateien, die normalisierten Eingabedaten und die technische Dokumentation. Diesem Paket liegt auch die entsprechende englische Anleitung bei.

## Datendateien

Jede vollständige .DCT-, .THS- oder .HYP-Datei darf höchstens 1000000 Bytes (1 MB) umfassen. Kopfbereich, Index, Auffüllbytes und Nutzdaten zählen mit. Die folgenden Werte gelten für die verteilten Dateien vom 03.10.2026; BUILD.json dokumentiert die Ergebnisse eigener Neuerstellungen.

| Datei | Einträge | Gesamte Bytes |
| --- | ---: | ---: |
| DE_DE.DCT | 130396 | 999766 |
| DE_DE.THS | 3744 | 258145 |
| DE_DE.HYP | 115252 | 999766 |

## Sprachliche Abdeckung

Das Wörterbuch enthält ausdrücklich aufgeführte Wortformen und Zusammensetzungen aus der gemeinfreien deutschen Quelle sowie vier unabhängig erstellte E-Mail-Formen. Die 1114 selbst zusammengestellten Alltagsschreibungen (1102 kanonische Eintragsschlüssel) müssen erhalten bleiben. Der Thesaurus enthält Fachterminologie. Die deutsche Silbentrennung wird mit den ausgewählten Mustern für die reformierte Rechtschreibung vorberechnet. Zusammensetzungen, die im Wörterbuch fehlen, gehören nicht zur derzeitigen Abdeckung.

Vorschläge beruhen auf der Ähnlichkeit der Buchstabenfolgen. Grammatik und Bedeutung ganzer Sätze werden nicht geprüft. Der Wortschatz bleibt begrenzt.

## Kompatibilität und Lizenzen

Die Dateien verwenden das bestehende OLX1-Format und die OpenSpellGEOS-Bibliothek. Beim Nachschlagen werden kleine Zwischenspeicher verwendet und benötigte Daten aus der Datei gelesen; das Wörterbuch wird nicht vollständig in den Arbeitsspeicher geladen. Bibliothek, Konvertierungswerkzeuge und selbst erstellte Ergänzungen stehen unter Apache-2.0. Für die Sprachquellen gelten weiterhin ihre eigenen Apache-kompatiblen Lizenzen oder ihr gemeinfreier beziehungsweise CC0-Status. Die vollständigen ursprünglichen Rechtstexte liegen unverändert in NOTICES.TXT und LICENSES bei.

## Prüfung

Die Prüfungen auf dem Build-Rechner haben jeden Datensatz dekodiert, Datei-Prüfsummen und die 1-MB-Grenzen überprüft, die tatsächlichen Dateien mit dem C-Leser abgefragt, die GDI-Bezeichnungen kontrolliert und alle sechs Rechtschreibwörterbücher bytegenau neu erstellt. Dies ist kein neuer Test der GEOS-Benutzeroberfläche und keine unabhängige sprachliche Redaktion durch Muttersprachler.
