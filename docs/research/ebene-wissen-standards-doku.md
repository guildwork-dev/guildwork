<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
> Research note, dated 2026-11-01, not binding. Kept in German as written (ADR-53); the binding documents are docs/architecture and docs/design.

# Recherche: Ebenen Wissensbasis, Team-Standards und Learnings, Dokumentation

**Dated, not binding.** Datierte Recherche, Stand 2026-10-31, nicht verbindlich und nicht übersetzt; verbindlich ist die Plattform-Doku ([docs/architektur/](../architecture/README.md)).

Stand 2026-10-31. Auftrag: Owner-Vorgaben dritte Runde (jeder Service auf Weltstandard seines Fachgebiets, Open Source, selbst hostbar). Einstufungen wie in `docs/architektur/README.md` Abschnitt 6: **BELEGT** (Primärquelle gelesen), **GESAGT** (Herstelleraussage, Marketing, Drittbericht), **ABGELEITET** (eigener Schluss), **VERMUTET**. Alle Webquellen abgerufen am 2026-10-31. Das Abrufwerkzeug liefert eine Zusammenfassung durch ein kleines Modell; Zitate sind deshalb sinngemäß. Wo "BELEGT" steht, war es die Herstellerdoku, das Repo oder der Datensatz selbst.

Kürzel für die Architektur: [A01] bis [A09] = `docs/architektur/01-plugin-schnittstellen.md` bis `09-entscheidungen.md`; die Schichten L0 bis L5 der Wissensbasis stehen in [A02] Abschnitt 6.

---

## 1. Urteil (Kurzfassung)

1. **Es gibt nicht einen Weltstandard, sondern fünf Teilebenen mit je eigener Spitzengruppe** (ABGELEITET):
   - **Codebase-Verständnis und Retrieval für Agenten:** Sourcegraph (Zoekt, Deep Search), Augment Context Engine, Cursor (Semantic Search plus grep). Unabhängige Produktvergleiche fehlen; die einzige unabhängige Messung des Kontextabrufs (ContextBench, 2026) vergleicht Agenten-Gerüste und Modelle, nicht Produkte.
   - **Repo-Q&A und Wiki:** Devin DeepWiki und Ask Devin, Sourcegraph Deep Search; Qodo mit DeepCodeBench als offenem Messsatz.
   - **Team-Standards (Regeln, Leitlinien):** Der Standard für das Dateiformat ist **AGENTS.md** (Linux Foundation, Agentic AI Foundation). Beim Ableiten aus Review-Historie führt Qodo Rule Miner, bei der Messung je Regel Bugbot und Greptile (Akzeptanz- bzw. Addressed-Rate je Regel).
   - **Learnings und Memory:** GitHub Copilot Memory ist das am strengsten dokumentierte Modell (Zitate je Fakt, Prüfung gegen den Branch vor Nutzung, Abstimmung, Ablauf).
   - **Dokumentation:** Mintlify (Doku-Plattform mit Autopilot aus gemergten PRs), Swimm (code-gekoppelte Doku mit Auto-sync), DeepWiki (generiertes Wiki), Dosu. Ein offener Messsatz existiert nur für generierte Repo-Doku (CodeWikiBench) und Docstrings (DocAgent).
2. **Unsere Architektur deckt den Kern gut ab** (Schichten L0 bis L5, Zitatprüfung nach Copilot-Prinzip, Regeln vom Basis-SHA, Rule-Miner-Muster). **Die Lücken liegen bei den Produktfunktionen um den Kern herum:** Lesen fremder Regelformate, Messung je Regel und je Learning, Lebenszyklus von Learnings (Scope, Freigabeverzug, Abstimmung, Ablauf, Import und Export, Secret-Redaktion), Q&A und Wiki als Nutzerfläche, und eine **Doku-Ebene fehlt ganz** (kein Service für Doku-Drift oder Doku-PRs).
3. **Gate B ist für diese Ebenen jetzt messbar** und nicht mehr nur "offen" (Backlog M5): ContextBench (Kontextabruf, Code Apache-2.0), SWE-QA (Apache-2.0) und DeepCodeBench (Apache-2.0) für Repo-Q&A, CoIR und RepoQA für die Retrieval-Bausteine, CodeWikiBench für generierte Doku. Wegen Open Source (Owner-Vorgabe 2) müssen die Pflicht-Testsätze öffentlich und lizenzrein sein; die internen Sätze K2 und R3 werden zur optionalen "eigene Repos"-Messung.
4. **Wichtigster Technikbefund 2026:** Mehr Retrieval-Gerüst bringt nicht automatisch mehr (ContextBench: komplexere Gerüste nicht durchgängig besser als ein einfacher Agent, Modelle sammeln breit und unpräzise; BELEGT im Paper laut Zusammenfassung). Cursor misst grep plus semantische Suche als beste Kombination (GESAGT). Das bestätigt das ADR-Prinzip "KB nur bei Eval-Gewinn".

---

## 2. Befunde mit Quellen

### 2.1 Spitzengruppe je Teilebene und warum

**a) Codebase-Verständnis und Retrieval**

| Anbieter | Was belegt ist | Einstufung, Quelle |
|---|---|---|
| Sourcegraph Deep Search | Agentische Schleife über Sourcegraphs Code-Suche und Code-Navigation; Analyse per kleinen Lua-Skripten in einer Sandbox ohne Netz, System- und allgemeinen Dateizugriff; nur lesend mit bestehenden Repo-Rechten; Scope über Search Contexts; Verbrauch über Credits, Kontingente je Nutzer einstellbar (Beispiel "60 Deep Search per hour"); API und MCP-Server; nicht für BYOK-Kunden; für erschöpfende Fragen weiter klassische Code-Suche, weil Deep Search nur eine Stichprobe der Treffer nutzt | BELEGT [sg-deepsearch] |
| Sourcegraph Zoekt | Trigramm-Index für Teilstring- und Regex-Suche über viele Repos, Symbol-Rangfolge über Universal ctags, Apache-2.0, seit 2017 von Sourcegraph gepflegt | BELEGT [zoekt] |
| Sourcegraph und Amp | Amp wurde am 2025-12-02 aus Sourcegraph ausgegründet; Sourcegraph konzentriert sich auf Code-Suche und Code-Verständnis, Cody nur noch Enterprise | GESAGT [amp-spinout] (Herstellermeldung plus Drittberichte, nicht selbst gelesen) |
| Augment Context Engine | Semantischer Echtzeit-Index über Code, Commits, Doku, Tickets; seit 2026-02-06 als MCP-Server für beliebige Agenten (lokal über Auggie CLI oder entfernt mit Cross-Repo); Gewinne "70 %+" bzw. "30 bis 80 %" über Claude Code, Cursor, Codex auf 300 Elasticsearch-PRs | Funktionen GESAGT [augment-ce], [augment-mcp]; Zahlen GESAGT, Eigenmessung des Herstellers |
| Cursor Semantic Search | Eigenes Embedding-Modell, trainiert aus Agenten-Sitzungen; laut Cursor im Mittel 12,5 % höhere Antwortgenauigkeit (6,5 bis 23,5 % je Modell) im internen "Cursor Context Benchmark"; Online-A/B: Code-Retention plus 0,3 %, in Repos ab 1.000 Dateien plus 2,6 %; grep plus semantische Suche zusammen am besten | GESAGT [cursor-semsearch] |
| Greptile | Vorab-Index beim Signup: Docstrings je Funktion, Klasse, Datei, Verzeichnis per LLM, dann Graph (Aufrufe, Importe, Abhängigkeiten), Docstrings eingebettet | BELEGT Ablauf [greptile-graph]; Einbettung der Docstrings GESAGT (Hatchet-Fallstudie) |

