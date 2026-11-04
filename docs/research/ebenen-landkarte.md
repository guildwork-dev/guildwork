<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
> Research note, dated 2026-11-01, not binding. Kept in German as written (ADR-53); the binding documents are docs/architecture and docs/design.

# Ebenen-Landkarte: KI-Agenten und Dienste je Aufgabe im Entwicklungszyklus (Stand 2026-10-31)

**Dated, not binding.** Datierte Recherche, Stand 2026-10-31, nicht verbindlich und nicht übersetzt; verbindlich ist die Plattform-Doku ([docs/architektur/](../architecture/README.md)).

Recherche zur dritten Owner-Runde (Owner, 2026-10-31, Vorgaben 1 bis 5). Thema: Welche Ebenen des Softwareentwicklungszyklus haben 2026 spezialisierte KI-Agenten oder Dienste, wer ist dort der Standard, was deckt unsere Zielarchitektur ([docs/architektur/](../architecture/README.md)) heute ab, und was soll daraus werden.

Abgrenzung: Für Review, Planung und Architektur, Coding, QA, PR-Fix und CI, Wissen/Standards/Doku sowie statische Analyse und Security recherchieren eigene Agenten parallel. Diese Ebenen stehen hier nur kurz mit Verweis auf die schon belegten Messlatten in [02-services.md](../architecture/02-services.md). Der Schwerpunkt liegt auf den übrigen Ebenen und auf der Gesamtkarte.

Einstufung wie im [README](../architecture/README.md) Abschnitt 6: **BELEGT** (Primärquelle selbst gelesen), **GESAGT** (Herstelleraussage, Marketing, Drittbericht, Suchauszug), **ABGELEITET** (eigener Schluss), **VERMUTET**. Alle Webquellen abgerufen am 2026-10-31. Das Abrufwerkzeug liefert eine Zusammenfassung durch ein kleines Modell; Zitate sind deshalb sinngemäß. Wo nur ein Suchauszug vorlag und die Seite nicht selbst abgerufen wurde, steht GESAGT mit dem Vermerk "Suchauszug".

---

## 1. Urteil (Kurzfassung)

1. **Die sieben Services decken den Kern ab, aber nicht die Ränder.** Planner, Coder, Reviewer, QA, PR-Fixer, Indexer und Standards treffen die Ebenen, auf denen die stärksten Anbieter 2026 arbeiten (Review, Coding, Planung, Tests, PR-Fix, Wissen). Es fehlen ganz: **Issue-Triage** (Duplikate, Labels, Zuständigkeit, Spam und Slop), **Doku-Pflege** (Docstrings, Doku-Sync nach Merge, Release Notes), die Anbindung von **Abhängigkeits-Bots**, **Incident-Übergaben** aus Beobachtungswerkzeugen und **Migrationskampagnen über viele Repos**. ABGELEITET aus Abschnitt 2 und [02](../architecture/02-services.md).
2. **Zwei neue Services lohnen sich, der Rest wird Plugin oder bewusst nicht gebaut.**
   - Neu als Service: `triage` (läuft auf jedem Issue, ohne Shell, billig, Eingang des autonomen Durchlaufs) und `docs` (Docstrings, Doku-Sync, Release Notes). Beide haben einen klaren Standard (Linear Triage Intelligence; Mintlify Agent).
   - Als Plugin eines bestehenden Services: Security-Scanner, Sonar, Abhängigkeits-Bots, Kosten-Diff für IaC, Barrierefreiheit, Performance-Benchmarks, Rezept-Engines für Migrationen.
   - Bewusst kein eigener Agent: Incident und On-Call (SRE). Die Standards (Azure SRE Agent, Datadog Bits, PagerDuty SRE Agent, Sentry Seer) brauchen Produktionszugriff und Telemetrie; unsere Plattform wird stattdessen das **Ziel ihrer Übergabe** (Seer übergibt bereits an Claude Code, Cursor und Copilot, [sentry-fix] BELEGT).
3. **Die wichtigste Architekturlücke ist keine Ebene, sondern eine Plugin-Art.** Fast alle Randebenen werden 2026 von deterministischen Werkzeugen getragen, die ein Agent aufruft (Renovate, Dependabot CLI, OpenRewrite, Infracost, axe-core, Semgrep, Sonar). Unsere acht Plugin-Arten haben dafür keinen Platz; das Self-Check-Bündel des Coders nennt Semgrep, osv-scanner und gitleaks fest im Text ([02](../architecture/02-services.md) Abschnitt 2 Stufe 4). Empfehlung: neunte Plugin-Art **`Analyzer`** mit SARIF-artiger Befundausgabe, Lauf in der Sandbox und Lizenzangabe im Manifest. ABGELEITET.
4. **Open Source (Vorgabe 2) ändert die Werkzeugwahl.** Ein öffentliches, selbst hostbares Projekt darf nur frei lizenzierte Werkzeuge mitliefern. Codeflash steht unter BSL-1.1 ([codeflash] BELEGT), Teile von OpenRewrite unter Moderne Source Available oder proprietär ([openrewrite] BELEGT), Renovate unter AGPL-3.0 ([renovate] BELEGT), Axe MCP Server ist Teil eines Bezahlprodukts ([axe-mcp] GESAGT). Folge: Fremdwerkzeuge werden nie gebündelt, sondern vom Betreiber als Image gewählt; die Plattform liefert nur Standardwerkzeuge mit freier Lizenz (Dependabot-core MIT, axe-core MPL-2.0, Infracost Apache-2.0, OpenRewrite-Kern Apache-2.0). ABGELEITET, rechtliche Bewertung ungeprüft.
5. **Für den öffentlichen Einsatz ist Triage mit Spam- und Slop-Erkennung Pflicht, nicht Kür.** Wer die Plattform auf öffentliche Repos setzt, bekommt fremde Issues und PRs als Auslöser; das eigene Repo wird ebenfalls öffentlich. GitHub nennt Triage, Duplikate, Spam und Slop als die Wünsche der Maintainer ([gh-models-blog] GESAGT, Suchauszug). ABGELEITET.

---

## 2. Befunde mit Quellen

### 2.1 Die Gesamtkarte: Ebenen und wer dort 2026 arbeitet

Die Ebenen folgen dem Ablauf eines Tickets. Spalte "Muster" beschreibt die Mechanik, die der Standard nutzt und die wir übernehmen würden.

