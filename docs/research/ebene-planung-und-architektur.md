<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
> Research note, dated 2026-11-01, not binding. Kept in German as written (ADR-53); the binding documents are docs/architecture and docs/design.

# Ebene Planung und Architektur: Standard, Fähigkeiten, Messung, Lücken

**Dated, not binding.** Datierte Recherche, Stand 2026-10-31, nicht verbindlich und nicht übersetzt; verbindlich ist die Plattform-Doku ([docs/architektur/](../architecture/README.md)).

Stand 2026-10-31. Alle Webquellen am 2026-10-31 abgerufen. Einstufung wie in [docs/architektur/README.md](../architecture/README.md) Abschnitt 6: BELEGT (Primärquelle selbst gelesen), GESAGT (Herstelleraussage, Marketing, Drittbericht), ABGELEITET (eigener Schluss), VERMUTET. Die Web-Werkzeuge liefern teils eine Zusammenfassung durch ein kleines Modell; wo das so ist, sind Zitate sinngemäß. Selbst roh gelesen (curl) wurden: Claude-Code-Doku zum Plan-Modus, Devin "Ask Devin" und "SDLC integration", Spec-Kit-README und Lizenzdateien, Loc-Bench-Datensatzkarten auf Hugging Face.

Bezug: ergänzt [02](../architecture/02-services.md) Abschnitt 1 (Planner), [07](../architecture/07-eval.md) Abschnitte 3.2 und 4, [09](../architecture/09-decisions.md). Was dort schon belegt ist (Factory Spec Mode und Missions, Jules und Copilot mit Plan-Freigabe), wird hier nur aktualisiert oder korrigiert.

---

## 1. Urteil (Kurzfassung)

1. **Planung (Ticket zu Plan): Es gibt keinen einzelnen Weltstandard und keinen unabhängigen Produktvergleich.** Die Spitzengruppe nach Funktionsumfang und Offenlegung (ABGELEITET): **Kiro** und **GitHub Spec Kit** (für spezifikationsgetriebene Entwicklung mit Anforderungen, Design, Tasks), **Jules** (einziger Anbieter mit veröffentlichtem Messwert für eine Plan-Kritik: 9,5 % weniger Task-Fehlschläge, GESAGT), **Factory Spec Mode** (Steuerung der Autonomie nach Freigabe), **Devin Ask/DeepWiki** (Recherche und Konfidenz je Ticket). Plan-Modi in Claude Code, Cursor und Copilot sind inzwischen Grundausstattung, kein Unterscheidungsmerkmal. Spec Kit ist mit 144,2k GitHub-Sternen das meistbeachtete offene Werkzeug dieser Ebene (Zähler auf der Repo-Seite, BELEGT als Zählerstand, kein Qualitätsbeleg).
2. **Architektur und Design: Der anerkannte Standard ist eine Methode, kein Produkt.** arc42 (Gliederung), C4 (Diagramme, mit offizieller Review-Checkliste), ADR (Nygard, MADR), ISO/IEC/IEEE 42010:2022 (Begriffe der Architekturbeschreibung), ATAM des SEI (Bewertung gegen Qualitätsszenarien), STRIDE und das Threat Modeling Manifesto (Bedrohungsanalyse). KI-gestütztes Architektur-Review gibt es als Produkt fast nur für **Threat Modeling** (STRIDE GPT MIT, AWS Threat Designer Apache-2.0, kommerziell Clearly AI, Prime Security, Apiiro, IriusRisk; Letztere GESAGT) und für **Cloud-Architektur gegen Well-Architected** (AWS IaC Analyzer, GESAGT). Ein KI-Produkt, das ADRs oder arc42 belegt prüft, habe ich nicht gefunden (ungeprüft, ob es eines gibt).
3. **Benchmarks:** Für Planungsqualität gibt es seit 2026 erste öffentliche Datensätze: **SWE-RPG** (163 Fälle mit Referenz für Rückfragen und Plan, August 2026; Repo ohne Lizenzdatei, also nicht ohne Erlaubnis nutzbar), **Ambig-SWE** (Rückfragen bei unterspezifizierten Issues, Code MIT, ICLR 2026), **Loc-Bench** (Datei-Lokalisierung, V0.1 Apache-2.0), **DevBench** (Software-Design aus PRD, Apache-2.0). Für Architektur-Review und Threat Models gibt es keinen anerkannten Benchmark (ungeprüft, nichts gefunden).
4. **Unsere Architektur deckt die Plan-Kernmechanik gut ab** (Phasen und Tasks, Nur-Lese-Phase, Zitatprüfung, Plan-Kritik wie Jules, Autonomiewahl wie Factory). **Es fehlen:** (a) eine Architektur- und Design-Ebene als eigener Service (Spezifikation, ADR, Design-Review, Threat Model), obwohl der Owner sie als Ebene nennt; (b) spezifikationsgetriebene Artefakte im Repo mit Rückverfolgbarkeit Anforderung, Task, Test; (c) Plan aus freier Beschreibung, PRD oder Bild; (d) Plan-Konformitätsprüfung nach der Umsetzung; (e) ein extern kalibrierbares Gate B für den Planner, das nicht von einem Vergleichslauf gegen ein Fremdprodukt abhängt.

---

## 2. Befunde mit Quellen

### 2.1 Planung: Anbieter und Mechanik (Stand 2026-10-31)

