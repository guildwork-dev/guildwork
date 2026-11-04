<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
> Research note, dated 2026-11-01, not binding. Kept in German as written (ADR-53); the binding documents are docs/architecture and docs/design.

# Recherche: Ebene autonomes Coding (Ticket zu PR)

**Dated, not binding.** Datierte Recherche, Stand 2026-10-31, nicht verbindlich und nicht übersetzt; verbindlich ist die Plattform-Doku ([docs/architektur/](../architecture/README.md)).

Stand 2026-10-31. Alle Webquellen am 2026-10-31 abgerufen. Einstufung wie in [docs/architektur/README.md](../architecture/README.md) Abschnitt 6: BELEGT (Primärquelle selbst gelesen), GESAGT (Herstelleraussage, Marketing, Drittbericht, Suchauszug), ABGELEITET (eigener Schluss), VERMUTET. Was nicht geprüft werden konnte, steht als "ungeprüft" da.

Hinweis zur Lesetiefe: Die Webseiten wurden über ein Abrufwerkzeug gelesen, das den Inhalt durch ein kleines Modell zusammenfasst. Zitate sind deshalb sinngemäß, außer bei den beiden Claude-Code-Seiten [cc-cloud] und [cc-selfhosted] und der Lizenzdatei [cc-license], die im Wortlaut vorlagen. Seiten, die nur als Suchauszug vorlagen (etwa die OpenAI-Beiträge, die 403 lieferten), sind als GESAGT eingestuft.

Bezug: Diese Datei ergänzt [02-services.md](../architecture/02-services.md) Abschnitt 2 (Coder) und [07-eval.md](../architecture/07-eval.md) Abschnitte 3.2 und 4. Was dort schon belegt ist (Devin Blueprints, Codex-Setup-Trennung, Copilot-Selbstprüfung, Cursor/Devin-Belege), wird hier nicht wiederholt, sondern nur ergänzt oder korrigiert.

---

## 1. Urteil (Kurzfassung)

1. **Es gibt auf dieser Ebene keinen einzelnen Standard wie CodeRabbit beim Review, sondern zwei Schichten.** (a) Der **Agentenkern** (Harness plus Modell): Hier führen Anthropic mit Claude Code und OpenAI mit Codex. Auf Scales eigener Leaderboard-Seite stehen Claude Code und Codex als Harness ausdrücklich in den Spitzenzeilen von SWE-Bench Pro V2 und SWE Atlas ([scale-lb] BELEGT). (b) Die **Produkthülle Ticket zu PR** (Umgebung, Auslöser, Selbstprüfung, Steuerung, Übergabe, Parallelität): Hier setzen GitHub Copilot cloud agent (Reichweite, eingebaute Selbstprüfung), Devin (Blueprints, Managed Devins, Übernahme durch Menschen), Cursor Cloud Agents (Computer Use, Snapshots, Remote-Desktop-Übernahme) und Claude Code in der Cloud (Teleport, Auto-Fix, selbst gehostete Runner) den Maßstab. ABGELEITET.
2. **Unsere Architektur liegt beim Kern richtig:** Sie erfindet keinen eigenen Agenten-Loop, sondern kapselt die besten Harnesses als `AgentRuntime` ([01](../architecture/01-plugin-interfaces.md) Abschnitt 6). Das ist nach den Belegen die einzige Chance, das Niveau zu halten, weil der Harness allein 4 bis 20 Prozentpunkte ausmacht ([morph-pro], [scale-lb] GESAGT bzw. BELEGT). Beim Sicherheitsmodell (Lesen und Wirken getrennt, Credentials außerhalb der Sandbox, ausgehende Long-Poll-Worker) liegt sie auf oder über dem Niveau: Claude Code self-hosted, Factory OpenCompute und Warp nutzen dasselbe Muster "nur ausgehend, Lease, Heartbeat" ([cc-selfhosted], [factory-opencompute] BELEGT).
3. **Lücken bei der Produkthülle (Major für Anforderung 1):** (L1) kein Nachsteuern eines laufenden Coder-Runs, (L2) keine Rückfrage aus dem Coding heraus (der Zustandsautomat kennt `awaiting_input` nur aus `planning`), (L3) keine Übergabe einer laufenden Sitzung an einen Menschen und zurück, (L4) kein agentengeführter Umgebungsaufbau für Repos ohne Blueprint, (L5) kein Aufteilen großer Pläne in parallele Kind-Runs. Alle fünf hat jeder der führenden Anbieter in irgendeiner Form (Tabelle in Abschnitt 2.3). ABGELEITET.
4. **Gate B für den Coder ist in [07](../architecture/07-eval.md) mit veraltetem Bezug definiert.** SWE-bench Verified gilt als kontaminiert und fehlerhaft ([openai-verified], [epoch-verified] GESAGT bzw. BELEGT). OpenAI hat im Juli 2026 auch die Empfehlung für SWE-bench Pro v1 zurückgenommen, weil rund 30 % der 731 öffentlichen Aufgaben kaputt seien ([openai-noise] GESAGT). SWE-Bench Pro V2 ist an der Spitze gesättigt (99,40 bzw. 98,00 auf V2 Full und HARD, [scale-lb] BELEGT). Gate B muss deshalb auf einen Korb aus SWE-Bench Pro V2 HARD-51, SWE Atlas (Refactoring, Test Writing), SWE-rebench (frische, dekontaminierte Aufgaben) und Terminal-Bench umgestellt werden, gemessen über das Harbor-Format, dazu ein eigener C#-Bezug (SWE-Sharp-Bench), weil keine SWE-bench-Variante C# abdeckt. Vorschlag konkret in Abschnitt 3.3.
5. **Open-Source-Vorgabe (Owner, dritte Runde) trifft die Coding-Ebene direkt:** Claude Code ist proprietär ("All rights reserved", [cc-license] BELEGT), Codex CLI ist Apache-2.0 ([codex-repo] BELEGT), das OpenHands Agent SDK MIT ([oh-sdk-repo] BELEGT). Eine öffentliche Distribution darf Claude Code nicht mitliefern, nur als vom Nutzer selbst installierte Laufzeit anbinden (rechtlich ungeprüft, Owner-Entscheidung OE-1). Mindestens ein freier Harness muss für den Coder qualifiziert sein, sonst ist die Plattform für Dritte ohne Anthropic-Vertrag nicht nutzbar.

---

## 2. Befunde mit Quellen

### 2.1 Marktstellung (wer wird genutzt)

