<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
> Research note, dated 2026-11-01, not binding. Kept in German as written (ADR-53); the binding documents are docs/architecture and docs/design.

# Ebene QA und Testerzeugung: Standard, Fähigkeiten, Messung, Lücken

**Dated, not binding.** Datierte Recherche, Stand 2026-10-31, nicht verbindlich und nicht übersetzt; verbindlich ist die Plattform-Doku ([docs/architektur/](../architecture/README.md)).

Stand 2026-10-31. Recherche zur dritten Owner-Runde (Owner, 2026-10-31: jede Ebene auf Weltstandard, Open Source, eigenes Hosting). Betrifft den Service `qa` in [02](../architecture/02-services.md) Abschnitt 4, den QA-Teil von [07](../architecture/07-eval.md) (3.3 und Abschnitt 4) und Stufe 3 in [08](../architecture/08-roadmap.md). Was dort schon belegt steht (TestGen-LLM, ACH, Playwright Test Agents, Factory QA, CodeRabbit Unit Tests, Qodo Cover), wird hier nicht wiederholt, sondern ergänzt oder korrigiert.

Einstufung wie im [README](../architecture/README.md) Abschnitt 6: **BELEGT** (Primärquelle selbst gelesen, hier über WebFetch-Zusammenfassung oder Code), **GESAGT** (Hersteller, Marketing, Drittbericht), **ABGELEITET** (eigener Schluss), **VERMUTET**. Alle Webquellen abgerufen am 2026-10-31. Hinweis zur Methode: WebFetch liefert die Seite durch ein kleines Modell zusammengefasst; Zitate sind deshalb sinngemäß, Zahlen wurden wo möglich an einer zweiten Stelle gegengeprüft (vermerkt). Lizenzdateien und die Agent-Definitionen in `dotnet/skills` wurden direkt gelesen (curl bzw. flacher Klon `dotnet/skills@95e7d0c`, 2026-10-28).

---

## 1. Urteil (Kurzfassung)

1. **Es gibt keinen einzelnen Weltstandard für QA, sondern vier Teilfelder mit je eigener Spitze** (ABGELEITET):
   - **Reproduktionstests (fail-to-pass):** messbar und öffentlich gerankt über SWT-bench. Spitze am 2026-10-31: Microsoft DPIAgent (GPT-5, mit Testauswahl) 87,5 % Erfolg auf SWT-bench Verified, eingetragen 2026-10-23 ([swt-lb] BELEGT als Leaderboard-Eintrag, Prüfverfahren der Einreichungen ungeprüft). Für allgemeine Agenten liefert der OpenHands Index die Kategorie Testing (bestes Modell 91,9, [oh-index] BELEGT).
   - **Unit-Tests mit nachgewiesenem Nutzen:** Der Maßstab für Methode und belastbare Zahlen ist Meta (TestGen-LLM, ACH und seit 2026-01 die "Just-in-Time Catching Tests", [jit] BELEGT). Als Produkt im Entwicklerwerkzeug ist GitHub Copilot vorn: `@Test` in Visual Studio 2026 v18.3 ist GA ([ms-vs-test] BELEGT), und der quelloffene Multi-Agent `code-testing-generator` (MIT) kam am 2026-07-31 ([ms-polyglot] BELEGT, Lizenz selbst gelesen). Diffblue (Java, seit Jahren am Markt) bleibt Referenz im Enterprise-Java-Segment, alle Vergleichszahlen dort sind GESAGT.
   - **E2E im Browser:** Die offene Basis sind die Playwright Test Agents (Apache-2.0). Kommerziell an der Spitze stehen mabl (Enterprise), Momentic (Tests als YAML im Repo, Explorations-Agent "Mo") und QA Wolf (Managed Service). Unabhängige Benchmarks gibt es hier nicht (ABGELEITET aus erfolgloser Suche).
   - **Mutationsgestützte Prüfung im Code-Review:** Google zeigt Mutanten nur auf geänderten Zeilen im Review an und filtert sie nach Kontext ([google-mut] BELEGT).
2. **Korrekturen an unserer Architektur und Vorrecherche:**
   - Qodo ist kein Maßstab für Testerzeugung mehr. Qodo Cover ist seit 2025-06-15 ungepflegt (steht schon in 02). Neu: Der v1-Befehl `test` wurde laut Qodo am 2026-10-01 "ohne direkten Ersatz" entfernt ([qodo-sunset] BELEGT). Die aktuelle Qodo-Doku führt keine Testerzeugung mehr ([qodo-llms] BELEGT).
   - Octomind ist eingestellt (Produkt Ende Mai 2025, Firma Ende Juni 2025; [octomind-closed] GESAGT, die Domain löst am 2026-10-31 nicht mehr auf, selbst geprüft).
   - Gate B der QA in [07](../architecture/07-eval.md) Abschnitt 4 ist so nicht messbar. Es soll "gegen die Testing-Kategorie im OpenHands Index für dasselbe Modell" kalibrieren, aber unser Modell (Opus 5.5) steht dort nicht. Der Snapshot vom 2026-06-30 nennt außerdem weder Teilmenge noch Modus von SWT-bench ([oh-index] BELEGT).
   - Der Bezugswert "Meta 73 %" ist eine Annahmequote aus Test-a-thons nach harten Filtern (TestGen-LLM, [testgen] BELEGT; ebenso 73 % bei ACH, [ach] BELEGT). Mit einer Annahmequote für Test-PRs im normalen Review-Fluss ist er nicht gleichzusetzen.
3. **Größte Lücken** (ABGELEITET, Einzelheiten in Abschnitt 5):
   - Unser QA erzeugt nur "hardening"-Tests, die den heutigen Code festschreiben. Den Modus "catching" (Tests, die auf dem Diff scheitern sollen und damit Bugs finden, samt Prüfung auf Fehlalarme) gibt es nicht.
   - Es fehlen: Test-Qualitätsprüfung der Assertions, Zwang "Test wird vom Standard-Testbefehl des Repos gefunden", Pfad-Policy "QA darf nur Testdateien ändern", Flake-Quarantäne und Fehlerklassifikation sowie öffentlich weitergebbare Eval-Datensätze für ein Open-Source-Projekt.