| Anbieter | Was Nutzer bekommen | Einstufung, Quelle |
|---|---|---|
| **Kiro** (Specs) | Drei Dateien: `requirements.md` (oder `bugfix.md`), `design.md` (Architektur, Sequenzdiagramme, Datenfluss, Fehlerbehandlung, Teststrategie), `tasks.md`. Varianten Requirements-First und Design-First; Bugfix-Spec mit "current/expected/unchanged behavior"; Quick Spec ohne Freigabe-Gates; "Analyze Requirements" prüft auf "logical inconsistencies, ambiguities, conflicting constraints, and gaps"; Anforderungen in EARS ("WHEN [condition/event] THE SYSTEM SHALL [expected behavior]"); Tasks als Abhängigkeitsgraph in "waves" (Wellen sequentiell, Tasks einer Welle parallel). | BELEGT [kiro-specs], [kiro-feature] |
| Kiro Correctness | Aus EARS-Anforderungen werden testbare Eigenschaften abgeleitet und als Property-Based Tests mit Shrinking ausgeführt; Hover zeigt Verbindung Eigenschaft, Anforderung, Task; "evidence of correctness, not a proof"; nur in der IDE. | BELEGT [kiro-correctness] |
| **GitHub Spec Kit** | MIT-Lizenz; neun Befehle: `constitution`, `specify`, `clarify` ("asks targeted questions about anything underspecified"), `plan`, `checklist` ("unit tests for your requirements"), `tasks` (abhängigkeitsgeordnet), `analyze` (nur lesend, "conflicts, gaps, and ambiguities across spec.md, plan.md, and tasks.md"), `implement` (offene Checklistenpunkte sind ein Gate), `converge` (prüft Code gegen Spec, Plan, Tasks, ergänzt fehlende Tasks bis "Converged"). Erweiterungen für Bugfix (`verified`, `partial`, `failed`) und Ideenbewertung (`go`, `needs-clarification`, `kill`). Letztes Release v1.2.5 vom 2026-10-28. | BELEGT [speckit-repo], [speckit-quickstart], [speckit-release] |
| **Jules** (Google) | "Interactive Plan" seit 2025-08-08 (liest Code, stellt Rückfragen, verfeinert den Plan); Critic-Agent für Code seit 2025-08-08; **Planning Critic** seit 2026-01-26 prüft "all plans that do not require human intervention", Ergebnis laut Google "a 9.5% reduction in task failure rates". Automatische Freigabe nach 5 Minuten ohne Antwort laut Drittberichten. | Changelog BELEGT [jules-changelog]; 9,5 % GESAGT; 5-Minuten-Frist GESAGT (Drittberichte, ungeprüft) |
| **Factory** Spec Mode | Nur lesend ("should not edit files, change configuration, make commits, start services, or write to external systems"); `ExitSpecMode` zur Freigabe; danach manuelle Freigaben oder Autonomie Low, Medium, High; Org-Maximum blendet höhere Optionen aus; eigenes Planungsmodell (`specModeModel`, `specModeReasoningEffort`); Spec optional als Markdown unter `.factory/docs`, Name `YYYY-MM-DD-slug.md`. | BELEGT [factory-spec] (aktualisiert die Angaben in 02) |
| **Devin** | "Interactive Planning" als eigene Doku-Seite leitet am 2026-10-31 auf die Tutorial-Übersicht um (ABGELEITET: Funktion aufgegangen in Ask Devin). Ask Devin: Fragen mit Code-Zitaten und Plan-Modus, der einen "context-rich prompt" für eine Agent-Sitzung erzeugt; mit Jira oder Linear "automatically analyzes tickets and provides confidence scores". DeepWiki: automatische Wikis mit Architekturdiagrammen, Steuerung über `.devin/wiki.json` (höchstens 30 Seiten, Enterprise 80), freie DeepWiki-MCP für öffentliche Repos. | BELEGT [devin-ask], [devin-sdlc], [devin-wiki] |
| **GitHub Copilot** | Cloud Agent: Plan auf Wunsch im Prompt, Freigabe oder Feedback vor Code, Deep Research, Arbeit auf Branch ohne PR (Changelog 2026-03-31 bzw. 2026-04-01). Copilot CLI: Plan-Modus per Shift+Tab, `/plan`, `--plan`; `plan.md` im Sitzungsordner; "Accept plan and build in Autopilot". VS Code: Plan-Agent, Visual Studio: Plan als `.copilot/plans/plan-{title}.md`. | Changelog BELEGT [copilot-plan]; CLI, VS Code, Visual Studio GESAGT (Suchauszüge aus docs.github.com und devblogs, nicht selbst gelesen) |
| **Claude Code** | Plan-Modus: liest, führt erkundende Shell-Befehle aus, "does not edit your source"; Freigabe mit Wahl des Folgemodus; "No, keep planning"; Ctrl+G öffnet den Plan im Editor; als Projekt-Standard über `defaultMode: plan`. | BELEGT [cc-planmode] |
| **Cursor** Plan Mode | Seit 2025-10-07: Recherche, Rückfragen, Markdown-Plan mit Dateipfaden und Code-Referenzen, To-dos editierbar, "Build", optional im Repo speichern; "Most new features at Cursor now begin with Agent writing a plan". Keine Messwerte. | GESAGT [cursor-plan] |
| **Linear for Agents** | Agent-Sitzung mit `plan` als Liste von Schritten, Status `pending`, `inProgress`, `completed`, `canceled`; Plan nur als Ganzes ersetzbar; fünf Aktivitätsarten `thought`, `elicitation`, `action`, `response`, `error`; "technology preview". Delegation statt Zuweisung, Mensch bleibt Owner. | BELEGT [linear-interaction], [linear-agents] |
| **Augment Intent** | Desktop-Werkzeug, "living spec", Coordinator, Implementors in Wellen, Verifier prüft gegen die Spec, drei menschliche Prüfpunkte; Public Beta seit Februar 2026. | GESAGT [augment-intent] (nur Herstellerseiten gefunden) |
| **Traycer** | Desktop-App, laut eigener Doku "open-source", startet Claude Code, Codex, Cursor parallel, Artefakte "specs, tickets, stories and reviews". Plan-Verifikation gegen Umsetzung auf der Seite nicht beschrieben. | GESAGT [traycer]; Lizenz ungeprüft (Repo nicht gefunden, GitHub-API im Rate-Limit) |
| **Tessl** | 2026 umpositioniert zu einer Registry von Agent-Skills; Spec-Framework in geschlossener Beta; Kachel `tessl-labs/spec-driven-development` (Rückfragen, Spec zuerst, Prüfpunkt, Umsetzung gegen Spec). | GESAGT [tessl] (Suchauszüge, Herstellerseiten nicht selbst gelesen) |

**Marktstellung, unabhängige Benchmarks, öffentliche Messwerte:**
- Unabhängige Vergleiche von Planungsprodukten: keine gefunden (ungeprüft, ob es welche gibt). Kein Anbieter außer Jules veröffentlicht einen Messwert zur Planungsqualität; Cursor nennt nur qualitative Nutzen (GESAGT).
- Öffentlich gemessen sind nur **Harnesses**, nicht Produkte: SWE-RPG prüft Claude Code, Codex und OpenCode mit sechs Modellen, mittlere Resolve-Rate 31,5 %; die größte Schwäche ist das Erkennen nicht genannter Anforderungen ("24.5%-46.0% of agent runs") [swe-rpg] (BELEGT, Abstract gelesen).
- "From Plan to Action" (21.120 SWE-agent-Trajektorien, 4 Modelle, SWE-bench Verified und Pro): ein Plan erhöht die Lösungsrate, periodische Plan-Erinnerungen senken Abweichungen, und "A subpar plan hurts performance even more than no plan at all" [plan-to-action] (BELEGT, Abstract gelesen).
- Ambig-SWE: Modelle unterscheiden schlecht zwischen klaren und unterspezifizierten Aufgaben; Interaktion verbessert die Leistung um bis zu 74 % gegenüber nicht-interaktiv [ambig-swe] (BELEGT, Abstract gelesen). Werte je Modell (laut Suchauszug Claude Sonnet 4 89 %) GESAGT, nicht im Abstract.
- RigorBench misst Prozessdisziplin mit dem Pfeiler "Planning Fidelity" (30 Aufgaben) [rigorbench] (BELEGT, Abstract); Artefakte ohne Repo-Link und ohne Lizenzangabe.

**Spitzengruppe und Warum (ABGELEITET):** Kiro und Spec Kit führen bei der Spezifikation (Anforderungen, Design, Tasks, Konsistenzanalyse, Konvergenzprüfung, Rückverfolgbarkeit bis zum Test). Jules führt bei der Absicherung automatischer Freigaben (Planning Critic mit Messwert). Factory führt bei der Steuerung nach Freigabe. Ein Produkt, das alle drei verbindet, gibt es nicht; das ist unsere Chance und unser Maßstab.