| Befund | Einstufung | Quelle |
|---|---|---|
| GitHub: Im September 2026 starten Entwickler mehr als 40 % der Pull Requests mit einem Agenten, im März 17 %; 110 Mio. Agent-PRs im September. Agent-PRs mergen zu 90 % binnen zwei Wochen, Vergleichsgruppe rund 86 %. | GESAGT (Hersteller über eigene Plattform, Primärseite gelesen) | [octoverse-2026] |
| GitHub: 55 % der monatlich aktiven Copilot-Nutzer verwenden agentische Funktionen; Copilot cloud agent wuchs 230 % zum Vorjahr. Keine Aufschlüsselung je Agent. | GESAGT | [octoverse-2026] |
| Amplifying.ai: Von 136,1 Mio. zugeordneten Commits und PRs auf öffentlichem GitHub entfallen 77 % auf Claude Code; Claude Code, Cursor und Replit Agent zusammen 91 %. | GESAGT (nur Suchauszug, Primärseite nicht gelesen) | [amplifying] |
| Amplifying.ai Autonomie-Seite (Fenster 2026-07-30 bis 2026-08-28, je Agent 120 gemergte PRs): Anteil gemergter Agent-PRs mit menschlichem Reviewer in bedeutenden Repos: Copilot 80,5 %, Cursor 77,8 %, Devin 51,6 %, Claude Code 30,5 %, Codex 28,6 %, Jules 12,5 %; Tests berührt: Codex 69,2 %, Cursor 55,8 %, Claude Code 47,5 %, Copilot 31,7 %. | BELEGT (Seite gelesen) | [amplifying-autonomy] |
| **Korrektur zu einem Suchauszug:** Ein Suchwerkzeug nannte "80,5 % Merge-Rate" für Copilot. Die Primärseite misst aber nur bereits gemergte PRs und meldet Review-Anteile, keine Merge-Raten. Merge-Raten je Agent sind damit für 2026 nicht belegt. | BELEGT | [amplifying-autonomy] |
| AIDev (Li et al.): 456.000 Agent-PRs von Codex, Devin, Copilot, Cursor, Claude Code; Merge-Raten auf Repos mit mindestens 500 Sternen: Mensch 76,8 %, Codex 64 %, Cursor 51,4 %, Claude Code 52,5 %, Devin 49 %, Copilot 35 %. Daten bis Mitte 2025, damit veraltet. Zweite Fassung 932.791 PRs bis 2025-08-01, öffentlich auf Hugging Face und Zenodo. | GESAGT (Sekundärzusammenfassung, Paper nicht selbst gelesen) | [aidev] |

Schluss (ABGELEITET): Nach Verbreitung führen Claude Code und Copilot, nach Funktionsbreite der Produkthülle Devin, Cursor und Copilot. Codex ist beim Agentenkern in der Spitzengruppe. Jules, Factory, Amp, Warp und Augment sind Nischen mit einzelnen übernehmenswerten Mechaniken.

### 2.2 Unabhängige Benchmarks und wer einheitlich misst

