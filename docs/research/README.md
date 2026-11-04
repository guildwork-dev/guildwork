<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
> Research note, dated 2026-11-01, not binding. Kept in German as written (ADR-53); the binding documents are docs/architecture and docs/design.

# Recherchen: Index (Stand 2026-10-31)

**Dated, not binding.** Datierte Recherche, Stand 2026-10-31, nicht verbindlich und nicht übersetzt; verbindlich ist die Plattform-Doku.

Dieser Ordner enthält datierte Recherchen. **Keine Datei hier ist verbindlich.** Verbindlich ist die Plattform-Doku in [docs/architektur/](../architecture/README.md); sie verlinkt die Recherchen als Beleg mit Abschnitt. Widersprechen sich zwei Berichte, entscheidet das Lesen der Belege, nicht das Datum. Wo eine Gegenprüfung korrigiert hat, gilt die Korrektur.

Veröffentlichungsstatus nach [12-open-source-and-project.md](../architecture/12-open-source-and-project.md) Abschnitt 4.2: Die hier gelisteten Dateien sind **öffentlich nach Neutralisierung** (Firmen-, Personen- und Hostbezug sowie lokale Pfade entfernt). Private Recherchen stehen nicht in diesem Index.

## 1. Recherchen der dritten Runde (`docs/recherche/`)

| Datei | Datum | Thema | Verbindlich | Veröffentlichung | Hinweis |
|---|---|---|---|---|---|
| [bothy-vorlage-projekt-setup.md](bothy-vorlage-projekt-setup.md) | 2026-10-31 | Projekt-Setup des Vorbildprojekts bothy: CI, Runner, Red-Team-Gate, Lizenz, Release, Governance | nein | öffentlich nach Neutralisierung | Vorlage ist `origin/main`, nicht der lokale Arbeitsbaum. Die ADR-Vorschläge ADR-37 bis ADR-43 und E1 bis E5 dort sind überholt; es gilt die Nummerierung in [09](../architecture/09-decisions.md) |
| [ebene-coding.md](ebene-coding.md) | 2026-10-31 | Standard, Fähigkeiten und Messung für autonomes Coding | nein | öffentlich nach Neutralisierung | |
| [ebene-planung-und-architektur.md](ebene-planung-und-architektur.md) | 2026-10-31 | Standard für Planung und Architektur, Grundlage des Service `architect` | nein | öffentlich nach Neutralisierung | |
| [ebene-pr-fix-und-ci.md](ebene-pr-fix-und-ci.md) | 2026-10-31 | Standard für PR-Fix und CI-Reparatur | nein | öffentlich nach Neutralisierung | |
| [ebene-qa-und-tests.md](ebene-qa-und-tests.md) | 2026-10-31 | Standard für QA und Testerzeugung | nein | öffentlich nach Neutralisierung | |
| [ebene-review.md](ebene-review.md) | 2026-10-31 | Standard für PR-Code-Review | nein | öffentlich nach Neutralisierung | |
| [ebene-statische-analyse-und-security.md](ebene-statische-analyse-und-security.md) | 2026-10-31 | statische Analyse, Quality Gate, Security Review, Plugin-Art `Analyzer` | nein | öffentlich nach Neutralisierung | Empfehlung 4.2 (SonarQube Cloud am Entwicklungs-Repo) und Messung A2 auf SonarQube-Cloud-Ergebnissen sind überholt durch O19 ([12](../architecture/12-open-source-and-project.md) Abschnitt 5.3) |
| [ebene-wissen-standards-doku.md](ebene-wissen-standards-doku.md) | 2026-10-31 | Wissensbasis, Team-Standards, Doku | nein | öffentlich nach Neutralisierung | |
| [ebenen-landkarte.md](ebenen-landkarte.md) | 2026-10-31 | Landkarte der Ebenen im Entwicklungszyklus und ihrer Standards | nein | öffentlich nach Neutralisierung | Abschnitt 2.3, Zeile "E3 bis E6, E9, E10, E20, E21 ... ja", ist überholt: Architektur (E3) war nicht abgedeckt |
| [hosting-und-installation.md](hosting-und-installation.md) | 2026-10-31 | Installation und Hosting je Basis, Treiber, Upgrade, Telemetrie | nein | öffentlich nach Neutralisierung | |
| [open-source-lizenz-und-recht.md](open-source-lizenz-und-recht.md) | 2026-10-31 | Lizenzwahl, Nutzungsbedingungen von Anthropic, CodeRabbit, SonarSource und Werkzeugen | nein | öffentlich nach Neutralisierung | Korrekturen der Gegenprüfung gehen vor; L1 bis L6 sind in O16 bis O20, O2 und ADR-51 aufgegangen |
| [gegenpruefung-lizenz-und-recht.md](gegenpruefung-lizenz-und-recht.md) | 2026-10-31 | Gegenprüfung des Lizenzberichts an den Originalquellen | nein | öffentlich nach Neutralisierung | geht dem Lizenzbericht vor (Marke ist Wort-Bild-Dienstleistungsmarke; API-Guthaben gedeckelt; Sonar-OSS-Plan verlangt Open-Source-Lizenz; Opengrep-Regeln verbieten nur den Verkauf) |