### 2.2 Architektur und Design: anerkannte Standards

| Standard | Inhalt | Lizenz, Nutzbarkeit für ein öffentliches Repo | Quelle |
|---|---|---|---|
| **arc42** | 12 Abschnitte: Einführung und Ziele, Randbedingungen, Kontext und Abgrenzung, Lösungsstrategie, Bausteinsicht, Laufzeitsicht, Verteilungssicht, Querschnittskonzepte, Architekturentscheidungen, Qualitätsanforderungen (Qualitätsbaum, Szenarien), Risiken und technische Schulden, Glossar; dazu Qualitätsmodell quality.arc42.org | "Open source and free, also for commercial use", Fußzeile CC BY-SA 4.0 (Share-Alike: mitgelieferte Vorlagen erben die Lizenz) | BELEGT [arc42] |
| **C4** | Ebenen System Context, Container, Component, Code; Zusatzdiagramme System Landscape, Dynamic, Deployment; notations- und werkzeugunabhängig; **offizielle Review-Checkliste** mit 21 Ja/Nein-Fragen (Titel, Typ, Scope, Legende, Elemente, Beziehungen mit Beschriftung und Technologie) | Website und Checkliste CC BY 4.0 | BELEGT [c4], [c4-checklist] |
| **ADR** | "captures a single AD and its rationale"; Sammlung ist das Decision Log; Vorlagen Nygard (2011), Y-Statements (Zdun), MADR; Azure und AWS empfehlen ADRs in ihrer Architekturdoku | MADR: "MIT OR CC0-1.0" | BELEGT [adr], [madr-license] |
| **ISO/IEC/IEEE 42010:2022** | Anforderungen an Architekturbeschreibungen, Rahmenwerke, Sprachen und Sichtpunkte; legt bewusst keine Methode, Notation oder Werkzeuge fest; verweist auf ISO/IEC/IEEE 42030 für Architekturbewertung | kostenpflichtige Norm (ISO-Shop laut Suchauszug CHF 204) | GESAGT [iso42010] (iso.org lieferte 403, Inhalt aus Suchauszügen) |
| **ATAM** (SEI) | Bewertung einer Architektur gegen Qualitätsziele: Utility Tree, Qualitätsszenarien (Quelle, Stimulus, Umgebung, Artefakt, Antwort, Antwortmaß), Ergebnis Risiken, Nicht-Risiken, Sensitivitätspunkte, Tradeoffs; Bericht CMU/SEI-2000-TR-004 | Methode, frei beschrieben | GESAGT [atam] (SEI-Seite nicht selbst gelesen) |
| **STRIDE** | Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege; Kern des Microsoft SDL Threat Modeling Tool | Methode | BELEGT [ms-stride] |
| **Threat Modeling Manifesto** | Vier Fragen: "What are we working on? What can go wrong? What are we going to do about it? Did we do a good enough job?"; Werte, Prinzipien, Muster, Anti-Muster | CC BY 4.0 | BELEGT [tm-manifesto] |
| **EARS** | Anforderungssyntax von Mavin u. a. (Rolls-Royce), RE '09, DOI 10.1109/RE.2009.9; Grundform "WHILE ... WHEN ... the system SHALL ..."; von Kiro übernommen | Methode, Paper bei IEEE | GESAGT [ears] (Paper nicht selbst gelesen); Kiro-Nutzung BELEGT [kiro-feature] |

### 2.3 Wer KI-gestütztes Architektur- oder Design-Review anbietet

| Anbieter | Angebot | Einstufung |
|---|---|---|
| STRIDE GPT (mrwadams) | MIT; Threat Model und Angriffsbäume nach STRIDE, Gegenmaßnahmen, DREAD-Bewertung, Gherkin-Testfälle, Diagramme als Eingabe, MITRE-ATT&CK- und ATLAS-Zuordnung, CLI-Analyse einer Codebasis, Modelle über LiteLLM; Version 0.20 "threats that cite verified code evidence"; etwa 1,1k Sterne | BELEGT [stride-gpt] |
| AWS Threat Designer (awslabs) | Apache-2.0; bis zu drei Architekturdiagramme je Auftrag, STRIDE (oder MAESTRO für agentische KI), Export PDF, DOCX, JSON, Katalog früherer Modelle; Voll-Deployment auf AWS oder lokale CLI mit Bedrock- oder OpenAI-Credentials | BELEGT [threat-designer] |
| AWS Threat Composer | Apache-2.0 (Lizenzdatei gelesen); Funktionsumfang nicht geprüft | Lizenz BELEGT [threat-composer], Rest ungeprüft |
| OWASP Threat Dragon | Apache-2.0 (Lizenzdatei gelesen); KI-Funktionen ungeprüft | Lizenz BELEGT [threat-dragon] |
| AWS Well-Architected IaC Analyzer | prüft IaC und Architekturdiagramme gegen Well-Architected mit Bedrock; Lizenz laut Drittseiten MIT-0 | GESAGT [wa-iac] |
| Clearly AI, Prime Security, Apiiro, Seezo, DevArmor, IriusRisk, Oplane | kommerzielle Design-Reviews und Threat Models vor dem Code | GESAGT [tm-market] (Presse und Herstellerangaben) |
| Factory Skill "threat-model-generation", Claude-Code-Plugins für STRIDE | Agent-Skills, die aus einer Codebasis ein STRIDE-Modell erzeugen | GESAGT [tm-market] |
| Devin DeepWiki | Architekturdiagramme aus Code, aber kein Review | BELEGT [devin-wiki] |

ABGELEITET: Für Design-Review ist die Spitzengruppe nicht ein Produkt, sondern die Kombination "Methode plus KI-Assistenz": ATAM-artige Prüfung gegen Qualitätsszenarien, C4-Checkliste für Diagramme, ADR-Pflicht für Entscheidungen, STRIDE für Bedrohungen. Unser Standard für diese Ebene sollte daher "Methode vollständig angewendet und jede Aussage mit Zitat belegt" sein, gemessen gegen menschliche Architektur-Reviews.

### 2.4 Fähigkeits-Checkliste des Standards

Spalte "bei uns" verweist auf `docs/architektur`. "ja" heißt beschrieben, nicht gebaut.