| Benchmark | Stand und Messwerte | Bewertung | Einstufung | Quelle |
|---|---|---|---|---|
| **SWE-bench Verified** (500 Aufgaben, Python) | OpenAI meldet seit 2026-02-23 keine Verified-Werte mehr: Kontamination (Modelle reproduzieren Original-Fixes aus dem Gedächtnis), 59,4 % von 138 geprüften schwer lösbaren Aufgaben mit Mängeln. Epoch stuft den Satz als "Flawed" ein, Fehlerrate 5 bis 10 %, misst 484 von 500 Aufgaben. | Als Gate-B-Bezug ungeeignet; höchstens als Rauchtest | OpenAI GESAGT (403, Suchauszug); Epoch BELEGT | [openai-verified], [epoch-verified] |
| **SWE-bench Pro v1** (Scale, 731 öffentlich, 276 kommerziell privat, 858 zurückgehalten) | Scale SEAL einheitlich (SWE-Agent bzw. mini-swe-agent, bis 250 Züge, ohne Kostenlimit): Spitze Muse Spark 1.1 61,50 ± 3,10, gpt-5.4 (xHigh) 59,10 ± 3,56, claude-opus-4-6 51,90 ± 3,61. Hersteller-Harness liegt 10 bis 30 Punkte darüber. OpenAI 2026-07-08: rund 30 % der öffentlichen Aufgaben kaputt (Automatik 200 von 731, fünf Ingenieure 249 von 731), Empfehlung zurückgezogen. | Nicht mehr als alleiniger Bezug | Scale BELEGT; OpenAI GESAGT | [scale-pro-v1], [openai-noise], [morph-pro] |
| **SWE-Bench Pro V2** (seit 2026-09-22; 642 Aufgaben aus 11 Repos: Go 256, Python 237, JS 145, TS 4; Teilmenge HARD-51) | Leaderboard listet Harness je Zeile: V2 Full: Opus 5 (Claude Code) xhigh 99,40 ± 0,40; Gemini 4 Argon (mini-swe-agent) 99,22; Fable 5.1 (Claude Code) 99,10. HARD: Opus 5 (Claude Code) 98,00; Fable 5.1 (Claude Code) 92,20; Gemini 4 Argon 92,16. Format Harbor, Images öffentlich unter `ghcr.io/scaleapi/swe-bench_pro-v2`, "locked protocol" (Agent offline, Neubewertung in frischer Sandbox). Harness MIT; Aufgabeninhalte unter den Lizenzen der Upstream-Repos. | Spitze gesättigt; als Untergrenze brauchbar, weil derselbe Harness mit demselben Modell einen veröffentlichten Bezug hat | BELEGT | [scale-lb], [scale-pro-repo], [scale-pro-hf] |
| **SWE Atlas** (Scale; Codebase QnA 124, Test Writing 90, Refactoring 70 Aufgaben aus 18 Repos; programmatische plus Rubrik-Prüfer) | Refactoring: GPT 6 Astra (Codex) 59,05 ± 6,43; Fable-5.1 (Claude Code) 56,67. Test Writing: Fable-5.1 (Claude Code) 67,04; Opus 5 (Claude Code) 62,22. QnA: Opus 5 (Claude Code) 63,17. | **Nicht gesättigt** und misst Qualität (Wartbarkeit, Konventionen), nicht nur grüne Tests: passt zu "Niveau". QnA-Satz öffentlich (`ScaleAI/SWE-Atlas-QnA`, auch in Harbor); Lizenz und Verfügbarkeit von Refactoring und Test Writing ungeprüft | Werte BELEGT; Aufbau GESAGT | [scale-lb], [scale-atlas] |
| **Terminal-Bench** (Stanford, Laude Institute; 2.0 mit 89 Aufgaben) | Offizielle Seite nennt inzwischen "Terminal-Bench 4.0", Tabelle wurde nicht geladen (ungeprüft). Letzter gelesener 2.0-Stand über Dritte (2026-04-27): Codex/GPT-5.5 82,0 ± 2,2, ForgeCode/GPT-5.4 81,8. Jede Zeile ist Agent plus Modell. | Misst Umgebungs- und Shell-Kompetenz; Harness Harbor (Apache-2.0) | 4.0 ungeprüft; 2.0-Werte GESAGT; Harbor BELEGT | [tbench], [codesota-tb], [harbor] |
| **SWE-rebench** (Nebius) | Monatlich frische Aufgaben aus GitHub nach dem Veröffentlichungsdatum jedes Modells, festes 128K-ReAct-Gerüst, 5 Läufe je Modell. Begleitende Datensätze CC-BY-4.0, Lizenz je Upstream-Repo im Datensatz vermerkt. | Bester Schutz gegen Kontamination; nur Python | GESAGT (Paper und Blog nicht selbst gelesen); Lizenz des Leaderboard-Satzes ungeprüft | [swe-rebench] |
| **OpenHands Index** | Fester Harness (OpenHands SDK), variiert nur das Modell; fünf Kategorien: swe-bench, swe-bench-multimodal, commit0, swt-bench, gaia. Spitze claude-fable-5 81,00 (Ø-Kosten 5,54 USD), claude-opus-4-8 71,88 (2,46 USD), GPT-5.5 65,94 (2,31 USD); 33 Einträge, Datenstand 2026-10-22; SDK-Versionen der Zeilen unterschiedlich. | Kostenbezug je Aufgabe; Issue-Kategorie nutzt Verified (siehe oben) | BELEGT (API abgerufen) | [oh-index-api] |
| **Epoch AI Benchmarking Hub** | Eigene Läufe mit Inspect; seit 2026-02 v2.0.0 mit neuem Gerüst; seit 2026-02-13 auch Claude Code und Codex über Inspect-SWE als Gerüst. | Unabhängiger Prüfer; Tabelle nicht ladbar | BELEGT (Methodik), Werte ungeprüft | [epoch-verified] |
| **Multi-SWE-bench** (ByteDance; 1.632 Aufgaben, Java, TS, JS, Go, Rust, C, C++) | Code Apache-2.0, Daten CC0 mit Vorbehalt der Upstream-Lizenzen; Leaderboard meist selbst gemeldet | Sprachbreite, kein C# | GESAGT | [multi-swe] |
| **SWE-bench Multilingual** (300 Aufgaben, 42 Repos, 9 Sprachen) | gleiches Protokoll wie SWE-bench | kein C#; Lizenz ungeprüft | BELEGT (Seite) | [swe-multi] |
| **SWE-PolyBench** (Amazon; 2.110 Aufgaben, Verified 394; Python, Java, JS, TS) | MIT laut Hugging-Face-Metadaten | kein C# | GESAGT | [polybench] |
| **SWE-Sharp-Bench** (Microsoft Research; 150 C#-Aufgaben aus 17 Repos) | Gleiches Setup löst 70 % Python-Verified, aber nur 40 % C#; bestes Ergebnis OpenHands + GPT-5 47,3 % | Einziger gefundener C#-Bezug; Lizenz ungeprüft | GESAGT (Paper nicht selbst gelesen) | [swe-sharp] |
| **SWE-Lancer** (OpenAI; 1.488 Upwork-Aufgaben, Diamond öffentlich) | Repo am 2025-07-18 archiviert; Lizenz widersprüchlich | Nicht mehr gepflegt; nur Idee (Wert in USD statt Prozent) | GESAGT | [swe-lancer] |
| **METR Time Horizon** | Misst die Länge (menschliche Dauer) von Aufgaben, die ein Agent zu 50 % löst; Suite an der Messgrenze (über 16 Stunden unzuverlässig) | Kein Gate, aber Hinweis, wie lang Aufgaben je Run sein dürfen | GESAGT | [metr] |

Wer misst einheitlich (ABGELEITET aus den Zeilen oben): Scale (SEAL, eigenes Gerüst, und seit V2 ausgewiesene Hersteller-Harnesses), Epoch AI (Inspect, eigene Läufe), OpenHands Index (fester Harness, Modelle variieren), SWE-rebench (festes Gerüst, frische Aufgaben), Terminal-Bench (Agent plus Modell, Konfidenzintervalle). Werte von Herstellern und Aggregatoren (BenchLM, MorphLLM, llm-stats) sind GESAGT und widersprechen sich.

**Korrektur zu [07-eval.md](../architecture/07-eval.md) Abschnitt 3.2 C2 und [02-services.md](../architecture/02-services.md) Coder-DoD:** Dort ist [swebench-pro] eine MorphLLM-Seite (Aggregator) und "Scale SEAL" als Bezug genannt. Primärquelle ist Scales Leaderboard selbst ([scale-lb]); der Bezug muss die V2-Fassung mit Harness-Angabe sein, nicht v1.

### 2.3 Fähigkeits-Checkliste des Standards

Spalte "Wir": ja, teilweise, nein, mit Fundstelle in `docs/architektur`. Kürzel der Anbieter: CC = Claude Code (Cloud-Sitzungen), CX = OpenAI Codex Cloud, CP = GitHub Copilot cloud agent, DV = Devin, CU = Cursor Cloud Agents, JU = Jules, FA = Factory, AM = Amp, WA = Warp Oz, OH = OpenHands.

| # | Fähigkeit | Wer hat sie | Beleg | Wir |
|---|---|---|---|---|
| 1 | Auslöser aus Ticket, Zuweisung, Label | CP (Agents-Tab, Issue-Panel), JU (Label `jules`), CU (`@cursor` in GitHub, Bitbucket, Linear), DV (Jira, Linear, Slack), FA (Delegations Jira, Linear, Slack) | [cp-about], [jules-tasks], [cu-cloud], [devin-llms], [factory-llms] BELEGT | ja: [03](../architecture/03-flow-and-orchestration.md) 1a, [04](../architecture/04-configuration-and-limits.md) `routing` |
| 2 | Auslöser aus Chat (Slack, Teams) | CU, DV, FA, CC (Claude Tag in Slack), CP (Integrationen) | [cu-cloud], [cc-cloud], [factory-llms] BELEGT | nein: nur Notifier in Stufe 9 ([08](../architecture/08-roadmap.md)) |
| 3 | Zeitplan- und Ereignis-Automationen | CP (Automations), DV (Scheduled Sessions), CC (Routines), WA (Triggers, Schedules) | [cp-about], [devin-adv], [cc-cloud], [warp-env] BELEGT bzw. GESAGT | teilweise: Ereignis-Auslöser ja, Zeitplan nur für Indexer und Standards ([02](../architecture/02-services.md) 6, 7) |
| 4 | Umgebung deklarativ mit Snapshot | DV (Blueprint), CP (`copilot-setup-steps.yml` mit Schlüssel `snapshot`), CU (`.cursor/environment.json`, Snapshot, Dockerfile), CC (Setup-Skript, gecacht nur bei Lauf unter rund 5 Minuten), WA (Environments) | [devin-bp], [cp-env], [cu-cloud], [cc-cloud] BELEGT | ja: [02](../architecture/02-services.md) Coder Stufe 1, [01](../architecture/01-plugin-interfaces.md) `SandboxSpec`, `buildSnapshot` |
| 5 | Schichten Installation/Org/Repo, Post-Build-Prüfung, periodischer Neubau, Anheften an letzten guten Build | DV (Enterprise/Org/Repo, `post-build`, Neubau etwa alle 24 h, Pin unter 7 Tagen) | [devin-bp] BELEGT | teilweise: `post_build` und `snapshotKey` ja ([04](../architecture/04-configuration-and-limits.md) Zeile `environment`), Schichten, periodischer Neubau und Pin nein |
| 6 | Agentengeführter Umgebungsaufbau (Agent erkundet Repo, installiert, testet, schlägt Konfiguration vor) | CU ("agent-led setup"), CX (prüft Repos, installiert, testet den Ablauf vor "Publish"), DV (schlägt Blueprint-Änderung in der Sitzung vor) | [cu-cloud], [cx-cloud], [devin-bp] BELEGT | **nein** |
| 7 | Secrets nur im Setup, nicht im Snapshot | DV, CX; CU injiziert beim Start | [devin-bp], [cu-cloud] BELEGT | ja: `phases.setup.secrets` ([01](../architecture/01-plugin-interfaces.md) 8) |
| 8 | Git- und API-Credentials außerhalb der Sandbox (Proxy setzt sie ein) | CC (GitHub-Proxy, "network secrets" außerhalb der Sandbox) | [cc-cloud] BELEGT | ja: Effect Gateway, Credential-Relay ([README](../architecture/README.md) Leitidee 3, [05](../architecture/05-security.md)) |
| 9 | Egress-Allowlist | CP (Firewall, nicht mit Self-hosted-Runnern), CU, CC (Stufe "Trusted"), CX | [cp-env], [cu-cloud], [cc-cloud] BELEGT | ja: [05](../architecture/05-security.md) |
| 10 | Selbst gehostete Ausführung, nur ausgehende Verbindungen | CC (Runner pollt `api.anthropic.com`, Lease etwa 60 s, Runner je Besitzer gesperrt), FA (OpenCompute verbindet nach außen), CP (ARC, flüchtige Runner empfohlen), WA (Kubernetes-Worker), AM (Runner) | [cc-selfhosted], [factory-opencompute], [cp-env] BELEGT; [warp-env], [amp] GESAGT | ja: [README](../architecture/README.md) Leitidee 4, `WorkerApi` ([01](../architecture/01-plugin-interfaces.md) 8) |
| 11 | Plan vor Code mit Freigabe | JU, CP, FA (Spec Mode, Specs in `.factory/docs/`), CC (Plan-Modus) | [jules-tasks], [factory-spec-web], [cc-cloud] BELEGT bzw. GESAGT | ja: Planner ([02](../architecture/02-services.md) 1) |
| 12 | Rückfrage bei Unklarheit **während des Codings**, Sitzung wartet und läuft mit Antwort weiter | CC (Antwort bis Ablauf der Umgebung möglich), JU, DV | [cc-cloud], [jules-tasks] BELEGT | **teilweise**: `request_human_input` ist erlaubt ([02](../architecture/02-services.md) 0), aber der Zustandsautomat kennt `awaiting_input` nur aus `planning` ([03](../architecture/03-flow-and-orchestration.md) 2.1) |
| 13 | Nachsteuern einer laufenden Sitzung (neue Anweisung, ohne Abbruch) | CC (`claude -p "..." --cloud <id>`, Nachricht in Warteschlange), JU (Chat jederzeit, Neuplanung), CP ("steer in the same session"), DV (stoppen und umlenken; Seitenfrage `/btw` nur lesend) | [cc-cloud], [jules-tasks], [cp-about], [devin-tools] BELEGT | **nein**: nur `stop`, `continue`, `hold` ([03](../architecture/03-flow-and-orchestration.md) 4) |
| 14 | Übergabe an Menschen und zurück (Übernahme mitten im Lauf) | CC (`--teleport` holt Sitzung samt Branch und Verlauf ins Terminal), DV (IDE-Übernahme, Terminal beschreibbar, SSH, Fortsetzen mit Hinweis auf Änderungen), CU (Remote-Desktop übernehmen und zurückgeben), CX (Diff lokal anwenden, GESAGT) | [cc-cloud], [devin-tools], [devin-llms], [cu-cloud] BELEGT; [cx-bon] GESAGT | **nein**: nur Branch und Run Record; Fremd-Commit führt korrekt zu `awaiting_human_review` ([03](../architecture/03-flow-and-orchestration.md) 1a Punkt 11) |
| 15 | Live-Protokoll der Sitzung, teilbar | CP (Session-Logs für Repo-Leser), DV (Progress-Tab), CU (geteilte URL, nur lesend; Team-Follow-ups), AM (Threads, teilbar), CC (Sitzung teilen) | [cp-about], [devin-tools], [cu-cloud], [cc-cloud] BELEGT; [amp] GESAGT | teilweise: Run Record und Admin-UI ([README](../architecture/README.md) Glossar), nicht live, nicht für Ticket-Leser |
| 16 | Selbstprüfung vor dem PR (Tests, Linter, CodeQL, Advisory, Secret Scanning, Code Review), je Repo abschaltbar | CP | [cp-validate] BELEGT | ja: Self-Check-Bündel und Self-Review ([02](../architecture/02-services.md) Coder Stufen 4, 5) |
| 17 | Kritiker im Generierungs-Loop (adversariales Review vor Abschluss, Schleife bis keine Einwände) | JU ("critic augmented generation") | [jules-critic] GESAGT | ja: Self-Review mit `repair_rounds` ([02](../architecture/02-services.md) Coder Stufe 5) |
| 18 | Laufende App bedienen, Screenshots und Videos als Beleg | CU (Desktop und Browser, Artefakte), DV (Testing und Aufnahmen) | [cu-cloud], [devin-tools] BELEGT | teilweise: nur im QA-Service ([02](../architecture/02-services.md) 4), nicht im Coder |
| 19 | Parallele Versuche (Best-of-N) | CX (`--attempts`, 1 bis 4 laut Drittquelle) | [cx-bon] GESAGT | teilweise: optional, Standard 1, Roadmap Stufe 9 ([02](../architecture/02-services.md) Coder Stufe 6, [08](../architecture/08-roadmap.md)) |
| 20 | Viele parallele Sitzungen je Nutzer | CU ("as many agents as you want"), CC (je `--cloud` eine Sitzung), CX | [cu-cloud], [cc-cloud] BELEGT | ja: Pools mit Obergrenze ([01](../architecture/01-plugin-interfaces.md) 8, [04](../architecture/04-configuration-and-limits.md) Limits) |
| 21 | Zerlegung in Kind-Sitzungen mit eigener VM, Koordinator führt zusammen | DV (Managed Devins mit ACU-Limit je Kind, Weckruf bei Abschluss), FA (Missions mit Meilensteinen und QA-Validierung; Workstreams), CC (Projects koordinieren parallele Cloud-Sitzungen) | [devin-adv], [factory-missions-web], [cc-cloud] BELEGT | **teilweise**: `phases[]` im Plan, Subagenten mit `maxDepth: 1` in derselben Sandbox ([01](../architecture/01-plugin-interfaces.md) 6); keine Kind-Runs |
| 22 | Änderungen über mehrere Repos | CU (koordinierte PRs je Repo), CP (Cloud-Sandbox über mehrere Repos), DV (Org-Snapshot mit mehreren Repos) | [cu-cloud], [cp-about], [devin-bp] BELEGT | teilweise: `targetRepos?` nur im Planner ([02](../architecture/02-services.md) 1) |
| 23 | PR-Beschreibung nach Repo-Vorlage, mit Sitzungs-Link und Herkunfts-Trailern | DV (PR-Templates), AM (`Amp-Thread-ID`, `Co-authored-by`), CP (PR-Zusammenfassungen) | [devin-llms] BELEGT (Seitentitel); [amp] GESAGT | teilweise: `prBodyMd` mit Plan-Link und Self-Check ([02](../architecture/02-services.md) Coder Ausgang); Repo-Vorlage und Trailer nein |
| 24 | Gestapelte PRs | DV | [devin-llms] BELEGT (Seitentitel) | teilweise: nur PR-Fixer und QA ([02](../architecture/02-services.md) 4, 5) |
| 25 | PR beobachten und CI sowie Review-Kommentare selbst beheben | CC (Auto-Fix; fragt bei mehrdeutigen Kommentaren nach), CP (Agent Merge "Watch and fix") | [cc-cloud], [cp-about] BELEGT | ja: PR-Fixer ([02](../architecture/02-services.md) 5) |
| 26 | Wiederverwendbare Abläufe (Playbooks, Skills, Slash-Befehle) | DV (Playbooks, Skills aus erfolgreichen Sitzungen), CC (Skills, Plugins) | [devin-adv], [devin-llms] BELEGT | teilweise: Regeln in `.agents/rules/` ([02](../architecture/02-services.md) 7); keine Playbooks je Aufgabentyp |
| 27 | Sitzungsanalyse (warum gelungen oder gescheitert, Kosten gegen Erwartung) | DV (Session Insights) | [devin-adv] BELEGT | nein (Run Record speichert die Daten, Auswertung fehlt) |
| 28 | Kostengrenze je Sitzung und je Kind | DV (ACU-Limit), CU (Ausgabenlimit) | [devin-adv], [cu-cloud] BELEGT | ja: Limit-Ledger ([04](../architecture/04-configuration-and-limits.md) Limits) |
| 29 | Modellwahl, eigene Schlüssel | CP (Modellwahl), FA (BYOK), CU (kuratierte Liste) | [cp-about], [factory-llms], [cu-cloud] BELEGT | ja: `ModelProvider`, `runtime` je Service ([04](../architecture/04-configuration-and-limits.md) 5) |
| 30 | Reproduktion zuerst bei Fehlern | (im Standard nicht als Pflicht belegt) | | ja, über dem Standard: [02](../architecture/02-services.md) Coder Stufe 2 |
| 31 | Deterministische Merge-Entscheidung statt Agent | (kein Anbieter belegt; CP Agent Merge nutzt Auto-Merge des Hosters) | [cp-about] BELEGT | ja, über dem Standard: Merge-Gate ([03](../architecture/03-flow-and-orchestration.md) 1a) |

### 2.4 Was die Anbieter offenlegen und was proprietär bleibt

| Anbieter | Offengelegt und übernehmbar | Proprietär | Einstufung, Quelle |
|---|---|---|---|
| Claude Code | Runner-Protokoll der selbst gehosteten Umgebungen: Runner pollt, Lease etwa 60 s, Poll ist Heartbeat, Backoff bis 20 s, Runner nach erstem Besitzer gesperrt, `--retire-at` für geplantes Ende, Freigabe der Sitzung nach Zugende; GitHub-Proxy setzt Credentials außerhalb der VM; Repo-Bundle für Nicht-GitHub-Repos (bis 100 MB, sensible Dateien ausgelassen); Teleport-Voraussetzungen (sauberer Baum, gepushter Branch, gleiches Konto) | CLI selbst ("All rights reserved"), Steuerebene, Cloud-VMs | [cc-selfhosted], [cc-cloud], [cc-license] BELEGT |
| OpenAI Codex | CLI unter Apache-2.0 als Harness nutzbar; Cloud-Umgebung mit getrenntem Install-Skript, Netz-Schaltern, OIDC "outbound identity"; `codex cloud exec --attempts` | Codex Cloud, Modelle | [codex-repo], [cx-cloud] BELEGT; [cx-bon] GESAGT |
| GitHub Copilot | Format `copilot-setup-steps.yml` (genau ein Job, erlaubte Schlüssel `steps`, `permissions`, `runs-on`, `services`, `snapshot`, `timeout-minutes` höchstens 59); Liste der Validierungswerkzeuge; Empfehlung flüchtiger Runner | Agent, Firewall, Cloud-Sandbox | [cp-env], [cp-validate] BELEGT |
| Devin | Blueprint-YAML (`initialize`, `maintenance`, `knowledge`, `post-build`, `clone`), Schichtung und Bauabfolge, Neubau-Auslöser; Managed-Devins-Muster (Koordinator, Kinder mit eigenem Limit, Weckruf statt Polling); API mit OpenAPI v1 bis v3 | Agent, Modelle, Snapshot-Infrastruktur | [devin-bp], [devin-adv], [devin-llms] BELEGT |
| Cursor | `.cursor/environment.json`, Snapshot, Dockerfile; Hooks aus `.cursor/hooks.json`; Secrets beim Start injiziert | Agent, VMs, Computer Use | [cu-cloud] BELEGT |
| Jules | Prinzip "critic augmented generation" | Agent | [jules-critic] GESAGT |
| Factory | OpenCompute (Sandboxen im eigenen Kubernetes, nur ausgehende Verbindung); Missions mit Meilensteinen und QA-Validierung; Spec Mode speichert Specs als Markdown | alles außer `droid-action` (GitHub Action) | [factory-opencompute], [factory-missions-web] BELEGT |
| OpenHands | SDK, Agent Server, Workspaces (lokal, Docker, Kubernetes) unter MIT; Benchmarks-Repo; Index mit Rohdaten | Cloud-Angebot | [oh-sdk-repo], [oh-repo], [oh-index-api] BELEGT |
| Warp Oz | Trennung Environment (Repo, Abhängigkeiten, Compute) und Secrets; Self-Hosting als Kubernetes-Worker | Agent | [warp-env] GESAGT |
| Amp | Runner holen Threads ab; Trailer `Amp-Thread-ID` und `Co-authored-by` | Agent | [amp] GESAGT |
| Augment | Remote Agents offenbar in "Cosmos" aufgegangen (Sessions, Experts, Environments) | alles | GESAGT, Status ungeprüft [augment] |

Schluss (ABGELEITET): Übernehmbar sind fast ausschließlich **Formate und Abläufe** (Blueprint-Schema, Setup-Datei, Runner-Protokoll, Koordinator-Muster, Kritiker-Schleife). Die eigentliche Agentenqualität steckt in Harness und Modell und ist nur über die Harnesses selbst nutzbar. Für die Open-Source-Fassung sind Codex CLI und OpenHands SDK die freien Kandidaten; Claude Code bleibt eine vom Nutzer beigestellte Laufzeit.

---

## 3. Folgen für unsere Architektur

### 3.1 [02-services.md](../architecture/02-services.md) Abschnitt 2 Coder

1. **Messlatte ergänzen** um: Claude Code Cloud (Teleport, Auto-Fix, Nachrichten an laufende Sitzung) [cc-cloud]; Devin Managed Devins und Sitzungsübernahme [devin-adv], [devin-tools]; Jules Kritiker [jules-critic]; Cursor agentengeführter Umgebungsaufbau [cu-cloud]. Zeile "Codex Cloud Best-of-N" bleibt GESAGT.
2. **Stufe 0 neu "Umgebung bootstrappen"** (Lücke L4): Fehlt `.agents/environment.yaml`, startet ein Setup-Work-Item mit offenem Netz und ohne Repo-Schreibrecht, das Abhängigkeiten erkennt, installiert, Lint, Build und Tests ausführt und einen Blueprint-Vorschlag als eigenen PR (`propose_change` auf `.agents/environment.yaml`) liefert. Erst nach Merge gilt er. Neu in der Schreibwunsch-Tabelle Abschnitt 0: Coder darf `propose_change` auf `.agents/environment.yaml` nur in diesem Modus. Grund: Ohne das ist die Plattform für fremde Open-Source-Nutzer erst nach Handarbeit nutzbar.
3. **Stufe 3 erweitern um Rückfrage und Nachsteuern** (L1, L2): Der Coder darf mitten im Lauf `request_human_input` stellen; der Worker legt dann `snapshot(tag)` der Sandbox plus `sessionRef` ab und gibt die Lease frei. Antwort oder Steueranweisung eines Berechtigten startet ein neues Work-Item, das Snapshot und `AgentRuntime.resume()` nutzt (beides existiert schon in [01](../architecture/01-plugin-interfaces.md) 6 und 8). Neues Ereignis `run.steer { text, actor }`.
4. **Stufe 6 Best-of-N präzisieren:** Auswahl deterministisch (Self-Check grün, dann weniger P0/P1 im Self-Review, dann kleinerer Diff), alle Versuche im Run Record. Aktivierung nur, wenn Gate A auf C1 einen Gewinn je Kosten zeigt (bleibt wie [06](../architecture/06-operations-and-deployment.md) Kosten-Hebel 6).
5. **Neue Stufe "Zerlegung"** (L5): Plan-Phasen mit `parallelizable: true` und disjunkten Pfaden werden als Kind-Steps mit eigener Sandbox und eigenem Branch ausgeführt; ein deterministischer Integrator merged die Kind-Branches in den Agent-Branch oder öffnet gestapelte PRs; Konflikt führt zu einem Konflikt-Step des PR-Fixers. Je Kind eigenes Limit (Devin-Muster ACU je Kind).
6. **Ausgang `prBodyMd`:** Repo-Vorlage (`.github/pull_request_template.md` bzw. Host-Äquivalent) vom Basis-SHA befüllen; Link auf den Run Record; Trailer `Agent-Run: <url>` und `Co-authored-by` der Plattform-Identität in jedem Commit.
7. **Belege bei UI-Änderungen:** Coder ruft bei Diff in `qa.apps[].path_patterns` die QA-Bibliothek "E2E-Smoke" (wie der Reviewer als Bibliothek in Stufe 5) und hängt Screenshot oder Video an den PR. Kein eigener Browser im Coder.
8. **DoD-Tabelle:** Zeile "Resolve-Rate mit einheitlichem Harness C2" ersetzen durch den Gate-B-Korb aus Abschnitt 3.3 dieses Berichts.

### 3.2 [03-flow-and-orchestration.md](../architecture/03-flow-and-orchestration.md)

1. **Abschnitt 2.1 Zustandsautomat:** neu `coding --> awaiting_input: Rückfrage des Coders`, `awaiting_input --> coding: Antwort (resume aus Snapshot)`, `coding --> handed_off: @agent handoff`, `handed_off --> coding: @agent resume`, `handed_off --> awaiting_human_review: Mensch öffnet PR selbst`. Frist wie G1b.
2. **Abschnitt 4 Befehle:** neu `@agent say <Text>` (Nachsteuern; Recht: Auslöser oder Schreiben im Repo; der Text ist Anweisung nur von diesem Akteur, alle übrigen Inhalte bleiben `Untrusted`), `@agent handoff` (pusht den Zwischenstand auf `agent/<key>-wip`, legt Transkript-Bündel im Objektspeicher ab, postet die Fortsetzungsanweisung für das lokale Werkzeug), `@agent resume` (übernimmt den Branch inklusive menschlicher Commits als neue Basis; Merge-Gate Punkt 11 bleibt wirksam, das heißt nach menschlichen Commits nie Auto-Merge).
3. **Abschnitt 5 Fehlerpfade:** Zeilen für "Snapshot für Rückfrage scheitert" (Lauf endet `failed` mit Bericht, Zwischenstand als WIP-Branch), "Antwort nach Ablauf der Frist" (neuer Run aus dem WIP-Branch), "Steueranweisung während `proposing`" (wird in die nächste Fix-Runde übernommen, nicht verworfen).
4. **Abschnitt 2.3 Status-Kommentar:** Link auf eine nur lesende Live-Ansicht des Laufs (Ereignisse aus dem Run Record mit Secret-Filter), sichtbar für Personen mit Leserecht am Repo, wie Copilot-Session-Logs [cp-about].

### 3.3 [07-eval.md](../architecture/07-eval.md) Gate B Coder konkret und messbar

Vorschlag für Abschnitt 3.2 (C2 ersetzen) und Abschnitt 4 (Zeile Coder). Alle Zahlen außer den zitierten Bezugswerten sind Startwerte (Schätzung).

**Messgerät:** Der Eval-Dienst importiert Aufgaben im Harbor-Format (SWE-Bench Pro V2 und SWE Atlas QnA liegen schon so vor, Terminal-Bench nutzt Harbor offiziell; [scale-pro-repo], [scale-atlas], [harbor] BELEGT bzw. GESAGT). Je Aufgabe wird das öffentliche Image als `SandboxSpec.image` genommen; der Coder-Service läuft als normaler Plattform-Run mit `effect_sink: record`; bewertet wird mit dem Prüfer der Aufgabe in frischer Sandbox ("locked protocol" wie Scale). Damit bleibt die Regel aus [07](../architecture/07-eval.md) Abschnitt 1 erhalten: gemessen wird genau das, was live läuft.

| Gate-B-Teil | Datensatz | Bezugswert | Bestanden, wenn | Einstufung Bezug |
|---|---|---|---|---|
| B1 Untergrenze Fähigkeit | SWE-Bench Pro V2 HARD-51 (und V2 Full je Release) | Scale-Wert desselben Harness mit demselben Modell, zum Beispiel Opus 5 (Claude Code) xhigh 98,00 auf HARD | eigener Wert liegt nicht unterhalb des Konfidenzintervalls des Bezugs; bei 51 Aufgaben ist das 95-%-Intervall um 90 % etwa ±8 Punkte (ABGELEITET: 1,96 · √(0,9 · 0,1 / 51)) | BELEGT [scale-lb] |
| B2 Qualität über grüne Tests hinaus | SWE Atlas Refactoring (70) und Test Writing (90), Rubrik-Prüfer von Scale | Spitzenwert desselben Harness und Modells laut [scale-lb] (heute 56,67 bis 67,04) | nicht schlechter als Bezug innerhalb Intervall | BELEGT; Verfügbarkeit der Daten ungeprüft |
| B3 Kontamination | SWE-rebench, nur Aufgaben nach dem Modell-Stichtag, je Monat neu | SWE-rebench-Wert desselben Modells im festen Gerüst | eigener Wert mindestens gleich (Plattform darf das Modell nicht verschlechtern) | GESAGT [swe-rebench] |
| B4 Umgebung und Shell | Terminal-Bench (aktuelle Version über Harbor) | Wert derselben Agent-Modell-Zeile | innerhalb Intervall | Version ungeprüft [tbench] |
| B5 Sprachen der Nutzer | Multi-SWE-bench mini (400) oder SWE-PolyBench Verified (394) je nach Sprachmix; SWE-Sharp-Bench (150) für C# | kein Harness-gleicher Bezug veröffentlicht; Bezug ist der nackte Harness (Gate A) | Gate A grün je Sprache; Ergebnis veröffentlicht | GESAGT [multi-swe], [polybench], [swe-sharp] |
| B6 Online | eigene Agent-PRs | Merge-Rate menschlicher PRs derselben Repos; Außenbezug AIDev (Mensch 76,8 %, nur 2025-Daten) | Merge ohne menschliche Code-Änderung gemessen und berichtet, kein festes Ziel vor Messung | GESAGT [aidev] |

Regeln dazu (ABGELEITET):
- B1 bis B4 sind Release-Gates des Coders je Kombination (Harness, Modell); für jede Änderung an Prompt, Harness-Version oder Plattform-Code läuft als Regression B1 plus B2 Refactoring (etwa 120 Aufgaben).
- Ein Gate-B-Ergebnis verfällt, wenn der Bezug sich ändert (neue Leaderboard-Version) oder der Harness wechselt; die Messung trägt Datum und Leaderboard-Stand. Gespeicherte Gate-Status sind damit nur Beleg, solange die Regel gilt (Grundsatz aus [07](../architecture/07-eval.md) Abschnitt 2).
- Gate B ist ausdrücklich ein **Nicht-schlechter-als-der-Harness-Test**, kein Überbieten: Weil die Hersteller-Harnesses selbst an der Spitze stehen, erreicht die Plattform das Weltniveau, wenn ihre Hülle (Sandbox, Egress, Self-Check, Prompts) den Harness nicht verschlechtert. Den Mehrwert gegenüber dem nackten Harness zeigen B6 und die Produkt-Checkliste (Abschnitt 2.3), nicht die Benchmarks.
- **Online-Metriken** (Abschnitt 6 von [07](../architecture/07-eval.md) ergänzen): Merge-Rate der Agent-PRs, Anteil mit menschlichem Code-Commit vor Merge, Review-Runden je PR, Zeit bis Merge, Anteil Rückfragen und Anteil beantworteter Rückfragen, Abbrüche durch `stop`, Anteil Übergaben (`handoff`), Kosten je gemergtem PR. Vergleichbar mit den öffentlichen Größen von [amplifying-autonomy] (Review-Anteil, Zeit bis Merge, Tests berührt).
- **Kosten der Messung** (Schätzung aus den Durchschnittskosten je Aufgabe im OpenHands Index 1,44 bis 5,54 USD [oh-index-api]): Regression (etwa 120 Aufgaben) rund 170 bis 670 USD je Kombination; voller Release-Korb (V2 Full 642, HARD 51, Atlas 160, ein Monat SWE-rebench, Terminal-Bench) grob 1.500 bis 6.000 USD je Kombination. Owner-Entscheidung OE-2.

### 3.4 [01-plugin-interfaces.md](../architecture/01-plugin-interfaces.md)

1. **Abschnitt 6 AgentRuntime:** `RuntimeCap` um `STEER` (Nachricht in laufende Sitzung) und `EXPORT_SESSION` (Transkript für Fortsetzung in lokalem Werkzeug) ergänzen. `resume?()` wird für den Coder Pflicht, sobald L2 gebaut ist; Harness ohne `RESUME` kann keine Rückfragen im Coding und meldet das als `none`.
2. **Abschnitt 6 Harness-Liste:** OpenHands SDK (MIT) als dritter Coder-Harness neben `claude-code` und `codex` aufnehmen, Begründung Open-Source-Vorgabe und fester Harness des OpenHands Index (direkter Vergleichswert). Steht heute nur als Quelle im [README](../architecture/README.md), nicht als geplanter Adapter.
3. **Abschnitt 8 ExecutionBackend:** `snapshot(tag)` wird für Rückfrage und Übergabe benötigt, nicht nur optional; `restore(snapshotRef)` fehlt als Gegenstück. `SandboxSpec.envSpec` um `layers: [installation, org, repo]` und `refresh: { periodHours, pinBuildId? }` ergänzen (Devin-Muster, [devin-bp]).
4. **TriggerSource Chat** (Slack, Teams) als eigene Zeile in der Plugin-Matrix vormerken; Stufe 9 bleibt.

### 3.5 [04-configuration-and-limits.md](../architecture/04-configuration-and-limits.md)

- `services.coder`: neue Schlüssel `best_of_n` (Standard 1), `max_children` (Standard 0, Zerlegung aus), `ask_timeout_h`, `allow_steer` (Standard true), `allow_handoff` (Standard true), `env_bootstrap: off | propose` (Standard `propose`). Alle nur verschärfend außer `best_of_n` (innerhalb Installations-Obergrenze).
- Limits je Kind-Step als eigener Schlüssel `step` neben `service`.

### 3.6 [08-roadmap.md](../architecture/08-roadmap.md)

- Stufe 2 Fertig-Kriterium "Gate B auf C2 gemessen und berichtet" ersetzen durch "B1 (HARD-51) und B2 Refactoring für die erste Kombination gemessen und berichtet"; Rückfrage im Coding (L2) und `@agent say` (L1) in Stufe 2 aufnehmen, weil sie den Zustandsautomaten ändern und später teuer nachzurüsten sind.
- Agentengeführter Umgebungsaufbau (L4) in Stufe 2, weil C1 auf fremden Repos sonst an der Umgebung scheitert.
- Übergabe (L3) und Zerlegung (L5) als neue Stufe zwischen 5 und 6 oder in Stufe 9; Best-of-N bleibt Stufe 9, aber mit Messung auf C1 schon in Stufe 2 (Kosten-Nutzen bekannt, bevor gebaut wird).

### 3.7 [07-eval.md](../architecture/07-eval.md) Abschnitt 3.2 C1 und Open Source

- C1 ist auf "3 bis 5 Firmen-Repos" gebaut und das Eval-Repo als "privat" festgelegt. Mit der Open-Source-Vorgabe (Owner, dritte Runde) braucht das Projekt (a) einen **öffentlichen** C1-Satz aus permissiv lizenzierten Repos mit Lizenz je Fall (Muster SWE-rebench: Lizenz des Upstream-Repos je Instanz gespeichert, [swe-rebench]) und (b) einen Mechanismus "eigener privater Satz je Installation" mit demselben Format. Gate A misst die Installation auf ihrem privaten Satz, Gate B auf den öffentlichen Sätzen. Folgeliste: [02](../architecture/02-services.md) Coder-DoD, [08](../architecture/08-roadmap.md) Stufe 2 und 7 nennen Firmen-Repos.

### 3.8 [09-decisions.md](../architecture/09-decisions.md)

Neue ADR-Kandidaten: "Gate B Coder über Harbor-Korb statt SWE-bench-Pro-Stichprobe", "Rückfrage und Nachsteuern über Snapshot plus `resume`, nie über eine lebende Sandbox ohne Lease", "Zerlegung nur bei disjunkten Pfaden, Integration deterministisch", "Claude Code nur als vom Nutzer beigestellte Laufzeit".

---

## 4. Owner-Entscheidungen

| Nr. | Frage | Empfehlung | Grund |
|---|---|---|---|
| OE-1 (Recht) | Darf die öffentliche Distribution Claude Code mitliefern (etwa im Worker-Image) oder nur anbinden? | Nur anbinden: Images enthalten kein Claude-Code-Binary; der Installer lädt es auf der Nutzerseite nach Zustimmung zu Anthropics Bedingungen. Standard-Harness der freien Distribution ist Codex CLI oder OpenHands SDK. Rechtliche Prüfung vor der ersten Veröffentlichung eines Images. | Lizenzdatei "All rights reserved", Nutzung nach Commercial Terms [cc-license] BELEGT; Codex Apache-2.0 und OpenHands MIT erlauben Weitergabe [codex-repo], [oh-sdk-repo] BELEGT |
| OE-2 (Geld) | Budget für Gate-B-Läufe je Harness-Modell-Kombination | Regression (etwa 120 Aufgaben) je Änderung an Coder oder Harness, voller Korb nur je Release-Kandidat; Startbudget je Kombination und Release in der Größenordnung von wenigen Tausend USD (Schätzung Abschnitt 3.3); Limits vorher und nachher messen | ohne B1 bis B4 bleibt Anforderung 1 für den Coder unbewiesen; die volle Messung bei jeder Änderung wäre unverhältnismäßig |
| OE-3 (Produkt) | Eval-Ergebnisse öffentlich veröffentlichen (Rohdaten, Logs, je Kombination), wie OpenHands Index? | Ja, im öffentlichen Repo als versionierte Ergebnisse mit Harbor-Logs; keine Werte aus privaten Nutzer-Sätzen | Glaubwürdigkeit eines Open-Source-Projekts hängt an nachprüfbaren Zahlen; OpenHands und Scale machen es so [oh-index-api], [scale-lb] |
| OE-4 (Konten, Geld) | Vergleichsläufe gegen Copilot, Devin, Cursor, Jules auf denselben Aufgaben (ergänzt O13) | Nein; Bezug nur über veröffentlichte Werte (Scale, Terminal-Bench) und öffentliche PR-Daten (AIDev, Amplifying) | eigene Konten kosten Geld und erlauben laut Nutzungsbedingungen oft keine Benchmarks (ungeprüft); die Harness-Bezüge sind öffentlich |

---

## 5. Offene Punkte

1. Terminal-Bench: Die Startseite nennt "Terminal-Bench 4.0", Tabelle und Aufgabenzahl nicht geladen; ungeprüft, ob 2.0 noch das offizielle Leaderboard ist.
2. SWE Atlas Refactoring und Test Writing: Datenverfügbarkeit, Lizenz und Harbor-Unterstützung ungeprüft (nur QnA öffentlich belegt).
3. SWE-Bench Pro V2: Scale meldete am 05/18 "issues with the leaderboard"; ob die V2-Werte davon betroffen sind, ungeprüft. Ob die V2-Werte Prozent gelöster Aufgaben oder ein skalierter Wert sind (ein Aggregator nennt "scale score"), ungeprüft.
4. OpenAI-Beiträge zu Verified und Pro: Primärseiten lieferten 403; Inhalt nur aus Suchauszügen (GESAGT).
5. Merge-Raten je Agent für 2026: kein belastbarer Primärwert gefunden (Amplifying meldet Review-Anteile, AIDev endet 2025).
6. Lizenzen von SWE-Sharp-Bench, SWE-bench Multilingual, SWE-rebench-Leaderboard und Multi-SWE-bench (Daten "other" mit CC0-Text) vor Nutzung im öffentlichen Eval-Repo prüfen.
7. Ob ein Claude-Code-Transkript aus der Sandbox in ein lokales Claude Code zum Fortsetzen übernommen werden kann (`--resume` liest nur lokale Historie, [cc-cloud]); für `@agent handoff` ist sonst nur Branch plus Zusammenfassung möglich. Ungeprüft.
8. Codex Cloud Best-of-N: Bereich 1 bis 4 und Auswahl durch Mensch oder System nur aus Drittquellen.
9. Augment: Status der Remote Agents (aufgegangen in Cosmos) ungeprüft.
10. Nutzungsbedingungen der Anbieter zu Benchmarks mit ihren Produkten (OE-4) ungeprüft.

---

## 6. Quellen (alle abgerufen 2026-10-31)

Benchmarks und Messstellen:
- [scale-lb] https://labs.scale.com/leaderboard (BELEGT, Seite gelesen: SWE-Bench Pro V2 Full und HARD, SWE Atlas)
- [scale-pro-v1] https://labs.scale.com/leaderboard/swe_bench_pro_public (BELEGT)
- [scale-pro-repo] https://github.com/scaleapi/SWE-bench_Pro-os (BELEGT)
- [scale-pro-hf] https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro (BELEGT)
- [scale-atlas] https://labs.scale.com/papers/sweatlas, https://scale.com/blog/swe-atlas, https://huggingface.co/datasets/ScaleAI/SWE-Atlas-QnA (GESAGT, Suchauszug)
- [openai-verified] https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/ (403; GESAGT über Suchauszug)
- [openai-noise] https://openai.com/index/separating-signal-from-noise-coding-evaluations (403; GESAGT über Suchauszug)
- [epoch-verified] https://epoch.ai/benchmarks/swe-bench-verified (BELEGT, Methodik)
- [oh-index-api] https://index.openhands.dev/api/leaderboard (BELEGT, Datenstand 2026-10-22)
- [tbench] https://www.tbench.ai/ und https://www.tbench.ai/leaderboard/terminal-bench/2.0 (Tabelle nicht geladen)
- [codesota-tb] https://www.codesota.com/browse/agentic/autonomous-coding/terminal-bench-2 (GESAGT, Suchauszug)
- [harbor] https://github.com/laude-institute/harbor (BELEGT)
- [swe-rebench] https://nebius.com/blog/posts/introducing-swe-rebench, https://arxiv.org/abs/2505.20411, https://huggingface.co/datasets/nebius/SWE-rebench-V2-PRs (GESAGT, Suchauszug)
- [multi-swe] https://huggingface.co/datasets/ByteDance-Seed/Multi-SWE-bench, https://arxiv.org/abs/2504.02605 (GESAGT)
- [swe-multi] https://www.swebench.com/multilingual (BELEGT)
- [polybench] https://amazon-science.github.io/SWE-PolyBench, https://arxiv.org/abs/2504.08703 (GESAGT)
- [swe-sharp] https://arxiv.org/abs/2511.02352 (GESAGT)
- [swe-lancer] https://github.com/openai/swelancer-benchmark, https://arxiv.org/abs/2502.12115 (GESAGT)
- [metr] https://arxiv.org/abs/2503.14499 (GESAGT; neuere Werte nur Drittberichte)
- [morph-pro] https://www.morphllm.com/swe-bench-pro (GESAGT, Aggregator)

Markt:
- [octoverse-2026] https://github.blog/news-insights/octoverse/octoverse-commits-pushes-reach-new-highs-in-2026-as-developers-build-with-agents/ (GESAGT, Primärseite gelesen, Datum 2026-10-28)
- [amplifying] https://amplifying.ai/coding-agents/github-copilot (GESAGT, nur Suchauszug)
- [amplifying-autonomy] https://amplifying.ai/coding-agents/autonomy (BELEGT, Seite gelesen)
- [aidev] https://github.com/SAILResearch/AI_Teammates_in_SE3, https://emergentmind.com/topics/aidev-dataset (GESAGT, Sekundärzusammenfassung)

Anbieter:
- [cc-cloud] https://code.claude.com/docs/en/claude-code-on-the-web.md (BELEGT, Wortlaut)
- [cc-selfhosted] https://code.claude.com/docs/en/self-hosted-environments.md (BELEGT, Wortlaut)
- [cc-license] https://github.com/anthropics/claude-code/blob/main/LICENSE.md (BELEGT, Wortlaut)
- [cx-cloud] https://learn.chatgpt.com/docs/cloud (BELEGT; Weiterleitung von developers.openai.com/codex/cloud)
- [cx-bon] https://codex.danielvaughan.com/2026/04/01/codex-cloud-exec-best-of-n-attempts/ (GESAGT)
- [codex-repo] https://github.com/openai/codex (BELEGT, Lizenz)
- [cp-about] https://docs.github.com/en/copilot/concepts/agents/coding-agent/about-coding-agent (BELEGT)
- [cp-env] https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/customize-the-agent-environment (BELEGT)
- [cp-validate] https://github.blog/changelog/2026-03-18-configure-copilot-coding-agents-validation-tools/ (BELEGT)
- [devin-bp] https://docs.devin.ai/onboard-devin/environment/blueprints.md (BELEGT)
- [devin-tools] https://docs.devin.ai/work-with-devin/devin-session-tools.md (BELEGT)
- [devin-adv] https://docs.devin.ai/work-with-devin/advanced-capabilities.md (BELEGT)
- [devin-llms] https://docs.devin.ai/llms.txt (BELEGT, Seitenverzeichnis)
- [cu-cloud] https://cursor.com/docs/cloud-agent (BELEGT)
- [jules-tasks] https://jules.google/docs/running-tasks (BELEGT)
- [jules-critic] https://developers.googleblog.com/en/meet-jules-sharpest-critic-and-most-valuable-ally/ (GESAGT, Suchauszug)
- [factory-llms] https://docs.factory.com/llms.txt (BELEGT, Seitenverzeichnis)
- [factory-missions-web] https://docs.factory.com/missions/overview.md (BELEGT)
- [factory-opencompute] https://docs.factory.com/opencompute/overview.md (BELEGT)
- [factory-spec-web] https://docs.factory.ai/cli/configuration/cli-reference (GESAGT, Suchauszug)
- [oh-repo] https://github.com/OpenHands/OpenHands (BELEGT)
- [oh-sdk-repo] https://github.com/OpenHands/software-agent-sdk (BELEGT)
- [warp-env] https://docs.warp.dev/agent-platform/cloud-agents/environments (GESAGT, Suchauszug)
- [amp] https://www.ampcode.com/news (GESAGT, Suchauszug)
- [augment] https://docs.augmentcode.com/feature-availability, https://www.augmentcode.com/blog/production-ready-ai-remote-agents-now-available-for-all-augment-code-users (GESAGT, Suchauszug)