4. **Messbar machen** (Abschnitt 2.3, Vorschlag für 07): SWT-bench Verified (Unit-Test-Modus, 433 Fälle) und TDD-Bench Verified (Apache-2.0, 449 Fälle) als öffentliche Bezüge für Reproduktion. XRepoTest (Code MIT) für Mehrsprachigkeit mit Mutation Score. Eigene Q2/Q3 bleiben für Mutation und E2E. TestGenEval nur optional, weil die Lizenz CC BY-NC 4.0 ist (selbst gelesen).

---

## 2. Befunde mit Quellen

### 2.1 Wer ist Spitze, und warum

**a) Reproduktionstests (Issue zu fail-to-pass-Test)**

| Eintrag | Wert | Datum | Einstufung, Quelle |
|---|---|---|---|
| SWT-bench Verified, Unit-Test-Modus, Platz 1: DPIAgent (GPT-5, mit Testauswahl), Microsoft | Erfolg S 87,5 %, Coverage-Delta 71,6 % | 2026-10-23 | BELEGT als Leaderboard-Eintrag [swt-lb]; ob die Einreichung vom Betreiber nachgerechnet wurde: ungeprüft |
| Platz 2: LogicStar L*Agent v1 | 84,0 %, 67,7 % | 2025-09-13 | wie oben |
| Platz 3: PatchTwin+Guard (GPT-5) | 82,9 %, 78,7 % | 2026-07-08 | wie oben |
| OpenHands (GPT-5) | 79,8 %, 66,3 % | 2025-08-22 | wie oben |
| DPIAgent (Claude Opus 4.5) | 78,8 %, 65,6 % | 2026-10-23 | wie oben |
| SWT-bench Verified, Skript-Modus: TEX-T (Claude 4 Sonnet), Salesforce | 87,0 %, 69,8 % | 2025-12-17 | wie oben |
| SWT-bench Lite, Unit-Test-Modus: ReProAgent (GPT-5-mini) | 56,2 %, 64,8 % | 2026-04-20 | wie oben |
| OpenHands Index, Kategorie Testing (SWT-bench), bester Wert: claude-fable-5 | 91,9 (Kosten 1,47 USD, Laufzeit 220 je Fall, Einheit laut Seite nicht genannt) | Snapshot 2026-06-30 | BELEGT [oh-index]; Lizenz Apache-2.0; Teilmenge und Modus nicht angegeben |
| OpenHands Index Testing, weitere: claude-opus-4-8 84,3; GPT-5.5 83,4; MiniMax-M3 81,1 (offene Gewichte, 0,11 USD) | | 2026-06-30 | BELEGT [oh-index] |

Messgröße (BELEGT [swt-lb], [swt-repo]): Ein Fall gilt als gelöst, wenn mindestens ein Test am Originalcode scheitert und mit dem Fix besteht und kein Test auf dem gefixten Stand scheitert. Coverage-Delta ist die mittlere Zeilenabdeckung des lösenden Patches. Die Website trägt im Fuß "Last updated on 2025-04-10", enthält aber Einträge bis 2026-10-23; einzelne Zahlen in den News weichen von der Tabelle ab, die Seite nennt eine Neubewertung vom 2025-09-13 mit "rund 2 bis 3 %" höheren Werten (BELEGT [swt-lb]). Für Vergleiche gilt deshalb die Tabelle mit Datum.

Warum Spitze (ABGELEITET): Das ist die einzige QA-Teilaufgabe mit öffentlichem, laufend gepflegtem Ranking auf echten Repos. Die besten Systeme sind Agenten mit Testauswahl und Ausführung, keine Einmal-Prompts. Laut Originalpaper korrelieren Testerzeugung und Reparatur nur schwach, und erzeugte Tests als Filter verdoppelten die Präzision von SWE-Agent ([swt-paper] GESAGT über Suchauszug, Paper nicht selbst gelesen).

**b) Unit-Tests mit nachgewiesenem Nutzen**

