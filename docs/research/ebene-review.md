<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
> Research note, dated 2026-11-01, not binding. Kept in German as written (ADR-53); the binding documents are docs/architecture and docs/design.

# Ebene PR-Code-Review: weltweiter Standard, Fähigkeits-Checkliste, Messung und Lücken (Stand 2026-10-31)

**Dated, not binding.** Datierte Recherche, Stand 2026-10-31, nicht verbindlich und nicht übersetzt; verbindlich ist die Plattform-Doku ([docs/architektur/](../architecture/README.md)).

Recherche für die dritte Owner-Runde (Owner, 2026-10-31): jede Ebene auf dem Niveau des weltweiten Standards ihres Fachgebiets, Projekt wird Open Source und von jedem selbst hostbar, nur Planung. Diese Datei behandelt nur die Ebene **PR-Code-Review** (Service `reviewer` in [02](../architecture/02-services.md) Abschnitt 3).

Einstufung wie im [README](../architecture/README.md) Abschnitt 6: **BELEGT** (Primärquelle selbst gelesen: Herstellerdoku, Repo, Datei, eigene Rechnung aus Primärdaten), **GESAGT** (Herstelleraussage, Marketing, Presse), **ABGELEITET** (eigener Schluss), **VERMUTET**. Alle Webquellen abgerufen am 2026-10-31. Das Abrufwerkzeug fasst Seiten durch ein kleines Modell zusammen; wo ich Rohdaten selbst per `curl` gelesen oder gerechnet habe, steht das dabei.

---

## 1. Urteil (Kurzfassung)

1. **Es gibt keinen einzelnen Qualitätsführer, sondern eine Spitzengruppe.** Auf dem einzigen herstellerunabhängigen Benchmark (Martian Code Review Bench) liegen offline Qodo Extended, cubic und Augment vorn (F2 im Profil `core` 64 bis 65 %, eigene Rechnung aus den MIT-Daten, BELEGT), online laut Presse cubic, Greptile, CodeRabbit und Copilot (cubic 64,9 % F1, Copilot 60,9 %, Stand 2026-10-06, GESAGT). Codex lag im Juli auf Platz 2 (GESAGT, Greptile). Die Abstände in der Spitze liegen innerhalb der statistischen Unschärfe eines 50-PR-Datensatzes (ABGELEITET, Abschnitt 2.3).
2. **Der Volumenstandard ist GitHub Copilot code review.** Copilot macht laut GitHub "more than one in five code reviews on GitHub" und läuft in über 12.000 Orgs automatisch (GESAGT, GitHub-Blog). Messlatte für unseren Reviewer ist deshalb: **Funktionsumfang und Treffsicherheit wie die Spitzengruppe.**
3. **Unser Gate B für den Reviewer steht auf einer falschen Zahl.** [07](../architecture/07-eval.md) Abschnitt 3.1 und 4 nimmt Greptiles 60,8 % F1 als Bezug für den Offline-Satz R2. Diese Zahl stammt vom **Online**-Leaderboard (Greptile-Post zum Stand 2026-07-30, BELEGT gelesen). Offline zeigt Martian standardmäßig F2 im Profil `core`; dort liegt Greptile v4 bei 51,2 % F2. Außerdem hat der Offline-Satz 173 Golden Comments, nicht 136 (selbst gezählt, BELEGT). Beides ist zu korrigieren.
4. **Zwei neue, offen lizenzierte Messwege machen Gate B konkret:** Martian Code Review Bench (MIT, Daten, Richter-Pipeline und Online-ETL im Repo, BELEGT) und **GitHub ReviewBench** (MIT, 219 PRs aus 187 Repos, Container-Vertrag für Prüflinge, lokaler Richter, Leave-Producer-Out-Wertung, BELEGT). Dazu SWE-PRBench (CC-BY-4.0) und AACR-Bench (Apache-2.0) als Ergänzung. O12 ("Martian-Lizenz prüfen") ist damit für den Benchmark selbst erledigt.
5. **Unser Reviewer-Kern ist auf Standardniveau entworfen, die Begleitfunktionen fehlen weitgehend.** Vorhanden: Befundschema, Verifier, Inkrement, Pfad-Anweisungen, Learnings, Ticket-Finder, Fix-Prompt, PR-Fixer. Es fehlen: Walkthrough mit Change-Tabelle, Sequenzdiagramme, Aufwand, verwandte PRs und Issues, Labels und Reviewer-Vorschläge, eingebaute und eigene Pre-Merge-Checks, Docstrings, lokaler Review in IDE und CLI (Pre-commit), ein Entwickler-MCP, Review-Analytics mit Export und Berichten, Multi-Repo-Kontext, Pause und Resume. Abschnitt 5 listet sie mit Ort in der Architektur.
6. **Für das Open-Source-Ziel** muss der Reviewer fremde Regeldateien lesen (AGENTS.md, CLAUDE.md, `.cursorrules`, Copilot-Instructions und weitere; Abschnitt 3 Nr. 12) und die Benchmark-Adapter mitliefern, aber keine Benchmark-Daten ins öffentliche Repo kopieren (Lizenzen der Quell-Repos, Abschnitt 4).

---

## 2. Befunde mit Quellen

### 2.1 Marktstellung (wer ist Standard)

| Aussage | Einstufung | Quelle |
|---|---|---|
| Copilot code review: "usage has grown 10X, now accounting for more than one in five code reviews on GitHub"; "More than 12,000 organizations now run Copilot code review automatically on every pull request"; 71 % der Reviews mit Befund, 29 % still, rund 5,1 Kommentare je Review (Stand 2026-03-05) | GESAGT (Herstellerblog, selbst gelesen) | [gh-60m] |
| Copilot code review: Stufen Lite, Balanced (Standard), Max; geschätzte Kosten je Review rund 0,25, 1,50 und 10 USD ohne Actions-Minuten; Anweisungen vom **Head**-Branch; Modellwahl nicht möglich; IDE: VS Code, Visual Studio, Xcode, JetBrains, CLI, Mobile, Azure DevOps (Preview) | BELEGT | [gh-ccr-doc] |
| CodeRabbit nennt sich "most installed AI app on GitHub and GitLab"; Series C 143 Mio. USD bei 1,5 Mrd. Bewertung (2026); ARR rund 40 Mio. USD (Schätzung Sacra, April 2026); rund 2 Mio. verbundene Repos | GESAGT bzw. Schätzung Dritter, nicht an Primärquelle geprüft | [sacra-cr], Suchauszüge |
| Cursor hat Graphite im Dezember 2025 gekauft; Graphite bleibt eigenständiges Produkt; der Name "Diamond" ist seit 2025-10 durch "Graphite Agent" ersetzt; eine Zusammenlegung mit Bugbot war angekündigt, ist aber nicht belegt | GESAGT (Presse) | [tc-graphite] |
| Bugbot: inkrementell seit letztem Review, Konfiguration vom Basis-Branch, learned rules, `@cursor remember`, Autofix (höchstens 3 Versuche), Check mit "fail on unresolved issues", `/review-bugbot` vor dem Push, Admin-API, nutzungsbasierte Abrechnung seit 2026-05 | BELEGT | [cursor-bugbot] |
| Bugbot laut Juni-Update rund 3-mal schneller (rund 90 s), 22 % billiger, 10 % mehr Bugs | GESAGT, nur Suchauszug, nicht selbst gelesen | Suchauszug zu cursor.com/blog/bugbot-updates-june-2026 |
| Ellipsis vermarktet sich heute als "Managed Claude Code agents in the cloud", nicht mehr als Review-Bot | BELEGT (Seitentitel und Beschreibung gelesen) | [ellipsis] |

