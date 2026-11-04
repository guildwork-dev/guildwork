<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
> Research note, dated 2026-11-01, not binding. Kept in German as written (ADR-53); the binding documents are docs/architecture and docs/design.

# Ebenen statische Analyse, Quality Gate und Security Review: Standard, Messung, Anbindung

**Dated, not binding.** Datierte Recherche, Stand 2026-10-31, nicht verbindlich und nicht übersetzt; verbindlich ist die Plattform-Doku ([docs/architektur/](../architecture/README.md)).

Stand 2026-10-31. Auftrag: Owner-Vorgaben vom 2026-10-31 (dritte Runde): Niveau des Weltstandards je Ebene, Open Source, selbst hostbar auf Azure, AWS, Google Cloud und Hetzner, CodeRabbit und SonarQube am Entwicklungs-Repo wie in bothy, nur Planung. Kürzel und Einstufungen wie im [README der Architektur](../architecture/README.md) Abschnitt 6. Alle Webquellen abgerufen am 2026-10-31; die Abrufwerkzeuge liefern Zusammenfassungen durch ein kleines Modell, Zitate sind sinngemäß. "Suchauszug" heißt: nur über die Websuche gelesen, nicht an der Seite selbst.

Abgrenzung: Die parallele Recherche [ebenen-landkarte.md](ebenen-landkarte.md) schlägt eine neunte Plugin-Art `Analyzer` vor; dieser Bericht übernimmt den Namen und füllt den Vertrag für diese Ebene aus.

---

## 1. Urteil (Kurzfassung)

1. **Statische Analyse nicht nachbauen, sondern anbinden.** Die Ebene hat zwei verschiedene Standards: für Codequalität und Quality Gate ist es SonarQube (Marktstellung und das Konzept "Quality Gate auf neuem Code"), für Security-SAST die Spitzengruppe aus Checkmarx, Snyk, Veracode, OpenText, Black Duck und HCL laut Gartner und Forrester 2025; im Open-Source-Bereich sind es CodeQL, Semgrep CE und Opengrep. Keiner dieser Analyzer lässt sich in vertretbarer Zeit gleichwertig nachbauen, und alle sprechen SARIF 2.1.0 oder ein Format, das sich dahin abbilden lässt. Unsere Plattform bindet sie über die neue Plugin-Art **`Analyzer`** an, mit SARIF 2.1.0 als Normalform. Das ist ABGELEITET aus den Befunden 2.1 bis 2.4.
2. **Der Wert liegt in der KI-Schicht darüber, und dort ist der Standard 2026 neu gesetzt.** Claude Security (vorher Claude Code Security), Codex Security (vorher Aardvark), Semgrep Assistant, Aikido AutoTriage, Snyk Agent Fix, Copilot Autofix und CodeMender folgen demselben Muster: (a) Regelwerkzeug oder LLM liefert Kandidaten, (b) ein Verifier versucht jeden Befund zu beweisen oder zu widerlegen, mit Erreichbarkeit, Ausnutzbarkeit und wenn möglich Reproduktion in der Sandbox, (c) Bedrohungsmodell je Repo als Kontext, (d) Fix gilt nur, wenn der Alarm beim erneuten Scan verschwindet und die Tests grün bleiben, (e) Team-Gedächtnis für Fehlalarme. Unsere Architektur hat (b) und Teile von (e) für den Reviewer, aber (a) mit Analyzer-Kandidaten, (c), (d) als Pflicht und den geplanten Ganz-Repo-Scan nicht.
3. **Lizenzlage für ein Open-Source-Projekt:** Frei mitlieferbar als eigene Prozesse sind Opengrep (LGPL-2.1), Semgrep CE als Engine (LGPL-2.1), SonarQube Community Build (LGPL-3.0, als eigener Begleitdienst), ast-grep (MIT), gitleaks (MIT), osv-scanner, Trivy, Checkov, Bandit, gosec (alle Apache-2.0). **Nicht mitlieferbar** sind: die Semgrep-Registry-Regeln (Rules License: nur interne Nutzung, kein Angebot als Dienst), die CodeQL-CLI (nur Open-Source-Code auf GitHub.com oder mit GitHub-Lizenz, kein Hosting für andere) und der SonarQube MCP Server (Source-Available-Lizenz SSAL). CodeQL kommt deshalb nur als "bring your own": Ergebnisse aus dem Code Scanning des Nutzers lesen, nicht selbst ausführen. Alles BELEGT, siehe 2.4.
4. **SonarQube Community Build kann keine PR-Analyse.** Branch- und PR-Analyse sowie PR-Dekoration beginnen bei der Developer Edition. Für selbst hostende Nutzer ohne Bezahl-Edition muss die Plattform das Quality Gate auf neuem Code deshalb selbst aus SARIF-Baselines berechnen können ("Plattform-Gate"), mit Sonar als optionaler Quelle. Für das öffentliche Entwicklungs-Repo passt SonarQube Cloud (laut Hersteller kostenlos für Open-Source-Projekte, GESAGT) plus lokaler Community Build, genau wie in bothy.
5. **Messbarkeit:** Für den deterministischen Teil (Analyzer anbinden, Gate rechnen) ist Gate B eine Paritätsprüfung gegen das Originalwerkzeug und gegen SonarQubes Sonar-way-Gate. Für den KI-Security-Teil gibt es öffentliche Datensätze mit klarer Lizenz (Juliet CC0, OpenSSF CVE Benchmark MIT, CyberGym Apache-2.0, OWASP Benchmark GPL-2.0, CWE-Bench-Java laut Index MIT) und wenige veröffentlichte Bezugswerte, fast alle vom Hersteller selbst gemessen. Gate B wird deshalb als "mindestens die Vereinigung von Opengrep und CodeQL unter gleichen Bedingungen, bei Fehlalarmen auf gepatchten Versionen nicht schlechter" definiert, siehe Abschnitt 3.7.

---

## 2. Befunde mit Quellen

### 2.1 Wer setzt den Standard (Stand 2026-10-31)

| Ebene | Standard bzw. Spitzengruppe | Warum | Einstufung, Quelle |
|---|---|---|---|
| Quality Gate, Codequalität | SonarQube (Server, Cloud, Community Build) | Herstellerangabe 7 Mio. Entwickler und 400.000 Organisationen; Investor Permira nennt es "market standard" für automatisierte statische Codequalität; das Konzept Quality Gate auf neuem Code mit vier festen Bedingungen ist dokumentiert und wird von anderen nachgeahmt | Zahlen GESAGT [sonar-stats] (Suchauszug, Hersteller- und Investorenaussagen, Abweichungen zwischen Quellen); Gate-Konzept mit den vier Bedingungen BELEGT [bothy-sonar] |
| SAST, Application Security Testing | Gartner Magic Quadrant AST 2025 (veröffentlicht 2025-10-06): Leader Black Duck, Checkmarx, HCLSoftware, OpenText, Snyk, Veracode | unabhängige Analystenbewertung; Forrester Wave SAST Q3 2025 nennt mindestens Checkmarx, Snyk, Veracode als Leader | GESAGT [gartner-ast] [forrester-sast] (Herstellermeldungen und Gartner-Abstract über Suchauszug; Veracode als Leader nur über eine Sammelseite). Eine Ausgabe 2026 ist angekündigt (Invicti meldet "Visionary"), Leader ungeprüft |
| SAST, offen und kostenlos | CodeQL (Abfragen MIT, CLI proprietär), Semgrep CE und Opengrep (LGPL-2.1) | CodeQL ist Standard im GitHub Code Scanning und Grundlage von Copilot Autofix; Semgrep CE und Opengrep sind die verbreiteten Regel-Engines (GitLab nutzt Semgrep in allen Tarifen, Aikido nutzt Opengrep) | BELEGT [gh-autofix] [gl-sast] [codeql-lic] [opengrep]; Aikido-Nutzung GESAGT [aikido] |
| KI-Security-Review (agentisch) | Claude Security (Anthropic), Codex Security (OpenAI), dazu ZeroPath, DryRun Security, Corgea | 2026 die neue Klasse: Bedrohungsmodell, Verifikation je Befund, Patch-Vorschlag; Anthropic meldet über 500 gefundene Schwachstellen in Open-Source-Code mit Opus 4.6 | Produktbeschreibungen BELEGT [an-ccsec] [cx-sec]; Zahlen GESAGT |
| KI-Fix für Analyzer-Befunde | Copilot Autofix (CodeQL), Snyk Agent Fix, Checkmarx Remediation Assist | Fix wird gegen den Analyzer erneut geprüft | BELEGT [gh-autofix]; Snyk GESAGT [snyk-fix]; Checkmarx GESAGT [cmx] |
| Fix-Forschung | Google DeepMind CodeMender (nicht allgemein verfügbar), Big Sleep (Finden) | 72 Fixes in sechs Monaten upstream; Validierung mit Differential-Tests, Fuzzing, SMT, LLM-Richter für funktionale Gleichheit | BELEGT [codemender] (Blog selbst gelesen); Zahl GESAGT |