| # | Fähigkeit | wer hat sie | Beleg | bei uns |
|---|---|---|---|---|
| 1 | Plan per Erwähnung oder Befehl im Ticket | Jules, Copilot, Devin | [jules-changelog] | ja, 02 Abschnitt 1, 03 Abschnitt 4 |
| 3 | Plan aus freier Beschreibung, PRD oder Design-Spec ohne Ticket | Kiro, Spec Kit, Cursor, Claude Code | [kiro-specs] | nein: `PlanRequest` kennt nur `workItem | change` (02 Abschnitt 1 Eingang) |
| 5 | Recherche mit Code-Zitaten | Devin, Cursor | [devin-ask] | ja, 02 Abschnitt 1 Stufen 3 bis 5 |
| 8 | Rückfragen bei Unklarheit statt Plan | Jules, Cursor, Spec Kit `clarify`, Kiro Quick Spec | [jules-changelog], [speckit-quickstart] | ja, Klarheits-Gate 02 Abschnitt 1 Stufe 2, G1b |
| 10 | Phasen und Tasks | Kiro, Spec Kit | [kiro-specs] | ja, `phases[].tasks[]` |
| 11 | Task-Abhängigkeitsgraph, parallele Wellen | Kiro, Spec Kit (abhängigkeitsgeordnet), Augment (GESAGT) | [kiro-specs], [speckit-quickstart] | nein: Phasen sind linear |
| 12 | Agent-Prompt je Phase und gesamt, Übergabe an fremde Agenten | Devin | [devin-ask] | ja, `agentPrompt`, 02 Abschnitt 2 "Aus" |
| 14 | Verfeinern im Dialog, Neu-Planen mit Feedback | Devin, Claude Code, Cursor | [cc-planmode] | teilweise: Änderungswunsch erzeugt Plan v2 (03 Abschnitt 1, Schritt G1); kein Dialog über mehrere Runden beschrieben |
| 15 | Mensch editiert den Plan direkt | Claude Code (Ctrl+G), Cursor, Copilot CLI | [cc-planmode], [cursor-plan] | nein: kein Weg, einen vom Menschen bearbeiteten Plan als neue Version zu übernehmen |
| 16 | Autonomie bei Freigabe wählen, Org-Obergrenze | Factory, Claude Code | [factory-spec], [cc-planmode] | ja, 02 Abschnitt 1 Qualitätsmechanik, `max_autonomy` |
| 17 | Zweiter Agent kritisiert automatisch freigegebene Pläne | Jules Planning Critic | [jules-changelog] | ja, Plan-Kritik 02 Abschnitt 1 Stufe 6 (nur bei `high` und `full`) |
| 18 | Freigabe nach Zeitablauf ohne Antwort | Jules (GESAGT) | Drittberichte | bewusst nein, 03 Abschnitt 1a "Ein Durchwinken gibt es nicht" (richtig so, ABGELEITET) |
| 19 | Konfidenz- oder Machbarkeitswert je Ticket | Devin mit Jira und Linear | [devin-sdlc] | nein: nur `risk` und `estimate` |
| 20 | Kostenschätzung vor Freigabe | keiner der Anbieter belegt | - | ja, `estimate` und `auto_if` (eigene Stärke) |
| 21 | Eigenes Modell für die Planung | Factory | [factory-spec] | ja, `services.planner.runtime`, `model_hint` (04) |
| 22 | Plan bzw. Spec als Datei im Repo | Factory, Kiro, Spec Kit, Cursor, Visual Studio | [factory-spec], [kiro-specs], [cursor-plan] | nein: Plan nur als Kommentar und in `artifacts` |
| 23 | Nativer Plan im Tracker | Linear Agent Plan | [linear-interaction] | ja, 01 `AgentSession.plan`; Statuswerte weichen ab (Abschnitt 2.7) |
| 24 | Strukturierte, testbare Anforderungen (EARS) | Kiro | [kiro-feature] | nein: `acceptance[]` ist Freitext |
| 25 | Konsistenzanalyse Anforderung, Plan, Tasks | Kiro "Analyze Requirements", Spec Kit `analyze` | [kiro-feature], [speckit-quickstart] | teilweise: Plan-Kritik prüft Plan gegen Ticket, keine Prüfung auf Lücken und Widersprüche im Ticket selbst |
| 26 | Projektprinzipien als Prüfmaßstab für jeden Plan | Spec Kit `constitution`, Kiro Steering | [speckit-quickstart] | teilweise: Regeln und AGENTS.md vom Basis-SHA (ADR-17), Standards-Service; nicht als Prüfschritt im Planner |
| 27 | Qualitäts-Checkliste für Anforderungen als Gate | Spec Kit `checklist` | [speckit-quickstart] | nein |
| 28 | Rückverfolgbarkeit Anforderung, Task, Test; Property-Tests aus Anforderungen | Kiro | [kiro-correctness] | teilweise: `acceptance[]`, QA nutzt Akzeptanzkriterien optional (02 Abschnitt 4); keine IDs, keine Zuordnung |
| 29 | Konvergenzprüfung: Umsetzung gegen Spec, fehlende Tasks nachziehen | Spec Kit `converge`, Augment Verifier (GESAGT), Factory Missions Validator | [speckit-quickstart], [factory-missions] | teilweise: Reviewer sieht Ticket und Plan (03 Abschnitt 1a Punkt 3), aber kein eigener Abgleich und keine Befundart "weicht vom Plan ab" |
| 30 | Bugfix-Spezifikation (aktuelles, erwartetes, unverändertes Verhalten) | Kiro, Spec Kit Bug-Erweiterung | [kiro-specs], [speckit-repo] | teilweise: Coder "Reproduktion zuerst" (02 Abschnitt 2 Stufe 2), Planner kennt keinen Bugfix-Typ |
| 31 | Design-First-Variante (Entwurf vor Anforderungen) | Kiro | [kiro-feature] | nein |
| 32 | Deep Research und Q&A über die Codebasis | Copilot, Devin Ask | [copilot-plan], [devin-ask] | ja, Befehl `ask` über Indexer (02 Abschnitt 6) |
| 33 | Repo-Wiki mit Architekturdiagrammen | Devin DeepWiki | [devin-wiki] | teilweise: KB-Schichten L0 bis L5 (02 Abschnitt 6), keine Diagramme |
| 34 | ADR-Entwurf zu einer Entscheidung im Plan | keiner belegt (Methode [adr]) | - | nein |
| 35 | Architekturbeschreibung nach arc42 bzw. C4 erzeugen und aktuell halten | teilweise Devin (Diagramme), Kiro (`design.md`) | [devin-wiki], [kiro-specs] | nein |
| 36 | Design-Review gegen Qualitätsziele (ATAM-artig) | kein KI-Produkt belegt; Well-Architected-Analyse für Cloud (GESAGT) | [atam], [wa-iac] | nein |
| 37 | Threat Model nach STRIDE aus Design oder Code | STRIDE GPT, Threat Designer, kommerzielle Anbieter | [stride-gpt], [threat-designer] | nein als Service; nur eigene Sicherheitsarchitektur in 05 |
| 38 | Diagramm-Review nach C4-Checkliste | C4 (Methode) | [c4-checklist] | nein |

Die Nummern 2, 4, 6, 7, 9 und 13 entfallen in dieser Fassung: sie stützten sich nur auf Herstellerdoku, deren Auswertung nach [10](../architecture/10-standards-per-layer.md) Abschnitt 16 nicht weitergeführt wird. Zählung (selbst ausgezählt in dieser Tabelle): 11 ja, 1 bewusst nein (Nr. 18), 7 teilweise, 13 nein. Die Nein-Punkte betreffen Spezifikation und Rückverfolgbarkeit (11, 22, 24, 27, 31), die fehlende Architektur-Ebene (34 bis 38) sowie Eingänge und Kontext des Planners (3, 15, 19).