**Schluss (ABGELEITET):** Nach Verbreitung ist CodeRabbit der Maßstab, den der Owner nennt (GESAGT, [sacra-cr]); nach Volumen ist es Copilot. Nach gemessener Treffsicherheit gibt es eine Spitzengruppe aus cubic, Qodo, Augment, Greptile, CodeRabbit, Copilot und Codex, deren Rangfolge je Benchmark, Profil und Richter wechselt.

### 2.2 Benchmarks und Datensätze

| Benchmark | Inhalt | Lizenz | Richter, Metrik | Nutzbar für uns | Einstufung, Quelle |
|---|---|---|---|---|---|
| **Martian Code Review Bench, offline** | 50 PRs aus Sentry, Grafana, Cal.com, Discourse, Keycloak; 173 Golden Comments (Critical 12, High 54, Medium 61, Low 46, selbst gezählt); Kategorien bug, security, concurrency, data, api, perf, test_gap, doc_defect, style, speculative | MIT (GitHub-API `spdx_id: MIT`, letzter Push 2026-09-15) | drei Richter (Claude Opus 4.5, GPT-5.2, Claude Sonnet 4.5), Standard Opus 4.5; Profile `strict`, `core`, `all`; F-beta 0,5 bis 3, Standard `core` und beta 2 | ja, als R2; Datensatz "builds on Augment and Greptile's published dataset", PR-URLs liegen teils unter `ai-code-review-evaluation/*-greptile` (Herkunft vom Hersteller) | BELEGT: [mcr-repo], [mcr-method], Dateien `offline/golden_comments/*.json`, `offline/analysis/benchmark_dashboard.json` |
| **Martian, online** | zieht laufend frische öffentliche PRs mit Bot-Kommentaren; Präzision = Vorschläge, die zu einer echten Änderung führten; Recall = echte Fixes, die der Bot vorher genannt hatte | MIT (Pipeline `online/etl`, `online/api_service`) | LLM-Schritte: Vorschläge extrahieren, Fixes extrahieren, Abgleich | als Online-Metrik auf eigenen Repos nachbaubar; öffentlich nur, wenn unser Bot auf Open-Source-Repos läuft und Martian ihn aufnimmt | BELEGT Repo-Struktur und Methodik [mcr-repo], [mcr-method]; Ranglisten GESAGT |
| **GitHub ReviewBench** | 219 PRs aus 187 Repos, 19 Sprachen; Test-Satz 25 PRs mit 352 Befunden; voller Satz 2.623 als TP gelabelte Befunde; Spiegel-Repos `review-bench/<owner>_<repo>` | MIT (LICENSE gelesen) | Leaderboard-Richter Claude Sonnet 5; Harbor-Variante mit Claude Opus 5; grounded und augmented Precision, Recall, F1, F-beta; Filter nach Schwere und Kategorie | ja, als R4: Prüfling ist ein Container nach festem Vertrag (Diff, Repo am Head, `findings.json` mit Datei, Zeilen, Text), lokale Wertung mit eigenem Richter möglich, Leaderboard nur über Portal | BELEGT: [rb-readme], [rb-contract], [rb-blog] |
| ReviewBench, Verzerrung | 45,2 % der Golden-TPs stammen von `ccr` (Copilot code review), davon 36,5 Punkte aus `ccr:gpt-5.5`; nur 1,5 % aus menschlichen Review-Kommentaren; GitHub hat die Erstläufe der Konkurrenz selbst ausgeführt, Copilot am 1. Oktober, cubic und Greptile im Juni | | Leave-Producer-Out-Wertung vorhanden | Bezug immer mit Leave-Producer-Out `ccr` rechnen | BELEGT [rb-readme], [rb-method]; Testdaten GESAGT [tns-rb] |
| ReviewBench, Ergebnis | Copilot Balanced 40,1 % grounded F1 auf Platz 1 | | | Bezugswert, aber vom Hersteller des Erstplatzierten | GESAGT [tns-rb]; Leaderboard-Seite lädt per JavaScript, nicht selbst gelesen |
| **SWE-PRBench** | 350 PRs, Ground Truth aus menschlichem Review-Feedback; Modelle finden 15 bis 31 % der menschlich gemeldeten Probleme, mit mehr Kontext monoton schlechter | CC-BY-4.0 (HF-README gelesen) | LLM-Richter | ja, als Menschen-Abgleich (R5) | Lizenz BELEGT [swe-prbench-hf]; Ergebnisse GESAGT [swe-prbench-arxiv] |
| **AACR-Bench** | 200 PRs aus 50 Repos, 10 Sprachen, 1.505 Kommentare (391 echte, 1.114 LLM-erzeugt und von über 80 Ingenieuren geprüft), Repo-Kontext | Apache-2.0 (LICENSE gelesen) | | ja, mehrsprachig mit Repo-Kontext | Lizenz BELEGT [aacr-gh]; Inhalt GESAGT [aacr-arxiv] |
| ContextCRBench | 67.910 Einträge, Zeilen-Kommentare mit Issue-, PR- und Code-Kontext | ungeprüft | | eher für Training und Teilaufgaben | GESAGT [ctxcr-arxiv] |
| SWR-Bench | 1.000 PRs aus den 12 Python-Projekten von SWE-bench | ungeprüft | LLM-Richter über Change-Points | nur Python | GESAGT [swr-fse] |
| LangChain ReviewBench | 59 Aufgaben aus dem LangSmith-Code, ohne Anbieter-Leaderboard | ungeprüft | | Modellvergleich, nicht Produkt | GESAGT [tns-rb] |
| Tenki, AIMultiple RevEval, Greptile-Benchmark 2025 | Hersteller- oder Händlertests | | | nicht als Bezug | GESAGT |