**Unabhängige Messwerte sind dünn.** Die meisten Vergleichszahlen kommen vom Hersteller selbst (ZeroPath, DryRun, Corgea, Aikido, Semgrep, OpenAI). Die RealVuln-Arbeit nennt Hersteller-Benchmarks ausdrücklich als solche ("vendor-controlled conditions") und ist selbst von einem Anbieter (kolega-ai) veröffentlicht, dessen Werkzeug dort vorne liegt [realvuln] (BELEGT, Abstract gelesen; Interessenkonflikt ABGELEITET).

### 2.2 SonarQube im Detail

| Aussage | Einstufung | Quelle |
|---|---|---|
| Community Build ist LGPL-3.0, Release `26.10.0.133078` vom 2026-10-12 | BELEGT | GitHub-API `SonarSource/sonarqube`, [sonar-repo] |
| Community Build ist "the free, open-source edition"; die Bezahl-Editionen (Server Developer, Enterprise, Data Center, Cloud) haben zusätzlich mehr Sprachen, Branch-Analyse und PR-Dekoration, SCA, Taint-Analyse (SAST), Secrets-Erkennung, IaC, Architekturverwaltung, Portfolios, Compliance-Berichte (OWASP Top 10, CWE, PCI DSS), Remediation Agent; einiges nur mit Add-on "Advanced Security" | BELEGT (README) | [sonar-repo] |
| PR-Analyse erst in den Bezahl-Editionen (ab Developer Edition); der Community Build analysiert nur einen Branch | BELEGT (README), Edition-Blog GESAGT | [sonar-repo], [sonar-pr] |
| Community-Plugin `mc1arke/sonarqube-community-branch-plugin` (LGPL-3.0) rüstet Branch- und PR-Dekoration nach, wird nicht von SonarSource unterstützt, verlangt `-javaagent` und Austausch der Web-App, kein Upgrade-Pfad ohne Datenverlust | BELEGT | [sonar-branchplugin] |
| Quality Gate mit den vier Sonar-way-Bedingungen auf neuem Code: keine neuen Issues, alle neuen Security Hotspots geprüft, Abdeckung neuer Code mindestens 80 %, Duplizierung neuer Code höchstens 3 % (bothy-Gate "Bothy way") | BELEGT | [bothy-sonar] |
| `api/qualitygates/project_status?pullRequest=` liefert keine Revision und ist als veraltet markiert | GESAGT (Community-Forum) | [sonar-webhooks] |
| SonarQube MCP Server unter "SONAR Source-Available License v1.0", Nutzung nur für "Non-Competitive Purpose"; Release `1.30.0.4763` vom 2026-10-23; arbeitet auch mit dem Community Build | Lizenzname und Klausel GESAGT (Suchauszug, Hersteller und Defra-Bewertung); GitHub meldet `NOASSERTION` BELEGT | [sonar-mcp] |
| Cloud: Free bis 50.000 Zeilen privat, Team ab 34 USD im Monat bis 100.000 Zeilen, Open-Source-Maintainer "free forever" mit Funktionen des bezahlten Plans | GESAGT (Preisseite) | [sonar-pricing] |
| bothy nutzt genau dieses Muster: `sonar-project.properties` identisch für lokalen Community Build und SonarQube Cloud, Gate "Bothy way" als JSON im Repo mit den vier Sonar-way-Metriken und benannten Konfigurationsschlüsseln, `sonar.qualitygate.wait=true`, Job `sonar` als Teil des einzigen Pflicht-Checks `ci-ok`; lokaler Community Build per Compose nur auf 127.0.0.1 | BELEGT (selbst gelesen) | [bothy-sonar] |

### 2.3 SAST-Engines und Bausteine (Ergänzung zu den Vorarbeiten)

Versionen und Lizenzen über die GitHub-API am 2026-10-31 gelesen (BELEGT):

| Werkzeug | Lizenz | letzte Version | Rolle |
|---|---|---|---|
| Semgrep CE | LGPL-2.1 (Engine) | v1.183.0, 2026-10-29 | Regel-SAST, Taint innerhalb einer Funktion in CE |
| Opengrep | LGPL-2.1 | v1.33.1, 2026-10-29 | Fork von Semgrep 1.100.0; Taint zwischen Methoden einer Datei (`--taint-intrafile`), zusätzliche Sprachen (Visual Basic, Apex, Elixir), SARIF mit `matchBasedId/v1`-Fingerprint, signierte Releases [opengrep] |
| CodeQL-Abfragen | MIT | laufend | Abfragebibliothek |
| CodeQL-CLI | GitHub CodeQL Terms (`NOASSERTION`) | v2.27.3, 2026-10-20 | Engine, Nutzungsgrenzen siehe 2.4 |
| SonarQube Community Build | LGPL-3.0 | 26.10.0.133078, 2026-10-12 | Quality Gate, Codequalität |
| ast-grep | MIT | 0.51.0, 2026-10-15 | Strukturregeln |
| gitleaks | MIT | v8.30.1, 2026-03-21 | Secrets |
| osv-scanner | Apache-2.0 | v2.7.0, 2026-10-12 | SCA gegen OSV |
| Trivy | Apache-2.0 | v0.76.1, 2026-10-21 | SCA, IaC, Container |
| Checkov | Apache-2.0 | 3.4.0, 2026-10-28 | IaC |
| Bandit | Apache-2.0 | 1.9.4, 2026-02-25 | Python-SAST |
| gosec | Apache-2.0 | v2.30.0, 2026-10-23 | Go-SAST |
| reviewdog | MIT | v0.21.2, 2026-09-18 | Transport auf PR-Zeilen |

GitLab nutzt in allen Tarifen ein Semgrep-basiertes Analyzer-Set; Free und Premium bekommen nur den JSON-Bericht, die MR-Anzeige neuer Befunde, Advanced SAST (dateiübergreifend), Fehlalarm-Erkennung und agentische Behebung sind Ultimate (BELEGT [gl-sast]). Für eine selbst gehostete GitLab-Free-Instanz muss unsere Plattform die Befunde also selbst in den MR bringen (deckt sich mit der Ersatzkette in [01](../architecture/01-plugin-interfaces.md) Abschnitt 5, Zeile `CHECK_ANNOTATIONS`).

### 2.4 Lizenzen mit Wirkung auf ein Open-Source-Projekt