| Wer | Was | Zahlen | Einstufung, Quelle |
|---|---|---|---|
| Meta TestGen-LLM (FSE 2024) | verbessert bestehende Testklassen; Filter: baut, besteht zuverlässig, erhöht Abdeckung | 75 % bauen, 57 % bestehen zuverlässig, 25 % erhöhen Abdeckung; im Test-a-thon 11,5 % der Klassen verbessert, 73 % der Empfehlungen angenommen | BELEGT [testgen] |
| Meta ACH (FSE 2025 Industry) | mutationsgeführt: erst gezielte Mutanten, dann Tests, die sie töten; LLM-Agent für äquivalente Mutanten | 10.795 Kotlin-Klassen, 9.095 Mutanten, 571 Tests; Äquivalenz-Erkennung Präzision 0,79 und Recall 0,47, mit Vorverarbeitung 0,95 und 0,96; 73 % der Tests angenommen | BELEGT [ach] |
| **Meta JiT Catching Tests (arXiv 2601.22832, 2026-01-30, FSE 2026 Industry)** | neu: Tests, die auf dem Diff scheitern **sollen**, um Bugs vor dem Landen zu finden; regel- und LLM-basierte Prüfer gegen Fehlalarme | 22.126 erzeugte Tests; diff-bewusste Verfahren erzeugen 4-mal mehr Kandidaten als Hardening-Tests und 20-mal mehr als zufällig scheiternde; Prüfer senken menschlichen Prüfaufwand um 70 %; 41 Kandidaten gemeldet, 8 echte Bugs, davon 4 schwer | BELEGT [jit] |
| Meta Positionspapier "Harden and Catch" (FSE 2025 Keynote) | definiert die JiTTest-Aufgabe | | GESAGT [harden-catch] (Suchauszug) |
| GitHub Copilot `@Test` (Visual Studio 2026 v18.3, GA am 2026-02-11) | erzeugt Tests für Member, Klasse, Datei, Projekt, Lösung oder aktuellen git-Diff; baut, führt aus, repariert, wiederholt; Abdeckung vorher und nachher; nur C#, bezahlte Copilot-Lizenz; auf Roslyn und MSBuild gebaut | | BELEGT [ms-vs-test] |
| Microsoft `code-testing-generator` (2026-07-31, MIT, `dotnet/skills` Plugin `dotnet-test`) | Koordinator mit Unteragenten (Researcher, Planner, Implementer, Builder, Tester, Fixer, Linter) plus `test-quality-auditor`; mehrsprachig (.NET, Python, Go, TypeScript, Java, Rust); ändert keinen Produktionscode; keine Tests mit echten URLs, Ports oder Timing; leichte Mutationsprüfung; Test muss vom generischen Testbefehl gefunden werden | internes Benchmark 152 Aufgaben: 92,1 % gegen 78,9 % bei Standard-Copilot mit gleichem Modell; auf 15 Diff-Aufgaben 15 gegen 0; SWE Atlas 16/44 gegen 12/44 | Mechanik BELEGT (Agent-Dateien selbst gelesen, [ms-skills]); Zahlen GESAGT (Herstellerblog [ms-polyglot], internes Benchmark) |
| Diffblue Cover | Java; Reinforcement Learning statt LLM; IntelliJ-Plugin, CLI, CI ("Cover Pipeline"), "Cover Optimize" führt nur die von der Änderung betroffenen Tests aus, "Cover Reports" | | BELEGT [diffblue-cover] |
| Diffblue Testing Agent (2026-03-24) | Java und Python; delegiert die Codeerzeugung an die vorhandene Agentenplattform (Copilot, Claude Code); zerlegt Projekte in Partitionen; arbeitet in temporären git-Worktrees; nur geprüfte Ausgabe wird committet, der Rest zurückgerollt; läuft lokal (Server plus CLI) | 81 % Zeilenabdeckung gegen 32 % (Senior-Entwickler mit Claude Code) auf 8 Java-Projekten | Mechanik BELEGT [diffblue-agents]; Zahl GESAGT [diffblue-pr], die Benchmark-Seite war ohne Inhalt abrufbar |
| Qodo | v1 `test` am 2026-10-01 ohne Ersatz entfernt; aktuelle Doku dreht sich um Review | | BELEGT [qodo-sunset], [qodo-llms] |

Warum Spitze (ABGELEITET): Meta liefert als einziger industrielle Zahlen mit Peer Review und eine Filterkette, die Halluzination wirksam begrenzt. Microsoft liefert die bislang vollständigste **offene** Agentenaufteilung für Unit-Tests, samt Regeln, die genau unsere Fehlerklassen treffen. Diffblue und Copilot führen nach Verbreitung im Enterprise-Umfeld; Marktanteile sind ungeprüft, es lagen keine unabhängigen Zahlen vor.

**c) E2E im Browser und auf Mobilgeräten**

| Wer | Kern | Einstufung, Quelle |
|---|---|---|
| Playwright Test Agents (Microsoft, Apache-2.0) | Planner, Generator, Healer; Healer liefert bestehenden oder übersprungenen Test, wenn die Funktion kaputt ist; `init-agents --loop=claude\|codex\|opencode\|vscode`; Definitionen sind Anweisungen plus MCP-Tools und sind bei jedem Playwright-Update neu zu erzeugen | BELEGT [playwright-agents], Lizenz selbst gelesen |
| Momentic | Tests als YAML im Repo; Agent-Schleife mit Auto-Heal und Step-Cache; Quarantäne und Fehlerklassifikation im Lauf; `visualDiff` und `assertVisually`; Tests aus PR-Diff und aus User Story; KI-Testauswahl; Mo erkundet eine laufende App aus einem Brief und meldet Befunde mit Belegen, ein zweiter Agent versucht den Bug zu reproduzieren; GitHub-App mit PR-Zusammenfassung und Auto-Heal-Reparatur-PRs; E-Mail, SMS, OTP; Request-Mocking; iOS und Android; lokaler MCP-Server für Coding-Agenten | BELEGT [momentic-docs], [momentic-llms] |
| mabl | Test Creation Agent (Early Access laut Doku), GenAI Assertions (LLM als Richter), Auto Test Failure Analysis, Advanced Auto-Heal, Visual Assist; Paket `@mablhq/playwright-tools` bringt GenAI Assertions in Playwright; Changelog 2026: MCP, Agent-Anweisungen, Fehleranalyse in Slack und Teams | GESAGT [mabl-help] (Suchauszüge der Hilfeseiten, nicht einzeln geöffnet); "85 % weniger Wartung" GESAGT |
| QA Wolf | Managed Service: Mapping-Agent erstellt Abdeckungskarte, erzeugt Playwright- und Appium-Code, 3 Wiederholungen bei Fehlschlag, dann Untersuchung durch Agenten; Traces, Video, Netzlogs; Tests im Kunden-GitHub | GESAGT [qawolf] (nur Marketingseiten gefunden) |
| Testsigma Atto | Agenten Generator, Analyzer, Healer, Bug Reporter laut v2-Doku; Coverage Planner und Optimizer angekündigt, aber nicht verfügbar | GESAGT [testsigma] (Suchauszug der Doku) |
| Factory Automated QA | Zuordnung Diff zu App über `path_patterns`, pass/fail/blocked, Belege, Pflicht-Check, lernt Sub-Skills nach Fehlschlag (Auto-Commit oder Draft-PR) | BELEGT [factory-qa] (ergänzt 02 um "Failure learning") |
| Octomind | eingestellt 2025 | GESAGT [octomind-closed]; Domain löst nicht mehr auf (selbst geprüft) |