### 2.3 Werte auf Martian offline (eigene Rechnung)

Rechnung: Mikro-Mittel über die 50 PRs aus `offline/analysis/benchmark_dashboard.json` (Feld `tool_metrics` mit tp, fp, fn je PR und Profil), Richter Claude Opus 4.5 (Standard der Seite), Profil `core` (Standard). Probe: Copilot ergibt 58,0 % F2 auf Platz 5; The New Stack meldet für das Offline-Leaderboard "GitHub Copilot sits fifth with a 58% F2 score" und Qodo Deep auf Platz 1, cubic 2, Augment 3 ([tns-rb]). Die Rechnung trifft also die veröffentlichte Ansicht (BELEGT, Stand der Repo-Datei 2026-09-15; das Live-Leaderboard kann neuer sein).

| Werkzeug (Name laut Datei) | Präzision | Recall | F1 | F2 (Standard) |
|---|---|---|---|---|
| Qodo Extended | 67,1 % | 64,6 % | 65,8 % | 65,1 % |
| cubic v2 | 61,5 % | 65,8 % | 63,6 % | 64,9 % |
| Augment | 59,5 % | 65,2 % | 62,2 % | 64,0 % |
| Qodo v2 | 55,4 % | 62,0 % | 58,5 % | 60,6 % |
| GitHub Copilot | 38,5 % | 66,5 % | 48,7 % | 58,0 % |
| Gemini | 45,3 % | 55,1 % | 49,7 % | 52,8 % |
| GitLab Duo | 53,5 % | 52,5 % | 53,0 % | 52,7 % |
| Sourcery | 41,0 % | 55,1 % | 47,0 % | 51,5 % |
| Greptile v4 | 50,9 % | 51,3 % | 51,1 % | 51,2 % |
| CodeRabbit | 32,6 % | 59,5 % | 42,2 % | 51,1 % |
| Macroscope | 61,1 % | 48,7 % | 54,2 % | 50,8 % |
| Cursor Bugbot | 56,9 % | 46,8 % | 51,4 % | 48,6 % |
| Claude Code (CLI) | 46,3 % | 48,1 % | 47,2 % | 47,7 % |
| Devin | 69,1 % | 41,1 % | 51,6 % | 44,8 % |
| Kodus | 59,2 % | 38,6 % | 46,7 % | 41,5 % |
| Baz | 61,5 % | 37,3 % | 46,5 % | 40,5 % |
| Claude Code | 43,2 % | 38,0 % | 40,4 % | 38,9 % |
| Graphite | 100 % | 7,6 % | 14,1 % | 9,3 % |

Weitere Zeilen (gitar, codeant-v2, kg) stehen in der Datei. Mit dem Richter Sonnet 4.5 bzw. GPT-5.2 bleibt die Spitze (cubic, Qodo, Augment) gleich, die Reihenfolge darin wechselt (selbst gerechnet, BELEGT).

**Was daraus folgt (ABGELEITET):**
- CodeRabbit ist offline recall-stark und präzisionsschwach (32,6 % Präzision), online dagegen vorn: dort zählt, was Entwickler ändern, offline nur der Treffer auf 173 Golden Comments. Offline bestraft ein Werkzeug für echte Befunde, die nicht im Gold-Satz stehen; Martian selbst nennt das Offline-Ergebnis "might measure the wrong thing" und macht online zur Hauptmetrik ([mcr-method]).
- Statistik: Bei 173 Golden Comments hat ein Recall um 60 % eine Standardabweichung von rund 3,7 Punkten, das 95-%-Intervall ist rund plus minus 7 Punkte. Unterschiede in der Spitze (65,1 gegen 64,0) sind damit nicht unterscheidbar. Ein Gate B "mindestens bester Wert" auf diesem Satz allein wäre Zufall.
- Unser Ziel aus [07](../architecture/07-eval.md) Abschnitt 1 (10 Punkte Unterschied signifikant) erreicht man nur mit mehreren Sätzen zusammen (R2 plus R4 plus R5).

### 2.4 Martian online (Presse- und Herstellerangaben)

| Stand | Werte | Einstufung, Quelle |
|---|---|---|
| 2026-02 bis 03 (Start) | CodeRabbit 51,2 % bzw. 51,5 % F1, Platz 1; Greptile 50,2 % F1 mit 66,2 % Präzision | GESAGT [cr-martian], Suchauszug morphllm |
| 2026-07-30 | Greptile 60,8 % F1 (76,2 % P, 50,6 % R), Codex Connector 59,4 %, cubic 58,7 %, Devin 58,6 %, CodeRabbit 57,5 % (64,9 % P, 51,6 % R) | GESAGT (Greptile-Post, selbst gelesen) [greptile-martian] |
| 2026-10-06 | cubic 64,9 % F1, dann Greptile und CodeRabbit, Copilot Platz 4 mit 60,9 % | GESAGT [tns-rb] |

Das Live-Leaderboard `codereview.withmartian.com` lädt per JavaScript und war nicht selbst lesbar (ungeprüft).

### 2.5 Mechanik-Belege

| Anbieter | Mechanik | Einstufung, Quelle |
|---|---|---|
| Copilot code review | Ensemble mehrerer unabhängiger Läufe in der Stufe Lite: online Address Rate plus 8,0 %, Recall plus 13,6 %, Kommentare plus 61 %, Kosten je Review minus 8,0 %; ReviewBench sagte die Richtung voraus | GESAGT (GitHub-Blog, selbst gelesen) [rb-blog] |
| Copilot code review | agentische Architektur mit Repo-Kontext, Memory, Review-Plan vor dem Lesen, liest verlinkte Issues und PRs | GESAGT [gh-60m] |
| Greptile | Review-Tiers Base, Plus, Apex, Auto (1, 3, 10 Credits); Confidence Score 0 bis 5; Auto-Approve nur bei 5/5 mit Risiko-Deckel; `.greptile/`-Konfiguration kaskadierend je Verzeichnis; CLI für lokale Branches; MCP-Server für IDE-Agenten (offene Kommentare holen, Fixes, Reports); Analytics mit Address Rate, Bugs nach P0 bis P3, Export; Jira- und Linear-Abgleich; Self-Host per Docker Compose oder Helm | BELEGT [greptile-llms], [greptile-anatomy], [greptile-tiers], [greptile-approve], [greptile-analytics], [greptile-cli] |
| Qodo | mehrere Fach-Agenten; Kontext aus Codebasis, PR-Historie, Tickets, Standards; Befundarten Bugs, Regelverstöße, Anforderungslücken, UX-Abweichung zu Figma, Konflikte über Repos; Blast Radius; "Track resolved findings"; Review-Analytics; PR-Triage; On-Prem | BELEGT (Doku-Index und Übersicht) [qodo-overview], [qodo-llms] |
| cubic | Ultrareview, Custom Agents, Cross-Repo, Auto-Approval, Auto-Fix, Issue-Abgleich, Memory, `cubic.yaml`, eigene Review-Oberfläche mit gruppierten Änderungen, AI-Chat mit Diagrammen, CLI lokal und headless, MCP-Server, Analytics, Codebase-Scans, AI-Wiki | BELEGT (Doku-Index) [cubic-llms] |
| Baz | Planner, Review-Agenten aus wiederkehrendem Feedback ("Recommended Reviewers"), Custom Reviewers per Prompt, Security mit "SAST-inside", Plugins für Claude Code, Codex, Cursor, CLI, viele Tracker-Anbindungen | BELEGT (Doku-Index) [baz-llms] |
| Codex | `@codex review`, automatisches Review, nur P0 und P1 auf GitHub, Regeln in `## Code Review Rules` im nächstgelegenen AGENTS.md, `@codex fix the P1 issue`, `@codex security review` (Preview) | BELEGT [codex-gh] |
| Gemini Code Assist | Zusammenfassung, Review, `/gemini` im Kommentar, Styleguide je Repo oder über Google Cloud, `.github/workflows` immer ausgenommen; Enterprise-Variante in Preview, Verbindung immer in `us-east1` | BELEGT [gemini-review] |