| Nr | Ebene | Standard (führend) | Zweite Reihe | Muster des Standards | Einstufung |
|---|---|---|---|---|---|
| E1 | Issue-Triage, Duplikate, Routing | Linear Triage Intelligence | GitHub Agentic Workflows "Issue Triage"; GitHub Models mit `actions/ai-inference`; Jira/Rovo (ungeprüft) | Vektorsuche über Issues und PRs, Vorschläge für Labels, Zuständige, Duplikate; je Eigenschaft "zeigen, verstecken, automatisch anwenden" | [linear-triage], [gh-aw] BELEGT |
| E2 | Anforderungen, Spezifikation | Kiro Specs (EARS-Notation, `requirements.md`, `design.md`, `tasks.md`); GitHub Spec Kit | Factory Spec Mode | Spezifikation als versionierte Dateien im Repo, Anforderungen in festem Satzmuster, Analyse auf Widersprüche | Spec Kit [speckit] BELEGT; Kiro [kiro] GESAGT (nur Drittquellen) |
| E3 | Planung | Factory | Jules, Copilot cloud agent | siehe [02](../architecture/02-services.md) Abschnitt 1 | eigener Agent |
| E4 | Architektur | kein belegter Einzelstandard | Factory Missions | eigener Agent | eigener Agent |
| E5 | Coding | Devin, Codex Cloud, Copilot cloud agent, Cursor | Jules, Factory, OpenHands | siehe [02](../architecture/02-services.md) Abschnitt 2 | eigener Agent |
| E6 | Code-Review | GitHub Copilot code review (Volumen); Spitzengruppe nach Treffsicherheit ([ebene-review](ebene-review.md) Abschnitt 1) | CodeRabbit, Greptile, Bugbot, Devin Review | siehe [02](../architecture/02-services.md) Abschnitt 3 | eigener Agent |
| E7 | Security (SAST, SCA, Secrets, Fix) | GitHub Code Scanning mit Copilot Autofix; Snyk Agent Fix | Semgrep (Assistant heißt jetzt "Multimodal", Autofix-PRs für Code in Beta), Sonar AI CodeFix | Fund durch deterministische Engine, Fix durch LLM, Fix gilt nur, wenn der Alarm verschwindet | [gh-autofix] BELEGT; Snyk, Semgrep [semgrep-rn] GESAGT (Suchauszug); eigener Agent |
| E8 | Statische Codequalität | SonarQube Server | Qodana, Codacy (ungeprüft) | Quality Gate je Projekt | eigener Agent |
| E9 | Tests und QA | Meta TestGen-LLM und ACH, Playwright Test Agents, Factory QA | Copilot "Test Improver" | siehe [02](../architecture/02-services.md) Abschnitt 4 | eigener Agent |
| E10 | PR-Fix (Review-Threads, Konflikte) | Copilot Agent Merge | Bugbot Autofix, Pullfrog | siehe [02](../architecture/02-services.md) Abschnitt 5 | eigener Agent |
| E11 | CI-Reparatur | Copilot Agent Merge | gh-aw "CI Doctor" (rote CI auf dem Default-Branch, Issue mit Ursache), Sentry Seer PR-Iteration | Ursache erst klären, dann exakter CI-Befehl; bei wiederholtem Fehler bestehendes Issue fortschreiben | [gh-aw] BELEGT; Rest eigener Agent |
| E12 | Abhängigkeiten | Renovate; Dependabot | Dependabot-Alarm an Coding-Agenten (Copilot, Claude, Codex), Snyk Fix-PRs | regelbasierter Bot für Updates, Coding-Agent nur für Fälle außerhalb der Regeln | [renovate], [dependabot-core], [dependabot-agents] BELEGT |
| E13 | Doku und Docstrings | Mintlify Agent (Doku-PR nach Feature-PR) | DeepWiki (Devin), gh-aw "Daily Documentation Updater" | Doku-PR aus gemergtem Code-PR | [gh-aw] BELEGT; Mintlify [mintlify] GESAGT (Repo-Diffs) |
| E14 | Release Notes, Changelog | GitHub generierte Release Notes; release-please; git-cliff | Mintlify Changelog-PR | deterministisch aus Conventional Commits und PR-Labels, LLM nur zum Umschreiben für Leser, Mensch prüft vor Veröffentlichung | [relnotes] GESAGT |
| E15 | Migration, Modernisierung | AWS Transform (Mainframe, Windows, VMware, eigene Transformationen); Moderne mit OpenRewrite und Moddy | Copilot App Modernization (ungeprüft), Grit (ungeprüft) | deterministische Rezepte auf typisiertem Syntaxbaum, Agent plant und ruft Rezepte auf, über viele Repos in einem Lauf | [aws-transform], [openrewrite] BELEGT; Moddy [moddy] GESAGT |
| E16 | Incident, On-Call, SRE | Azure SRE Agent; Datadog Bits Investigation (früher Bits AI SRE) | PagerDuty SRE Agent, incident.io AI SRE, Sentry Seer Issue Fix | Hypothesen über Telemetrie, Lese-Modus zuerst, Abhilfe nur auf Freigabe, Übergabe an GitHub, Jira, Azure DevOps oder an Coding-Agenten | [az-sre], [sentry-fix] BELEGT; [dd-bits] BELEGT (Übersichtsseite), Rest GESAGT |
| E17 | Performance | Codeflash (nur Python, BSL-1.1) | CodSpeed (ungeprüft) | mehrere Kandidaten, Korrektheit per Tests und Replay-Tests, Messung im Loop, Schwelle für "schneller" | [codeflash] BELEGT; Schwelle 10 % [codeflash-search] GESAGT |
| E18 | Barrierefreiheit | Deque Axe MCP Server (Teil von Axe DevTools for Web) | axe-core (MPL-2.0) in eigenen E2E-Läufen | Prüfung im echten Browser, Agent bekommt Fix-Anleitung, bis 25 Befunde je Anfrage | [axe-mcp] GESAGT; [axe-core] BELEGT |
| E19 | Cloud-Kostenanalyse (FinOps) | Infracost (Kosten-Diff und Policies im PR) | OpenCost, Cloudability, CAST AI (alle ungeprüft) | Kosten-Diff je PR für IaC, Policies in Rego, Guardrails warnen oder blockieren | [infracost] BELEGT (Repo); Policies, AI-Funktionen [infracost-blog] GESAGT |
| E20 | Wissen, Q&A, Onboarding | Copilot Memory, DeepWiki | Devin Memory, Greptile | siehe [02](../architecture/02-services.md) Abschnitt 6 | eigener Agent |
| E21 | Teamregeln aus Feedback | Qodo Rule Miner | Greptile, Bugbot Learnings | siehe [02](../architecture/02-services.md) Abschnitt 7 | eigener Agent |
| E22 | Wartung als Dauerlauf ("Continuous AI") | GitHub Agentic Workflows (gh-aw) | Repo Assist, Test Improver, Code Simplifier (gh-aw-Galerie) | Markdown-Workflow, kompiliert zu gehärteter Actions-Datei; Agent nur lesend, Schreiben nur über deklarierte "safe outputs" in eigenem Job, davor eigener Prüfjob gegen bösartige Ausgaben | [gh-aw] BELEGT |