Warum Spitze (ABGELEITET): Für Selbsthoster ist Playwright die einzige offene, breit unterstützte Basis mit eigenem Agentenmuster. Die kommerziellen Anbieter differenzieren sich über Betrieb (Parallel-Infrastruktur, Quarantäne, Fehlerklassifikation, Mobile, E-Mail/SMS), nicht über offene Methoden. Einen öffentlichen Benchmark für E2E-Agenten haben wir nicht gefunden (ungeprüft, ob einer existiert).

**d) Mutationstests im Review**

Google: Mutanten nur auf geändertem Code im Code-Review, Begrenzung je Zeile und je Review, kontextbasierte Filterung, Operatorwahl nach historischem Nutzen; Größenordnung 24.000 Entwickler und 1.000 Projekte (BELEGT [google-mut], Abstract).

### 2.2 Fähigkeits-Checkliste des Standards

Spalte "bei uns" bezieht sich auf `docs/architektur` am 2026-10-31.

| Nr. | Fähigkeit | wer hat sie | Beleg | bei uns |
|---|---|---|---|---|
| F1 | Reproduktionstest rot am Basis, grün mit Fix | SWT-bench-Spitze, Devin, unsere Messlatte | [swt-lb] | ja: 02 Abschnitt 4 Stufe 3, 02 Abschnitt 2 Stufe 2 |
| F2 | Harte Filter: baut, besteht mehrfach, bringt Abdeckung | Meta TestGen-LLM, Qodo Cover | [testgen], [qodo-cover] | ja: 02 Abschnitt 4 Stufe 4 |
| F3 | Mutationsgeführte Erzeugung, Äquivalenz-Richter | Meta ACH, Microsoft (leicht) | [ach], [ms-polyglot] | ja: 02 Abschnitt 4 Stufe 4 |
| F4 | **Catching-Modus**: Tests, die auf dem Diff scheitern sollen, plus Prüfer gegen Fehlalarme | Meta JiT | [jit] | **nein** |
| F5 | Mutanten als Review-Hinweis auf geänderten Zeilen | Google | [google-mut] | **nein** |
| F6 | Testqualitäts-Audit: schwache Assertions, Anti-Pattern, Lücken | Microsoft `test-quality-auditor` | [ms-skills] | **nein** |
| F7 | Neuer Test muss vom Standard-Testbefehl des Repos gefunden werden ("Harness Discovery Check"), sonst zählt er als 0 | Microsoft | [ms-skills] `code-testing-implementer.agent.md` | **nein** |
| F8 | Nur Testdateien ändern; bestehende Testdateien nur anhängen; Produktionscode tabu; Build-Manifeste nur zum Registrieren | Microsoft | [ms-skills] | teilweise: 02 Abschnitt 0 begrenzt QA auf Branch, nicht auf Pfade |
| F9 | Keine Tests mit echten URLs, Ports, Timing | Microsoft | [ms-skills] | teilweise: Egress-Allowlist in 05 Abschnitt 2 verhindert Netz, nicht Timing-Abhängigkeit |
| F10 | Nie `skip` oder `ignore` setzen, um grün zu werden | Microsoft, unsere Gates | [ms-skills] | ja: 02 Abschnitt 2 harte Gates, 02 Abschnitt 5 Verbote |
| F11 | Umfang wählbar: Member, Klasse, Datei, Projekt, Lösung, git-Diff | Copilot `@Test` | [ms-vs-test] | teilweise: `scope` und `targets` in 02 Abschnitt 4 Eingang, keine Stufen Klasse/Projekt |
| F12 | Abdeckung vorher und nachher im Bericht | Copilot `@Test`, Diffblue Reports | [ms-vs-test], [diffblue-cover] | teilweise: `mutation.before/after` in `QAReport`, keine Zeilenabdeckung |
| F15 | Ganzes Projekt partitioniert, in Worktrees, nur Geprüftes committen, Rest zurückrollen | Diffblue Testing Agent | [diffblue-agents] | nein (QA ist diff-bezogen) |
| F16 | Nur betroffene Tests ausführen (Test Impact) | Diffblue Cover Optimize, Momentic KI-Testauswahl | [diffblue-cover], [momentic-llms] | teilweise: 02 Abschnitt 4 Stufe 2 "Tests der betroffenen Bereiche", Auswahlverfahren offen |
| F17 | E2E: Planner, Generator, Healer; Healer heilt nie eine kaputte Funktion weg | Playwright | [playwright-agents] | ja: 02 Abschnitt 4 Stufe 5 |
| F18 | Explorativer Agent auf Preview-Deployment mit Befund und Reproduktionsversuch | Momentic Mo, QA Wolf Mapping, Factory QA | [momentic-docs], [qawolf], [factory-qa] | teilweise: Playwright-Planner erkundet, kein Preview-Deployment-Auslöser, kein zweiter Reproduktions-Agent |
| F19 | Diff zu App zuordnen, nur betroffene App testen, pass/fail/blocked mit Belegen, Pflicht-Check | Factory | [factory-qa] | ja: 02 Abschnitt 4 Stufen 1 und 6, 04 Abschnitt 4 `qa.apps` |
| F20 | Tests aus Ticket, User Story oder Akzeptanzkriterien | Momentic, Testsigma, mabl | [momentic-llms], [testsigma] | teilweise: Planner optional als Quelle (02 Abschnitt 4 Abhängigkeiten) |
| F21 | Flake-Quarantäne und Fehlerklassifikation (echter Bug, Test, Umgebung) | Momentic, Testsigma Analyzer, mabl Auto TFA, QA Wolf | [momentic-llms], [testsigma], [mabl-help], [qawolf] | **nein** (nur Flake-Rate als Metrik in 07) |
| F22 | Visueller Vergleich mit Golden Files | Momentic, mabl | [momentic-llms], [mabl-help] | **nein** |
| F23 | LLM-Assertions (semantische Prüfung eines Screens) | mabl GenAI Assertions, Momentic `assertVisually` | [mabl-help], [momentic-llms] | nein |
| F24 | Auth-Flows mit E-Mail- und SMS-OTP, Request-Mocking, Testdaten | Momentic | [momentic-llms] | nein |
| F25 | Mobile (iOS, Android) | Momentic, QA Wolf | [momentic-docs], [qawolf] | nein |
| F26 | Auto-Heal als Reparatur-PR | Momentic, Factory (Sub-Skill-Update) | [momentic-llms], [factory-qa] | teilweise: Healer heilt im Lauf; ob die Heilung als PR zurückgeht, ist offen |
| F27 | Belege: Screenshots, Video, Traces, Netzlogs | Factory, QA Wolf, Momentic, Devin | [factory-qa], [qawolf], [momentic-docs] | ja: `evidence` in `QAReport` (02 Abschnitt 4) |
| F28 | MCP-Server, damit fremde Coding-Agenten QA nutzen | Momentic, mabl, Playwright | [momentic-llms], [mabl-help], [playwright-agents] | teilweise: Plattform-MCP existiert (01), QA-Tools darin nicht benannt |
| F29 | Lernschleife: abgelehnte oder fehlgeschlagene Tests verbessern künftige Läufe | Factory Failure learning, Momentic Memory | [factory-qa], [momentic-llms] | teilweise: Standards-Service (02 Abschnitt 7) nur für Review-Feedback |