| Baustein | Was erlaubt ist | Was verboten ist | Folge für uns | Einstufung, Quelle |
|---|---|---|---|---|
| Semgrep CE Engine | LGPL-2.1, Nutzung als eigener Prozess | | mitlieferbar als Analyzer-Image | BELEGT [semgrep-lic] |
| Semgrep Rules (Registry) | Kopieren und Ändern "only for your own internal business purposes" | "distribute the rules, or to make them available to others as a service" | nicht im Image, nicht in einer gehosteten Installation für Dritte; der Betreiber darf sie für seine eigene Firma selbst einbinden | BELEGT [semgrep-rules] |
| Opengrep | LGPL-2.1, Versprechen, offen zu bleiben | | Standard-Engine für Regel-SAST | BELEGT [opengrep]; Lizenz der Opengrep-Regelsammlung: ungeprüft |
| CodeQL-CLI | Analyse von Code unter OSI-Lizenz; CI nur, wenn das Projekt auf GitHub.com liegt; mit Lizenz für GitHub Advanced Security bzw. Code Security auch privat | "provide or make available the Software as a hosted solution ... for others to use"; Analyse nicht offener Codebasen; weitergeben | nie im Image, nie von unserer Plattform für Dritte ausgeführt; nur Ergebnisse aus dem Code Scanning des Nutzers lesen (SCM-Fähigkeit) | BELEGT [codeql-lic] |
| GitHub Code Scanning | SARIF 2.1.0-Upload auch von Drittwerkzeugen; private Repos brauchen "GitHub Code Security"; Copilot Autofix für alle öffentlichen Repos | | SARIF-Upload als optionale Ausgabe, wo der Nutzer die Lizenz hat | BELEGT [gh-sarif] [gh-cs] [gh-autofix] |
| SonarQube Community Build | LGPL-3.0 | | als optionaler Begleitdienst im Installationspaket möglich (eigener Container, eigene DB) | BELEGT [sonar-repo]; Einbindungsweise ABGELEITET |
| SonarQube MCP Server | "Non-Competitive Purpose" | Wettbewerb mit Sonar | nicht mitliefern; ob eine Plattform mit eigenem Quality Gate als "competing" gilt: ungeprüft, Rechtsfrage | GESAGT [sonar-mcp] |
| `anthropics/claude-code-security-review` | MIT | | Prompt- und Filtermuster übernehmbar; Repo seit 2026-02-11 ohne Push, "not hardened against prompt injection" | BELEGT [ccsr] |
| OWASP Benchmark | GPL-2.0 | | nur als externer Eval-Datensatz laden, nicht ins Plattform-Repo kopieren | BELEGT (GitHub-API, [owasp-bench]); Einbindungsweise ABGELEITET |

### 2.5 KI-Security-Review: was die Anbieter offenlegen

| Anbieter | Offengelegte Mechanik (übernehmbar als Idee) | Proprietär bzw. unbekannt | Einstufung, Quelle |
|---|---|---|---|
| Claude Security (Anthropic, seit 2026-02-20 als Claude Code Security, später umbenannt) | liest Code "wie ein Sicherheitsforscher", Datenfluss über Komponenten; "multi-stage verification": Claude versucht jeden Befund zu beweisen oder zu widerlegen; Schwere und eigene Konfidenz je Befund; nichts ohne menschliche Freigabe; Open-Source-Maintainer bekommen kostenlosen Zugang | Prompts, Stufen im Detail, Preis; Umbenennung und öffentliche Beta für Enterprise nur über Drittbericht | Mechanik BELEGT [an-ccsec]; Umbenennung GESAGT [ccsec-rename] |
| `claude-code-security-review` und `/security-review` | Diff-bewusst, zehn Kategorien, harte Ausschlussliste (DoS, Rate-Limit, Ressourcen, generische Eingabeprüfung, Open Redirect), zweiter LLM-Pass als Filter, Datei mit eigenen Fehlalarm-Regeln, Eval-Werkzeug `claudecode/evals/` | | BELEGT [ccsr] |
| Codex Security (OpenAI, vorher Aardvark, seit 2026-03-06) | Bedrohungsmodell je Repo als editierbares Artefakt, Commits neueste zuerst gegen Modell und Repo prüfen, Reproduktion in isolierter Sandbox, Patch per Codex, Ergebnis mit Code-Kontext, Begründung, Validierungsbeleg; CLI und SDK im Paket `@openai/codex-security`; Änderungs-Review auf PR, Commit, Diff; Triage von Befunden anderer Scanner | Modell, Prompts, Preis | Ablauf BELEGT [cx-sec] (Hersteller-Doku); Bedrohungsmodell und Sandbox-Details GESAGT (Drittberichte [cx-sec-3p]); 92 % Recall auf "golden repositories" GESAGT [aardvark] |
| Semgrep Assistant (heute "Multimodal") | LLM-Triage von Regel-Befunden; "Memories" aus Triage-Begründungen, Vorschlag durch Assistant, Freigabe durch Admin, Scope je Schwachstellenklasse; Zustimmung Nutzer 95 bis 96 %; intern 96 % auf echten Treffern, nur 41 % auf Fehlalarmen (bewusst konservativ) | Modelle, Prompts | Memories BELEGT (Suchauszug der Doku); Zahlen GESAGT [semgrep-ai] |
| Aikido AutoTriage | erst deterministische Erreichbarkeit, dann LLM: zuerst Ausnutzbarkeit ausschließen (Validierung, Sanitizing, Casting), sonst Schwere 0 bis 100 nach Kontext verschieben; Reasoning-Modelle nur für schwere Fälle (Pfad-Traversal) | Engine-Kopplung an Opengrep nicht dokumentiert | Ablauf BELEGT (Suchauszug der Hilfe); Zahlen GESAGT [aikido] |
| Snyk Agent Fix (vorher DeepCode AI Fix) | mehrere Fix-Kandidaten, jeder vom Regel-Engine erneut geprüft, ungültige verworfen; seit 2026-05 agentisch; nur dateilokale Fixes | Modell, "over 80 % accurate" ohne Methode | GESAGT [snyk-fix] (Suchauszug der Doku) |
| Copilot Autofix | ein Fix je CodeQL-Alarm, Standard an; "agentic autofix" prüft mit erneutem CodeQL-Lauf; kostet keine AI-Credits | Prompts, Messwerte | BELEGT [gh-autofix] |
| ZeroPath | PR-Scans mit Inline-Kommentaren und Check, Regeln in natürlicher Sprache, Fix-PRs, SCA mit Erreichbarkeit, Secrets mit Verifikation, IaC, CLI mit SARIF, Bedrohungsmodell, MCP-Server; offener Benchmark-Fork von XBOW mit gepatchten Varianten für Fehlalarme | Engine | Funktionen BELEGT [zeropath-docs]; Benchmark-Werte GESAGT [zeropath-bench] |
| DryRun Security | PR-Security-Review ohne Regeln, "Natural Language Code Policies" mit blockierenden Checks, DeepScan für ganze Repos, Risk Register | Engine | GESAGT [dryrun] (nur Dritt- und Marketplace-Quellen) |
| Corgea BLAST | LLM plus AST, als eigener Scanner oder als Triage- und Fix-Schicht über Snyk, Semgrep, Checkmarx, Fortify, Coverity | Engine, Zahlen | GESAGT [corgea] |
| Checkmarx One Assist | Developer Assist als Find-und-Fix-Schleife in Cursor, Windsurf, Kiro und Claude Code; Triage Assist und Remediation Assist (seit 2026-03 bzw. 2026-07 GA); seit 2026-10-15 im Claude Marketplace | alles | GESAGT [cmx] |
| CodeMender (DeepMind) | Werkzeuge: statische und dynamische Analyse, Differential-Tests, Fuzzing, SMT; Kritik-Agent vergleicht Original und Patch; LLM-Richter für funktionale Gleichheit; nur Patches, die Ursache beheben, funktional korrekt sind, keine Regression haben und Stilregeln folgen, gehen an Menschen | nicht veröffentlicht | BELEGT [codemender] |

### 2.6 Benchmarks und Datensätze