Warum diese Gruppe (ABGELEITET): Sourcegraph hat die längste Produktgeschichte bei Code-Suche über sehr viele Repos und legt den Kern (Zoekt, SCIP) offen; Augment und Cursor sind die einzigen, die 2025/2026 Messwerte zum Nutzen ihres Retrievals für Agenten veröffentlicht haben (alle selbst gemessen). Eine **unabhängige** Rangliste der Produkte gibt es nicht (ungeprüft, ob eine existiert; in der Suche nicht gefunden).

**b) Repo-Q&A und Wiki**

| Anbieter | Was belegt ist | Einstufung, Quelle |
|---|---|---|
| Devin DeepWiki | Wiki automatisch beim Verbinden der Repos, mit Architekturdiagrammen, Quell-Links und Zusammenfassungen; Steuerung über `.devin/wiki.json` (`repo_notes`, `pages` mit `title`, `purpose`, optional `parent`, `page_notes`); mit Datei werden genau die definierten Seiten erzeugt; höchstens 30 Seiten (80 Enterprise), 100 Notizen, 10.000 Zeichen je Notiz; Aufwandstufen low (kostenlos), medium etwa 5 bis 10 ACU, high etwa 20 bis 40 ACU je Wiki | BELEGT [devin-wiki] |
| DeepWiki MCP | öffentlich, kostenlos, ohne Anmeldung, nur öffentliche Repos; Tools `read_wiki_structure`, `read_wiki_contents`, `ask_question`; private Repos nur über Devin-MCP mit API-Key | BELEGT [deepwiki-mcp] |
| Devin Knowledge | Wissenseinträge mit Pflicht-Auslöser (Trigger-Beschreibung), Abruf nur bei passender Arbeit, nicht alles am Start; Bindung an kein, ein oder alle Repos; Devin schlägt Einträge aus Chat-Feedback vor, Mensch bearbeitet oder verwirft | BELEGT [devin-knowledge] |
| Sourcegraph Deep Search | siehe a) | BELEGT |
| Qodo Deep Research | auf DeepCodeBench laut Qodo Fact Recall etwa 0,76 bis 0,77 gegenüber codex-cli 0,72 bis 0,76, claude-code 0,59 bis 0,68, gemini-cli 0,41 bis 0,48 | GESAGT, Eigenmessung des Herstellers [qodo-dcb] |

Unabhängiger Vergleich generierter Repo-Doku: CodeWiki (MIT) erreicht laut seinen Autoren auf CodeWikiBench 68,79 % gegenüber DeepWiki 64,06 % (GESAGT, Autoren des Konkurrenzprodukts [codewiki]).

**c) Team-Standards (Regeln und Leitlinien)**