---

## 3. Fähigkeits-Checkliste des Standards

Spalte "bei uns" verweist auf `docs/architektur/`. "teilweise" heißt: Mechanik angelegt, aber nicht als Funktion für Nutzer beschrieben.

| # | Fähigkeit | wer hat sie (Auswahl) | Beleg | bei uns |
|---|---|---|---|---|
| 1 | Automatisches Review bei Öffnen, Push, Ready; Filter nach Branch, Label, Titel, Draft | Copilot, Bugbot, Greptile, cubic | [gh-ccr-doc]; [cursor-bugbot] | ja: [02](../architecture/02-services.md) 3 Eingang, [04](../architecture/04-configuration-and-limits.md) `routing` |
| 2 | Inkrementelles Review seit letzter geprüfter SHA, "Addressed in commit" | Bugbot | [cursor-bugbot] | ja: 02 3 Stufe 8 |
| 4 | Walkthrough: Zusammenfassung, Change-Tabelle je Datei-Kohorte | Greptile, Qodo, Gemini | [greptile-anatomy]; [qodo-llms] | teilweise: Feld `summary` in `ReviewArtifact` (02 3), kein Schema |
| 5 | Sequenz- oder Ablaufdiagramme (Mermaid) | Greptile, cubic (im Chat) | [greptile-anatomy]; [cubic-llms] | nein |
| 6 | Risiko- bzw. Confidence Score | Greptile (0 bis 5) | [greptile-anatomy] | teilweise: `riskScore` (02 3), kein Aufwand |
| 8 | Inline-Befunde mit Schwere, Kategorie, Suggestion-Block | alle | [gh-ccr-doc] | ja: 02 3, 01 5 `renderSuggestion` |
| 9 | Fix-Prompt je Befund und Weitergabe an externe Agenten (Button, "Fix All") | Greptile, Bugbot ("Fix in Cursor"), cubic | [greptile-llms]; [cursor-bugbot] | teilweise: `agent_prompt` ja, Übergabe an fremde Agenten nein |
| 10 | Strenge-Profile und Tiefen-Stufen, vom Nutzer wählbar | Copilot (Lite, Balanced, Max), Greptile (Tiers), Bugbot (Effort) | [gh-ccr-doc]; [greptile-tiers]; [cursor-bugbot] | teilweise: `profile`, Router (02 3, 04), keine wählbaren Tiefen-Stufen |
| 11 | Pfad-Anweisungen per Glob | Copilot (`applyTo`), Greptile (`.greptile/` je Verzeichnis), Bugbot (BUGBOT.md aufwärts), Codex (verschachtelte AGENTS.md) | [gh-ccr-doc]; [greptile-llms]; [cursor-bugbot]; [codex-gh] | ja: 04 `path_instructions`, vom Basis-SHA |
| 12 | Fremde Regeldateien automatisch lesen (AGENTS.md, CLAUDE.md, `.cursorrules`, Copilot-Instructions, GEMINI.md, BUGBOT.md) | Baz, cubic | [baz-llms] | teilweise: 04 2 nennt AGENTS.md, REVIEW.md, CLAUDE.md, `.agents/rules` |
| 14 | Learnings aus Chat, `remember`-Befehl, Lernen aus Reaktionen und Annahme | Bugbot, Greptile, cubic, Qodo | [cursor-bugbot]; [greptile-llms] | teilweise: Learning-Kandidat aus Chat (02 3 Optional), Rauschfilter, Standards-Service; kein Befehl |
| 15 | Chat im PR mit Repo-Zugriff, Rückzug von Befunden | Greptile, Qodo, cubic, Gemini, Codex | [qodo-llms]; [gemini-review] | teilweise: `@agent ask` (03 4), Chat im Thread nur als Option (02 3) |
| 16 | Linter und SAST als Kandidatensignal im Review (verifiziert) | Baz ("SAST-inside") | [baz-llms] | teilweise: Linter bleiben eigener Workflow (Planungsstand 2026-10-31), `CheckEvidence` liest CI |
| 18 | Issue-Bezug: Ticket-Erfüllung je Anforderung | Qodo, Greptile, cubic, Baz, Copilot (liest verlinkte Issues) | [qodo-overview]; [greptile-llms]; [gh-60m] | ja: Finder `ticket` (02 3 Stufe 4) |
| 21 | Merge blockieren bei offenen Befunden | Bugbot ("fail on unresolved") | [cursor-bugbot] | ja: Check `ai-review` mit `failure` (02 3) |
| 22 | Automatische Freigabe (Approve) mit Risiko-Deckel | Greptile, cubic, Copilot (zählt nur, wenn erlaubt) | [greptile-approve]; [cubic-llms]; [gh-ccr-doc] | nein: 02 3 "nie Approve"; Merge-Gate nur für Agent-PRs (03 1a) |
| 25 | Fix comments, Fix CI, Merge-Konflikte | Bugbot, cubic, Codex | [cursor-bugbot]; [codex-gh] | ja: PR-Fixer (02 5) |
| 27 | Review in der IDE auf nicht committeten Änderungen | Copilot, cubic, Greptile (über MCP) | [gh-ccr-doc]; [cubic-llms] | nein |
| 28 | CLI-Review vor dem Push (Pre-commit), maschinenlesbare Ausgabe für Coding-Agenten | Greptile CLI, cubic CLI, Bugbot `/review-bugbot`, Baz CLI, Qodo Toolbox | [greptile-cli]; [cubic-llms]; [cursor-bugbot]; [baz-llms]; [qodo-llms] | nein |
| 29 | MCP-Server für Entwickler-Agenten (offene Befunde holen, als behoben melden, Regeln anlegen) | Greptile, cubic, Baz, Qodo | [greptile-llms]; [cubic-llms]; [baz-llms]; [qodo-llms] | nein: Plattform-MCP nur für Sandbox-Agenten ([05](../architecture/05-security.md) 1) |
| 30 | Multi-Repo- bzw. Cross-Repo-Kontext | Greptile, cubic, Qodo | [greptile-llms]; [cubic-llms] | nein |
| 32 | Security-Spur mit Reachability, Blast Radius, Delta-Scan | Qodo, Baz | [qodo-llms]; [baz-llms] | teilweise: Finder `security` (02 3) |
| 33 | Review-Analytics (Acceptance oder Address Rate, Kommentare je PR, Schwere, Zeit bis Merge), Export, geplante Berichte | Greptile, Bugbot (API mit `resolution_status`), cubic, Qodo | [greptile-analytics]; [cursor-bugbot] | teilweise: Metriken in 07 6, Admin-UI und Ledger-Dashboards nur für Kosten ([06](../architecture/06-operations-and-deployment.md) 4) |
| 34 | Review-Queue und Review-Oberfläche (Triage, gruppierte Änderungen in Lesereihenfolge) | cubic, Qodo (PR Triage), Graphite | [cubic-llms] | nein |
| 35 | Benachrichtigung und Agent in Slack oder Discord | Baz | [baz-llms] | teilweise: `Notifier` (01 10) |
| 36 | Mehrere Code-Hoster | Greptile (unter anderem Gitea, Perforce) | [greptile-llms] | ja: 01 5 und 11.2 |
| 37 | Selbst hosten | Greptile (Docker Compose, Helm), Qodo (On-Prem) | [greptile-llms]; [qodo-llms] | ja: Kern der Architektur (06) |
| 39 | Kosten je Review offen ausgewiesen | Copilot (Doku), Greptile (Credits je Tier) | [gh-ccr-doc]; [greptile-tiers] | ja: Ledger (06, 07 6) |