| Datensatz | Inhalt | Lizenz | Nutzen für uns | Einstufung, Quelle |
|---|---|---|---|---|
| Juliet C/C++ 1.3 und Java 1.3 (NIST SARD) | synthetische Testfälle zu 118 bzw. 112 CWEs | US-Werk, sonst CC0-1.0 | Regressionsset für Analyzer und Security-Finder, frei mitlieferbar | BELEGT (Suchauszug der SARD-Seiten) [juliet] |
| OWASP Benchmark v1.2 | lauffähige Web-App, Java und Python, Auswertung über BenchmarkUtils (Youden-Index verlinkt), Scorecards für CodeQL, Semgrep, Snyk Code, SonarQube CE u. a. | GPL-2.0 | Fehlalarm-Rate auf bekannten Nicht-Treffern | BELEGT [owasp-bench] |
| OpenSSF CVE Benchmark | 218 echte CVEs in JS/TS, jeweils verwundbare und gepatchte Fassung (misst Fehlalarm auf dem Fix) | Werkzeug MIT, Fall-Repos mit Lizenz des Ursprungsprojekts | bestes Muster "vorher/nachher"; seit 2024-03 ruhend | GESAGT (Suchauszug von Repo und OpenSSF-Blog) [ossf-cve] |
| CWE-Bench-Java (IRIS) | 120 CVEs in großen Java-Projekten, 2025-08 um 93 CVEs erweitert; CodeQL fand 27, IRIS mit GPT-4 55, Fehlfundrate weiter 84,82 % | laut Repo-Index MIT, ungeprüft | Bezugswert CodeQL auf echten CVEs; zeigt das Muster "LLM ergänzt Taint-Spezifikation für CodeQL" | GESAGT (Paper über Suchauszug) [iris] |
| CASTLE | 250 kompilierbare C-Programme, 25 CWEs; Statik hat viele Fehlalarme, LLMs stark auf kleinen Programmen, schwächer bei großem Code | ungeprüft | C-Teil | GESAGT [castle] |
| RealVuln | 26 absichtlich verwundbare Python-Repos, 676 Schwachstellen, 120 Fehlalarm-Fallen; F3: Kolega.Dev 73,0, Claude Sonnet 4.6 51,7, Semgrep 17,7; F1: Sonnet 4.6 60,9 | Paper CC BY 4.0, Code "open-source", Lizenz ungeprüft | einziger neuerer Vergleich Regel-SAST gegen allgemeines LLM | BELEGT (Abstract) [realvuln] |
| ZeroPath validation-benchmarks | XBOW-Fork, 104 Apps, Hinweise entfernt, 25 gepatchte Varianten für Fehlalarme | ungeprüft | Business-Logik-Fälle (IDOR, Auth) | GESAGT [zeropath-bench] |
| CyberGym | 1.507 echte Schwachstellen aus OSS-Fuzz in 188 Projekten; Aufgabe: PoC erzeugen, geprüft auf alter und neuer Fassung | Apache-2.0 (README) | misst die Fähigkeit "Befund in der Sandbox beweisen" (Verifier-Stufe `proven`); Basisdaten rund 240 GB | GESAGT (Paper und README über Suchauszug) [cybergym] |

**Online-Metriken, die die Anbieter selbst nennen:** Zustimmung der Nutzer zur KI-Triage (Semgrep), Anteil automatisch triagierter Befunde (Semgrep 60 %, GESAGT), Rückgang Fehlalarme und überhöhter Schweregrade (Codex Security über 50 % bzw. über 90 %, GESAGT [cx-sec-3p]), Fix-Gültigkeit (Snyk), Zeit bis zur Behebung. Für das Quality Gate gibt es keinen Benchmark, sondern eine Definition (Sonar way).

---

## 3. Folgen für unsere Architektur

Antwort auf die Kernfrage: **Wir bauen keine Analyse-Engine. Wir bauen (1) eine Plugin-Art `Analyzer` mit SARIF 2.1.0 als Normalform, (2) ein Plattform-Gate auf neuem Code, das auch ohne Sonar-Bezahl-Edition funktioniert, und (3) die KI-Schicht darüber: Triage und Verifikation der Analyzer-Kandidaten, Security-Finder mit Bedrohungsmodell, Fix mit Neu-Scan-Pflicht und einen planbaren Ganz-Repo-Scan.** ABGELEITET aus 2.1 bis 2.5.

### 3.1 Fähigkeits-Checkliste des Standards

Spalte "bei uns": Fundstelle in `docs/architektur`.

| # | Fähigkeit | wer sie hat | Beleg | bei uns |
|---|---|---|---|---|
| 1 | Quality Gate mit Bedingungen auf neuem Code, Status je PR | SonarQube (ab Developer), bothy | [sonar-repo] [bothy-sonar] | nein; nur Check `ai-review` ([02](../architecture/02-services.md) Abschnitt 3 "Ausgang") und Merge-Gate ([03](../architecture/03-flow-and-orchestration.md) Abschnitt 1a) |
| 2 | Abdeckung neuer Code als Gate-Bedingung | SonarQube | [bothy-sonar] | nein (QA misst Mutation, nicht Abdeckung, [07](../architecture/07-eval.md) 3.3) |
| 3 | Duplizierung neuer Code | SonarQube | [bothy-sonar] | nein |
| 4 | Security Hotspots mit Prüf-Workflow | SonarQube | [bothy-sonar] | nein |
| 6 | Externe Ergebnisse importieren (SARIF, generisch) | GitHub Code Scanning | [gh-sarif] | nein |
| 7 | Stabile Fingerprints über Commits, nur neue Befunde zeigen (Baseline) | GitHub (`partialFingerprints`), SARIF `baselineState`, Opengrep `matchBasedId` | [gh-sarif] [sarif] [opengrep] | teilweise: Fingerprint und Inkrement nur für LLM-Befunde ([02](../architecture/02-services.md) Abschnitt 3 Stufen 6 und 8) |
| 8 | Unterdrückung mit Begründung, dauerhaft | SARIF `suppressions`, Semgrep Memories | [sarif] [semgrep-ai] | teilweise: Rauschfilter über früher abgelehnte Befunde ([02](../architecture/02-services.md) Abschnitt 3 Stufe 6) |
| 9 | Ergebnis als Pflicht-Check mit Zeilen-Annotationen | alle | [gh-sarif] | ja für das Review ([01](../architecture/01-plugin-interfaces.md) Abschnitt 5 und 11.2 `CHECK_ANNOTATIONS`) |
| 10 | SARIF-Ausgabe an den Hoster (GitHub Code Scanning, GitLab-Bericht) | ZeroPath-CLI | [zeropath-docs] | nein |
| 11 | Secrets im PR-Diff als Befund | ZeroPath | [zeropath-docs] | teilweise: gitleaks nur als Schwärzung und Coder-Gate ([05](../architecture/05-security.md) Abschnitte 3 und 5) |
| 12 | SCA mit Erreichbarkeit | Snyk, Aikido, ZeroPath, Sonar Advanced Security | [aikido] [zeropath-docs] [sonar-repo] | teilweise: osv-Abgleich nur für neue Abhängigkeiten im Merge-Gate ([03](../architecture/03-flow-and-orchestration.md) 1a Bedingung 7) |
| 13 | IaC-Prüfung | ZeroPath, Sonar-Bezahl-Editionen | [zeropath-docs] [sonar-repo] | nein |
| 14 | CWE- und OWASP-Zuordnung je Befund | Sonar-Bezahl-Editionen | [sonar-repo] | nein (Befundschema ohne CWE, [02](../architecture/02-services.md) Abschnitt 3 "Ausgang") |
| 15 | Reachability und Exploitability als eigene Felder, Schwere danach gedeckelt | Aikido | [aikido] | nein |
| 16 | Bedrohungsmodell je Repo als editierbares Artefakt | Codex Security, ZeroPath | [cx-sec] [zeropath-docs] | nein |
| 17 | Verifikation je Befund mit Beweis oder Widerlegung, Konfidenz | Claude Security, Codex Security | [an-ccsec] [cx-sec] | ja für LLM-Befunde (Verifier, `proven`, `plausible`, `unsupported`, [02](../architecture/02-services.md) Abschnitt 3 Stufe 5) |
| 18 | Analyzer-Befunde nur als Kandidaten, vom Verifier bestätigt | Aikido, Semgrep Assistant | [aikido] [semgrep-ai] | nein (Linter getrennt, ADR-33) |
| 19 | Reproduktion bzw. PoC in der Sandbox | Codex Security | [cx-sec-3p] | teilweise: Verifier darf Build und Tests laufen lassen ([02](../architecture/02-services.md) Abschnitt 3 Stufe 5), kein PoC-Ziel |
| 20 | Security-Fix gilt nur, wenn Alarm beim Neu-Scan weg und Tests grün | Copilot Autofix (agentisch), Snyk, CodeMender | [gh-autofix] [snyk-fix] [codemender] | teilweise: als Messlatte im PR-Fixer genannt ([02](../architecture/02-services.md) Abschnitt 5 Messlatte), nicht als hartes Gate |
| 21 | Blockierender Security-Check mit Schwelle | DryRun | [dryrun] | teilweise: Merge-Gate verlangt 0 offene P0/P1 ([03](../architecture/03-flow-and-orchestration.md) 1a Bedingung 3), kein eigener Security-Check |
| 22 | Ganz-Repo-Scan geplant oder auf Abruf (Deep Scan) | Codex Security, Claude Security, DryRun | [cx-sec] [an-ccsec] [dryrun] | nein |
| 24 | Regeln in natürlicher Sprache, durchgesetzt im PR | DryRun, ZeroPath | [dryrun] [zeropath-docs] | teilweise: Regeln aus `REVIEW.md` mit Zitatpflicht und Standards-Service ([02](../architecture/02-services.md) Abschnitte 3 und 7) |
| 25 | Befund, den nur die KI fand, wird deterministische Regel mit Regel-Test | bothy-Regel, Semgrep Memories | [bothy-sonar] (`.semgrep/` mit Testdatei je Regel) | teilweise: Standards-Service erzeugt Regel-PRs ([02](../architecture/02-services.md) Abschnitt 7), kein Ziel "Opengrep- oder ast-grep-Regel mit Test" |
| 26 | Team-Gedächtnis für Fehlalarme mit Freigabe | Semgrep Memories | [semgrep-ai] | teilweise: Learning-Kandidaten aus Chat ([02](../architecture/02-services.md) Abschnitt 3 "Optional") |
| 27 | Portfolio, Dashboard, Trend | SonarQube Enterprise, Checkmarx Insights | [sonar-repo] [cmx] | nein (Admin-UI ohne Befund-Trend, [06](../architecture/06-operations-and-deployment.md) Abschnitt 4) |
| 28 | IDE-Anbindung, MCP für Ergebnisse | Sonar MCP, ZeroPath MCP, Checkmarx Developer Assist | [sonar-mcp] [zeropath-docs] [cmx] | teilweise: Plattform-MCP mit Lese-Tools ([01](../architecture/01-plugin-interfaces.md), README Abschnitt 3) |
| 29 | Lizenz- und SBOM-Policy | Sonar Advanced Security | [sonar-pricing] | nein |