### 2.5 Wie man das Niveau misst

**Öffentliche Datensätze und Benchmarks:**

| Datensatz | Misst | Größe | Lizenz | Nutzbar für | Quelle |
|---|---|---|---|---|---|
| SWE-RPG | Rückfrage- und Plan-Referenz als "information points" (Ziel, Ort, Ansatz, Randbedingungen, Validierung) plus ausführbare Patches | 163 Fälle, 31 Repos Python und Java, 113 Bugfix, 50 Feature | Paper CC BY 4.0; **Repo ohne Lizenzdatei** (Dateiliste gelesen: `data`, `evaluation`, README, INSTALLATION) | Gate B Planner, wenn die Autoren eine Lizenz geben; sonst nur die Methode nachbauen | BELEGT [swe-rpg], [swe-rpg-repo] |
| Ambig-SWE | Erkennen unterspezifizierter Aufgaben, gezielte Rückfragen, Gewinn durch Interaktion | abgeleitet aus SWE-bench Verified | Code MIT (Lizenzdatei gelesen); zugrunde liegende Verified-Daten: Lizenz auf Hugging Face nicht ausgewiesen (ungeprüft) | P2 (Rückfragen-Korrektheit) | BELEGT [ambig-swe], [ambig-swe-repo] |
| Loc-Bench | Datei- und Funktions-Lokalisierung aus Issue-Text | V1 560 Fälle (Bug 242, Feature 150, Performance 139, Security 29), V0.1 660 | V0.1 Apache-2.0 (Datensatzkarte), V1 ohne Lizenzangabe; LocAgent-Code Apache-2.0 | P1 Datei-Recall extern kalibriert; Bezugswert LocAgent "up to 92.7% accuracy on file-level localization" | BELEGT [locagent], [locbench-hf] |
| SWE-bench Verified, Pro | Resolve-Rate; Plan-Nutzen als Differenz mit und ohne Plan | 500 (Verified, laut [swebench-pro] GESAGT) | Code MIT (Lizenzdatei gelesen); Datensätze auf Hugging Face ohne Lizenz-Tag (ungeprüft) | Plan-Nutzen extern vergleichbar mit [plan-to-action] | BELEGT [swebench-license] |
| DevBench | Software-Design aus PRD: UML-Klassen- und Sequenzdiagramme in Mermaid, Architekturentwurf; LLM-Richter | laut Paper mehrere Repos (Anzahl ungeprüft) | Apache-2.0 (Lizenzdatei gelesen) | Design-Ebene D1 | BELEGT Lizenz [devbench]; Inhalt GESAGT (Suchauszug) |
| DesBench | design-aware Codegenerierung, OO-Modellierung, Akzeptanztest-Design | 30 Java-Projekte | ungeprüft | Design-Ebene, nach Lizenzprüfung | GESAGT [desbench] |
| RigorBench | Prozessdisziplin inkl. Planning Fidelity | 30 Aufgaben | ungeprüft, kein Repo-Link | nur Methode | BELEGT Abstract [rigorbench] |
| Threat Models, ADR, arc42 | - | - | - | **kein öffentlicher Benchmark gefunden** (ungeprüft) | - |

**Online-Metriken je Unterebene (Vorschlag, ABGELEITET):**
- Planung: Freigabe ohne Änderung; Zahl der Plan-Versionen bis Freigabe; Anteil Rückfragen, die der Mensch als nötig bestätigt; Plan-Drift (Anteil geänderter Dateien im PR, die der Plan nicht nennt, und genannter, nicht angefasster Dateien); Task-Fehlerrate des Coders mit und ohne Plan-Kritik (Bezug Jules 9,5 %, GESAGT); Merge ohne Nacharbeit je Plan.
- Spezifikation: Anteil Akzeptanzkriterien mit zugeordnetem Test; Anteil Anforderungen, die `converge` als erfüllt meldet; vom Menschen nachgetragene Anforderungen nach Freigabe.
- Architektur-Review: Annahmequote der Befunde (wie Address Rate beim Reviewer); Anteil Befunde mit Zitat auf Code oder Dokument; später im Betrieb aufgetretene Probleme, die das Review hätte finden müssen (Stichprobe).
- Threat Model: Übereinstimmung mit dem Modell eines Sicherheitsmenschen auf denselben Systemen (Recall der Bedrohungen, Präzision), Anteil Bedrohungen mit belegtem Code-Ort (STRIDE GPT 0.20 macht das laut Changelog, BELEGT [stride-gpt]).

**Gate B je Ebene konkret und messbar (Vorschlag für [07](../architecture/07-eval.md) Abschnitt 4, ABGELEITET):**

| Ebene | Gate A | Gate B (ohne Vergleichslauf gegen Fremdprodukt) | Gate B (mit Vergleichslauf, O13) |
|---|---|---|---|
| Planner: Lokalisierung | Datei-Recall auf P1 nicht unter nacktem Harness | Datei-Acc@5 auf Loc-Bench V0.1 mindestens auf dem Wert von LocAgent mit demselben Modell, Stand bei Messung festhalten | P1 gegen CodeRabbit Plan auf denselben Issues |
| Planner: Rückfragen | P2: Rückfrage bei unklaren, keine bei klaren Tickets | Erkennungsrate auf Ambig-SWE-Methode (eigene Repos oder Verified nach Lizenzklärung) mindestens bester veröffentlichter Wert desselben Modells | - |
| Planner: Plan-Inhalt | Plan-Nutzen größer 0 | Abdeckung der Referenz-"information points" auf SWE-RPG mindestens bester veröffentlichter Harness (nur nach Lizenz, sonst eigener Satz P3 nach derselben Methode) | - |
| Planner: Plan-Kritik | erkennt eingepflanzte Fehler im Plan (P4, eigene Fälle: falsche Datei, fehlende Randbedingung, verletzte Regel) | Task-Fehlerrate mit Kritik minus ohne Kritik mindestens so gut wie Jules' 9,5 % (GESAGT, nur Richtwert) | - |
| Spezifikation | Konsistenzanalyse findet eingepflanzte Widersprüche (S-Satz, eigene Fälle) | Rückverfolgbarkeit 100 % (jedes Kriterium hat Task und Test), Konvergenzbericht deckt sich mit Mensch-Label | gegen Kiro oder Spec Kit nur als Methode, kein Konto nötig (Spec Kit ist MIT und lokal lauffähig) |
| Design und Architektur | Design-Review findet eingepflanzte Mängel in eigenen Architekturdokumenten | DevBench-Design mit LLM-Richter mindestens bester veröffentlichter Wert; C4-Checkliste 21 von 21 automatisch prüfbar | - |
| Threat Model | Recall auf eigenen, von Menschen modellierten Systemen größer als STRIDE GPT mit demselben Modell (MIT, lokal vergleichbar) | ehrlich "offen": kein öffentlicher Bezugswert | - |