Die Nummern 3, 7, 13, 17, 19, 20, 23, 24, 26, 31 und 38 entfallen in dieser Fassung: sie stützten sich nur auf Herstellerdoku oder private Vorarbeiten, deren Auswertung nach [10](../architecture/10-standards-per-layer.md) Abschnitt 16 nicht weitergeführt wird.

Zählung: ja 10, teilweise 11, nein 7 von 28 (per Skript aus der Tabelle gezählt).

---

## 4. Wie man das Niveau misst (Vorschlag für Gate B Reviewer)

### 4.1 Offline-Sätze

| Satz | Quelle | Wertung | Rolle |
|---|---|---|---|
| R1 bothy | wie [07](../architecture/07-eval.md) 3.1 | Recall auf adressierten CodeRabbit-Befunden | Gate A, Regression; nicht veröffentlichbar (eigene Daten) |
| R2 Martian offline (neu gefasst) | `withmartian/code-review-benchmark`, MIT, 50 PRs, 173 Golden Comments | genau wie die Seite: Profil `core`, F-beta 2, Richter Claude Opus 4.5, Mikro-Mittel; Bezugswerte aus derselben Datei mit demselben Richter neu rechnen | Gate B, Teil 1 |
| R4 ReviewBench (neu) | `review-bench/ReviewBench`, MIT, 219 PRs | grounded Recall und F1 mit Leaderboard-Richter (Claude Sonnet 5), dazu Leave-Producer-Out `ccr`; drei Läufe wie das offizielle Finale | Gate B, Teil 2 |
| R5 SWE-PRBench, AACR-Bench (neu) | CC-BY-4.0 bzw. Apache-2.0 | Recall gegen menschliches Feedback (SWE-PRBench), mehrsprachig mit Repo-Kontext (AACR) | Gate A gegen nacktes Claude Code; Plausibilität |
| R3 privat je Installation | wie 07 3.1 | Präzision von Hand | Gate A Präzision |

**Adapter statt Kopie:** Unser Reviewer bekommt einen Eval-Adapter, der den ReviewBench-Vertrag erfüllt (Repo am Head unter `/work/repo`, Diff, `findings.json` mit `file`, `start_line`, `end_line`, `message`; [rb-contract]). Derselbe Adapter bedient R2 und R5. Der Vertrag passt zu unserer Sandbox (frischer Container je PR, Egress-Allowlist über Proxy); die Plattform-Kette bleibt gleich, nur `effect_sink: record` (07 1). Die Benchmark-Daten werden zur Laufzeit geladen, nicht ins öffentliche Repo kopiert (Quell-Repos stehen unter eigenen Lizenzen, Abschnitt 6 Owner-Punkt B).

### 4.2 Gate B Reviewer, konkret

| Messgröße | Satz | Bezugswert (heute) | Schwelle |
|---|---|---|---|
| F2 `core` | R2 | Spitze 65,1 % (Qodo Extended), Maßstab CodeRabbit 51,1 %, nacktes Claude Code (CLI) 47,7 % (eigene Rechnung, BELEGT) | Pflicht: nicht unter CodeRabbit im 95-%-Intervall; Ziel: im Intervall der Spitze. Bezug bei jedem Lauf aus der dann aktuellen Datei neu rechnen, weil das Leaderboard sich ändert |
| Präzision `core` | R2 | CodeRabbit 32,6 %, Spitze 59 bis 67 % | Startwert 55 % (Schätzung), damit "Niveau Spitze" nicht über reinen Recall erreicht wird |
| grounded Recall und F1, Leave-Producer-Out `ccr` | R4 | Copilot Balanced 40,1 % F1 (GESAGT, ohne Leave-Producer-Out) | nicht unter dem besten öffentlich gelisteten Wert im Intervall; Zahl vor dem ersten Lauf vom Leaderboard ablesen (ungeprüft, JS-Seite) |
| Kommentare je PR, Anteil stiller Läufe | R2, R4 | Copilot 5,1 je Review, 29 % still (GESAGT) | berichten, keine Schwelle |
| Dauer bis Review | Pilot | Greptile rund 3 min (BELEGT Doku), Bugbot rund 90 s (GESAGT) | Startwert nach Pilot festlegen |
| Kosten je Review | alle | Copilot 0,25, 1,50, 10 USD je Stufe (BELEGT) | berichten je Provider, keine Schwelle vor Messung |

### 4.3 Online-Metriken