Die Nummern 5, 23 und 30 entfallen in dieser Fassung: sie stützten sich nur auf Herstellerdoku oder private Vorarbeiten, deren Auswertung nach [10](../architecture/10-standards-per-layer.md) Abschnitt 16 nicht weitergeführt wird.

### 3.2 Neue Plugin-Art `Analyzer` ([01-plugin-interfaces.md](../architecture/01-plugin-interfaces.md))

- **Abschnitt 1.1:** `PluginKind` um `"Analyzer"` erweitern (gleicher Name wie in [ebenen-landkarte.md](ebenen-landkarte.md)). Manifest-Zusatz: `license` (SPDX, Pflicht), `image` mit Digest, `languages`, `runsRepoCode: boolean` (ESLint mit Plugins, Build-basierte Analyse), `needsBuild`, `offline: boolean`, `rulesLicense` (getrennt von der Engine-Lizenz, wegen Semgrep Rules License).
- **Neuer Abschnitt "Analyzer"** mit zwei Betriebsarten:
  - `run`: in der Sandbox, Eingabe Workspace plus `scope: diff | full` plus `baselineSha`, Ausgabe SARIF 2.1.0 im Objektspeicher plus Kennzahlen. Die Plattform setzt `baselineState` selbst, indem sie Basis und Head mit denselben gepinnten Versionen analysiert oder eine gecachte Basis-Analyse nutzt.
  - `ingest`: Ergebnisse von außen lesen: SARIF aus einem CI-Artefakt (`ci_event`), Alarme aus dem Code Scanning des Hosters (GitHub, GitLab-Bericht), Sonar-Webhook mit `qualityGate.status` und `revision` (HMAC prüfen; Revision muss gleich dem Head-SHA sein, sonst `neutral`).
  - Capabilities: `SARIF_NATIVE`, `FINGERPRINT`, `BASELINE`, `TAINT_INTERFILE`, `AUTOFIX`, `QUALITY_GATE`.
  - Normalisierung: SARIF-Ergebnis wird zu einem `AnalyzerFinding` (Regel, Ort, Level, `security-severity`, CWE aus Regel-Tags, Fingerprint). Fehlt ein Fingerprint, berechnet die Plattform einen eigenen aus Regel, Pfad und normalisierter Zeile (Muster `primaryLocationLineHash`, [gh-sarif]).
- **Abschnitt 5 SCMProvider:** neue Fähigkeiten `CODE_SCANNING_READ` (Alarme lesen, für CodeQL "bring your own") und `CODE_SCANNING_UPLOAD` (SARIF hochladen, GitHub nur mit Code-Security-Lizenz bei privaten Repos; GitLab: SAST-Bericht nur als Artefakt, MR-Anzeige erst Ultimate). Ersatzkette: Code Scanning, sonst Check-Annotationen, sonst Zusammenfassung.
- **Abschnitt 11:** Provider-Matrix "Analyzer" mit Lizenz, Sprache, Rolle, mitgeliefert ja/nein (Tabelle 2.3 und 2.4).

### 3.3 Services ([02-services.md](../architecture/02-services.md))

- **Neuer Service `analysis` (deterministisch, ohne LLM).** Zweck: Analyzer je Repo ausführen oder einlesen, Plattform-Gate auf neuem Code berechnen, Check `quality-gate` setzen. Messlatte: SonarQube Quality Gate. Bedingungen als benannte Konfigurationswerte nach dem bothy-Muster (Sonar way als Startwerte: 0 neue Befunde ab Schwelle, Abdeckung neuer Code, Duplizierung neuer Code). Ist eine Sonar-Instanz angebunden und kann sie PRs analysieren, ist ihr Gate am Head-SHA die Quelle; sonst rechnet `analysis` selbst. Allein an: reiner Gate-Dienst ohne LLM-Kosten. Abhängigkeiten: `Analyzer`, `ExecutionBackend`.
- **Reviewer Abschnitt 3:** Stufe 3 Kontextpaket liest `analysis`-Befunde am Head; Stufe 4 bekommt sie als Kandidaten; Stufe 5 Verifier bestätigt oder verwirft sie wie LLM-Befunde; Stufe 6 dedupliziert LLM- und Analyzer-Befunde über Ort und CWE. Befundschema um `cwe[]`, `reachability`, `exploitability`, `source: llm | analyzer:<id>` erweitern. Der Security-Finder liest das Bedrohungsmodell des Repos (Artefakt aus `security`). Schwere-Deckel: `unreachable` höchstens P3.
- **Neuer Service `security` (oder Modus des Reviewers, siehe Owner-Entscheidung 4.3).** Zweck: Bedrohungsmodell je Repo erzeugen und als versioniertes Artefakt per PR pflegen; Ganz-Repo-Scan auf Abruf oder nach Zeitplan in den Phasen Kartieren, Untersuchen, Beweisen; Triage fremder Befunde (Code Scanning, Sonar). Messlatte: Codex Security, Claude Security. Ausgabe: Befunde mit Beleg, optional Fix-Auftrag an den PR-Fixer.
- **Coder Abschnitt 2 Stufe 4 und PR-Fixer Abschnitt 5:** Self-Check-Bündel als Liste von `Analyzer`-Instanzen statt fester Namen; harte Regel für Security-Fixe: Fix gilt nur, wenn der auslösende Befund beim Neu-Scan derselben Analyzer-Version weg ist, keine neuen Befunde ab Schwelle entstehen und die Tests grün sind (Copilot-Autofix- und Snyk-Muster).
- **Standards Abschnitt 7:** Ziel "Regel-Kompilierung": ein Befund, den nur das LLM fand und den Menschen bestätigt haben, wird als Opengrep- oder ast-grep-Regel mit positivem und negativem Testfall vorgeschlagen (bothy-Muster `.semgrep/<regel>.yaml` plus Testdatei).