F13 und F14 entfallen in dieser Fassung: sie stützten sich nur auf Herstellerdoku, deren Auswertung nach [10](../architecture/10-standards-per-layer.md) Abschnitt 16 nicht weitergeführt wird.

### 2.3 Wie man das Niveau misst

**Öffentliche Datensätze und Lizenzen** (Lizenzdateien selbst gelesen, soweit nicht anders vermerkt):

| Datensatz | Aufgabe | Größe | Lizenz | Eignung für uns |
|---|---|---|---|---|
| SWT-bench (Lite, Verified) | Reproduktionstest aus Issue, Python | Verified 433 Fälle aus 11 Projekten ([swt-hf] BELEGT); Gesamt 1.983, Lite 276 ([swt-paper] GESAGT) | Harness laut README MIT, LICENSE-Datei unter erwartetem Pfad nicht gefunden; Datensatzkarte nennt keine Lizenz (BELEGT [swt-hf]); Herkunft SWE-bench | Gate B Reproduktion; Lizenz klären (offen) |
| TDD-Bench Verified (IBM) | Tests aus Issue vor dem Fix, mit Abdeckung auf der Änderung | 449 Fälle aus SWE-bench Verified | Apache-2.0 (selbst gelesen) | zweiter Bezug, gut weitergebbar |
| Multi-SWT-Bench (arXiv 2609.34752, 2026-09-28) | Reproduktion in 8 Sprachen inkl. Java, TS, Go, Rust, C++ | 1.963 Fälle | Datensatz-Lizenz und Ort nicht genannt (BELEGT, Abstract) | wichtig für C#/TS-fernes Bild; ungeprüft |
| XRepoTest (EMNLP 2026) | Unit-Tests auf Repo-Ebene in Go, Rust, Julia, PHP, Ruby; Mutation Score für Go, Rust, Ruby; Metrik Invocation Rate | Größe ungeprüft | Code MIT (README, BELEGT); Datensatz auf Hugging Face, Lizenz ungeprüft | Unit-Tests mehrsprachig |
| TestGenEval (Meta FAIR, ICLR 2025) | Testdatei erzeugen, Test ergänzen; Abdeckung und Mutation Score | 1.210 Datei-Paare, 11 Python-Repos; Lite 160 | **CC BY-NC 4.0** (selbst gelesen) | nur optional, nicht im Repo ausliefern (ADR-34 sinngemäß) |
| TestEval (NAACL 2025 Findings) | gezielte Zeilen-, Zweig-, Pfadabdeckung auf LeetCode-Programmen | 210 Programme | MIT (selbst gelesen) | nur Rauchtest, kein Repo-Kontext |
| OpenHands Index | Agent-Ergebnisse je Modell, Kategorie Testing | 34 Modelle | Apache-2.0 | Bezugswerte, nicht unser Modell |
| SWE Atlas (von Microsoft genutzt) | Tests müssen eingeschleuste Fehler fangen | 44 Unit-Test-Aufgaben laut [ms-polyglot] | ungeprüft | prüfen |

**Online-Metriken** (ABGELEITET aus den Quellen):
- Annahmequote der Test-PRs und Test-Commits (Meta: Annahme im Test-a-thon, [testgen], [ach]).
- Catching-Präzision: Anteil gemeldeter Catch-Kandidaten, die echte Bugs sind (Meta 8 von 41, [jit]), und menschlicher Prüfaufwand je Kandidat.
- Flake-Rate neuer Tests über n CI-Läufe, Anteil quarantänierter Tests, Heal-Rate und **Falsch-Heilung** (Healer machte grün, obwohl die Funktion kaputt war).
- Mutation Score auf geänderten Zeilen vor und nach QA; Abdeckung auf geänderten Zeilen (Coverage-Delta wie SWT-bench).
- Für den autonomen Durchlauf: Anteil von Agent-PRs, bei denen QA einen Fehler fand, den Reviewer nicht fand, und Revert-Rate nach Merge.

**Vorschlag Gate B je Teilfeld** (ABGELEITET; Startwerte sind Schätzungen, Statistik nach 07 Abschnitt 1):