- **Address Rate nach Martian-Definition** (Vorschlag wird zur echten Änderung) und **Recall nach Martian** (echte Fixes nach dem Review, die der Bot vorher genannt hatte). Die ETL-Pipeline liegt unter MIT im Repo (`online/etl`) und kann auf unsere eigenen Repos zeigen (BELEGT Struktur). Damit sind unsere Online-Werte mit dem öffentlichen Leaderboard vergleichbar, statt einer eigenen Definition.
- Weiter wie 07 6: Resolution Rate beim Merge (Bugbot), Rückzüge, Reaktionen nur als Nebensignal.

### 4.4 Gates für die Begleitfunktionen (neu, Startwerte als Schätzung)

| Funktion | Messung | Gate |
|---|---|---|
| Walkthrough | Richter-Rubrik (vollständig, korrekt, keine erfundene Datei) gegen Stichprobe mit Menschen-Label | jede genannte Datei existiert im Diff (deterministisch, 100 %) |
| Sequenzdiagramm | Mermaid parst; jeder Teilnehmer ist ein Symbol oder Dienst im Diff oder Impact-Set | 100 % parsbar, 0 erfundene Teilnehmer |
| Aufwand und Risiko | Spearman gegen menschliche Review-Dauer bzw. spätere Reverts | berichten, Schwelle nach Pilot |
| Pre-Merge-Checks | eigene Fälle je Check (pass, fail, inconclusive) | Fehlurteil 0 auf der Suite |
| Docstrings | Build und Linter grün, nur berührte Symbole, Format wie vorhandene Docstrings | 100 % Build grün |
| Lokaler Review (CLI, IDE) | gleiche Befunde wie PR-Review auf demselben Diff | Übereinstimmung der P0/P1-Fingerprints, Startwert 90 % |

---

## 5. Was die Anbieter offenlegen und was proprietär bleibt

**Übernehmbar:**
- **ReviewBench** (MIT): Agent-Vertrag, `try-agent.sh`, Richter-CLI mit frei wählbarem Modell, Klassifikator-Prompts für Schwere und Kategorie, Leave-Producer-Out-Wertung, Methodik mit Validitätsgrenzen ([rb-readme], [rb-contract], [rb-method]). Der Vertrag eignet sich auch als unser externes Plugin-Format für "fremden Reviewer als Finder" (ABGELEITET).
- **Martian** (MIT): Golden Comments, Richter-Pipeline, Online-ETL und API-Dienst ([mcr-repo]).
- **Formate aus Doku** (Idee, nicht Code): Greptile `.greptile/` kaskadierend ([greptile-llms]); Copilot `applyTo` ([gh-ccr-doc]); Codex `## Code Review Rules` in AGENTS.md ([codex-gh]); Bugbot `bugbot.yaml` vom Basis-Branch ([cursor-bugbot]). Für ein Open-Source-Produkt heißt das: diese Dateien als Regelquellen einlesen, damit Teams ohne Umbau wechseln können.
- **Mechaniken mit Messbeleg** (GESAGT): Ensemble mehrerer Läufe (Copilot, [rb-blog]); Auto-Tier nach Größe und Risiko (Greptile [greptile-tiers]); Approve nur bei bestem Score und Risiko-Deckel (Greptile).
- **AACR-Bench** (Apache-2.0), **SWE-PRBench** (CC-BY-4.0): Datensätze und Harness.

**Proprietär (nicht übernehmbar):** Prompts aller Review-Produkte, Modellzuordnung je Stufe, Filterschwellen, Greptiles Confidence-Formel (nur Kriterien genannt), Qodo Extended und Ultrareview im Detail, Bugbots Lernmechanik im Detail. Nachbau nur über die beschriebenen Kriterien plus Eval.

---

## 6. Folgen für unsere Architektur

### 6.1 Konkrete Änderungen je Datei