Die früheren Nennungen von CodeRabbit-Produkten in E1 bis E4, E9 bis E11, E13 und E14 entfallen in dieser Fassung: sie stützten sich nur auf Herstellerdoku oder private Vorarbeiten, deren Auswertung nach [10](../architecture/10-standards-per-layer.md) Abschnitt 16 nicht weitergeführt wird. Dasselbe gilt für die Tabelle im Anhang.

### 2.2 Einzelbefunde zu den Randebenen

**E1 Issue-Triage.**
- Linear Triage Intelligence vergleicht jedes Issue in Triage mit dem übrigen Bestand, schlägt Team, Projekt, Zuständige, Labels, Duplikate und Relationen vor; je Eigenschaft "shown, hidden oder auto-applied"; Anleitung in Klartext je Workspace, Team, Unterteam, die lokalste wiegt am meisten; Dauer laut Linear 1 bis 4 Minuten; nur Business und Enterprise. [linear-triage] BELEGT.
- gh-aw liefert einen fertigen Triage-Workflow: Rechte lesend, Schreiben nur über `add-comment` und `add-labels`; `staged: true` zeigt die Ausgaben nur an. [gh-aw] BELEGT. Automatisches Schließen von Duplikaten gilt in Drittquellen als riskanteste Aktion und erst nach nachgewiesener Treffsicherheit ([agentpatterns-triage] GESAGT, Suchauszug).
- GitHub nennt aus einer Umfrage unter über 500 Maintainern: 60 % wollen Hilfe bei Triage, 30 % Duplikaterkennung, 10 % Spam-Schutz, 5 % Slop-Erkennung ([gh-models-blog] GESAGT, Suchauszug, Seite nicht selbst gelesen).

**E2 Anforderungen.**
- GitHub Spec Kit (MIT): Ablauf `constitution`, `specify`, `plan`, `tasks`, `implement`, `converge`; Erweiterungen für Fehler (`bug-assess`, `bug-fix`, `bug-test`, Urteil `verified`, `partial`, `failed`) und Ideenprüfung (Urteil `go`, `needs-clarification`, `kill`). [speckit] BELEGT.
- Kiro: Spezifikation als drei Markdown-Dateien in `.kiro/specs/`, Anforderungen in EARS ("WHEN ... THE SYSTEM SHALL ..."), "Analyze Requirements" sucht Widersprüche und Lücken, Bugfix-Spec mit `bugfix.md` (Ist, Soll, unverändert). [kiro] GESAGT, die Herstellerdoku auf kiro.dev wurde nicht gelesen (ungeprüft).
- Für uns relevant: Unser `PlanArtifact` hat `acceptance[]` und `questions[]`, aber kein festes Satzmuster und keine Datei im Repo. Details gehören zur Planungs-Recherche.

**E11 CI-Reparatur auf dem Default-Branch.** Der PR-Fixer behandelt rote CI an PRs. gh-aw "CI Doctor" behandelt rote CI auf dem Default-Branch: untersucht und eröffnet ein Issue mit wahrscheinlicher Ursache, aktualisiert bei Wiederholung das bestehende Issue ([gh-aw] BELEGT). Diesen Fall hat unsere Architektur nicht, und es gibt keinen Schreibwunsch `propose_issue` ([02](../architecture/02-services.md) Abschnitt 0). ABGELEITET.

**E12 Abhängigkeiten.**
- Renovate: AGPL-3.0-only; Plattformen GitHub, GitLab, Bitbucket, Azure DevOps, Gitea, Forgejo, dazu experimentell CodeCommit, Gerrit, SCM-Manager; Betrieb als CLI auf allen Plattformen oder als geschlossene, freie Mend-Community-Edition. [renovate] BELEGT.
- Dependabot-core: MIT; "hosting your own standalone Dependabot"; PR-Ziele GitHub, GHE, Azure DevOps, GitLab, Bitbucket, CodeCommit; die Dependabot CLI erzeugt Diffs, aber keine PRs. [dependabot-core] BELEGT.
- Seit 2026-04-07 lassen sich Dependabot-Alarme an Coding-Agenten zuweisen (Copilot, Claude, Codex); jeder öffnet einen eigenen Draft-PR, versucht auch Testfehler zu beheben; braucht GitHub Code Security und Copilot mit Coding Agent; nur github.com. [dependabot-agents] BELEGT.
- Muster (ABGELEITET): Der Regel-Bot macht die Masse, der Agent nur Updates mit Bruch. Unser `FixRequest.source` kennt bereits `security_alert` ([02](../architecture/02-services.md) Abschnitt 5); ein roter Renovate- oder Dependabot-PR ist für den PR-Fixer ein normaler `ci_failure`. Was fehlt, ist der Lauf des Bots selbst und die Policy, dass der PR-Fixer auf Bot-Branches Manifeste und Lockfiles ändern darf (heute verboten, Stufe 5 "Verbote").

**E13 Doku und Docstrings.**
- Mintlify Agent: Doku-PR aus einem gemergten Feature-PR, auch Changelog-Einträge; vollautomatisch über die Agent-API aus einer GitHub Action. [mintlify] GESAGT (nur Diffs im Repo `mintlify/docs`, Doku-Seite nicht selbst gelesen).
- gh-aw "Daily Documentation Updater" aktualisiert Doku aus jüngsten Codeänderungen; in einem Beispiel nur PRs mit Titelpräfix `docs:` auf Branches `agentic/docs-sync-*`, nie Auto-Merge. [gh-aw] BELEGT für den Workflow, Beispiel GESAGT (Suchauszug).

**E14 Release Notes.** GitHub erzeugt Release Notes aus gemergten PRs mit Kategorien über `.github/release.yml`; release-please öffnet einen Release-PR mit `CHANGELOG.md` und Versionssprung; git-cliff erzeugt Changelogs aus Conventional Commits über `cliff.toml`. Drittquellen warnen: LLMs vergraben Breaking Changes und erfinden Versionsnummern und Daten. [relnotes] GESAGT (Drittquelle, Herstellerdoku nicht gelesen). Daraus (ABGELEITET): Version, Datum und Breaking-Liste deterministisch, das Modell schreibt nur Text, der Verifier prüft jede Zeile gegen einen PR.