### 2.6 Was die Anbieter offenlegen und was proprietär bleibt

**Übernehmbar (offen oder als Methode beschrieben):**
- Spec Kit vollständig (MIT): Vorlagen, Befehlsfolge, `analyze`, `checklist`, `converge`. Direkt als Vorlagen unseres Planner- bzw. Architekt-Services nutzbar, mit Lizenzhinweis.
- Kiro: Dateiaufbau `requirements.md`, `design.md`, `tasks.md`, EARS, Wellen-Ausführung, Property-Ableitung aus Anforderungen. Produkt proprietär, die Methode ist in der Doku vollständig beschrieben.
- Jules: Muster "Planning Critic nur für automatisch freigegebene Pläne" mit Messwert. Prompt und Modell proprietär.
- Factory: `ExitSpecMode` als Tool-Aufruf zur Freigabe, Autonomiestufen, eigenes Planungsmodell, Datei-Benennung.
- Linear: Agent-Plan-Protokoll ist öffentliche API.
- Devin: `.devin/wiki.json` als Steuerdatei für Wikis (Idee); Konfidenzwerte nur als Funktion beschrieben, Berechnung proprietär.
- Methoden: arc42 (CC BY-SA), C4 und C4-Checkliste (CC BY 4.0), MADR (MIT oder CC0), Threat Modeling Manifesto (CC BY 4.0), STRIDE, ATAM.
- Code für Threat Models: STRIDE GPT (MIT), Threat Designer, Threat Composer, Threat Dragon (alle Apache-2.0) als Ideengeber oder Bibliothek; LocAgent (Apache-2.0) für graphbasierte Lokalisierung.

**Proprietär oder ungeprüft:** Devin-Suche, Cursor-Plan-Werkzeuge, Copilot-Planner, Augment Context Engine, Tessl-Regenerierung (laut Drittbericht geschlossene Beta, GESAGT), Traycer-Lizenz (ungeprüft), Patente (nicht gesucht, ungeprüft).

### 2.7 Korrekturen und Aktualisierungen bestehender Dokumente

| Stelle | Stand dort | Korrektur | Beleg |
|---|---|---|---|
| 02 Abschnitt 1 Messlatte, Zeile Jules | "Plan-Freigabe vor Code, Rückfragen" | ergänzen: Planning Critic für automatisch freigegebene Pläne, 9,5 % weniger Task-Fehlschläge (GESAGT) | [jules-changelog] |
| 01 Zeile 183 `plan(...)` | Status `pending`, `in_progress`, `done` | Linear nutzt `pending`, `inProgress`, `completed`, `canceled`; Adapter muss abbilden und `canceled` kennen (Minor) | [linear-interaction] BELEGT |
| README [devin-ask] | Interactive Planning implizit | Devin-Seite "interactive-planning" leitet auf die Tutorial-Übersicht; Planung liegt jetzt in Ask Devin | [devin-ask] BELEGT |
| README Titel mit Firmennamen | firmenspezifisch | widerspricht Owner-Vorgabe 2 vom 2026-10-31 (Open Source, nicht auf eine Firma spezialisiert); gehört zur Folgeliste der Gesamtrunde, nicht zu diesem Thema | ABGELEITET |

---

## 3. Folgen für unsere Architektur

Alle Punkte ABGELEITET aus Abschnitt 2. Kein Punkt ist gebaut.

1. **[02](../architecture/02-services.md) neuer Abschnitt "Architekt" (Service `architect`)**, zwischen Planner und Coder, `mode: off | shadow | live` wie alle Services. Aufgaben in drei Modi:
   - `spec`: Anforderungen (EARS mit IDs), Design (C4-Ebenen 1 bis 3 als Mermaid, Datenfluss, Fehlerbehandlung, Teststrategie), Tasks mit Abhängigkeitsgraph. Vorlage Spec Kit (MIT) und Kiro-Methode.
   - `adr`: ADR-Entwurf nach MADR für jede `designChoice` mit Tragweite über das Ticket hinaus (Kriterium im Manifest), als Datei unter einem konfigurierbaren Pfad, etwa `docs/adr/`.
   - `review`: Design-Review gegen Qualitätsszenarien (ATAM-artig: Utility Tree aus `arc42`-Abschnitt 10 bzw. Repo-Konfiguration), C4-Checkliste für Diagramme, STRIDE-Threat-Model für berührte Vertrauensgrenzen; jeder Befund mit Zitat auf Datei oder Dokumentstelle, Schwere und Evidenzstufe wie beim Reviewer.
   - Auslöser: `@agent design`, `@agent adr`, `@agent design-review`; automatisch in `ticket-to-pr`, wenn `plan.risk == high`, `protected_paths` berührt sind oder das Repo `architect.required_if` setzt; zusätzlich als PR-Review für Pfade wie `docs/architektur/**`, `docs/adr/**`, `*.c4`, `*.dsl`.
   - Schreibwünsche (02 Abschnitt 0): `propose_comment`, `propose_change` (nur Doku-Pfade), `request_human_input`, `propose_check` (`ai-design-review`). Keine Shell nötig außer für Diagramm-Rendering; Egress nur LLM und Plattform-MCP.
2. **[02](../architecture/02-services.md) Abschnitt 1 Planner:**
   - Messlatte um Kiro, Spec Kit, Jules Planning Critic, Devin Ask, Claude Code und Copilot Plan-Modus ergänzen.
   - Eingang: `PlanRequest { workItem | change | brief }` mit `brief = { text, attachments[] (Bild, PRD-Dokument) }`; Befehl `@agent plan` auch in Chat-Notifiern (Slack, Teams) und als freier Text.
   - Ausgang `PlanArtifact` erweitern: `kind: feature | bugfix | refactor`, `requirements[]` (ID, EARS-Text, Quelle im Ticket), `tasks[].dependsOn[]` und `tasks[].requirementIds[]`, `acceptance[].requirementId` und `acceptance[].testHint`, `assumptions[]`, `relatedItems[]` (Duplikate, verwandte Tickets über KnowledgeStore), `confidence` (0 bis 1, kalibriert gegen Resolve-Rate), `humanEdited: boolean`.
   - Neue Stufe "Konsistenzanalyse" vor der Synthese (Spec-Kit-`analyze`-Prinzip): Lücken, Widersprüche, nicht genannte Anforderungen; Ergebnis fließt in `questions[]`. Begründung: SWE-RPG nennt nicht genannte Anforderungen als größte Fehlerquelle.
   - Neue Stufe "Prinzipien-Prüfung": Plan gegen Regeln, AGENTS.md und eine optionale Repo-Datei mit Projektprinzipien (Spec-Kit-`constitution`), vom Basis-SHA.
   - Plan-Datei im Repo optional (`planner.persist: none | branch`): bei `branch` legt der Coder den freigegebenen Plan als erste Datei im Agent-Branch ab, etwa `.agents/plans/<key>.md`; Standard `none`, damit Repos ohne Wunsch sauber bleiben.
   - Menschliche Bearbeitung: Befehl `@agent plan --replace` mit angehängtem Markdown oder Bearbeitung des Plan-Kommentars erzeugt `v{n+1}` mit `humanEdited: true`; Plan-Verifier läuft erneut.