| Datei, Abschnitt | Was neu oder anders |
|---|---|
| [07](../architecture/07-eval.md) 3.1 R2 | "136 handkuratierte Golden Comments" auf **173** korrigieren (selbst gezählt); Lizenz MIT als BELEGT eintragen; Herkunft "baut auf dem veröffentlichten Datensatz von Augment und Greptile auf" als Einschränkung ergänzen; Wertung festlegen: Profil `core`, F-beta 2, Richter Opus 4.5, Bezugswerte aus der Datei mit demselben Richter |
| 07 3.1 R2 und 4 Zeile Reviewer | Bezug "Greptile 60,8 % F1" streichen (Online-Wert, nicht R2); ersetzen durch die Tabelle aus Abschnitt 4.2 dieses Berichts; Online-Werte (Greptile 60,8 % am 2026-07-30, cubic 64,9 % am 2026-10-06) nur als Bezug für die Online-Metrik, GESAGT |
| 07 3.1 | neue Sätze **R4 ReviewBench** und **R5 SWE-PRBench, AACR-Bench** mit Lizenz, Größe, Richter; Hinweis auf `ccr`-Verzerrung und Leave-Producer-Out |
| 07 1 | "Eval-Adapter nach ReviewBench-Vertrag" als gemeinsame Schnittstelle aller Review-Sätze; Daten zur Laufzeit laden, nicht ins Repo |
| 07 3.1 Metriken, 6 | Online Address Rate und Recall nach Martian-Definition, Pipeline aus `online/etl` |
| 07 4 | Gates der Begleitfunktionen (Abschnitt 4.4) als eigene Zeilen oder als Unterpunkt Reviewer |
| 07 7 und [09](../architecture/09-decisions.md) O12 | O12 für den Benchmark selbst als erledigt markieren (MIT BELEGT); offen bleibt nur die Weitergabe von Code der Quell-Repos (Owner-Punkt B) |
| [02](../architecture/02-services.md) 3 Messlatte | Zeilen ergänzen: Qodo (mehrere Fach-Agenten, Anforderungslücken), cubic (Spitze Martian), Copilot (Stufen Lite, Balanced, Max; Ensemble), Greptile (Tiers, Confidence, Auto-Approve). Messlatte-Satz: "Funktionsumfang und Treffsicherheit wie die Spitzengruppe auf R2 und R4" |
| 02 3 Ausgang | `ReviewArtifact` erweitern: `walkthrough { summary, changes[]: { files[], text } }`, `diagram?` (Mermaid), `effort` (1 bis 5), `related[]` (Issues, PRs mit Zitat), `labels[]`, `suggestedReviewers[]`, `preMergeChecks[]: { id, result: passed, failed, inconclusive, reason }` |
| 02 3 Stufen | neue Stufe "Begleit-Generatoren" parallel zu den Findern (kleines Modell, nur Zusammenfassung des Kontextpakets); neue Stufe "Linter-Import": SARIF bzw. rdjson aus CI und Werkzeugen wie SonarQube, Semgrep, ruff als **Kandidatensignal**, das der Verifier bestätigt. Die Regel des Planungsstands, dass Linter nicht im Reviewer laufen, bleibt und wird um den Import ergänzt (heute ADR-33 in [09](../architecture/09-decisions.md)) |
| 02 3 Optional | Chat im Thread aus "Optional" in den Kern heben (Funktion 15 gehört bei allen Anbietern zum Grundumfang); `@agent remember` als ausdrücklicher Learning-Befehl |
| 02 neu 3a "Lokaler Review" | Reviewer als Bibliothek (gibt es schon für den Coder-Self-Review, 02 2 Stufe 5) plus CLI `agent review --local [--uncommitted]` und IDE-Erweiterung später. Basis ist der Merge-Base mit dem Default-Branch, Regeln vom Default-Branch. Ausgabe maschinenlesbar für Coding-Agenten. Ausführung wahlweise lokal mit eigenem Credential des Nutzers oder als Work-Item über die Work-API |
| 02 neu 3b "Entwickler-MCP" | Lese-Tools für IDE-Agenten: offene Befunde eines PRs, Fix-Prompt, Regeln, Learnings; Schreibwunsch nur "als behoben markiert" (wird beim nächsten Inkrement verifiziert) |
| 02 3 Pre-Merge | `checks[]` in der Konfiguration: eingebaute (Titel, Beschreibung, Issue verlinkt, Docstring-Abdeckung berührter Symbole) und eigene in natürlicher Sprache, read-only im Verifier; Ergebnis als eigener Check oder Abschnitt, optional blockierend |
| 02 3 Finishing Touches | `@agent docstrings` als kleiner Job des PR-Fixers (Commit auf Agent-Branch oder Stacked-PR, gleiche Verbote); `@agent tests` als Alias auf `@agent qa unit` |
| [03](../architecture/03-flow-and-orchestration.md) 4 Befehle | neu: `@agent pause`, `@agent resume`, `@agent summary`, `@agent remember <Fakt>`, `@agent docstrings`, `@agent tests`, `@agent resolve` (eigene Threads); Auto-Pause nach `reviewer.auto_pause_after` Commits |
| [04](../architecture/04-configuration-and-limits.md) 3 `services.reviewer` | neue Schlüssel: `tier: auto, base, deep` (Router-Deckel), `summary: { walkthrough, diagrams, effort, related, labels, reviewers }`, `checks[]`, `auto_pause_after`, `guideline_sources: [AGENTS.md, CLAUDE.md, .cursorrules, .github/copilot-instructions.md, .github/instructions/**, GEMINI.md, .cursor/BUGBOT.md, .greptile/**]`, `linter_import: [sarif, rdjson]` |
| 04 2 Basis-Branch-Regel | ausdrücklich: alle fremden Regeldateien aus `guideline_sources` vom Basis-SHA (Copilot liest vom Head, [gh-ccr-doc]; wir bewusst nicht) |
| [01](../architecture/01-plugin-interfaces.md) 3 TriggerSource | Ursprung `cli` (lokaler Review) und `mcp` (Entwickler-MCP) als Eingänge mit Nutzer-Identität |
| 01 5 SCMProvider | Fähigkeiten `REQUEST_REVIEWERS` und `RELATED_SEARCH` (Issues und PRs suchen) ergänzen; `LABELS` ist da |
| [05](../architecture/05-security.md) | lokaler Review: Diff verlässt den Rechner des Nutzers nur bei Ausführung über die Work-API, Datenweg-Policy gilt; Entwickler-MCP: Token je Nutzer, nur Lesen plus "behoben markieren", Rechte beim Provider geprüft; Linter-Import: SARIF ist Untrusted |
| [06](../architecture/06-operations-and-deployment.md) 4 | Admin-UI "Review-Analytics": Address Rate, Recall nach Martian, Kommentare je PR nach Schwere, stille Läufe, Zeit bis Merge, Kosten je Review; Export CSV; geplanter Bericht über `Notifier` |
| [08](../architecture/08-roadmap.md) | Reviewer-Stufe teilen: Kern (heutige Stufe) und "Reviewer Begleitfunktionen" (Walkthrough, Diagramm, Checks, Chat, Pause) als eigene Stufe danach; CLI, Entwickler-MCP und Analytics als spätere Stufe; Eval-Adapter nach ReviewBench-Vertrag gehört in Stufe 0 |
| README 6 Webquellen | Quellen aus Abschnitt 8 dieses Berichts aufnehmen; [martian] auf das Repo umstellen |

### 6.2 Lücken, die den Abstand zum Standard ausmachen (nach Wirkung geordnet, ABGELEITET)

1. **Messbarkeit:** Ohne R2-Neufassung und R4 ist "Niveau des Standards" nicht prüfbar. Höchste Priorität, weil alle anderen Entscheidungen (Filter, Ensemble, Tiers) darauf kalibriert werden.
2. **Treffsicherheit:** Spitze liegt bei rund 60 % Präzision und 65 % Recall auf R2. Hebel laut Herstellern: Verifier je Befund (haben wir), Ensemble mehrerer Läufe mit Mehrheit (bei uns nur für P0 optional, 02 3; Copilot meldet für Lite mehr Recall und weniger Kosten, GESAGT), Fach-Finder (haben wir), Tiers nach Risiko (Router, ohne Nutzerwahl).
3. **Begleitfunktionen** 4 bis 6: für Nutzer sofort sichtbar, technisch klein (Generatoren auf dem schon vorhandenen Kontextpaket).
4. **Entwickler-Schleife** 27 bis 29: lokaler Review und MCP. Heute Standard bei Greptile, cubic, Bugbot, Baz, Qodo; bei uns gar nicht vorgesehen.
5. **Analytics** 33: ohne sie kein Nachweis gegenüber Teams und kein Online-Gate.
6. **Kontextbreite** 30, 16: Multi-Repo, MCP-Quellen, Linter-Import.
7. **Queue und Oberfläche** 34: eigener Produktbereich, eher später.

---

## 7. Owner-Entscheidungen