**E15 Migration und Modernisierung.**
- AWS Transform: "agentic AI service" für Windows, Mainframe, VMware und eigene Transformationen; fertige Definitionen für Java-, Node.js- und Python-Upgrades, eigene Transformationen möglich. [aws-transform] BELEGT. Mainframe nach Java über Blu Age und Kiro: GESAGT (Suchauszug re:Post).
- OpenRewrite: Kern Apache-2.0, Rezepte auf dem "Lossless Semantic Tree", Sprachen Java, Kotlin, Groovy, JS/TS, Python, C#; Parser und Basisrezepte für Sprachen außer Java unter Moderne Source Available, einige Rezepte nur kommerziell. [openrewrite] BELEGT.
- Moderne Moddy: ein Agent über viele Repos, nutzt OpenRewrite-Rezepte als Werkzeuge, über MCP auch für fremde Coding-Agenten. [moddy] GESAGT.
- Muster (ABGELEITET): Kampagne = ein Plan, viele Repos, deterministische Rezepte, Agent nur für Reste. Unsere Runs sind je Repo; der Planner hat nur `targetRepos?` ([02](../architecture/02-services.md) Abschnitt 1). Eine Kampagne mit Eltern-Run und Kind-Runs je Repo fehlt in [03](../architecture/03-flow-and-orchestration.md).

**E16 Incident, On-Call, SRE.**
- Azure SRE Agent: untersucht Vorfälle über Azure-Ressourcen, fragt Azure Monitor und Application Insights ab, schlägt Lösungen vor, nimmt Abhilfe nur im "privileged mode" vor; "Reader mode" nur lesend; eigene Subagenten und MCP-Server; Integrationen unter anderem Azure DevOps und GitHub; gehostet in Sweden Central, East US 2, Australia East. [az-sre] BELEGT (FAQ, Stand der Seite 2026-06-02). GA seit 2026: [az-sre-ga] GESAGT (Suchauszug Tech Community, nicht selbst gelesen).
- Datadog Bits Investigation (früher Bits AI SRE): "autonomous AI agent that investigates production issues end to end", Hypothesen und Telemetrie im Wechsel. [dd-bits] BELEGT. GA am 2025-12-02 und Code-Fix-Vorschläge: GESAGT (Suchauszug Presse und Produktseite).
- PagerDuty SRE Agent: GA in der Incident-Detailseite am 2026-04-30, Skills seit 2026-08 (Early Access). [pd-sre] GESAGT (Suchauszug Changelog).
- Sentry Seer Issue Fix: Ursache, Lösungsplan, Code, PR; GitHub-PR-Iteration auf rote CI und Review-Kommentare; Automatik endet je Einstellung nach Ursache, Plan oder Draft-PR; Code-Schritt kann an "Claude Agent, Cursor Cloud Agent, GitHub Copilot Cloud Agent" übergeben werden, nur GitHub; Auto-Läufe erst ab 10 Ereignissen in 14 Tagen und ausreichendem Fixability-Wert; kein Merge. [sentry-fix] BELEGT. Seer meldet Webhooks wie `seer.root_cause_completed` und `seer.pr_created` ([sentry-webhooks] GESAGT, Suchauszug).
- incident.io: Übergabe aus der Untersuchung in eine Claude-Code-Sitzung, PR und Statusmeldung über MCP; Genauigkeitsangabe "90%+" ohne unabhängigen Beleg. [incidentio] GESAGT.
- Muster (ABGELEITET): Die SRE-Agenten untersuchen mit Telemetrie und Produktionsrechten und übergeben den Code-Anteil. Diese Übergabe ist für uns ein Eingang: Ticket oder Webhook mit Ursache und Plan, danach unser Coder und PR-Fixer.

**E17 Performance.** Codeflash: Python-Optimierer, LLM-Kandidaten, Korrektheit per Tests, Messung, PR mit der besten Variante; als GitHub Action auf neuen PR-Code; Lizenz BSL-1.1. [codeflash] BELEGT. Schwelle "mindestens 10 % schneller", Messung als schnellster Lauf in der Schleife, Replay-Tests aus echten Eingaben: [codeflash-search] GESAGT (Suchauszug der Doku). Muster für uns (ABGELEITET): ein Performance-Befund gilt nur mit Messung auf ruhiger Maschine; im geteilten Pool `office` sind Zeitmessungen verrauscht (Codeflash rät selbst zu einer eigenen Maschine, [codeflash-search] GESAGT).

**E18 Barrierefreiheit.** Axe MCP Server: im Bündel Axe DevTools for Web; Prüfung im echten Browser, geführte Tests (zuerst Tastatur), Prüfung hinter Login über Cookies, Batch-Abhilfe bis 25 Befunde je Anfrage, lokal per `npx`, eigenes LLM für On-Prem-Kunden; Preise nicht genannt. [axe-mcp] GESAGT (Herstellerblog 2026-08-05). axe-core selbst: MPL-2.0. [axe-core] BELEGT. Muster (ABGELEITET): axe-core läuft in unserer QA-E2E-Stufe im selben Chromium wie die Playwright-Prüfung; Befunde gehen als QA-Befunde mit WCAG-Bezug in den Bericht.

**E19 Kostenanalyse.** Infracost: Apache-2.0; Kosten-Schätzung und FinOps-Prüfungen für Terraform, Terragrunt, CloudFormation, AWS CDK vor dem Deployment; CLI `infracost scan`, Editor per LSP, Skills für KI-Agenten, PR-Kommentare mit Kosten-Diff. [infracost] BELEGT. Policies in Rego und Guardrails, die PRs blockieren: [infracost-blog] GESAGT. Abgrenzung: Die Kosten unserer eigenen LLM-Läufe sind keine Ebene, sondern schon Limit-Ledger ([04](../architecture/04-configuration-and-limits.md) Abschnitt 6).

**E22 Continuous AI und gh-aw als Vergleichsmodell.**
- gh-aw: Markdown-Workflow, `gh aw compile` erzeugt "a hardened, pinned Actions workflow"; Engines Copilot, Claude Code, Codex, Antigravity, Pi, dazu Beispiele für Kiro, OpenCode, Cursor; "Only the writes you declared are applied, by a separate job with its own permissions"; ein eigener Prüfjob "scans proposed outputs and blocks suspicious ones"; Status technische Vorschau. [gh-aw] BELEGT. Die Zahl "578 geschlossene Issues in 13 Repos" für Repo Assist: GESAGT.
- Für uns (ABGELEITET): gh-aw bestätigt zwei Grundentscheidungen der Architektur, getrennte Schreibstelle (unser Effect Gateway) und Lesen per Default. Es ist zugleich der stärkste kostenlose Mitbewerber für die Randebenen Triage, CI Doctor, Doku-Sync, weil es in jedem GitHub-Repo ohne eigenen Server läuft. Unser Mehrwert liegt dort nur in SCM-Neutralität (GitLab, Azure DevOps, Gitea), Eval-Gates und zentralen Limits.

### 2.3 Abdeckung durch unsere Architektur heute