### 3.4 Ablauf, Konfiguration, Sicherheit, Betrieb

- **[03](../architecture/03-flow-and-orchestration.md) Abschnitt 1a Merge-Gate:** neue Bedingung "Plattform-Gate bzw. externes Quality Gate am Head-SHA grün; externes Gate nur, wenn seine Revision gleich dem Head-SHA ist". Bedingung 7 (osv) geht darin auf. Abschnitt 5 Fehlerpfade: Analyzer-Absturz, Zeitlimit, Bericht ohne Pflichtfelder (wir markieren `neutral` mit Grund, nie stilles Grün).
- **[04](../architecture/04-configuration-and-limits.md) Abschnitt 3:** Block `analysis:` mit `analyzers: [{id, image, profile}]`, `gate: {new_findings_max, min_severity, new_coverage_min_percent, new_duplication_max_percent}`, `external_gate: {provider: sonar, required: bool}`; Block `security:` mit `threat_model: on`, `deep_scan: {schedule, budget_usd}`. Installationsebene: Allowlist der Analyzer-Images (nur verschärfend).
- **[05](../architecture/05-security.md) Abschnitt 3:** Analyzer laufen nur in der Sandbox; `runsRepoCode: true` nur mit derselben Isolation wie Build und Tests; Regeln und Analyzer-Konfiguration vom Basis-SHA (ADR-17 gilt auch hier); Analyzer-Images per Digest gepinnt und signiert, wo der Hersteller signiert (Opengrep signiert mit Cosign, [opengrep]). Abschnitt 4 Prompt Injection: SARIF-Nachrichten fremder Werkzeuge sind `Untrusted`.
- **[06](../architecture/06-operations-and-deployment.md) Abschnitt 2:** Das Installationspaket (Compose und Helm, Azure, AWS, Google Cloud, Hetzner) enthält einen Analyzer-Katalog mit freien Lizenzen; SonarQube Community Build als optionaler Begleitdienst mit eigener Postgres-Datenbank (eigene DB ist ABGELEITET aus Betriebstrennung; Speicherbedarf laut Hersteller 4 GB bis 1 Mio. Zeilen, zitiert in [bothy-sonar], dort BELEGT). Offline-Regelbündel für Installationen ohne Internet.
- **[08](../architecture/08-roadmap.md):** `analysis` im `ingest`-Modus mit Stufe 1 (Reviewer liest vorhandene CI-Ergebnisse), `run`-Modus und Plattform-Gate mit Stufe 2 (Self-Check braucht ihn), Bedrohungsmodell und Deep Scan frühestens Stufe 6.
- **[09](../architecture/09-decisions.md):** ADR-33 ändern: "Analyzer laufen deterministisch über die Plugin-Art `Analyzer`; ihre Befunde sind Kandidaten für den Verifier; Inline nur P0 und P1 bleibt". Grund: Ein selbst hostender Nutzer hat nicht immer eine CI mit Analyzern. Neue ADRs: "Keine eigene Analyse-Engine; SARIF 2.1.0 als Normalform", "Lizenzpolitik für Analyzer und Regeln (2.4)", "CodeQL nur lesend über den Hoster".
- **[README](../architecture/README.md):** Glossar um `Analyzer`, `SARIF`, `Quality Gate`, `Plattform-Gate`, `Bedrohungsmodell`; Zählungen "8 Plugin-Arten" und "7 Services" anpassen; Quellenliste ergänzen.

### 3.5 Gate A und Gate B messbar machen ([07-eval.md](../architecture/07-eval.md) Abschnitte 3 und 4)

Neue Testsätze (Startgrößen sind Schätzungen):

| Testsatz | Inhalt | Lizenz |
|---|---|---|
| A1 Analyzer-Parität | je Analyzer 20 Fixture-Repos; SARIF unserer Ausführung gegen Direktaufruf derselben Version | eigene Fixtures |
| A2 Gate-Parität | 30 PRs eines öffentlichen Repos mit SonarQube-Cloud-Analyse (zuerst das eigene Entwicklungs-Repo, Vorgabe 3); Plattform-Gate gegen Sonar-Gate am selben SHA | eigene Daten |
| SEC1 Paare verwundbar/gepatcht | OpenSSF CVE Benchmark (JS/TS), CWE-Bench-Java | MIT bzw. laut Index MIT (prüfen) |
| SEC2 synthetisch | Stichprobe aus Juliet C/C++ und Java, OWASP Benchmark (nur extern geladen) | CC0, GPL-2.0 |
| SEC3 Logik | ZeroPath-Fork und RealVuln (Python), nach Lizenzprüfung | ungeprüft |
| SEC4 eigene Seeds | absichtlich eingebaute Fehler (IDOR, fehlende Autorisierung, SSRF, Injection) in Kopien eigener Repos; bothy-Regeln wie "kein Modell-Credential im Server" als echte Projektregel | eigene Daten |
| SEC5 Beweis | CyberGym Level 1 Stichprobe: Verifier soll PoC erzeugen | Apache-2.0 |
| SEC6 Fix | Befunde aus SEC1 und SEC4; Fix gilt bei: Alarm weg, keine neuen Alarme, Tests grün, gepatchte Fassung nicht als verwundbar gemeldet | wie oben |

| Service | Gate A | Gate B | Bezugswert und Einstufung |
|---|---|---|---|
| `analysis` | A1: 100 % gleiche Befund-Fingerprints wie der Direktaufruf; Fehlerpfade S6 | A2: Gate-Entscheidung stimmt in 100 % der Fälle mit Sonar überein, Abweichungen einzeln begründet | Sonar-way-Bedingungen BELEGT [bothy-sonar] |
| Reviewer, Security-Finder | Recall auf SEC1 bis SEC4 mindestens wie nacktes Claude Code mit `/security-review`-Prompt ([ccsr]) bei gleicher Fehlalarm-Rate auf gepatchten Fassungen | Recall mindestens wie die Vereinigung Opengrep plus CodeQL auf SEC1 und SEC2 unter gleichen Bedingungen (CodeQL nur auf Open-Source-Fällen, Lizenz erlaubt das), Fehlalarme auf gepatchten Fassungen nicht höher; Präzision ab 70 % wie beim Reviewer | CodeQL 27 von 120 auf CWE-Bench-Java GESAGT [iris]; RealVuln F3 Sonnet 4.6 51,7 gegen Semgrep 17,7 BELEGT [realvuln]; Herstellerwerte (Aardvark 92 %, ZeroPath 80 %) nur als GESAGT im Bericht, nicht als Schwelle |
| Verifier für Analyzer-Kandidaten | 0 verworfene Befunde, die in SEC1 bis SEC4 echt sind (hartes Gate, bewusst konservativ wie Semgrep) | Anteil korrekt verworfener Fehlalarme gemessen gegen Menschen-Labels; Zustimmung auf echten Treffern mindestens 95 % | Semgrep 96 % auf Treffern, 41 % auf Fehlalarmen GESAGT [semgrep-ai] |
| `security` (Bedrohungsmodell, Deep Scan) | Gewinn gegen Security-Finder ohne Modell auf SEC4 | SEC5: Anteil Befunde mit reproduziertem PoC; Vergleich mit Claude Security nur mit vorhandenem Konto (O13) | ohne öffentlichen Bezug: "Gate B offen" laut [07](../architecture/07-eval.md) Abschnitt 4 |
| PR-Fixer für Security-Befunde | SEC6 ohne Verstöße gegen die Fix-Regel | Fix-Gültigkeit mindestens wie der veröffentlichte Wert, sobald einer mit Methode vorliegt | Snyk "über 80 %" GESAGT ohne Methode, deshalb nur Bericht |