| Teilfeld | Gate A (nackter Harness, gleiches Modell) | Gate B (Weltstandard) | Bezug |
|---|---|---|---|
| Reproduktion | Erfolg S auf SWT-bench Verified (Unit-Test-Modus) mindestens wie nacktes Claude Code bzw. Codex mit gleichem Modell und einfachem Prompt | S auf SWT-bench Verified mindestens gleich dem besten Leaderboard-Eintrag **mit vergleichbarem Modell** innerhalb des Konfidenzintervalls; zusätzlich TDD-Bench Verified als zweiter Bezug | [swt-lb] Tabelle mit Datum festhalten; [tdd-bench] |
| Unit-Tests | Filter 100 % (wie heute) | Anteil gelöster Aufgaben auf einem öffentlichen Satz (XRepoTest-Teil Go/Rust/Ruby, optional TestGenEval Lite) über dem Wert eines nackten Agenten; Mutation Score auf Q2 über dem des nackten Agenten | Microsoft-Prinzip "spezialisiert gegen nackt mit gleichem Modell" [ms-polyglot] |
| Catching | Fehlalarmquote der Prüfer gemessen | Anteil echter Bugs unter gemeldeten Kandidaten nicht unter Meta (8/41, rund 20 %), auf Q4 (neu, siehe 3.2) | [jit] |
| E2E | Q3 wie heute | Q3 plus Falsch-Heilung 0; kein öffentlicher Bezug, deshalb "Gate B offen" | 07 Abschnitt 4 Regel |

---

## 3. Folgen für unsere Architektur

Konkrete Änderungen je Datei (nicht ausgeführt, nur vorgeschlagen; die Datei hier ist der einzige Schreibvorgang dieses Auftrags).

**[02-services.md](../architecture/02-services.md) Abschnitt 4 QA**
1. **Messlatte erweitern** um Meta JiT Catching [jit], Microsoft `code-testing-generator` [ms-polyglot], [ms-skills], Copilot `@Test` [ms-vs-test], Momentic [momentic-docs], Google Mutation im Review [google-mut]. Qodo-Satz ergänzen: v1 `test` am 2026-10-01 entfernt [qodo-sunset].
2. **Neuer Modus `catch`** in `QARequest.scope` (`unit | repro | e2e | catch | all`): diff-bewusste Erzeugung von Tests, die am Head scheitern; Prüfer (Regeln plus frisches Modell) entscheiden "echter Bug" gegen "Fehlalarm"; Ergebnis ist ein **Befund** an den Reviewer bzw. an `request_human_input`, nie ein Test-Commit. Grund: unsere Unit-Tests schreiben heute den bestehenden Code fest; Bugs im Diff findet so nur der Reviewer.
3. **Filter in Stufe 4 ergänzen:** (a) Discovery-Check: der Test wird vom Standard-Testbefehl des Repos gefunden und ausgeführt; (b) Test-Qualitätsprüfung (keine leeren oder tautologischen Assertions) nach Muster `test-quality-auditor`; (c) keine Tests mit Netz, Ports oder Zeitabhängigkeit.
4. **Pfad-Policy:** QA darf nur Testdateien anlegen oder an bestehende anhängen; Build-Manifeste nur zum Registrieren neuer Testprojekte; Produktionscode nie. Gehört als Regel in die Tabelle "Erlaubte Schreibwünsche" in Abschnitt 0 (`propose_push` nur `test_paths`).
5. **Stufe 6 Bericht:** Zeilenabdeckung auf geänderten Zeilen vorher und nachher, neben Mutation.
6. **Neue Stufe "Fehlerklassifikation"** nach jedem roten Lauf: `product_bug | test_bug | flake | environment`, mit Quarantäne-Liste je Repo (nur Vorschlag, Freigabe durch Mensch). Ein `flake` blockiert kein Merge-Gate, ein `product_bug` immer.
7. **DoD-Tabelle:** Zeile "Gültige Reproduktionstests" auf SWT-bench Verified und TDD-Bench Verified umstellen (siehe 07); neue Zeilen "Catch-Präzision Q4", "Falsch-Heilung 0", "Discovery-Check 100 %".

**[07-eval.md](../architecture/07-eval.md)**
1. Abschnitt 3.3 Q1: Bezug "OpenHands Index für dasselbe Modell" ersetzen durch eigenen Lauf auf SWT-bench Verified im Unit-Test-Modus mit offiziellem Harness, plus nackter Harness mit gleichem Modell; Leaderboard-Tabelle mit Datum ins Eval-Repo übernehmen. Grund: Opus 5.5 steht nicht im Index, Teilmenge und Modus sind dort nicht angegeben [oh-index].
2. Neu **Q4 Catching**: Fälle aus der eigenen Historie, in denen ein später gefundener Bug im PR schon steckte (bothy-Reverts und Fix-Commits), plus eingeschleuste Fehler. Metrik: Präzision und Recall der Catch-Befunde.
3. Neu **Q5 öffentlich**: TDD-Bench Verified (Apache-2.0) und XRepoTest (MIT) als Standard; TestGenEval nur als optionaler Download wegen CC BY-NC.
4. "Annahmequote nahe Meta 73 %" präzisieren: Meta misst im Test-a-thon nach Filtern [testgen], [ach]; als Startwert bleibt die eigene Messung im Pilot.
5. Abschnitt 1 "Eval-Repo (privat)": Für das Open-Source-Projekt braucht es zwei Teile, ein **öffentliches Eval-Paket** (Harness, öffentliche Datensätze oder Download-Skripte, Bezugstabellen) und **private Fälle** je Installation (bothy, Firmen-Repos). Gehört zur Owner-Vorgabe 2 (Open Source); Querbezug zu anderen Ebenen.

**[04-configuration-and-limits.md](../architecture/04-configuration-and-limits.md)**
- Unter `services.qa` (Org-Default Zeile 121 und Repo-Beispiel Abschnitt 4) ergänzen: `test_paths`, `path_instructions`, `catch: { mode: off | shadow | live }`, `quarantine: { auto_propose: true }`, `output: pr | commit`. Egress-Eintrag für QA ist laut Minor M1 offen.