| # | Frage | Art | Empfehlung | Grund |
|---|---|---|---|---|
| A | Unseren Reviewer auf öffentlichen Leaderboards einreichen (ReviewBench-Portal, Martian) | Außenwirkung, Konto (GitHub-Login, GHCR-Image), Geld (eigene Inferenz für drei volle Läufe; Richter zahlt ReviewBench nur im Finale) | ja, aber erst nach grünem Gate A und internem R4-Lauf; eigener API-Schlüssel mit Ausgabengrenze, wie ReviewBench selbst empfiehlt | für ein Open-Source-Produkt ist ein unabhängiger öffentlicher Wert der stärkste Qualitätsbeleg; vorher intern messen vermeidet einen schwachen ersten Eintrag |
| B | Benchmark-Daten im öffentlichen Repo | Recht (Lizenzen) | nur Adapter und Download-Skript mit gepinntem Commit veröffentlichen, keine Kopien von Golden Sets oder PR-Code | die Benchmark-Repos sind MIT, CC-BY-4.0 bzw. Apache-2.0, die enthaltenen PRs aber Code der Quell-Repos unter deren Lizenzen (Sentry, Grafana, Cal.com u. a.; im Einzelnen ungeprüft) |
| C | Automatische Freigabe (Approve) für menschliche PRs anbieten | Produkt | als Option, Standard aus: nur bei leerem P0/P1, Risiko unter Deckel, nie auf `protected_paths`, zählt als eine Freigabe und ersetzt keine Branch-Regel (Muster Greptile) | Standardfunktion bei Greptile und cubic; das Merge-Gate für Agent-PRs gibt es schon, die Risiken sind dieselben |
| D | Eval-Budget für R2 und R4 (Richter- und Prüflingsläufe, drei Wiederholungen) | Geld | in O5 aufnehmen; Höhe nach einem Probelauf auf dem 25-PR-Testsatz von ReviewBench festlegen | ohne Probe ist jede Zahl geraten |

Keine weiteren echten Owner-Punkte: alle übrigen Folgen sind Architekturentscheidungen.

---

## 8. Offene Punkte

- Live-Leaderboards von Martian und ReviewBench nicht selbst gelesen (JavaScript); Werte nur aus Presse und Herstellern. Vor dem ersten Gate-B-Lauf direkt ablesen.
- ReviewBench-Werte für CodeRabbit, Greptile, cubic: ob gelistet, ungeprüft.
- Lizenz von SWR-Bench und ContextCRBench ungeprüft.
- Lizenzen der Quell-Repos in Martian und ReviewBench im Einzelnen ungeprüft (Owner-Punkt B).
- Copilot: ob CodeQL oder ESLint heute direkt im Review laufen, weiter unklar; die Doku nennt nur GitHub Code Quality als eigenes Produkt.
- Gemini Code Assist: Befehlsliste und `config.yaml` stehen auf einer anderen Seite, nicht gelesen.
- Qodo Extended ("Qodo Deep"), cubic Ultrareview und Greptile Apex: Mechanik nicht dokumentiert, nur Namen.
- Graphite Agent: aktueller Funktionsstand nach der Übernahme ungeprüft.
- Bugbot-Juni-Zahlen nur aus Suchauszug.
- Ob Martians Online-Tracker einen neuen Bot ohne Einreichung erfasst: ungeprüft (Liste der Bots ist fest im Code).

---

## 9. Quellen (alle abgerufen 2026-10-31)

Benchmarks:
- [mcr-repo] https://github.com/withmartian/code-review-benchmark (README, LICENSE über GitHub-API, `offline/golden_comments/*.json`, `offline/analysis/benchmark_dashboard.json`, selbst geladen und ausgewertet)
- [mcr-method] https://github.com/withmartian/code-review-benchmark/blob/main/methodology/summary.md
- [mcr-board] https://codereview.withmartian.com (nicht lesbar, JavaScript)
- [greptile-martian] https://www.greptile.com/content-library/greptile-martian-code-review-benchmark
- [cr-martian] https://coderabbit.ai/blog/coderabbit-tops-martian-code-review-benchmark (nur Suchauszug)
- [rb-blog] https://github.blog/ai-and-ml/reviewbench-an-open-benchmark-for-ai-code-review/
- [rb-readme] https://github.com/review-bench/ReviewBench (README und LICENSE per raw.githubusercontent.com gelesen)
- [rb-contract] https://github.com/review-bench/ReviewBench/blob/main/AGENT_CONTRACT.md
- [rb-method] https://github.com/review-bench/ReviewBench/blob/main/docs/METHODOLOGY.md (Abschnitt Producer-Zusammensetzung gelesen)
- [rb-site] https://review-bench.ai/ (nicht lesbar, JavaScript)
- [tns-rb] https://thenewstack.io/github-reviewbench-code-review/
- [swe-prbench-hf] https://huggingface.co/datasets/foundry-ai/swe-prbench
- [swe-prbench-arxiv] https://arxiv.org/abs/2603.26130
- [aacr-gh] https://github.com/alibaba/aacr-bench
- [aacr-arxiv] https://arxiv.org/abs/2601.19494
- [ctxcr-arxiv] https://arxiv.org/abs/2511.07017
- [swr-fse] https://conf.researchr.org/details/fse-2026/fse-2026-research-papers/78/SWR-Bench-Assessing-LLM-Performance-in-Real-World-Code-Review-Comment-Generation

Anbieter:
- [gh-60m] https://github.blog/ai-and-ml/github-copilot/60-million-copilot-code-reviews-and-counting/
- [gh-ccr-doc] https://docs.github.com/en/copilot/concepts/agents/code-review
- [cursor-bugbot] https://cursor.com/docs/bugbot
- [greptile-llms] https://www.greptile.com/docs/llms.txt
- [greptile-anatomy] https://www.greptile.com/docs/code-review/first-pr-review.md
- [greptile-tiers] https://www.greptile.com/docs/code-review/review-tiers.md
- [greptile-approve] https://www.greptile.com/docs/code-review/auto-approve-prs.md
- [greptile-analytics] https://www.greptile.com/docs/account/analytics.md
- [greptile-cli] https://www.greptile.com/docs/code-review/greptile-cli.md
- [qodo-llms] https://docs.qodo.ai/llms.txt
- [qodo-overview] https://docs.qodo.ai/code-review/overview
- [cubic-llms] https://docs.cubic.dev/llms.txt
- [baz-llms] https://docs.baz.co/llms.txt
- [ellipsis] https://docs.ellipsis.dev/llms.txt (leitet auf ellipsis.dev um, Seitentitel "Ellipsis | Managed Cloud Agents")
- [codex-gh] https://learn.chatgpt.com/docs/third-party/github
- [gemini-review] https://docs.cloud.google.com/gemini/docs/code-review/review-repo-code (Stand der Seite 2026-10-26)
- [tc-graphite] https://techcrunch.com/2025/12/19/cursor-continues-acquisition-spree-with-graphite-deal (GESAGT, Suchauszug)
- [sacra-cr] https://sacra.com/c/coderabbit/ (GESAGT, Suchauszug)

Eigenes Projekt: `docs/architektur/*`, vor allem [07](../architecture/07-eval.md) 3.1.