3. **[02](../architecture/02-services.md) Abschnitt 2 Coder:** Plan je Phase neu in den Kontext geben (Plan-Erinnerung, Beleg [plan-to-action]); Self-Check um "Plan-Abgleich" ergänzen: geänderte Dateien gegen `phases[].tasks[]`, jede `requirementId` mit Test oder begründetem Verzicht.
4. **[02](../architecture/02-services.md) Abschnitt 3 Reviewer:** Befundart `plan_deviation` (Umsetzung weicht vom freigegebenen Plan ab oder lässt eine Anforderung offen), Prüfung im Stil von Spec-Kit-`converge`. Merge-Gate in [03](../architecture/03-flow-and-orchestration.md) Abschnitt 1a: offene `plan_deviation` der Schwere P1 blockiert wie andere P1.
5. **[01](../architecture/01-plugin-interfaces.md):** `ServiceId` um `architect` erweitern (Zeile 74), `CommandName` um `design`, `adr`, `design-review` (Zeile 106); Linear-Planstatus abbilden (Abschnitt 2.7); KnowledgeStore um Dokumentquellen (Confluence, Notion, Repo-Doku) als eigene Quelle mit Herkunft je Abschnitt, nur lesend.
6. **[03](../architecture/03-flow-and-orchestration.md) Abschnitt 1 und 1a:** optionale Stufe `architect` in `ticket-to-pr` mit `on_disabled: skip` als Standard; neuer Freigabepunkt nur, wenn das Design-Review `blocked` meldet (dann G1 durch Menschen). Neues Artefakt `DesignArtifact` (Spec, ADR-Entwürfe, Review-Befunde, Threat Model) in der Liste der Übergaben.
7. **[04](../architecture/04-configuration-and-limits.md):** `services.architect` mit `mode`, `required_if`, `quality_scenarios_path`, `adr_path`, `threat_model: off | stride`; `services.planner.persist`, `services.planner.inputs: [work_item, brief, image]`; Limits für `architect` wie Planner (Startwert, Schätzung).
8. **[07](../architecture/07-eval.md):** Abschnitt 3.2 um P3 (Plan-Inhalt nach SWE-RPG-Methode), P4 (eingepflanzte Planfehler für die Plan-Kritik) und externe Kalibrierung über Loc-Bench V0.1 ergänzen; neuer Abschnitt "Architekt" mit D1 (DevBench-Design, Apache-2.0), D2 (eingepflanzte Mängel in Architekturdokumenten), D3 (Threat Models gegen menschliche Modelle, Vergleich mit STRIDE GPT); Gate-Tabelle in Abschnitt 4 nach Abschnitt 2.5 dieses Berichts; Online-Metriken in Abschnitt 6 um Plan-Drift, Versionen bis Freigabe, Rückverfolgbarkeit.
9. **[08](../architecture/08-roadmap.md):** Architekt nicht in Stufe 2, sondern nach Planner und Coder (eigene Stufe oder Teil von Stufe 6), zuerst nur `review` im Schattenmodus auf Architektur-PRs dieses Projekts selbst (das Repo hat mit `docs/architektur/` und der ADR-Liste in 09 echtes Material). `spec` und `adr` danach.
10. **[09](../architecture/09-decisions.md):** neue ADRs: "Architekt als eigener Service statt Planner-Erweiterung" (Grund: andere Eingänge, andere Prüfmethoden, eigene Qualifikation, Kette statt Gesamt-Agent nach ADR-35); "Spezifikationsartefakte nach Spec-Kit-Methode mit EARS"; "keine Freigabe nach Zeitablauf" (Abgrenzung zu Jules, bestätigt 03 Abschnitt 1a). Folgeliste um diesen Bericht ergänzen.
11. **README Glossar:** Begriffe Architekt, Spezifikation, ADR, Plan-Drift, Konvergenzprüfung.
12. **Open Source (Owner-Vorgabe 2):** Mitgelieferte Vorlagen brauchen klare Lizenzen. MADR, Spec Kit, C4-Checkliste sind mit MIT bzw. CC BY 4.0 und Namensnennung mitlieferbar; arc42 ist CC BY-SA 4.0 und sollte verlinkt statt eingebettet werden, damit das Share-Alike nicht auf eigene Vorlagen übergreift (ABGELEITET, keine Rechtsberatung).

---

## 4. Owner-Entscheidungen

| # | Frage | Art | Empfehlung | Grund |
|---|---|---|---|---|
| 1 | Wird "Architektur und Design" als eigener Service `architect` Teil des Produkts (der Owner nennt die Ebene ausdrücklich) oder bleibt es eine Planner-Option? | Produkt | Eigener Service, aber erst nach Planner und Coder, Start nur `review` im Schatten | Andere Eingänge und Methoden, eigene Qualifikation; passt zu ADR-35 (Kette statt Gesamt-Agent); geringes Risiko, weil zuerst nur lesend im Schatten |
| 2 | Öffentliche Benchmark-Daten ohne klare Lizenz (SWE-RPG ohne Lizenzdatei, Loc-Bench V1, SWE-bench-Datensätze ohne Lizenz-Tag) für Gate B nutzen und Ergebnisse im öffentlichen Repo veröffentlichen? | Recht (Lizenz) | Nur Datensätze mit ausdrücklicher Lizenz (Loc-Bench V0.1 Apache-2.0, DevBench Apache-2.0, Ambig-SWE-Code MIT) verwenden; die SWE-RPG-Autoren per Issue um eine Lizenz bitten, bis dahin die Methode auf eigenen Daten nachbauen | Im öffentlichen Repo wird jede Datennutzung sichtbar; ohne Lizenz gilt Urheberrecht |
| 3 | Vergleichslauf gegen CodeRabbit Plan (erweitert O13) | Konten, Geld, Daten nach außen | Nur auf eigenen öffentlichen oder ohnehin bei CodeRabbit liegenden Repos des Owners und nur mit vorhandenem Konto; Kosten vor dem Lauf als Entscheidungsblatt | Ohne Konto kein Gate B gegen den Maßstab; mit Loc-Bench und SWE-RPG-Methode gibt es einen Ersatz ohne Kosten |
| 4 | arc42-Vorlagen (CC BY-SA 4.0) im öffentlichen Repo mitliefern? | Recht (Lizenz) | Nein, nur verlinken; MADR und C4-Checkliste mitliefern (MIT bzw. CC BY 4.0 mit Namensnennung) | Share-Alike könnte eigene Vorlagen an CC BY-SA binden |

---

## 5. Offene Punkte