**Online je Ebene:** Anteil von Menschen als Fehlalarm markierter Befunde, Fix-Annahmequote, Zeit bis zur Behebung, Anteil `neutral` beim Gate, Anzahl Gate-Überstimmungen durch Menschen. Messbar ab dem Schattenbetrieb.

### 3.6 Was übernommen werden kann und was proprietär bleibt

- **Übernehmbar (Code oder Format):** SARIF 2.1.0 als OASIS-Standard mit `partialFingerprints`, `baselineState`, `suppressions`, `fixes` [sarif]; Sonar-way-Bedingungen als Startwerte [bothy-sonar]; GitHubs SARIF-Grenzen als Validierungsregeln (10 MB gzip, 20 Runs, 25.000 Ergebnisse je Run, davon 5.000 angezeigt, [gh-sarif]); Prompts und Ausschlussfilter aus `claude-code-security-review` (MIT, [ccsr]); Abfragen aus `github/codeql` (MIT) als Lesestoff, nicht die CLI.
- **Übernehmbar als Idee:** Bedrohungsmodell als editierbares Artefakt (Codex Security), erst deterministische Erreichbarkeit, dann LLM-Triage (Aikido), Memories mit Admin-Freigabe (Semgrep), Neu-Scan als Fix-Beweis (Copilot, Snyk), Kritik-Agent plus Richter für funktionale Gleichheit (CodeMender), LLM erzeugt Taint-Spezifikationen für eine Regel-Engine (IRIS).
- **Proprietär:** alle Modelle und Prompts der kommerziellen KI-Scanner, Sonars Taint-Engine und Regelsätze der Bezahl-Editionen, Semgrep Pro, CodeQL-CLI, Snyk-Engine, Checkmarx-Engine.

### 3.7 Lücken bis zum Niveau (Reihenfolge nach Wirkung)

1. Plugin-Art `Analyzer` mit SARIF und Baseline (Checkliste 6, 7, 10).
2. Plattform-Gate auf neuem Code inklusive Abdeckung und Duplizierung (1 bis 3), weil der Community Build keine PRs kann.
3. Analyzer-Befunde als Verifier-Kandidaten statt eigenem Workflow (18), dazu CWE, Reachability, Exploitability im Befundschema (14, 15).
4. Fix-Regel "Neu-Scan plus Tests" als hartes Gate (20).
5. Bedrohungsmodell und Ganz-Repo-Scan (16, 22, 19).
6. Regel-Kompilierung im Standards-Service (25) und Team-Gedächtnis für Fehlalarme mit Freigabe (26).
7. Secrets, SCA und IaC als normale Analyzer im PR (11 bis 13); SBOM und Lizenz-Policy (29) bleiben außerhalb dieser Ebene.

---

## 4. Owner-Entscheidungen

| # | Frage | Art | Empfehlung | Grund |
|---|---|---|---|---|
| 4.1 | Welche Analyzer liefert das öffentliche Projekt im Standard-Image mit? | Recht | Nur Engines mit OSI-Lizenz als eigener Prozess: Opengrep (Standard-Engine), Semgrep CE ohne Registry-Regeln, ast-grep, gitleaks, osv-scanner, Trivy, Checkov, Bandit, gosec; SonarQube Community Build nur als optionaler Begleitdienst. CodeQL-CLI, Semgrep-Registry-Regeln und SonarQube MCP Server nie mitliefern; CodeQL nur lesend über den Hoster | Lizenztexte in 2.4: Rules License verbietet Angebot als Dienst, CodeQL-Terms verbieten Hosting für andere und Analyse nicht offener Codebasen, MCP-Server ist Source-Available. Deckt sich mit [ebenen-landkarte.md](ebenen-landkarte.md) 4.3 |
| 4.2 | SonarQube für das öffentliche Entwicklungs-Repo: SonarQube Cloud oder nur selbst gehosteter Community Build? | Konten, eventuell Geld | SonarQube Cloud im kostenlosen Open-Source-Plan plus lokaler Community Build wie in bothy (gleiche `sonar-project.properties`, Gate-Datei im Repo); kein Community-Branch-Plugin | Cloud kann PR-Analyse und Dekoration, der Community Build nicht; das Plugin ist nicht unterstützt und ohne Upgrade-Pfad ([sonar-branchplugin]); "free forever" für OSS ist GESAGT und vor Anlage zu prüfen |
| 4.3 | Bekommt Security einen eigenen Service mit Ganz-Repo-Scan, oder bleibt Security ein Finder im Reviewer? | Produkt, Geld (Tokenkosten) | Eigener Service `security`, standardmäßig `off`, Deep Scan nur mit Budget je Lauf; PR-Zeit-Security bleibt Finder im Reviewer und nutzt das Bedrohungsmodell | Der Standard 2026 (Codex Security, Claude Security) trennt beides |
| 4.4 | Eval-Datensätze mit Copyleft (OWASP Benchmark GPL-2.0) und ungeklärter Lizenz (RealVuln, ZeroPath-Fork, CASTLE) nutzen? | Recht | GPL-2.0-Daten nur im getrennten Eval-Repo und zur Laufzeit geladen, nie im Plattform-Repo; Datensätze ohne geprüfte Lizenz erst nach Lizenzprüfung (wie O12) | Plattform-Code soll frei lizenzierbar bleiben |

Vergleichsläufe gegen kommerzielle Scanner (Snyk, ZeroPath, Claude Security) fallen unter das bestehende O13 in [09](../architecture/09-decisions.md); keine neue Entscheidung nötig.

---

## 5. Offene Punkte

1. Ob der SonarQube Community Build SARIF importieren kann und ob externe Befunde in sein Quality Gate eingehen: ungeprüft.
2. Ob `api/qualitygates/project_status` in einer V2-API ersetzt wird: ungeprüft (nur Forumsaussage).
3. Lizenz der Opengrep-Regelsammlung, von CASTLE, RealVuln und dem ZeroPath-Fork: ungeprüft. CWE-Bench-Java: MIT nur laut Drittindex.
4. Gartner Magic Quadrant AST 2026: Existenz angedeutet, Leader ungeprüft. Veracode als Leader 2025 nur über eine Sammelseite.
5. Ob die Nutzungsklausel des SonarQube MCP Servers ("Non-Competitive Purpose") eine Plattform mit eigenem Quality Gate trifft: Rechtsfrage, ungeprüft; durch Nicht-Mitliefern umgangen.
6. Codex-Security-Details (Sandbox-Validierung, Zahlen 1,2 Mio. Commits, 792 kritische, 10.561 hohe Befunde, 14 CVEs) nur über Drittberichte; OpenAIs Ankündigungsseite antwortete mit 403.
7. Claude Security: Umbenennung, öffentliche Beta und Modell nur über Drittbericht; ob es eine API oder Selbst-Hosting gibt: ungeprüft. Für unsere Plattform zählt nur das Muster.
8. Ob reine SARIF-Nachrichten fremder Werkzeuge für Prompt Injection genutzt werden können (sie sind frei formulierbarer Text aus dem Repo, etwa bei eigenen Regeln im PR): gilt als `Untrusted`, ein Testfall dafür fehlt in Suite S1 ([07](../architecture/07-eval.md) Abschnitt 5) und ist dort zu ergänzen.
9. Speicher- und Laufzeitbedarf der Analyzer je Sprache in der Sandbox: in Stufe 2 messen; keine Zahl ohne Messung.
10. Die Architektur trägt noch einen Firmennamen im Titel und in `apiVersion` ([01](../architecture/01-plugin-interfaces.md) Abschnitt 1.1); für ein öffentliches Projekt neutral benennen. Gehört zur Recherche über Open Source und Installation, hier nur vermerkt.