Grundlage: [02-services.md](../architecture/02-services.md) (7 Services), [01-plugin-interfaces.md](../architecture/01-plugin-interfaces.md) (8 Plugin-Arten, `CommandName`), [03](../architecture/03-flow-and-orchestration.md) Abschnitt 4 (Befehle). Selbst gelesen am 2026-10-31.

| Ebene | Abdeckung | Stelle |
|---|---|---|
| E1 Triage | **nein**; nur Gate-Logik im Reviewer und Klarheits-Gate im Planner; kein Befehl, kein Schreibwunsch für Labels oder Issues | 02 Abschnitt 1 Stufe 2, 01 `CommandName` |
| E2 Anforderungen | teilweise (Planner `acceptance[]`, `questions[]`) | 02 Abschnitt 1 |
| E3 bis E6, E9, E10, E20, E21 | ja (eigene Services) | 02 Abschnitte 1 bis 7 |
| E7 Security | teilweise: Security-Finder im Reviewer, Semgrep/osv/gitleaks im Self-Check, `security_alert` im PR-Fixer | 02 Abschnitte 2, 3, 5 |
| E8 Codequalität (Sonar) | nein als Anbindung; "Linter bleiben eigener Workflow" | ADR-33 in 09 |
| E11 CI-Reparatur | ja für PRs; **nein** für den Default-Branch | 02 Abschnitt 5 |
| E12 Abhängigkeiten | indirekt (Bot-PRs als normale PRs, Verbot für Lockfiles und Manifeste im PR-Fixer) | 02 Abschnitt 5 Stufe 5 |
| E13 Doku, Docstrings | **nein** | - |
| E14 Release Notes | **nein** | - |
| E15 Migration | nein als Kampagne; einzelne Repos über Coder | 02 Abschnitt 1 `targetRepos?` |
| E16 Incident | nein; keine Eingangsquelle für Beobachtungswerkzeuge (`subject` kennt kein `alert` oder `incident`) | 01 Abschnitt 2 |
| E17 Performance | nein | - |
| E18 Barrierefreiheit | nein; E2E-Stufe im QA wäre der Ort | 02 Abschnitt 4 Stufe 5 |
| E19 Kosten IaC | nein | - |
| E22 Dauerläufe | teilweise: `schedule` als Trigger-Modus vorhanden, aber kein Service nutzt ihn außer Indexer und Standards | 01 Abschnitt 3 |

---

## 3. Folgen für unsere Architektur

Konkret je Datei und Abschnitt. Nichts davon ist umgesetzt; der Text hier ist Vorschlag für die Architekturrunde.

### 3.1 [01-plugin-interfaces.md](../architecture/01-plugin-interfaces.md)

1. **Abschnitt 1.1 `PluginKind`: neunte Art `Analyzer`.** Vertrag (Skizze):
   - `describe()`: Sprachen, Dateimuster, Ausgabeformat, Laufzeit in der Sandbox (Image-Referenz, Netzbedarf), Kosten (`free`, `byo_license`).
   - `run(workspace, diff?, config) -> AnalyzerReport` mit Befunden im SARIF-Kern (Regel-ID, Ort, Schwere, Nachricht, optional Fix), damit Reviewer, Coder-Self-Check, QA und PR-Fixer dieselbe Form lesen.
   - Läuft immer als Work-Item in der Sandbox, nie in der Steuerzentrale (fremder Code).
   - Erste Instanzen: Semgrep oder Opengrep, osv-scanner, gitleaks (heute fest im Coder-Text), danach Sonar (Abruf des Quality-Gate-Ergebnisses statt eigenem Lauf), Infracost, axe-core, Renovate oder Dependabot im Modus "nur Diff", OpenRewrite.
   - Grund: Alle Randebenen außer Triage und Incident brauchen genau diese Form (Abschnitt 2.2); ohne sie wird jedes Werkzeug ein Sonderfall im Service-Code. ABGELEITET.
2. **Abschnitt 1.1 `PluginManifest`: Felder `license` (SPDX) und `distribution: bundled | operator_supplied`.** Eine Policy-Regel verbietet `bundled` für Lizenzen außerhalb einer Allowlist der Plattform-Lizenz. Grund: Vorgabe 2, Befund Urteil Punkt 4. ABGELEITET.
3. **Abschnitt 2 Event-Schema:** `subject` um `alert` und `incident` erweitern, `action` um `alert_fired` und `handoff`; `CommandName` um `triage`, `docs`, `release` ergänzen. Erste TriggerSource dafür: `sentry` (Seer-Webhooks, Übergabe mit Ursache und Plan) und ein generischer `incident-handoff` (signierter Webhook mit Ursache, Plan, Links), den Azure SRE Agent, PagerDuty oder incident.io über ihre GitHub-, Jira- oder Webhook-Ausgänge bedienen. ABGELEITET.
4. **Abschnitt 4 und 5 (WorkItemProvider, SCMProvider):** Fähigkeiten `SET_LABELS`, `CREATE_ISSUE`, `LINK_ITEMS`, `CLOSE_AS_DUPLICATE` prüfen und in die Matrizen 11.1 und 11.2 aufnehmen (für Triage und CI Doctor). Ungeprüft, ob alle SCM-Plugins sie schon führen.

### 3.2 [02-services.md](../architecture/02-services.md)

1. **Abschnitt 0 Schreibwünsche:** neue Einträge `propose_labels`, `propose_issue`, `propose_link` (Duplikat, verwandt). `propose_close` nur mit eigener Freigabe (siehe Owner-Entscheidung 4.1).
2. **Neuer Abschnitt "Triage" (Service `triage`):**
   - Zweck: jedes neue oder geänderte Issue einordnen: Duplikate und Verwandte mit Zitat, Labels, Zuständige aus Historie und CODEOWNERS, Repo-Zuordnung, Spam- und Slop-Einstufung, Klarheit (übernimmt das Klarheits-Gate des Planners als gemeinsame Bibliothek).
   - Messlatte: Linear Triage Intelligence (Abschnitt 2.2 E1).
   - Ohne Shell, kleines Modell plus Vektorsuche über Issues und PRs aus dem KnowledgeStore; je Eigenschaft `suggest | auto_apply | off` nach Linear-Muster.
   - Ausgang: Kommentar plus `propose_labels`, `propose_link`; Ereignis `item.triaged`, das `ticket-to-pr` mit `autonomy: full` als Eingang nutzen kann.
   - DoD (Vorschlag): Duplikat-Präzision und Recall auf einem Satz aus den Repos des Owners mit von Hand markierten Duplikaten; Label-Übernahmequote im Pilot; 0 automatische Schließungen ohne Freigabe.