**[08-roadmap.md](../architecture/08-roadmap.md) Stufe 3**
- Fertig-Kriterien ergänzen um Q4 (Catch-Präzision gemessen), Discovery-Check 100 % und den eigenen SWT-bench-Lauf. Catching als Teilstufe 3b nach Unit und Reproduktion, weil es Prüfer und eine Befundschnittstelle zum Reviewer braucht (ABGELEITET).

**[03-flow-and-orchestration.md](../architecture/03-flow-and-orchestration.md) Abschnitt 1a Merge-Gate**
- Bedingung "QA `pass`" präzisieren: `fail` aus Klasse `flake` oder `environment` führt zu Wiederholung oder `blocked`, nie zu Merge; offene Catch-Befunde mit Stufe P0/P1 blockieren.

**[01-plugin-interfaces.md](../architecture/01-plugin-interfaces.md)**
- Plattform-MCP: QA-Tools `qa.run`, `qa.report` für fremde Coding-Agenten benennen (Momentic, mabl, Playwright bieten MCP an). Kein neuer Plugin-Typ nötig; Mutations- und Coverage-Werkzeuge sind Teil des Worker-Images je Sprache (ABGELEITET).

**[06-operations-and-deployment.md](../architecture/06-operations-and-deployment.md)**, wegen Owner-Vorgabe 4 (Hosting auf Azure, AWS, GCP, Hetzner)
- QA braucht im Worker Docker-in-Docker und Chromium (steht in 02). Für Selbsthoster heißt das: das QA-Worker-Image ist schwerer und braucht privilegierte oder Sysbox-Container bzw. MicroVMs. In der Hosting-Matrix je Basis ausweisen, ob QA mit E2E dort lauffähig ist (ABGELEITET; Prüfung je Cloud gehört in die Recherche zur Betriebsebene).

**OSS-Bausteine, die wir übernehmen können** (Lizenz selbst gelesen):

| Baustein | Lizenz | Nutzen |
|---|---|---|
| Playwright, Playwright MCP, Test-Agent-Definitionen | Apache-2.0 | E2E-Stufe direkt |
| `dotnet/skills` Plugin `dotnet-test` (`code-testing-*`, `test-quality-auditor`) | MIT | Agentenaufteilung, Regeln, Discovery-Check als Vorlage |
| Stryker (JS/TS, .NET), PIT, gremlins (Go) | Apache-2.0 | Mutation |
| mutmut (Python) | BSD-artig (Text selbst gelesen) | Mutation |
| cargo-mutants (Rust) | MIT | Mutation |
| SWT-bench-Harness | MIT laut README | Eval |
| TDD-Bench Verified | Apache-2.0 | Eval |
| Mutahunter (LLM-Mutation) | **AGPL-3.0** | nur Idee (ADR-34) |
| Qodo Cover | **AGPL-3.0**, ungepflegt | nur Idee |
| TestGenEval | **CC BY-NC 4.0** | nur optionaler Download |

**Was proprietär bleibt** (ABGELEITET): Metas Systeme (nur Papers), Diffblue (RL-Modell, Agent-Server), mabl, Momentic, QA Wolf, Testsigma (Plattformen), CodeRabbit (Prompts und Pipeline), Copilot `@Test` (Visual-Studio-Integration). Übernehmbar sind dort nur Mechaniken aus Doku und Papers.

---

## 4. Owner-Entscheidungen (nur echte)

| # | Frage | Art | Empfehlung | Grund |
|---|---|---|---|---|
| QA-O1 | Datensätze mit Noncommercial-Lizenz (TestGenEval CC BY-NC 4.0) im öffentlichen Eval-Paket | Recht | nicht ausliefern, nur als optionales Download-Skript mit Lizenzhinweis; Standard sind Apache-2.0- und MIT-Sätze | Das Projekt wird öffentlich und von Dritten auch kommerziell betrieben; ADR-34 schließt Noncommercial-Code schon aus |
| QA-O2 | SWT-bench-Daten trotz unklarer Datensatzlizenz als Gate-B-Bezug nutzen | Recht | nutzen, aber nicht ins Repo kopieren, sondern zur Laufzeit von Hugging Face laden; Lizenz bei den Betreibern (ETH SRI, LogicStar) erfragen, bevor Ergebnisse veröffentlicht werden | einziger gepflegter öffentlicher Bezug für Reproduktion |
| QA-O3 | Ist Mobile-E2E (iOS, Android) Teil des Produktumfangs? | Produkt | nein für Version 1; Web, API, CLI zuerst; Mobile erst nach Nachfrage | braucht Mac- bzw. Emulator-Infrastruktur, die bei Selbsthostern auf Hetzner oder Docker kaum verfügbar ist (ABGELEITET) |
| QA-O4 | Dürfen Catch-Befunde ein Merge blockieren? | Produkt | ja, aber nur P0/P1 mit Prüfer-Urteil "echter Bug"; zuerst im Modus `shadow` messen | Meta zeigt rund 20 % Präzision der gemeldeten Kandidaten [jit]; ungefiltert wäre das Rauschen |

Keine Kosten- oder Konto-Entscheidung nötig: Alle Bezugsläufe gehen mit vorhandenen Modellzugängen; Vergleichsläufe gegen kommerzielle QA-Produkte (mabl, Momentic, Diffblue) würden neue Konten brauchen und sind nicht empfohlen, weil es dort keinen öffentlichen Bezug gibt (fällt unter O13).

---

## 5. Offene Punkte