- Unabhängiger Vergleich von Planungsprodukten: keiner gefunden; Marktanteile für Planungswerkzeuge: ungeprüft.
- Jules: Freigabe nach 5 Minuten nur aus Drittberichten (GESAGT); Changelog nennt nur "auto-approval and timeout validation".
- Copilot CLI und VS Code Plan-Agent: Details nur aus Suchauszügen (GESAGT), Doku nicht selbst gelesen.
- ISO/IEC/IEEE 42010:2022 und ATAM: Inhalte aus Suchauszügen, Primärquellen nicht gelesen (iso.org 403, SEI-Seite nicht abgerufen).
- DevBench: Zahl der Repos und veröffentlichte Design-Werte nicht geprüft; DesBench-Lizenz ungeprüft.
- SWE-RPG: veröffentlichte Werte je Harness für Plan-Abdeckung nicht gelesen (nur Abstract); Lizenz fehlt.
- Ambig-SWE: Erkennungsraten je Modell nur aus Suchauszug.
- Traycer: Open-Source-Behauptung und Lizenz ungeprüft; Tessl nur aus Drittquellen.
- KI-Produkte für ADR- oder arc42-Review: keines gefunden, ungeprüft.
- Patente der Anbieter zu Planung: nicht gesucht.
- Ob Kalibrierung eines `confidence`-Werts gegen die Resolve-Rate mit den Startgrößen aus [07](../architecture/07-eval.md) Abschnitt 1 statistisch trägt: erst nach erster Messung entscheidbar.

---

## 6. Quellen (alle abgerufen 2026-10-31)

Planung:
- [kiro-specs] https://kiro.dev/docs/specs/
- [kiro-feature] https://kiro.dev/docs/specs/feature-specs/
- [kiro-correctness] https://kiro.dev/docs/specs/correctness/
- [speckit-repo] https://github.com/github/spec-kit (README und LICENSE roh gelesen: MIT)
- [speckit-quickstart] https://github.github.io/spec-kit/quickstart.html
- [speckit-release] https://github.com/github/spec-kit/releases/tag/v1.2.5 (2026-10-28)
- [jules-changelog] https://jules.google/docs/changelog/
- [factory-spec] https://docs.factory.com/cli/user-guides/specification-mode
- [factory-missions] https://docs.factory.com/missions/planning.md (aus README, nicht erneut gelesen)
- [devin-ask] https://docs.devin.ai/work-with-devin/ask-devin.md (roh gelesen); https://docs.devin.ai/work-with-devin/interactive-planning.md (leitet auf Tutorial-Übersicht)
- [devin-sdlc] https://docs.devin.ai/essential-guidelines/sdlc-integration.md (roh gelesen)
- [devin-wiki] https://docs.devin.ai/work-with-devin/deepwiki.md
- [copilot-plan] https://github.blog/changelog/2026-03-31-research-plan-and-code-with-copilot-cloud-agent; Suchauszüge https://docs.github.com/en/copilot/how-tos/copilot-cli/cli-best-practices, https://docs.github.com/en/copilot/how-tos/use-copilot-agents/cloud-agent/research-plan-iterate, https://devblogs.microsoft.com/visualstudio/plan-before-you-build-introducing-the-plan-agent-in-visual-studio/ (GESAGT)
- [cc-planmode] https://code.claude.com/docs/en/permission-modes.md (Abschnitt "Analyze before you edit with plan mode", roh gelesen); https://code.claude.com/docs/en/common-workflows
- [cursor-plan] https://cursor.com/blog/plan-mode
- [linear-agents] https://linear.app/developers/agents
- [linear-interaction] https://linear.app/developers/agent-interaction
- [augment-intent] https://www.augmentcode.com/intent, https://www.augmentcode.com/guides/intent-walkthrough-prompt-to-merge (GESAGT, Suchauszug)
- [traycer] https://docs.traycer.ai/
- [tessl] https://tessl.io/registry/tessl-labs/spec-driven-development, https://codemyspec.com/blog/tessl-review (GESAGT, Suchauszug)

Architektur und Design:
- [arc42] https://arc42.org/overview
- [c4] https://c4model.com/
- [c4-checklist] https://c4model.com/diagrams/checklist
- [adr] https://adr.github.io/
- [madr-license] https://raw.githubusercontent.com/adr/madr/main/LICENSE ("MIT OR CC0-1.0")
- [iso42010] https://www.iso.org/standard/74393.html (403), Suchauszüge https://www.evs.ee/en/iso-iec-ieee-42010-2022 (GESAGT)
- [atam] https://resources.sei.cmu.edu/library/asset-view.cfm?assetid=513908 (nicht selbst gelesen), Suchauszug https://en.wikipedia.org/wiki/Architecture_tradeoff_analysis_method (GESAGT)
- [ms-stride] https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats
- [tm-manifesto] https://www.threatmodelingmanifesto.org/
- [ears] https://alistairmavin.com/ears, DOI 10.1109/RE.2009.9 (GESAGT, Suchauszug)
- [stride-gpt] https://github.com/mrwadams/stride-gpt
- [threat-designer] https://github.com/awslabs/threat-designer
- [threat-composer] https://raw.githubusercontent.com/awslabs/threat-composer/main/LICENSE (Apache-2.0)
- [threat-dragon] https://raw.githubusercontent.com/OWASP/threat-dragon/main/license.txt (Apache-2.0)
- [wa-iac] https://github.com/aws-samples/well-architected-iac-analyzer (GESAGT, Drittseiten)
- [tm-market] https://zeltser.com/media/rsac-2026-sandbox/clearly-ai, https://www.securityweek.com/prime-security-raises-20-million-to-build-agentic-security-architect/, https://www.iriusrisk.com/resources-blog/6-ai-threat-modeling-tools, https://skillselion.com/skills/factory-ai/factory-plugins/threat-model-generation (GESAGT)

Benchmarks und Studien:
- [swe-rpg] https://arxiv.org/abs/2608.09072 (2026-08-10)
- [swe-rpg-repo] https://github.com/Xin-Zhou-smu/SWE-RPG-Bench (Dateiliste gelesen, keine Lizenzdatei)
- [plan-to-action] https://arxiv.org/abs/2604.12147
- [ambig-swe] https://arxiv.org/abs/2502.13069
- [ambig-swe-repo] https://github.com/sani903/InteractiveSWEAgents (LICENSE: MIT)
- [locagent] https://arxiv.org/abs/2503.09089, https://github.com/gersteinlab/LocAgent (LICENSE: Apache-2.0)
- [locbench-hf] https://huggingface.co/datasets/czlll/Loc-Bench_V0.1 (Tag `license:apache-2.0`), https://huggingface.co/datasets/czlll/Loc-Bench_V1 (kein Lizenz-Tag)
- [swebench-license] https://raw.githubusercontent.com/SWE-bench/SWE-bench/main/LICENSE (MIT); Hugging-Face-Datensätze `princeton-nlp/SWE-bench_Verified`, `ScaleAI/SWE-bench_Pro` ohne Lizenz-Tag
- [swebench-pro] siehe README der Architektur (GESAGT)
- [devbench] https://arxiv.org/abs/2403.08604, https://raw.githubusercontent.com/open-compass/DevBench/main/LICENSE (Apache-2.0)
- [desbench] https://www.arxiv.org/pdf/2602.13611 (GESAGT, Suchauszug)
- [rigorbench] https://arxiv.org/abs/2606.22678