3. **Neuer Abschnitt "Docs" (Service `docs`):** drei Modi
   - `docstrings`: ast-grep findet Lücken in berührten Funktionen, Stil aus vorhandenen Docstrings, Folge-PR gegen den Ursprungs-Branch (Ersatzkette: Kommentar bei SCMs ohne Branch-Workflow).
   - `sync`: nach `pushed_default` Doku-PR für berührte Doku-Stellen (Mintlify- und gh-aw-Muster), nur Pfade aus `docs.paths`, nie Auto-Merge.
   - `release`: Release Notes und Changelog deterministisch (Version, Datum, Breaking-Liste aus Conventional Commits und Labels, Werkzeug wählbar: git-cliff oder release-please als `Analyzer`), Modell nur für Lesetext, Verifier prüft jede Zeile gegen einen PR.
   - Abgrenzung zum Indexer: Der Indexer schreibt in die KB, `docs` schreibt ins Repo. Details der Doku-Ebene liefert die Recherche "Wissen, Standards, Doku".
4. **Abschnitt 2 Coder Stufe 4 und Abschnitt 5 PR-Fixer Stufe 4:** "Self-Check-Bündel" als Liste von `Analyzer`-Instanzen aus der Repo-Konfiguration statt fester Werkzeugnamen.
5. **Abschnitt 5 PR-Fixer:**
   - `FixRequest.source` um `dependency_update` ergänzen: Auf Branches eines konfigurierten Abhängigkeits-Bots (Renovate, Dependabot) darf der PR-Fixer Manifeste und Lockfiles ändern, sonst bleibt das Verbot. Muster: Dependabot-Alarm an Coding-Agent ([dependabot-agents] BELEGT).
   - Modus `ci_doctor` für rote CI auf dem Default-Branch: nur Ursache und `propose_issue` (bei Wiederholung dasselbe Issue fortschreiben), kein Push.
6. **Abschnitt 4 QA:** Stufe 5 E2E um optionalen `Analyzer` axe-core erweitern (Befunde mit WCAG-Bezug); optionaler Scope `perf` nur mit Pool-Fähigkeit `QUIET_BENCH` (eigene Maschine), sonst `blocked`.
7. **Abschnitt 3 Reviewer Stufe 3 Kontextpaket:** Ergebnisse vorhandener `Analyzer` (Sonar Quality Gate, Infracost-Diff, Semgrep) als Kontext lesen, nicht neu rechnen; ein Kostensprung aus Infracost wird ein Befund nur mit Zitat der Policy. Das bleibt mit ADR-33 vereinbar (Linter bleiben eigener Workflow, der Reviewer liest nur).
8. **Abschnitt 8 Kombinationen:** Zeilen "Maintainer-Assistent" (`triage`), "Doku-Pflege" (`docs`), "Incident-Übergabe" (`coder`, `prfixer` mit Eingang `incident-handoff`).

### 3.3 [03-flow-and-orchestration.md](../architecture/03-flow-and-orchestration.md)

1. **Abschnitt 1a:** Der autonome Durchlauf beginnt mit `triage` (optional, `on_disabled: skip`), dann Planner. Spam- oder Slop-Einstufung beendet den Run mit `Skipped(triage_rejected)` und Vermerk, ohne Plan.
2. **Abschnitt 4 Befehle:** `@agent triage`, `@agent docs [docstrings|sync]`, `@agent release` mit Mindestrechten (Triage: Lesen; Docs und Release: Schreiben im Repo).
3. **Neuer Abschnitt "Kampagnen" (später):** Eltern-Run mit Plan und Rezeptliste, Kind-Runs je Repo, gemeinsames Budget im Limit-Ledger, Abbruchregel bei Fehlerquote. Nur skizzieren, Bau erst nach Stufe 9.

### 3.4 [04-configuration-and-limits.md](../architecture/04-configuration-and-limits.md)

- Abschnitt 3: Service-Blöcke `triage` (Eigenschaften mit `suggest | auto_apply | off`, `spam: label | hide_comment`) und `docs` (`paths`, `release.tool`), dazu `analyzers:` je Repo mit Image-Referenz und Lizenzangabe.
- Abschnitt 1: Allowlist der Analyzer-Images auf Installationsebene (nur verschärfend vererbbar).

### 3.5 [07-eval.md](../architecture/07-eval.md)

- Abschnitt 3: Testsätze T1 (Triage: Duplikate und Labels aus Repos des Owners, von Hand markiert) und D1 (Docs: berührte Funktionen ohne Docstring, Richter plus Stichprobe). Ein Gate B gegen ein Fremdprodukt entfällt (O13 abgelöst durch O18, [10](../architecture/10-standards-per-layer.md) Abschnitt 16).
- Abschnitt 5: Suite S1 (Injection) um Triage erweitern: Issue-Text fremder Nutzer auf öffentlichen Repos ist der häufigste Angriffsweg; gh-aw empfiehlt dafür ausdrücklich, Issue-Text als Daten zu behandeln ([gh-aw-tut] GESAGT).

### 3.6 [08-roadmap.md](../architecture/08-roadmap.md)

- Stufe 2: `Analyzer`-Vertrag `v1alpha1` verbindlich, weil das Self-Check-Bündel ihn als erstes braucht.
- Stufe 6 (Wissensbasis): `triage` dazu, weil Duplikatsuche die Vektorsuche über Issues und PRs braucht; vorher nur Labels ohne Duplikate möglich.
- Neue Stufe 10 "Randebenen", Reihenfolge nach Nutzen und Risiko: `docs` (docstrings, sync, release), PR-Fixer `dependency_update` und `ci_doctor`, Incident-Übergabe als Eingang, QA-Erweiterung axe-core, Infracost im Reviewer-Kontext, zuletzt Kampagnen.
- Hinweis: Vorgabe 2 (öffentliches Repo) kann `triage` mit Spam-Schutz für das eigene Repo früher nötig machen; dann reicht zunächst gh-aw "Issue Triage" auf unserem Entwicklungs-Repo als Fremdwerkzeug, ohne die Roadmap zu ändern. ABGELEITET.

### 3.7 [09-decisions.md](../architecture/09-decisions.md) und [README.md](../architecture/README.md)

- 09 Abschnitt 2: neue ADRs "Plugin-Art `Analyzer`", "Services `triage` und `docs`", "kein eigener SRE-Agent, nur Übergabe-Eingang", "Fremdwerkzeuge nie gebündelt außer freie Lizenz".
- 09 O14 ("zunächst nur intern") ist durch Vorgabe 2 überholt; die Bedingungen aus [cc-legal] für Auslieferung an Dritte bleiben zu prüfen. Das betrifft die Recherche zu Open Source und Lizenz.
- README Abschnitt 2 Punkt 2 und Glossar: "8 Plugin-Arten" und "7 Services" ändern sich mit dieser Empfehlung auf 9 und 9. Folgeliste: README Abschnitte 2, 4, 5; 01 Abschnitt 1.1; 02 Kopf; 08 Abschnitt 2.
- README-Titel, `apiVersion` in 01 Abschnitt 1.1 und der Pfad der Org-Konfiguration in 04 Abschnitt 3 sind firmenspezifisch und widersprechen Vorgabe 2; betrifft die Open-Source-Recherche, hier nur als Fund vermerkt.