- Ob die SWT-bench-Leaderboard-Einträge vom Betreiber nachgerechnet oder selbst gemeldet sind: ungeprüft.
- Lizenz der SWT-bench-Daten, von Multi-SWT-Bench, XRepoTest-Daten und SWE Atlas: ungeprüft.
- Diffblue-Benchmark-Methodik: die Seite lieferte keinen Inhalt; 81 % gegen 32 % bleibt GESAGT.
- mabl-Funktionen nur aus Suchauszügen der Hilfeseiten; Status des Test Creation Agent (Early Access oder GA) ungeprüft.
- QA Wolf: nur Marketingseiten, keine technische Doku gefunden.
- Ob es einen öffentlichen Benchmark für E2E-Testagenten gibt: nicht gefunden, ungeprüft.
- Welches Modell hinter Microsofts 92,1 % steht: im Blog nicht genannt (BELEGT, dass es fehlt).
- Ob das Originalpaper von SWT-bench die "Verdopplung der Präzision" so belegt: nur Suchauszug.
- Marktanteile im Testerzeugungsmarkt: keine unabhängigen Zahlen gefunden.
- Querbezug: Die Öffnung des Eval-Repos (Abschnitt 3, 07 Punkt 5) betrifft alle Ebenen und sollte in der Gesamtarchitektur einmal entschieden werden, nicht je Ebene.

---

## 6. Quellen (alle abgerufen 2026-10-31)

- [swt-lb] https://swtbench.com/ (Leaderboard Lite und Verified, Metrik-Definitionen)
- [swt-repo] https://github.com/logic-star-ai/swt-bench (README; Lizenz laut README MIT)
- [swt-hf] https://huggingface.co/datasets/nmuendler/SWT-bench_Verified_bm25_27k_zsp (433 Fälle, keine Lizenzangabe)
- [swt-paper] https://arxiv.org/abs/2406.12952 (nur über Suchauszug, GESAGT)
- [oh-index] https://huggingface.co/datasets/OpenHands/openhands-index (Snapshot 2026.06.30-3015ac6)
- [testgen] https://arxiv.org/abs/2402.09171
- [ach] https://arxiv.org/abs/2501.12862
- [jit] https://arxiv.org/abs/2601.22832
- [harden-catch] https://arxiv.org/abs/2504.16472 (Suchauszug)
- [google-mut] https://research.google/pubs/practical-mutation-testing-at-scale-a-view-from-google/
- [testgeneval] https://arxiv.org/abs/2410.00752; Lizenz https://raw.githubusercontent.com/facebookresearch/testgeneval/main/LICENSE
- [testeval] https://arxiv.org/abs/2406.04531; Lizenz https://raw.githubusercontent.com/LLM4SoftwareTesting/TestEval/main/LICENSE
- [tdd-bench] https://github.com/IBM/TDD-Bench-Verified
- [multi-swt] https://arxiv.org/abs/2609.34752
- [xrepotest] https://arxiv.org/abs/2608.25939 und https://github.com/solis-team/XRepoTest
- [ms-polyglot] https://devblogs.microsoft.com/dotnet/polyglot-unit-testing-agent/ (2026-07-31); Bericht dazu https://www.infoworld.com/article/4206367/microsoft-unveils-open-source-agent-that-generates-unit-tests.html
- [ms-skills] https://github.com/dotnet/skills (Commit 95e7d0c, 2026-10-28; `plugins/dotnet-test/agents/*.agent.md` selbst gelesen; LICENSE MIT)
- [ms-vs-test] https://devblogs.microsoft.com/dotnet/github-copilot-testing-for-dotnet-available-in-visual-studio/ (2026-02-11)
- [qodo-cover] https://github.com/qodo-ai/qodo-cover
- [qodo-sunset] https://docs.qodo.ai/sunsetting-legacy-v1-commands
- [qodo-llms] https://docs.qodo.ai/llms.txt
- [diffblue-cover] https://cover-docs.diffblue.com/
- [diffblue-agents] https://docs.diffblue.com/
- [diffblue-pr] https://www.diffblue.com/wp-content/uploads/2026/03/Diffblue_AI-Testing-Agents_Benchmark-Report_v4.pdf (Benchmark-Bericht des Herstellers: 80,7 % gegen 32,3 % Zeilenabdeckung auf 8 Java-Repos, gelesen 2026-11-01, GESAGT) und Meldung vom 2026-03-24 (Suchauszug, GESAGT); https://www.diffblue.com/benchmarks (ohne Inhalt abrufbar)
- [playwright-agents] https://playwright.dev/docs/test-agents; Lizenz https://raw.githubusercontent.com/microsoft/playwright/main/LICENSE
- [momentic-docs] https://momentic.ai/docs
- [momentic-llms] https://momentic.ai/docs/llms.txt
- [mabl-help] https://help.mabl.com/ (Suchauszüge zu Test Creation Agent, GenAI Assertions, Auto TFA, Advanced Auto-Heal, Changelog 2026)
- [qawolf] https://www.qawolf.com/education/playwright-automation-tool und /automation-testing (Marketing)
- [testsigma] https://testsigma.com/docs/v2/atto/ai-agents/ (Suchauszug)
- [factory-qa] https://docs.factory.com/automations/automated-qa.md
- [octomind-closed] https://www.distillintelligence.com/news/octomind (GESAGT); octomind.dev DNS nicht auflösbar (selbst geprüft)
- Lizenzen Mutationswerkzeuge (selbst gelesen): https://raw.githubusercontent.com/stryker-mutator/stryker-js/master/LICENSE, .../stryker-net/master/LICENSE, https://raw.githubusercontent.com/hcoles/pitest/master/LICENSE.txt, https://raw.githubusercontent.com/boxed/mutmut/main/LICENSE, https://raw.githubusercontent.com/sourcefrog/cargo-mutants/main/LICENSE, https://raw.githubusercontent.com/go-gremlins/gremlins/main/LICENSE, https://raw.githubusercontent.com/codeintegrity-ai/mutahunter/main/LICENSE, https://raw.githubusercontent.com/microsoft/playwright-mcp/main/LICENSE