---

## 6. Quellen (alle abgerufen 2026-10-31)

Eigenes Projekt und Vorbild (selbst gelesen):
- [ebenen-landkarte.md](ebenen-landkarte.md)
- [bothy-sonar] öffentliches Repo bothy ([bothy-repo] in [bothy-vorlage-projekt-setup](bothy-vorlage-projekt-setup.md) Abschnitt 6), ursprünglich an einem nicht veröffentlichten Planungsstand gelesen, am 2026-11-01 auf Commit `4485084b8` nachgeprüft (Gate-Datei mit den vier Bedingungen, `sonar.qualitygate.wait=true`, Job `sonar` vor `ci-ok`, Compose nur auf 127.0.0.1, `.semgrep/` mit Testdatei je Regel): `sonar-project.properties`, `quality/sonar/quality-gate.json`, `.coderabbit.yaml`, `.github/workflows/ci.yml` (Job `sonar`, `ci-ok`), `.github/workflows/codeql.yml`, `.semgrep/`, `docs/quality/sonarqube-local.md`, `docs/quality/gates.md`
- GitHub-API `https://api.github.com/repos/<owner>/<repo>` und `/releases/latest` für semgrep/semgrep, opengrep/opengrep, github/codeql-cli-binaries, github/codeql, SonarSource/sonarqube, SonarSource/sonarqube-mcp-server, anthropics/claude-code-security-review, OWASP-Benchmark/BenchmarkJava, ast-grep/ast-grep, google/osv-scanner, gitleaks/gitleaks, aquasecurity/trivy, bridgecrewio/checkov, PyCQA/bandit, securego/gosec, reviewdog/reviewdog (BELEGT)

Hersteller und Primärquellen:
- [sonar-repo] https://github.com/SonarSource/sonarqube (README, Lizenz)
- [sonar-pr] https://www.sonarsource.com/de/blog/sonarqube-compare-editions/ (Suchauszug)
- [sonar-branchplugin] https://github.com/mc1arke/sonarqube-community-branch-plugin
- [sonar-webhooks] https://community.sonarsource.com/t/deprecated-qualitygates-project-status-endpoint-has-no-v2-equivalent/181235 (GESAGT)
- [sonar-mcp] https://github.com/SonarSource/sonarqube-mcp-server (GitHub-API, Lizenz `NOASSERTION`, Release) und https://defra.github.io/ai-sdlc-tool-guidance/tool-guidance/mcps/sonarqube-mcp-summary (Suchauszug)
- [sonar-pricing] https://www.sonarsource.com/plans-and-pricing/
- [sonar-stats] https://www.trustradius.com/vendors/sonarsource, https://www.permira.com/portfolio/sonarsource/ (Suchauszug, GESAGT)
- [semgrep-lic] https://github.com/semgrep/semgrep/blob/develop/LICENSE
- [semgrep-rules] https://semgrep.dev/legal/rules-license/
- [semgrep-ai] https://semgrep.dev/blog/2025/building-an-appsec-ai-that-security-researchers-agree-with-96-of-the-time/, https://semgrep.dev/blog/2025/announcing-ai-noise-filtering-and-triage-memories, https://semgrep.dev/docs/semgrep-assistant/customize (Suchauszug)
- [opengrep] https://github.com/opengrep/opengrep
- [codeql-lic] https://github.com/github/codeql-cli-binaries/blob/main/LICENSE.md
- [gh-sarif] https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning
- [gh-cs] https://docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning
- [gh-autofix] https://docs.github.com/en/code-security/concepts/code-scanning/autofix-for-code-scanning
- [gl-sast] https://docs.gitlab.com/user/application_security/sast/
- [sarif] https://docs.oasis-open.org/sarif/sarif/v2.1.0/sarif-v2.1.0.html (OASIS Standard mit Errata 01, 2023-08-28)
- [an-ccsec] https://www.anthropic.com/news/claude-code-security
- [ccsec-rename] https://news.bensbites.co/posts/65614-anthropics-claude-security-formerly-claude-code-security-is-in-public-beta-for-enterprise-users-the-opus-47-powered-tool-can-scan-code-for-vulnerabilities (GESAGT)
- [ccsr] https://github.com/anthropics/claude-code-security-review
- [cx-sec] https://learn.chatgpt.com/docs/security (Weiterleitung von https://developers.openai.com/codex/security)
- [cx-sec-3p] https://codex.danielvaughan.com/2026/03/31/codex-security-agent-vulnerability-scanning-threat-modelling, https://www.unite.ai/openai-launches-codex-security-to-find-vulnerabilities-in-code (GESAGT)
- [aardvark] https://openai.com/index/introducing-aardvark (403 beim Abruf; Inhalt über https://venturebeat.com/security/meet-aardvark-openais-in-house-security-agent-for-code-analysis-and-patching, GESAGT)
- [codemender] https://deepmind.google/blog/introducing-codemender-an-ai-agent-for-code-security/
- [snyk-fix] https://docs.snyk.io/scan-with-snyk/snyk-code/manage-code-vulnerabilities/fix-code-vulnerabilities-automatically (Suchauszug)
- [aikido] https://help.aikido.dev/code-scanning/scanning-practices/sast-autotriage, https://www.aikido.dev/blog/reasoning-models-autotriage (Suchauszug)
- [zeropath-docs] https://zeropath.com/docs
- [zeropath-bench] https://zeropath.com/blog/toward-actual-benchmarks, https://github.com/ZeroPathAI/validation-benchmarks (Suchauszug, GESAGT)
- [dryrun] https://sacra.com/research/dryrun-security, https://aws.amazon.com/marketplace/pp/prodview-lva57v7kmxhei (GESAGT)
- [corgea] https://corgea.com/blog/whitepaper-blast-ai-powered-sast-scanner (Suchauszug, GESAGT)
- [cmx] https://checkmarx.com/product/checkmarx-one-assist, https://checkmarx.com/press-releases/checkmarx-joins-the-claude-marketplace/ (Suchauszug, GESAGT)

Markt und Benchmarks:
- [gartner-ast] https://www.gartner.com/en/documents/7027498, https://www.blackduck.com/resources/analyst-reports/gartner-magic-quadrant-appsec.html, https://www.invicti.com/clp/2026-gartner-magic-quadrant-for-application-security-testing (Suchauszug, GESAGT)
- [forrester-sast] https://checkmarx.com/blog/checkmarx-named-a-leader-in-the-forrester-wave-static-application-security-testing-solutions-q3-2025/, https://snyk.io/blog/snyk-named-a-leader-in-the-2025-forrester-sast-wave-sast-solutions-q3-2025, https://www.veracode.com/press-release/veracode-named-a-leader-in-the-2025-q3-forrester-wave-static-application-security-testing-solutions/ (GESAGT)
- [realvuln] https://arxiv.org/abs/2604.13764, Repo https://github.com/kolega-ai/Real-Vuln-Benchmark
- [castle] https://arxiv.org/abs/2503.09433, https://github.com/CASTLE-Benchmark (Suchauszug)
- [iris] https://arxiv.org/abs/2405.17238, https://github.com/iris-sast/iris, https://github.com/iris-sast/cwe-bench-java (Suchauszug)
- [ossf-cve] https://github.com/ossf-cve-benchmark/ossf-cve-benchmark (Suchauszug)
- [owasp-bench] https://owasp.org/www-project-benchmark/
- [juliet] https://samate.nist.gov/SARD/test-suites/112 und /111 (Suchauszug)
- [cybergym] https://arxiv.org/abs/2506.02548, https://github.com/sunblaze-ucb/cybergym (Suchauszug)