---

## 4. Owner-Entscheidungen

Nur echte Entscheidungen (Produkt, Recht, Geld).

| Nr | Frage | Art | Empfehlung | Grund |
|---|---|---|---|---|
| 4.1 | Darf `triage` Issues automatisch schließen (Duplikat, Spam)? | Produkt, Außenwirkung | Nein als Plattform-Standard. Nur Label, Kommentar und Verknüpfung; Schließen nur als Repo-Einstellung `auto_close: true`, wirksam erst nach grünem Eval T1 für dieses Repo | Schließen ist die riskanteste Triage-Aktion ([agentpatterns-triage] GESAGT); Linear schlägt nur vor oder setzt Eigenschaften ([linear-triage] BELEGT); ein fälschlich geschlossenes Issue eines Fremden auf einem öffentlichen Repo schadet dem Projekt |
| 4.2 | Eigener SRE- oder Incident-Agent mit Produktionszugriff? | Produkt | Nein. Nur Übergabe-Eingang für Sentry Seer, Azure SRE Agent, PagerDuty und Co.; danach unser Coder und PR-Fixer | Standards brauchen Telemetrie und Produktionsrechte, die unserer Trennung von Lesen und Wirken widersprechen; die Standards übergeben den Code-Teil bereits an Coding-Agenten ([sentry-fix] BELEGT) |
| 4.3 | Welche Fremdwerkzeuge liefert das öffentliche Projekt mit? | Recht | Nur Werkzeuge mit freier Lizenz als Standard-Image (Beispiele: Dependabot-core MIT, axe-core MPL-2.0, Infracost Apache-2.0, OpenRewrite-Kern Apache-2.0, Opengrep); AGPL-, BSL- und Bezahlwerkzeuge (Renovate, Codeflash, Axe DevTools, Sonar Server-Editionen) nur als vom Betreiber gewähltes Image | Vorgabe 2; Lizenzen laut Abschnitt 2.2; die rechtliche Frage, ob ein AGPL-Werkzeug im eigenen Container die Plattform berührt, ist ungeprüft und gehört zur Lizenz-Recherche |
| 4.4 | Bezahlte Fremddienste als Pflichtteil einer Ebene? | Geld | Nein. Jede Ebene muss mit kostenlosen Werkzeugen laufen; Bezahldienste (Axe DevTools, Infracost Cloud, Codeflash, Sonar-Editionen, Datadog, PagerDuty) nur als optionales Plugin | Jeder soll selbst hosten können (Vorgabe 2); Vorgabe des Owners gegen Ausgaben für Werkzeuge (globale Regel vom 2026-10-30 zu GitHub) |

---

## 5. Offene Punkte

1. **Ungeprüft:** Kiro-Herstellerdoku (nur Drittquellen gelesen), Semgrep-Release-Notes März 2026, Sonar-AI-Seiten, PagerDuty-Changelog, Azure-SRE-GA-Ankündigung, Mintlify-Doku-Seite, GitHub-Maintainer-Umfrage, Codeflash-Schwelle 10 %: jeweils nur Suchauszug. Vor Übernahme in die Architektur einmal an der Primärquelle lesen.
2. **Ungeprüft:** Copilot App Modernization, Grit, CodSpeed, Qodana, Codacy, OpenCost, Atlassian Rovo als Triage: nur genannt, nicht recherchiert.
3. **Ungeprüft:** Ob GitHub, GitLab, Azure DevOps, Gitea und Jira die Fähigkeiten `SET_LABELS`, `CREATE_ISSUE`, `CLOSE_AS_DUPLICATE` gleichwertig anbieten (Ersatzketten für `triage`).
4. **Messung offen:** Es gibt für keine Randebene einen öffentlichen Benchmark wie SWE-bench oder Martian; incident.io nennt "90%+" ohne unabhängigen Beleg ([incidentio] GESAGT). Ein Vergleichslauf gegen ein Fremdprodukt auf denselben Issues entfällt (O13 abgelöst durch O18); Gate B misst gegen nachgemessene offene Referenzen ([10](../architecture/10-standards-per-layer.md) Abschnitte 11, 12 und 16).
5. **Zu klären in der Lizenz-Recherche:** AGPL-Werkzeug (Renovate) als getrennter Container neben einer Plattform unter anderer Lizenz; Moderne Source Available für Nicht-Java-Rezepte.
6. **Technisch offen:** SARIF als Austauschformat für `Analyzer` reicht für Kosten-Diffs (Infracost) und Doku-Lücken nicht ohne Erweiterung; Schema-Entwurf in Stufe 2.
7. **Überschneidung mit parallelen Recherchen:** Security, statische Analyse und Sonar-Anbindung des Entwicklungs-Repos (Vorgabe 3), Doku und Wissen, CI-Reparatur. Die Empfehlungen hier zu `Analyzer`, `docs` und `ci_doctor` sind mit deren Ergebnissen abzugleichen; bei Widerspruch entscheiden die gelesenen Belege.

---

## 6. Quellen

Alle abgerufen am 2026-10-31.

Selbst gelesen (Seite abgerufen):
- [linear-triage] https://linear.app/docs/triage-intelligence
- [sentry-fix] https://docs.sentry.io/product/ai-in-sentry/seer/issue-fix
- [az-sre] https://learn.microsoft.com/en-ca/azure/sre-agent/faq (kanonisch https://learn.microsoft.com/en-us/azure/sre-agent/faq)
- [dd-bits] https://docs.datadoghq.com/bits_ai/bits_investigation/
- [renovate] https://github.com/renovatebot/renovate
- [dependabot-core] https://github.com/dependabot/dependabot-core
- [dependabot-agents] https://github.blog/changelog/2026-04-07-dependabot-alerts-are-now-assignable-to-ai-agents-for-remediation
- [gh-aw] https://github.github.com/gh-aw/
- [codeflash] https://github.com/codeflash-ai/codeflash
- [speckit] https://github.com/github/spec-kit
- [infracost] https://github.com/infracost/infracost
- [openrewrite] https://github.com/openrewrite/rewrite
- [axe-mcp] https://www.deque.com/blog/new-in-axe-mcp-server-more-automated-coverage-and-streamlined-developer-workflows/ (Herstellerblog, GESAGT)
- [axe-core] https://github.com/dequelabs/axe-core
- [aws-transform] https://aws.amazon.com/documentation-overview/transform/