| Anbieter | Was belegt ist | Einstufung, Quelle |
|---|---|---|
| AGENTS.md | offenes Markdown-Format, getragen von der Agentic AI Foundation unter der Linux Foundation; laut Seite über 60.000 Open-Source-Projekte; verschachtelt, "the closest one takes precedence", Chat-Prompt schlägt alles; unterstützt von Codex, Jules, Gemini CLI, Devin, Windsurf, Copilot coding agent, Cursor, Amp, Factory, Aider, goose, opencode, Augment und weiteren | BELEGT Format und Träger [agentsmd]; Zahl 60.000 GESAGT |
| Qodo Rule Miner | nur angenommene Kommentare mit Code-Änderung; Gewicht nach Code-Ownership; Wiederholung über PRs oder ein Kommentar eines starken Owners; Clusterung nach Pfad; Abschwächung bei abgelehnten Vorschlägen; Dedupe; Fenster etwa 1.000 zuletzt gemergte PRs; erster Lauf bis 10 Regeln je Repo, **danach alle zwei Wochen** bis 5; **Auto-Freigabe Standard für Orgs seit 2026-09-01**, ältere Orgs mit Freigabe-Tab; jede Regel mit Quelle (PR oder Anzahl PRs) | BELEGT [qodo-miner]; aktualisiert [A02] Abschnitt 7 |
| Cursor Bugbot Rules | Reihenfolge Team, Projekt-BUGBOT.md (aufwärts ab geänderter Datei), learned, manual; `.cursor/rules/*.mdc` gilt für Bugbot nicht; Learned Rules entstehen beim Merge oder Schließen eines PR (zählt wie ein Review) oder per Backfill; `@cursor remember`; 30.000 Zeichen je Regel, 100.000 je Review; **`bugbot run verbose=true` zeigt die benutzten, gekürzten und weggelassenen Regeln**; je Regel Kennzahlen Issues found, PRs reviewed, Accepted issues, Acceptance rate | BELEGT [cursor-bugbot] |
| Greptile Custom Standards | Dashboard-Regeln (Org, Team), `.greptile/` mit `config.json` (Regel, `scope`-Globs als Array, `severity`, `id` zum Abschalten geerbter Regeln), `rules.md`, `files.json` (Referenzdokumente); Kaskade je Verzeichnis; Regelvorschläge nach etwa 10 PRs; **je Regel "Usage" und "Addressed Rate"** | BELEGT [greptile-std] |
| Cursor Rules (Agent) | vier Anwendungsarten: Always, Globs, "Apply Intelligently" über `description`, manuell per @-Erwähnung; Team, Projekt, User mit Vorrang Team vor Projekt vor User; Regeln unter 500 Zeilen empfohlen | BELEGT [cursor-rules] |
| Copilot Custom Instructions | persönlich, Repo-weit `.github/copilot-instructions.md`, pfadbezogen `.github/instructions/*.instructions.md`, Agenten-Dateien `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, Org-Anweisungen (Business, Enterprise); **Code Review liest Repo- und Agenten-Anweisungen und Skills vom Head-Branch** | BELEGT [copilot-instr]; bestätigt [A04] Abschnitt 2 "Gegenbeispiele" jetzt aus Primärquelle |

**d) Learnings und Memory**

| Anbieter | Was belegt ist | Einstufung, Quelle |
|---|---|---|
| Copilot Memory | Repo-Fakten (mit Code-Zitat) und Nutzer-Präferenzen getrennt; Zitate vor Nutzung gegen den aktuellen Branch geprüft; internes Abstimmen hoch und runter, unter einer Schwelle nicht mehr genutzt und später gelöscht; Ablauf Standard 90 Tage ohne Bestätigung, Upvote setzt die Uhr zurück, Abruf nicht; Admin 7 bis 180 Tage; nicht über Repos gepoolt, nicht in Forks; Code Review und Autofix nutzen nur Repo-Fakten; im CLI dürfen nur Root-Agenten schreiben, Subagenten nur lesen; Secrets und Modell-Steuertoken abgelehnt; Memory im Kontext zählt gegen Tokens | BELEGT [copilot-memory]; [A02] Abschnitt 6 hat Zitat und Ablauf, nicht Abstimmung, Root-only-Schreiben, Trennung Repo/Nutzer |
| Bugbot, Greptile | siehe c) | BELEGT |
| Devin Knowledge | siehe b) | BELEGT |

**e) Dokumentation**

| Anbieter | Was belegt ist | Einstufung, Quelle |
|---|---|---|
| Mintlify Autopilot | beobachtet Default-Branches ausgewählter Repos; Check "Mintlify Autopilot" auf offenen PRs; nach Merge ein Vorschlag im Dashboard mit Grund; Agent entwirft daraus einen Doku-PR; auch direkt per `@mintlify` mit PR-Link, Slack, API; nur Custom-Plan | GESAGT: aus PRs im Repo `mintlify/docs`, nicht von der veröffentlichten Seite gelesen [mintlify]; Umbenennung in "agent suggestions" möglich (ungeprüft) |
| Swimm | code-gekoppelte Doku: Snippets, Smart Tokens, Pfade in Markdown im Repo; Auto-sync gleicht sie bei Code-Änderung ab, Mensch nimmt an; "Outdated" bei nicht auflösbarem Element; CI-Prüfung auf kaputte Doku je PR; GitHub-App kann Auto-sync-Commits in den offenen PR legen; Auto-sync "patentiert" (Patent nicht identifiziert) | GESAGT [swimm] (Herstellerblog, Doku-Auszüge über Suche) |
| Dosu | Wissensbasis aus Code, PRs, Issues, Slack, bestehender Doku; Doku-Updates bei PR-Merge; MCP-Server; Issue-Labeling und Dedupe; Self-Host nur Enterprise | GESAGT, nur Drittverzeichnisse [dosu]; ungeprüft an Herstellerdoku |
| GitHub Agentic Workflows | Vorlage `docs-updater` erkennt Drift zwischen Code und Doku und schlägt PRs vor | GESAGT [gh-aw-docs] |
| DeepWiki, CodeWiki | generierte Repo-Doku, siehe b) | BELEGT bzw. GESAGT |

### 2.2 Fähigkeits-Checkliste des Standards

Spalte "bei uns": Fundstelle in `docs/architektur`. "ja" heißt beschrieben, nicht gebaut.

| # | Fähigkeit | wer sie hat | Beleg | bei uns |
|---|---|---|---|---|
| 1 | Struktur-Graph (Symbole, Kanten, Impact) | Greptile | [greptile-graph] | ja: [A02] 6 L1, [A01] 9 `symbolContext`, `impact` |
| 2 | Hybride Suche (lexikalisch plus Vektor) | Cursor (grep plus semantisch), Sourcegraph (Zoekt plus Deep Search) | [cursor-semsearch], [zoekt] | ja: `search` BM25 plus Vektor plus RRF [A01] 9 |
| 3 | Regex- und Trigramm-Suche über viele Repos mit Symbol-Rang | Sourcegraph Zoekt | [zoekt] | teilweise: FTS in L3, kein Trigramm/Regex-Index über Repos |
| 4 | LLM-Zusammenfassungen je Symbol, Datei, Modul | Greptile | [greptile-graph] | ja: L2 [A02] 6 |
| 5 | Agentische Tiefensuche als Nutzerfläche (Frage, mehrstufige Suche, Antwort mit Quellen, Folgefragen) | Sourcegraph Deep Search, Ask Devin, Qodo | [sg-deepsearch], [devin-wiki] | teilweise: `@agent ask` über Indexer [A02] 8, ohne Ablauf, Schema, DoD |
| 6 | Generiertes Repo-Wiki mit Diagrammen, steuerbar per Datei | DeepWiki | [devin-wiki] | nein (L2 sind Zusammenfassungen, keine Seiten) |
| 7 | Kontext als MCP-Server für fremde Agenten | Augment, Sourcegraph, DeepWiki, Dosu | [augment-mcp], [sg-deepsearch], [deepwiki-mcp] | teilweise: Plattform-MCP nur für eigene Work-Items mit Item-Token [A01], [README] |
| 8 | Cross-Repo-Kontext | Augment remote, Sourcegraph | [augment-mcp] | teilweise: `CROSS_REPO`-Fähigkeit, nur mit Freigabe [A05] |
| 11 | Externe Wissensquellen per MCP (Confluence, Notion, Doku) | Dosu | [dosu] | nein |
| 12 | Fremde Regeldateien automatisch lesen (AGENTS.md, CLAUDE.md, `.cursor/rules`, Copilot-Instructions, GEMINI.md, `.windsurfrules`, `.clinerules`, SKILL.md) | Copilot, Cursor | [copilot-instr] | teilweise: AGENTS.md, REVIEW.md, CLAUDE.md, `.agents/rules/` [A04] 2; Rest fehlt |
| 13 | Geltung je Verzeichnis, nächste Datei gewinnt | AGENTS.md, Bugbot, Greptile | [agentsmd], [cursor-bugbot], [greptile-std] | teilweise: Globs je Regel, Verzeichnis-Kaskade nicht festgelegt |
| 14 | Regel-Anwendungsarten (immer, Glob, nach Beschreibung, manuell) | Cursor | [cursor-rules] | teilweise: Glob ja, Rest nein |
| 15 | Geerbte Regel per ID abschalten | Greptile | [greptile-std] | nein |
| 16 | Regel- und Leitlinien-Budget mit sichtbarer Kürzung | Bugbot (30.000/100.000 Zeichen, `verbose=true`) | [cursor-bugbot] | nein |
| 17 | Org- und Team-Regeln zentral | Bugbot Team Rules, Greptile Dashboard, Copilot Org-Anweisungen, Cursor Team Rules | [cursor-bugbot], [greptile-std], [copilot-instr] | teilweise: Org-Konfiguration [A04], Regeln nur im Repo |
| 18 | Konfiguration und Regeln vom Basis-SHA | Bugbot | [cursor-bugbot] | ja: [A04] 2 (Copilot liest vom Head, BELEGT [copilot-instr]) |
| 19 | Regeln aus Review-Historie ableiten | Qodo Rule Miner, Bugbot Learned Rules, Greptile Vorschläge | [qodo-miner], [cursor-bugbot], [greptile-std] | ja: Standards-Service [A02] 7 |
| 20 | Kennzahlen je Regel (Nutzung, Akzeptanz, Addressed Rate) | Bugbot, Greptile | [cursor-bugbot], [greptile-std] | nein (nur Annahmequote der Regel-PRs) |
| 21 | Automatisches Abschwächen oder Abschalten schlechter Regeln | Qodo (Decay), Bugbot (auto enable/disable) | [qodo-miner], [cursor-bugbot] | teilweise: Rücknahme-PR [A02] 7 |
| 22 | Learnings aus Chat | Bugbot `@cursor remember`, Devin, Copilot | [cursor-bugbot] | ja: [A02] 3 "Learning-Kandidat", nur Schreibberechtigte |
| 26 | Zitat je Learning, Prüfung vor Nutzung | Copilot Memory | [copilot-memory] | ja: [A01] 9, [A02] 6 |
| 27 | Abstimmen, Ablauf, Verlängerung bei Bestätigung | Copilot Memory | [copilot-memory] | teilweise: `invalid_at`, `last_verified`; kein Ablauf, keine Abstimmung |
| 28 | Repo-Fakten getrennt von Nutzer-Präferenzen | Copilot Memory | [copilot-memory] | nein |
| 29 | Secret-Redaktion vor Speicherung und Embedding | Copilot | [copilot-memory] | teilweise: gitleaks im Self-Check [A02] 2; für Learnings nicht festgelegt |
| 32 | Wissenseinträge mit Auslöser statt Dauer-Kontext | Devin Knowledge, Cursor "Apply Intelligently" | [devin-knowledge], [cursor-rules] | nein |
| 34 | Doku-Drift-Check auf PRs | Mintlify Autopilot, Swimm CI | [mintlify], [swimm] | nein |
| 35 | Doku-PR aus gemergtem Code-PR | Mintlify, Dosu, gh-aw | [mintlify], [dosu], [gh-aw-docs] | nein |
| 36 | Code-gekoppelte Doku (Token, Snippets automatisch nachgeführt) | Swimm | [swimm] | nein |
| 37 | Docstrings erzeugen | DocAgent | [docagent] | nein |

Die Nummern 9, 10, 23, 24, 25, 30, 31 und 33 entfallen in dieser Fassung: sie stützten sich nur auf Herstellerdoku, deren Auswertung nach [10](../architecture/10-standards-per-layer.md) Abschnitt 16 nicht weitergeführt wird.

### 2.3 Messung: Benchmarks, Lizenzen, Online-Metriken

**Öffentliche Testsätze** (Lizenz nur, wo selbst auf Repo oder Datensatzkarte gesehen; sonst "ungeprüft"):

| Satz | misst | Umfang | Lizenz | Einstufung, Quelle |
|---|---|---|---|---|
| ContextBench (2026) | Kontextabruf von Coding-Agenten gegen menschlich annotierten Gold-Kontext: Recall, Präzision, Effizienz auf Datei-, Symbol-, Span- und Edit-Ebene | 1.136 Aufgaben aus 66 Repos in 8 Sprachen, `contextbench_verified` 500 | Code Apache-2.0; Datensatzkarte ohne Lizenz (ungeprüft, also offen) | BELEGT [contextbench-gh], [contextbench-hf]; Befunde aus dem Paper [contextbench-paper] laut Zusammenfassung |
| SWE-QA (ACL 2026 Findings) | Repo-Q&A über mehrere Dateien, LLM-Richter | v2: 720 Fragen, 15 Python-Repos, 48 je Repo | Apache-2.0 (Repo und Datensatz) | BELEGT [sweqa-gh], [sweqa-hf] |
| DeepCodeBench (Qodo) | Repo-Q&A aus echten PRs, Bewertung "Fact Recall" je Fakt | 1.144 Paare laut Qodo | Apache-2.0 (Datensatzkarte) | Lizenz BELEGT [qodo-dcb-hf]; Umfang, Methode, Werte GESAGT [qodo-dcb] |
| CoIR (ACL 2025) | Code-Retrieval-Modelle, NDCG@10, MTEB-kompatibel | 10 Datensätze, 8 Aufgaben, 7 Domänen, etwa 2 Mio. Dokumente | Code Apache-2.0; Daten je Datensatz verschieden (ungeprüft) | BELEGT [coir] |
| RepoQA (EvalPlus) | Langkontext: Funktion aus Beschreibung in Repo-Kontext finden ("Search Needle Function") | 500 Tests (5 Sprachen, 10 Repos, 10 Nadeln) | Apache-2.0 | BELEGT [repoqa] |
| CodeRAG-Bench | Nutzen von Retrieval für Code-Erzeugung, inkl. RepoEval und SWE-bench Lite; NDCG, MRR, Recall | mehrere Aufgaben | ungeprüft (keine Lizenz auf der Repo-Seite) | BELEGT Aufbau [coderag] |
| Loc-Bench, LocAgent (ACL 2025) | Lokalisierung der zu ändernden Dateien, Module, Funktionen (Acc@k), auch auf SWE-bench Lite | Loc-Bench V1 560 Fälle | V0.1 Apache-2.0 laut Karte; V1 und Code ungeprüft | GESAGT über Suche [locagent]; Werte widersprüchlich zwischen Drittberichten, nicht zitieren |
| CodeWikiBench | generierte Repo-Doku gegen Rubriken aus der offiziellen Projekt-Doku, Richter-Agenten | 21 Repos, 7 Sprachen | CodeWiki MIT; Lizenz des Benchmarks ungeprüft | GESAGT [codewiki] |
| DocAgent (Meta, ACL 2025 Demo) | Docstrings: Vollständigkeit (deterministisch), Hilfreichkeit (Richter), Wahrhaftigkeit (genannte Entitäten existieren im Abhängigkeitsgraphen) | 366 Komponenten, 9 Python-Repos | MIT laut Drittquelle, ungeprüft | GESAGT [docagent] |

**Embedding-Modelle für lokalen Betrieb** (für O7 und Open Source wichtig; Werte sind Herstellerangaben):

| Modell | Lizenz | Wert | Einstufung |
|---|---|---|---|
| nomic-embed-code (7B) | Apache-2.0, Gewichte, Trainingsdaten und Eval-Code offen | CodeSearchNet je Sprache, kein CoIR-Mittel gefunden | GESAGT [nomic-code] |
| CodeRankEmbed (137M) | MIT | CoIR 60,1 (NDCG@10) | GESAGT [nomic-code] |
| Qodo-Embed-1-1.5B | OpenRAIL++-M | CoIR 68,53 (Drittbericht nennt 70,06) | GESAGT [qodo-embed] |
| jina-code-embeddings 0.5B, 1.5B | CC-BY-NC-4.0, nicht kommerziell | CoIR 73,94 (0.5B) | GESAGT [jina-code]; für ein Open-Source-Produkt mit kommerziellen Nutzern ungeeignet (ABGELEITET) |

**Online-Metriken der Spitzengruppe** (für [A07] Abschnitt 6):
- je Regel: Nutzung, gefundene und akzeptierte Befunde, Akzeptanzquote (Bugbot), Addressed Rate (Greptile), BELEGT.
- je Learning: Abstimmung und Ablauf (Copilot), BELEGT.
- Retrieval online: Code-Retention und unzufriedene Folgeanfragen im A/B (Cursor), GESAGT.
- Doku: Anteil gemergter PRs mit Doku-Vorschlag, angenommene Doku-PRs (ABGELEITET aus Mintlify-Ablauf).

### 2.4 Was offengelegt ist und übernommen werden kann, was proprietär bleibt

| Übernehmbar | Quelle | Art |
|---|---|---|
| Zoekt als Trigramm-/Regex-Index mit ctags-Rang | [zoekt], Apache-2.0 | Code |
| Deep-Search-Muster: agentische Schleife nur über Lese-Tools, Analyse-Skripte in netzloser Sandbox, Kontingent je Nutzer, Stichproben-Hinweis | [sg-deepsearch] | Idee |
| Copilot-Memory-Lebenszyklus: Zitat, Prüfung vor Nutzung, Abstimmung, Ablauf mit Reset bei Bestätigung, Root-only-Schreiben, Repo und Nutzer getrennt | [copilot-memory] | Idee |
| Liste fremder Regeldateien und Verzeichnis-Geltung | [agentsmd], [copilot-instr] | Idee (Dateinamen sind Fakten, frei) |
| Regel-Analytik je Regel, `verbose`-Ausgabe der benutzten Regeln | [cursor-bugbot], [greptile-std] | Idee |
| Rule-Miner-Parameter (Fenster 1.000 PRs, 10 dann 5, zwei Wochen, Ownership-Gewicht, Decay) | [qodo-miner] | Idee |
| DeepWiki-Steuerdatei (Seiten mit `purpose`, Notizen, Grenzen) | [devin-wiki] | Idee |
| Devin-Knowledge-Auslöser | [devin-knowledge] | Idee |
| CodeWiki (hierarchische Zerlegung, Kaskade), DocAgent (topologische Reihenfolge, Wahrhaftigkeit über Graph) | [codewiki] MIT, [docagent] MIT ungeprüft | Code bzw. Idee bis Lizenz geprüft |
| Swimm-Prinzip: Code-Referenzen in Doku als prüfbare Token, CI-Check "Doku kaputt" | [swimm] | Idee; Auto-sync-Algorithmus laut Hersteller patentiert, nicht nachbauen ohne Prüfung (VERMUTET Risiko) |
| Mintlify-Ablauf: Check auf PR, Vorschlag nach Merge, Agent-Entwurf als Doku-PR | [mintlify] | Idee |

**Proprietär bleibt:** Cursors Embedding-Modell und Trainingsdaten aus Agentensitzungen [cursor-semsearch]; Augments Index und Ranking [augment-ce]; Greptiles Graph-Index und Filter; Deep-Search-Modellwahl ("frontier and specialized models selected by Sourcegraph") [sg-deepsearch]; DeepWiki-Erzeugung; Bugbots Kriterien für automatisches An- und Abschalten gelernter Regeln (nicht dokumentiert) [cursor-bugbot]; Copilot-Schwellen für Abstimmungen [copilot-memory]; Swimms Auto-sync-Algorithmus [swimm].

### 2.5 Korrekturen und Aktualisierungen an Vorarbeiten

| Stelle | bisher | jetzt | Quelle |
|---|---|---|---|
| [A02] Abschnitt 7 Messlatte Qodo | "Erstlauf bis 10 Regeln je Repo, danach bis 5 je Lauf" | dazu: Lauf alle zwei Wochen, Fenster etwa 1.000 gemergte PRs, Auto-Freigabe ist seit 2026-09-01 Standard für neue Orgs | [qodo-miner] BELEGT |
| [A04] Abschnitt 2 | Gegenbeispiele für das Lesen vom Head, ohne Primärbeleg | für Copilot Code Review jetzt aus Primärdoku belegt (Head-Branch für Repo-, Agenten-Anweisungen und Skills) | [copilot-instr] BELEGT |
| Bugbot, frühere Annahme aus einem Herstellerblog | Learned Rules "aus Reaktionen und übersehenen Bugs" (GESAGT aus Blog) | Doku nennt als Quelle GitHub-Aktivität beim Merge oder Schließen und Backfill; Reaktionen als Signal nicht dokumentiert; Abschalten des Lernens schaltet auch manuelle Regeln ab (außer Azure DevOps) | [cursor-bugbot] BELEGT |
| frühere Annahme "Trend: agentische Suche statt Embeddings" | GESAGT | differenzieren: Cursor misst grep plus semantisch als beste Kombination (GESAGT), ContextBench zeigt, dass mehr Gerüst nicht automatisch besser abruft | [cursor-semsearch], [contextbench-paper] |
| [A07] 3.5, Backlog M5 | Gate B Wissensbasis "Zitat-Gültigkeit 100 %", Standards "Annahmequote" | durch extern vergleichbare Sätze ersetzbar, siehe Abschnitt 3 | diese Recherche |

### 2.6 Lücken in unserer Architektur (Zusammenfassung von 2.2)

Gewichtet nach Wirkung auf das Niveau (ABGELEITET):
1. **Doku-Ebene fehlt** (Zeilen 34 bis 37): kein Service für Doku-Drift, Doku-PRs, Wiki oder Docstrings.
2. **Fremde Regelformate werden nicht gelesen** (Zeilen 12 bis 15): Für ein öffentliches Produkt ist das der billigste Weg zu "funktioniert ab dem ersten PR", weil Nutzer ihre AGENTS.md, CLAUDE.md, Cursor- und Copilot-Dateien schon haben.
3. **Messung je Regel und je Learning fehlt** (Zeile 20): ohne sie kein Decay, keine Rücknahme mit Beleg, kein Gate B.
4. **Learnings-Lebenszyklus unvollständig** (Zeilen 26 bis 29): Ablauf mit Bestätigung, Trennung Repo und Nutzer, Secret-Redaktion.
5. **Q&A und Wiki als Nutzerfläche** (Zeilen 5, 6): `@agent ask` ist genannt, aber ohne Ablauf, Schema und DoD.
6. **Kontext für fremde Agenten per MCP** (Zeile 7): Augment, Sourcegraph, DeepWiki und Dosu bieten das; bei uns ist das Plattform-MCP an Work-Items gebunden.
7. **Regel-Budget und Transparenz** (Zeile 16): sichtbar machen, welche Regeln in einen Lauf gingen und welche gekürzt wurden.
8. **Lexikalischer Index über viele Repos** (Zeile 3): für große Installationen; Zoekt ist Apache-2.0.

---

## 3. Folgen für unsere Architektur

Alle Punkte sind Vorschläge für die nächste Architekturrunde (ABGELEITET), nicht umgesetzt.

| Datei | Abschnitt | neu oder anders |
|---|---|---|
| `docs/architektur/README.md` | 2 Leitidee, Glossar | Services von 7 auf 8: neuer Service `docs`. Glossar: **Leitlinie** (fremde oder eigene Regeldatei im Repo, gelesen am Basis-SHA), **Learning** (Fakt mit Zitat, Scope, Ablauf), **Regel-Kennzahlen**. Titel mit Firmennamen betrifft Owner-Vorgabe 2 und gehört der Recherche zu Open Source (hier nur Hinweis). |
| `02-services.md` | 6 Indexer, Messlatte | Zeilen ergänzen: Sourcegraph Deep Search und Zoekt, Augment Context Engine, Cursor Semantic Search, DeepWiki `wiki.json`, Devin Knowledge mit Auslösern (Quellen aus 2.1). |
| `02-services.md` | 6 Indexer, Ausgang und Stufen | **Ask-Ablauf** festlegen: `AskRequest { repo|org, question, scope }` zu `AskAnswer { answer, citations[], confidence, searchedQueries[] }`; Stufen: agentische Suche nur lesend über `kb.*` plus grep, Zitatprüfung wie Planner Stufe 5, Antwort ohne gültiges Zitat wird nicht ausgegeben; Hinweis "Stichprobe, nicht erschöpfend" wie bei Deep Search. MCP-Tool `kb.ask`. DoD siehe 07. |
| `02-services.md` | 6 Indexer, Qualitätsmechanik | Learnings-Lebenszyklus: Scope `repo | org | auto` (auto: öffentliche Repos nur eigene), PR-gebunden bis Merge, Freigabeverzug `approval_delay_days` (Start 0), Ablauf `expiry_days` (Start 90, Bereich 7 bis 180, Bezug Copilot) mit Verlängerung nur bei Bestätigung, Abstimmung aus Befund-Reaktionen, Trennung Repo-Fakten und Nutzer-Präferenzen (Reviewer nutzt nur Repo-Fakten), Secret-Redaktion vor Speicherung und Embedding, Kennzahlen `uses`, `last_used`, `never_used`. Import und Export (CSV/JSON). |
| `02-services.md` | 7 Standards | Messlatte aktualisieren (2.5). **Leitlinien-Lader** als Teil des Standards-Service (läuft auch bei `mode: off`, wie heute "Regeldateien von Hand"): liest am Basis-SHA AGENTS.md, AGENT.md, CLAUDE.md, `.claude/rules/**` (mit `paths`), GEMINI.md, `.cursorrules`, `.cursor/rules/*.mdc` (Frontmatter `globs`, `alwaysApply`, `description`), `.github/copilot-instructions.md`, `.github/instructions/*.instructions.md` (`applyTo`), `.windsurfrules`, `.clinerules/*`, `.greptile/`, `.cursor/BUGBOT.md`; Geltung ab eigenem Verzeichnis abwärts, nächste Datei gewinnt; Regel-IDs mit Abschalten geerbter Regeln; Budget je Lauf mit Bericht der gekürzten Quellen im Run Record und per `@agent review verbose`. **Regel-Kennzahlen** je `rule_id`: Befunde, PRs, angenommen, Addressed Rate; Decay und Rücknahme-PR nach Schwelle. Regel-PRs im AGENTS.md-kompatiblen Format. Lauf alle zwei Wochen als Startwert (Bezug Qodo), statt wöchentlich. |
| `02-services.md` | neu 8 `docs` | Zweck: Doku aktuell halten. Stufen: (1) Drift-Check auf PRs als Check `docs-drift` (`neutral` oder `success`, nie blockierend ohne Konfig), (2) nach Merge Doku-Vorschlag und optional Doku-PR (`propose_change` auf `docs_paths`), (3) Wiki-Seiten aus L2 nach Steuerdatei `.agents/wiki.yaml` (Seiten mit Zweck, Grenzen wie DeepWiki als Startwert), (4) optional Docstrings nach DocAgent-Prinzip (topologische Reihenfolge, Wahrhaftigkeit über L1). Code-Referenzen in Doku als prüfbare Zitate (Swimm-Prinzip, eigene Umsetzung). Erlaubte Schreibwünsche: `propose_change` (nur `docs_paths` und Docstrings), `propose_check`, `propose_comment`. Messlatte und DoD siehe 07. Standard `off`. |
| `02-services.md` | 0 Tabelle Schreibwünsche, 8 Kombinationen | Zeile `docs`; Kombination "Doku-Assistent: docs (+ indexer)". |
| `01-plugin-schnittstellen.md` | 9 KnowledgeStore | `KbCap` ergänzen um `LEXICAL_MULTI_REPO` (Zoekt-Implementierung optional), `RULE_STATS`, `LEARNING_LIFECYCLE`. Methoden: `ruleStats(repo, ruleId)`, `voteLearning(id, +1|-1, origin)`, `expireLearnings(now)`, `exportLearnings(scope, format)`, `importLearnings(source, origin)` (nur Schreibberechtigte, mit Redaktion). Learning-Typ um `kind: repo_fact | user_pref`, `scope`, `pr_ref?`, `expires_at`, `votes` erweitern. |
| `01-plugin-schnittstellen.md` | neu (Plattform-MCP) | Optionaler **externer KB-MCP-Endpunkt** (`kb.search`, `kb.ask`, `kb.symbol_context`) für Agenten außerhalb der Plattform, mit eigenem Token je Nutzer und Repo-Rechten des Providers; Standard aus. |
| `04-konfiguration-und-limits.md` | 2 Basis-Branch-Regel | Satz zu Copilot mit [copilot-instr] belegen; Liste der Leitlinien-Dateien aus 02 Abschnitt 7 übernehmen oder verlinken (ein Zuhause: 02). |
| `04-konfiguration-und-limits.md` | 3, 4 Beispiele | Schlüssel `knowledge: { learnings: { scope, approval_delay_days, expiry_days, user_prefs }, guidelines: { file_patterns, apply_to[], budget_chars, disabled_ids[] }, ask: { mode } }`, `services.docs: { mode, docs_paths, wiki_config }`; `data_policy.embeddings` mit erlaubten Modell-Lizenzen. |
| `05-sicherheit.md` | Mandanten, Bedrohungstabelle "Vergiftung von KB" | Scope `auto` als Standard (öffentliche Repos sehen keine Org-Learnings, Learnings aus öffentlichen Repos fließen nicht in private); Secret-Redaktion vor Embedding mit Test; externer KB-MCP nur lesend, Rechte je Anfrage beim Provider geprüft; Import von Learnings ist untrusted Inhalt (Injection-Fälle in S1). |
| `06-betrieb-und-deployment.md` | Technikwahl Wissensbasis, Kosten-Hebel 7 | Embedding-Modelle nur mit Lizenz, die Weitergabe und kommerzielle Nutzung erlaubt (Kandidaten CodeRankEmbed MIT, nomic-embed-code Apache-2.0; jina CC-BY-NC ausgeschlossen); Zoekt optional für große Installationen. Ob pgvector auf AWS und Google Cloud gleich verfügbar ist: ungeprüft, gehört zur Hosting-Recherche. |
| `07-eval.md` | 3.5 und neu 3.6 | Testsätze **K3** ContextBench verified (500), **K4** SWE-QA (720) und DeepCodeBench, **K5** CoIR-Teilmenge mit freien Datenlizenzen für die Embedding-Wahl und RepoQA für Langkontext, **D1** CodeWikiBench (nach Lizenzprüfung), **D2** eigener Drift-Satz aus öffentlichen Repos (gemergte PRs, die Doku mit änderten, gegen solche ohne; Wahrheit ist die menschliche Doku-Änderung). K2 und R3 werden "eigene Repos, optional", weil ein öffentliches Projekt reproduzierbare Pflicht-Sätze braucht. |
| `07-eval.md` | 4 Gate-Tabelle | Wissensbasis Gate B: auf K3 Datei- und Span-F1 des Coders mit KB mindestens gleich dem besten Leaderboard-Wert desselben Modells (Stand bei Messung festhalten) und K4 Fact Recall bzw. Richter-Wert mindestens gleich dem besten **selbst nachgemessenen** Referenz-Agenten (claude-code, codex-cli) unter demselben Richter; veröffentlichte Herstellerwerte (Qodo 0,76 bis 0,77, GESAGT) nur als Einordnung. Standards Gate B: Addressed Rate regelbasierter Befunde mindestens gleich der des Reviewers ohne Regel-Bezug, auf R1 und online. `docs` Gate A: Drift-Check Präzision auf D2 über einfachem Prompt; Gate B: CodeWikiBench-Wert mindestens gleich dem im Paper genannten DeepWiki-Wert (64,06 %, GESAGT) auf denselben Repos. Damit ist Backlog M5 erledigt. |
| `07-eval.md` | 6 Metriken | Online je Regel (Nutzung, Akzeptanz, Addressed Rate), je Learning (aktiv, nie genutzt, Abstimmung), Doku (Vorschläge je Merge, angenommene Doku-PRs). |
| `08-roadmap.md` | Stufe 6 | Reihenfolge: zuerst Leitlinien-Lader und Regel-Kennzahlen (billig, sofort wirksam), dann Learnings-Lebenszyklus, dann L2/L3 nur bei Eval-Gewinn; `docs` als eigene spätere Stufe nach Reviewer-Qualifikation. |
| `09-entscheidungen.md` | ADR neu, O7, O10, O12 | ADR: Service `docs`; ADR: Leitlinien-Lader liest fremde Formate; ADR: Learnings-Lebenszyklus nach Copilot. O7 um Lizenzfilter ergänzen. O10 und O12 siehe Abschnitt 4. |
| `backlog-minors.md` | M5 | durch neue Gate-B-Zeilen gelöst, sobald 07 angepasst ist. |

---

## 4. Owner-Entscheidungen

| # | Frage | Art | Empfehlung | Grund |
|---|---|---|---|---|
| W1 | Dürfen öffentliche Testsätze mit unklarer Datenlizenz (ContextBench-Daten, CodeRAG-Bench, Loc-Bench V1, CodeWikiBench) im öffentlichen Eval-Repo liegen? | Recht (Lizenz) | Nein. Im öffentlichen Repo nur Sätze mit geprüfter Lizenz (SWE-QA, DeepCodeBench, RepoQA: Apache-2.0); die übrigen nur per Download-Skript ohne Weitergabe der Daten, bis die Lizenz geklärt ist | Ein Open-Source-Repo verteilt, was es enthält; Download-Skripte verteilen nichts. Ergänzt O12 |
| W2 | Werden abgeleitete Regeln automatisch aktiv (Qodo macht das seit 2026-09-01 standardmäßig)? | Produkt | O10 bleibt "nein" als **Standard**, aber als Schalter `standards.auto_activate` je Installation, Obergrenze durch Org | Eigene Installationen anderer Betreiber wollen eventuell Qodo-Verhalten; Sicherheit bleibt beim Standard, weil Regeln Reviewer und Coder steuern ([A05] Vergiftung) |
| W3 | Darf eine Installation externe Kontext- oder Embedding-Dienste (Augment Context Engine, Voyage, OpenAI Embeddings, DeepWiki-MCP) als Plugin nutzen? | Daten nach außen | Ja als Plugin, Standard aus, nur mit `data_policy`-Freigabe; Standard-Modell lokal mit freier Lizenz | Ergänzt O7; Open Source braucht einen Weg ohne Drittanbieter, Betreiber dürfen aber selbst wählen |
| W4 | Ist Dokumentation (`docs`) Teil des Produkts? | Produkt | Ja, als achter Service, Standard `off`, Bau erst nach Reviewer-Qualifikation | Owner-Vorgabe 1 nennt "usw." für Ebenen; Mintlify, Swimm, Dosu und DeepWiki zeigen, dass Doku ein eigenes Fachgebiet mit eigenem Standard ist |
| W5 | Learnings-Scope-Standard für öffentliche Repos | Produkt, Datenschutz | `auto`: öffentliche Repos nur eigene Learnings, keine Org-Learnings hinein und keine hinaus | Bei öffentlicher Installation würden Org-Learnings sonst über öffentliche PR-Kommentare sichtbar (ABGELEITET) |

---

## 5. Offene Punkte

- Unabhängiger Produktvergleich für Codebase-Kontext (Sourcegraph, Augment, Cursor, Greptile): nicht gefunden; alle Zahlen sind Eigenmessungen.
- ContextBench-Leaderboard-Werte: nur als Bild im Repo, Webseite `contextbench.github.io` nicht gelesen; Lizenz der Daten offen.
- DeepCodeBench: Repos, Bewertungsprompt und Richter nicht auf der Datensatzkarte; Methode nur aus Qodo-Blog (GESAGT).
- SWE-QA: Kriterien des Richters nicht gelesen (nur Existenz von `score/llm-as-a-judge.py`).
- CodeRAG-Bench, Loc-Bench V1, CodeWikiBench, DocAgent: Lizenzen ungeprüft.
- Mintlify Autopilot: nur aus Doku-PRs im Repo `mintlify/docs`, aktueller Name und Umfang auf der veröffentlichten Seite ungeprüft.
- Dosu: nur Drittverzeichnisse; Herstellerdoku nicht gelesen.
- Swimm-Patent: Nummer und Ansprüche unbekannt; vor Umsetzung des Token-Abgleichs prüfen (Recht, technisch offen).
- SCIP-Lizenz ungeprüft.
- Copilot Code Review liest Anweisungen vom Head: belegt.
- Ob pgvector bei AWS RDS und Google Cloud SQL gleich nutzbar ist: ungeprüft, gehört zur Hosting-Recherche.
- Cursors "Cursor Context Benchmark" ist nicht öffentlich (laut Blog intern).

---

## 6. Quellen (alle abgerufen 2026-10-31)

Hersteller-Doku und Repos:
- [copilot-memory] https://docs.github.com/en/copilot/concepts/agents/copilot-memory
- [copilot-instr] https://docs.github.com/en/copilot/concepts/prompting/response-customization
- [devin-wiki] https://docs.devin.ai/work-with-devin/deepwiki.md
- [deepwiki-mcp] https://docs.devin.ai/work-with-devin/deepwiki-mcp
- [devin-knowledge] https://docs.devin.ai/product-guides/knowledge und https://docs.devin.ai/onboard-devin/knowledge-onboarding (über Suche, Auszüge)
- [qodo-miner] https://docs.qodo.ai/governance/rule-enforcement/rule-miner
- [greptile-std] https://www.greptile.com/docs/code-review/custom-standards
- [greptile-graph] https://www.greptile.com/docs/how-greptile-works/graph-based-codebase-context, https://www.greptile.com/code-context, https://hatchet.run/customers/greptile (über Suche)
- [cursor-bugbot] https://cursor.com/docs/bugbot
- [cursor-rules] https://cursor.com/docs/context/rules
- [agentsmd] https://agents.md/
- [sg-deepsearch] https://sourcegraph.com/docs/deep-search (über Suche, Auszüge der Doku)
- [zoekt] https://github.com/sourcegraph/zoekt
- [augment-ce] https://www.augmentcode.com/context-engine
- [augment-mcp] https://www.augmentcode.com/changelog/context-engine-mcp-in-ga, https://www.augmentcode.com/blog/context-engine-mcp-now-live (über Suche)

Benchmarks und Datensätze:
- [contextbench-gh] https://github.com/EuniAI/ContextBench
- [contextbench-hf] https://huggingface.co/datasets/Contextbench/ContextBench
- [contextbench-paper] https://arxiv.org/abs/2602.05892 (über Suche)
- [sweqa-gh] https://github.com/peng-weihan/SWE-QA-Bench
- [sweqa-hf] https://huggingface.co/datasets/swe-qa/SWE-QA-Benchmark
- [sweqa-paper] https://arxiv.org/abs/2509.14635 (über Suche)
- [qodo-dcb-hf] https://huggingface.co/datasets/Qodo/deep_code_bench/blob/main/README.md
- [qodo-dcb] Qodo-Blog "DeepCodeBench" (über Suche und Drittzusammenfassung, GESAGT)
- [coir] https://github.com/CoIR-team/coir
- [repoqa] https://github.com/evalplus/repoqa
- [coderag] https://github.com/code-rag-bench/code-rag-bench
- [locagent] https://github.com/gersteinlab/LocAgent, https://arxiv.org/abs/2503.09089 (über Suche)
- [codewiki] https://arxiv.org/abs/2510.24428, https://github.com/FSoft-AI4Code/CodeWiki (über Suche)
- [docagent] https://arxiv.org/abs/2504.08725, https://github.com/facebookresearch/DocAgent (über Suche)

Embedding-Modelle (über Suche, Herstellerangaben):
- [nomic-code] https://huggingface.co/nomic-ai/nomic-embed-code, https://huggingface.co/nomic-ai/CodeRankEmbed
- [qodo-embed] https://www.qodo.ai/blog/qodo-embed-1-code-embedding-code-retrieval
- [jina-code] https://jina.ai/models/jina-code-embeddings-0.5b/

Blogs, Drittberichte (GESAGT):
- [cursor-semsearch] https://cursor.com/blog/semsearch
- [amp-spinout] https://ampcode.com/news/amp-inc
- [mintlify] https://github.com/mintlify/docs/pull/2056/files und https://github.com/mintlify/docs/pull/2348
- [swimm] https://docs.swimm.io/features/code-coupling-suggestions, https://www.console.dev/interviews/swimm-gilad-navot
- [dosu] https://aiagentslist.com/agents/dosu (Drittverzeichnis)
- [gh-aw-docs] https://github.github.com/gh-aw/gallery/docs-automation/