Nur Suchauszug (nicht selbst abgerufen, GESAGT):
- [az-sre-ga] https://techcommunity.microsoft.com/blog/AppsonAzureBlog/announcing-general-availability-for-the-azure-sre-agent/4500682
- [pd-sre] https://support.pagerduty.com/main/changelog/sre-agent-within-the-incident-details-page-now-generally-available und https://www.pagerduty.com/blog/ai/meet-your-virtual-responder-pagerdutys-sre-agent-for-ai-driven-reliability/
- [incidentio] https://incident.io/blog/how-it-feels-to-run-an-incident-with-ai-sre und https://www.augmentcode.com/tools/best-ai-sre-tools
- [sentry-webhooks] https://docs.sentry.io/integrations/integration-platform/webhooks/seer/
- [semgrep-rn] https://docs.semgrep.dev/release-notes/march-2026
- [kiro] https://www.verdent.ai/guides/agents/kiro-spec-driven-development und https://www.promptz.dev/rules/general/kiro-specs
- [moddy] https://devops.com/moderne-adds-ai-agent-to-simplify-application-modernization-initiatives/ und https://aws.amazon.com/marketplace/pp/prodview-qa5qb3cy3ofbc
- [mintlify] https://github.com/mintlify/docs/pull/2094/files und https://github.com/mintlify/docs/pull/1386.diff
- [relnotes] https://deployhq.com/git/generating-changelogs-with-ai
- [infracost-blog] https://www.infracost.io/blog/native-cost-policies und https://www.infracost.io/product
- [codeflash-search] https://github.com/codeflash-ai/codeflash/pull/218
- [gh-models-blog] https://github.blog/open-source/maintainers/how-github-models-can-help-open-source-maintainers-focus-on-what-matters/
- [agentpatterns-triage] https://agentpatterns.ai/workflows/continuous-triage/
- [gh-aw-tut] https://tenki.cloud/blog/github-agentic-workflows-tutorial

Lokal (selbst gelesen): [docs/architektur/README.md](../architecture/README.md), [01](../architecture/01-plugin-interfaces.md), [02](../architecture/02-services.md), [03](../architecture/03-flow-and-orchestration.md) Abschnitt 4, [08](../architecture/08-roadmap.md), [09](../architecture/09-decisions.md) Abschnitt 3.

---

## Anhang: Tabelle Ebene, Standard, Abdeckung heute, Empfehlung, Ausbaustufe

Ausbaustufen nach [08](../architecture/08-roadmap.md); "10" ist die hier vorgeschlagene neue Stufe "Randebenen".

| Ebene | Standard | Abdeckung heute | Empfehlung | Ausbaustufe |
|---|---|---|---|---|
| Issue-Triage, Duplikate, Spam/Slop | Linear Triage Intelligence | nein | **eigener Service `triage`** (ohne Shell, Vektorsuche, Vorschlag statt Schließen) | 6 (mit KB); für das eigene öffentliche Repo vorher gh-aw als Fremdwerkzeug |
| Anforderungen, Spezifikation | Kiro Specs; GitHub Spec Kit | teilweise (Planner) | Teil von `planner` (Satzmuster für `acceptance[]`, optional Spec-Dateien im Repo) | 2 (Detail: Planungs-Recherche) |
| Planung | Factory | ja | bestehender Service `planner` | 2 |
| Architektur | kein belegter Einzelstandard | teilweise | Teil von `planner` (`designChoices`) und `reviewer` | 2 und 1 (Detail: Architektur-Recherche) |
| Coding | Devin, Codex Cloud, Copilot cloud agent | ja | bestehender Service `coder` | 2 |
| Code-Review | GitHub Copilot code review; Spitzengruppe nach Treffsicherheit | ja | bestehender Service `reviewer` | 1 |
| Security | Copilot Autofix; Snyk Agent Fix | teilweise | Teil von `reviewer`, `coder`, `prfixer` plus `Analyzer`-Plugins (Opengrep, osv-scanner, gitleaks) | 1 bis 4 (Detail: Security-Recherche) |
| Statische Codequalität | SonarQube Server | nein | `Analyzer`-Plugin (Quality Gate lesen), Ergebnis als Kontext im Reviewer | 2 |
| Tests und QA | TestGen-LLM, ACH, Playwright Agents, Factory QA | ja | bestehender Service `qa` | 3 |
| PR-Fix | Copilot Agent Merge | ja | bestehender Service `prfixer` | 4 |
| CI-Reparatur | gh-aw CI Doctor | ja für PRs, nein für Default-Branch | Teil von `prfixer`, neuer Modus `ci_doctor` (nur Issue, kein Push) | 4 (PR), 10 (Default-Branch) |
| Abhängigkeiten | Renovate; Dependabot | indirekt | Fremdwerkzeug als `Analyzer`/Bot-Plugin, `prfixer` mit Quelle `dependency_update` für gebrochene Updates | 10 |
| Doku und Docstrings | Mintlify Agent | nein | **eigener Service `docs`** (Modi `docstrings`, `sync`) | 10 |
| Release Notes, Changelog | GitHub Release Notes; release-please; git-cliff | nein | Teil von `docs` (Modus `release`, deterministisch plus Text vom Modell) | 10 |
| Migration, Modernisierung | AWS Transform; Moderne/OpenRewrite | nein | später Pipeline-Vorlage "Kampagne" über `planner` und `coder` mit OpenRewrite als `Analyzer`; kein eigener Service | nach 10 |
| Incident, On-Call, SRE | Azure SRE Agent; Datadog Bits Investigation | nein | **bewusst kein eigener Agent**; TriggerSource `sentry` und `incident-handoff`, dann `coder` und `prfixer` | 10 |
| Performance | Codeflash (BSL-1.1) | nein | bewusst kein eigener Service; QA-Scope `perf` nur mit ruhigem Pool, Werkzeug als `Analyzer` des Betreibers | nach 10 |
| Barrierefreiheit | Deque Axe MCP Server | nein | Teil von `qa` (axe-core MPL-2.0 in der E2E-Stufe) | 10 |
| Cloud-Kostenanalyse | Infracost | nein | `Analyzer`-Plugin, Kosten-Diff als Kontext und Befund im `reviewer` | 10 |
| Wissen, Q&A | Copilot Memory; DeepWiki | ja | bestehender Service `indexer` | 6 |
| Teamregeln | Qodo Rule Miner | ja | bestehender Service `standards` | 6 |
| Dauerläufe (Continuous AI) | GitHub Agentic Workflows | teilweise (`schedule`) | kein Service; Zeitplan-Auslöser für `triage`, `docs`, `ci_doctor`; gh-aw als Vergleich für Schreibschutz | 10 |
