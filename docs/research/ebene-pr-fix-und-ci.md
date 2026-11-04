<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
> Research note, dated 2026-11-01, not binding. Kept in German as written (ADR-53); the binding documents are docs/architecture and docs/design.

# Ebene PR-Fix und CI: Standard, Fähigkeiten, Messung, Lücken

**Dated, not binding.** Datierte Recherche, Stand 2026-10-31, nicht verbindlich und nicht übersetzt; verbindlich ist die Plattform-Doku ([docs/architektur/](../architecture/README.md)).

Stand und Abrufdatum aller Webquellen: 2026-10-31. Einstufungen wie in [docs/architektur/README.md](../architecture/README.md) Abschnitt 6: BELEGT (Primärquelle selbst gelesen), GESAGT (Herstelleraussage, Marketing, Drittbericht, Suchauszug), ABGELEITET (eigener Schluss), VERMUTET. Die Webseiten wurden mit einem Abrufwerkzeug gelesen, das den Inhalt durch ein kleines Modell zusammenfasst; Zitate sind deshalb sinngemäß und kurz. Was nur aus einem Suchauszug stammt, steht als GESAGT da, auch wenn die Quelle eine Herstellerseite ist.

Dieser Bericht ergänzt [02-services.md](../architecture/02-services.md) Abschnitt 5 (PR-Fixer), [07-eval.md](../architecture/07-eval.md) Abschnitte 3.4 und 4. Was dort schon belegt ist (Bugbot höchstens 3 Versuche, Copilot Agent Merge als Messlatte), wird hier nicht wiederholt, sondern nur korrigiert oder erweitert.

---

## 1. Urteil (Kurzfassung)

1. **Es gibt keinen einzelnen Weltstandard und keinen unabhängigen Produkt-Benchmark für PR-Fix.** Kein Anbieter veröffentlicht Werte auf einem gemeinsamen Datensatz. Öffentliche Zahlen sind ausschließlich Herstellerzahlen auf eigenen Daten (Bugbot: über 35 % der Autofix-Änderungen werden gemerged; Nx: etwa 60 % und mehr der CI-Fixe angenommen; beides GESAGT). Die Spitzengruppe ergibt sich deshalb aus Funktionsumfang und Marktstellung, nicht aus einer Messung (ABGELEITET).
2. **Spitzengruppe Stand 2026-10-31 (ABGELEITET):**
   - **GitHub Copilot** hat die breiteste Abdeckung: Agent Merge "Watch and fix" für rote Actions und Konflikte direkt in der Merge-Box, auch zusammen mit Auto-Merge (seit 2026-10-28); `@copilot` auf jedem PR für Review-Kommentare und rote Tests (seit 2026-03-24); Copilot Autofix für Code-Scanning-Alarme; Dependabot-Alarme an Agenten zuweisbar (seit 2026-04-07). Schwäche: nur GitHub, keine Fork-PRs.
   - **Cursor Bugbot Autofix** hat die einzige veröffentlichte Merge-Quote eines Fix-Agenten (über 35 %, GESAGT) und die sauberste Konfigurationsregel (Repo-Datei darf den Modus nur senken, BELEGT).
   - **Nx Self-Healing CI** ist der Spezialstandard für CI-Reparatur: Fix nur nach Verifikation, Auto-Apply nur für Aufgabenmuster mit hoher Verifikationsquote, Flakes werden neu gestartet statt "repariert" (BELEGT), aber an Nx-Workspaces gebunden.
   - **Gitar** liefert die beste offengelegte Fehlerklassifikation (vom PR verursacht oder nicht, Retry höchstens einmal je Commit, Recovery nach eigenem kaputten Fix höchstens 3 Commits) und liest Logs von elf CI-Systemen (BELEGT).
   - **Abhängigkeiten:** Renovate ist der offene Standard (AGPL-3.0, über 90 Paketmanager, 6 Plattformen plus experimentelle, BELEGT); Dependabot ist auf GitHub Standard, der Kern ist MIT (BELEGT).
   - **Merge Queues** (GitHub, Mergify, Trunk, Graphite) sind keine Fix-Agenten, sondern Nachbarn: Sie entscheiden, wann gemerged wird, und erzeugen eigene Fehlerfälle (rote Queue-Läufe).
3. **Unser Entwurf deckt den Kern ab** (Review-Threads, rote CI, Konflikte, Verbote, 3 Versuche, `expectedOldSha`), hat aber zehn Lücken zum Niveau der Spitzengruppe; die wichtigsten: keine Klassifikation "vom PR verursacht oder nicht" mit Retry statt Fix, keine Dauerschleife auf menschlichen PRs (O9 verbietet sie), keine Behandlung von Dependency-PRs (das Lockfile-Verbot blockiert genau diesen Fall), kein Schutz vor Bot-zu-Bot-Schleifen, CI-Logs nur über den SCM-Provider statt über ein eigenes CI-Plugin, keine Sicherheits- und SonarQube-Befunde als Eingang mit eigenem Testsatz.
4. **Abhängigkeits-Updates werden keine eigene Ebene.** Renovate bleibt das Werkzeug, das Updates erzeugt; unsere Plattform hängt sich als PR-Fixer-Profil `dependency_update` an dessen PRs (Fix bei Breaking Changes) und lässt Renovate selbst optional mitlaufen. Grund: Renovate deckt Paketmanager und Plattformen ab, die wir nie nachbauen würden, und Merge Confidence beruht auf privaten Mend-Daten, die nicht nachbaubar sind (Abschnitt 2.6).
5. **Gate B wird messbar** über öffentliche Datensätze je Fehlerart (CI-Repair-Bench, JetBrains LCA CI Builds Repair, BUMP, Merge-Bench, c-CRAB) plus Online-Metriken mit Herstellerbezug. Fast alle Datensätze haben eine ungeprüfte oder fehlende Datenlizenz; für ein öffentliches Repo muss das vor Nutzung geklärt werden. **Neu belegt:** In der bothy-Historie gibt es 0 Commits von CodeRabbit (selbst gezählt), damit ist der in [07] Abschnitt 4 vorgesehene Gate-B-Vergleich "F1 nicht schlechter als CodeRabbit Autofix auf bothy" ohne Vergleichslauf nicht möglich.

---

## 2. Befunde mit Quellen

### 2.1 (entfällt)

Die Auswertung der CodeRabbit-Herstellerdoku entfällt in dieser Fassung; sie wird nach [10](../architecture/10-standards-per-layer.md) Abschnitt 16 nicht weitergeführt.

### 2.2 GitHub Copilot

| Befund | Einstufung | Quelle |
|---|---|---|
| **Agent Merge in der Cloud** (2026-10-28): "Watch and fix" in der Merge-Box; Wahl, ob rote Actions-Workflows, Konflikte oder beides behoben werden; Arbeit in einer Cloud-Entwicklungsumgebung; als Standard für alle eigenen PRs einstellbar; zusammen mit Auto-Merge "merges it as soon as all requirements are met"; bezahlter Copilot-Plan | BELEGT | [copilot-merge] |
| Vorläufer: Konflikte per `@copilot` (2026-03-26), "Fix with Copilot"-Button für Konflikte (2026-04-13), Agent Merge im Copilot-App-Preview inklusive Antwort auf Review-Kommentare und Merge (2026-05-14), in VS Code mit Review-Feedback, roten Checks, Konflikten und Workflow-Reruns (Preview, September 2026) | GESAGT (Suchauszug) | [copilot-merge-search] |
| **`@copilot` auf jedem PR** (2026-03-24): Beispiele "Fix the failing tests", "Address this comment"; validiert mit Tests und Linter, pusht seitdem auf den bestehenden PR statt einen neuen zu öffnen; Fork-PRs nicht unterstützt; alle bezahlten Pläne, bei Business und Enterprise nach Admin-Freigabe | BELEGT | [copilot-anypr] |
| Auf Copilot-PRs: Actions laufen nach einem Push von Copilot standardmäßig nicht automatisch, ein Mensch klickt "Approve and run workflows"; Approve des Auftraggebers zählt nicht für den Branch-Schutz; Hinweis auf Änderungen unter `.github/workflows/` | BELEGT | [copilot-reviewprs] |
| Copilot reagiert nur auf Kommentare von Nutzern mit Schreibrecht; Empfehlung, Review-Kommentare zu bündeln; neue Sitzung erinnert sich an die vorige | GESAGT (Suchauszug aus älterer Doku) | [copilot-reviewprs-search] |
| **Copilot Autofix (Code Scanning)**: ein Vorschlag je Alarm aus LLM, Codebasis und Scanning-Analyse; an, sobald CodeQL an ist; für alle öffentlichen Repos, privat nur mit GitHub Code Security; zusätzlich "agentic autofix", der den Fix durch erneuten CodeQL-Lauf prüft und einen Draft-PR öffnet | BELEGT | [gh-autofix] |
| **Copilot-Autofix-Testharness**: über 2.300 Alarme aus öffentlichen Repos, deren markierter Code Testabdeckung hat; alle Vorschläge unverändert gemerged, dann Code Scanning und Unit-Tests; vier Fragen: Alarm weg, neue Alarme, Syntaxfehler, Testausgabe geändert; Ergebnis nur in Worten ("for many of the test alerts ... could be committed as-is") | BELEGT | [gh-autofix-ru] |
| **Dependabot-Alarme an Agenten** (2026-04-07, GA): "Assign to Agent" mit Copilot, Claude oder Codex; mehrere Agenten je Alarm, je ein eigener Draft-PR zum Vergleich; Anwendungsfälle Breaking Changes, Downgrade bei kompromittiertem Paket, Fälle außerhalb der Regel-Engine; braucht Code Security und Copilot mit Coding Agent | BELEGT | [gh-depagent] |

### 2.3 Cursor Bugbot Autofix

| Befund | Einstufung | Quelle |
|---|---|---|
| Autofix startet je Review mit Bugs einen Cloud Agent, pusht auf den PR-Branch oder einen neuen Branch, fasst im PR zusammen; eigener Check `Cursor Bugbot Autofix` nur mit `success` oder `neutral` | BELEGT | [cursor-bugbot] |
| Modi Off, Create New Branch (empfohlen), Commit to Existing Branch; `autofix.mode` in `.cursor/config/bugbot.yaml` kann den Dashboard-Modus nur senken; Commit auf bestehenden Branch höchstens 3 Versuche je PR; GitLab und Bitbucket nur bestehender Branch, Azure DevOps gar nicht; Stacked-PRs auf GitHub bekommen den Fix auf einem neuen Branch, angewendet per `@cursor push <sha>` | BELEGT | [cursor-bugbot] |
| "Over 35% of Bugbot Autofix changes are merged into the base PR"; Resolution Rate von 52 % auf 76 % in sechs Monaten; Agenten testen in eigenen VMs | GESAGT (Herstellerblog, selbst gelesen) | [cursor-autofix-blog] |

### 2.4 Nx Self-Healing CI, Gitar, Devin, Graphite

| Befund | Einstufung | Quelle |
|---|---|---|
| **Nx**: `npx nx fix-ci` als letzter Schritt mit `if: always()`, No-op bei grüner CI; Kontext aus Projektgraph und Build-Konfiguration; Vorschlag im Editor, als PR-Kommentar mit Begründung, Diff und Buttons oder in der Nx-Cloud-UI; `nx apply-locally` | BELEGT | [nx-shci] |
| Nx Auto-Apply nur, wenn alle drei gelten: Aufgabe passt auf Glob, Agent "highly confident", Fix "explicitly verified"; Voreinstellung "Deterministic Nx checks" (format, sync, conformance); Exclude schlägt Include; `.nx/ci-config.yaml` überschreibt das Dashboard | BELEGT | [nx-shci] |
| Nx: Flakes werden per leerem Commit neu gestartet statt repariert; nie Fixe auf `main`, `master`, `trunk` und ähnlichen; Drafts nur nach Einstellung; `.nx/SELF_HEALING.md` hat Vorrang vor `CLAUDE.md`; GitHub, GitLab, Azure DevOps, Bitbucket | BELEGT | [nx-shci] |
| Nx zeigt je Aufgabe "verification rate" (wie oft der Fix beim Rerun bestand) und Konfidenz, empfiehlt danach Auto-Apply | GESAGT (Herstellerblog, Suchauszug) | [nx-autoapply] |
| Nx: "about 60%+ of these fixes are accepted"; "time to green" minus 50 % | GESAGT (Marketing, Suchauszug) | [nx-diy], [nx-ttg] |
| **Gitar**: liest GitHub Actions, GitLab, Bitbucket und Azure Pipelines ohne Setup, Jenkins, CircleCI, Concourse, Buildkite, TeamCity, Harness und Bitrise mit eigenem Credential über den Status-Link; gleiche Fehler über Jobs werden nur einmal analysiert; Läufe veralteter Commits ignoriert | BELEGT | [gitar-ci] |
| Gitar trennt Fehler des PRs von Flakes, Infrastruktur und Fehlern des Ziel-Branches; nicht verursachte Fehler werden "at most once per commit" neu gestartet; Fix je nach `auto-apply` als Vorschlag oder Commit; bei erneutem Fehler neuer Versuch mit der Historie früherer Versuche; Recovery, wenn ein eigener Fix eine grüne CI rot macht, "stops after three consecutive Gitar commits" | BELEGT | [gitar-ci] |
| Gitar Enterprise: Agent läuft in der eigenen CI des Kunden, eigene LLM-Keys möglich | GESAGT (Suchauszug) | [gitar-search] |
| **Devin**: ignoriert Bot-Kommentare standardmäßig, "to prevent infinite feedback loops"; Allowlist je Bot oder alle Bots; Lint- und CI-Fehler werden immer bearbeitet; Warnung vor Endlosschleife Review-Bot und Devin | GESAGT (Suchauszug der Herstellerdoku) | [devin-bots] |
| **Graphite**: Chat am PR mit "Debug CI failures" und Ein-Klick-Fix; Cursor Cloud Agents aus Graphite für "Fix failing CI check" | GESAGT (Suchauszug) | [graphite-chat] |

### 2.5 Flakes und Merge Queues (Nachbarn der Ebene)

| Befund | Einstufung | Quelle |
|---|---|---|
| **Trunk Flaky Tests**: Monitore Pass-on-Retry, Failure Rate und Failure Count, je Branch-Art eigene Schwellen; "Merge queue failures are suspicious because the code has already passed PR checks"; Quarantäne lässt Tests laufen, ohne den CI-Job scheitern zu lassen; Erkennung höchstens 20 Minuten nach Upload | BELEGT | [trunk-detect], [trunk-flaky] |
| **Mergify Merge Queue**: spekulative Läufe bis 128 parallel (GitHub nativ bis 100, laut Mergify), Batches, Prioritäten, zweistufige CI, Pause, Monorepo-Scopes | BELEGT als Herstellerdoku, Vergleichszahl zu GitHub GESAGT | [mergify-mq] |
| **Renovate und Merge Queues**: unterstützt GitHub Merge Queue (`merge_group`) und GitLab Merge Trains ab 17.11 | BELEGT | [renovate-automerge] |

### 2.6 Abhängigkeits-Updates: Renovate und Dependabot

| Befund | Einstufung | Quelle |
|---|---|---|
| Renovate: Lizenz AGPL-3.0-only; GitHub, GitLab, Bitbucket, Azure DevOps, Gitea, Forgejo, experimentell CodeCommit, Gerrit, SCM-Manager; "over 90 different package managers"; Betrieb per `npx renovate`, GitHub Action, GitLab Runner | BELEGT | [renovate] |
| Mend Renovate Community und Enterprise Self-Hosted: Container-Images, Nutzung unter Mend Terms of Service, Lizenzschlüssel per Formular nötig; Doku im Repo MIT | BELEGT | [renovate-ce] |
| Merge Confidence (Age, Adoption, Passing, Confidence) beruht auf Daten der Mend-App seit 2017; "The algorithm ... is private"; nur Go, npm, Maven, PyPI, NuGet, Packagist, RubyGems; Badges auch self-hosted; Workflows wie "automerge Very High" nur für zahlende Mend-Kunden oder OSS in Mend Community Cloud | BELEGT | [renovate-mc] |
| Renovate Automerge: wartet auf grüne Checks, standardmäßig über das Plattform-Automerge, höchstens ein Automerge je Ziel-Branch und Lauf | BELEGT | [renovate-automerge] |
| Pusht jemand einen eigenen Commit auf einen Renovate-Branch (etwa um Tests zu reparieren), stoppt Renovate alle Updates dieses Branches und warnt per Kommentar; die Rebase-Checkbox oder das Label `rebase` verwirft solche Änderungen | GESAGT (Suchauszug der Renovate-Doku) | [renovate-rebase] |
| Dependabot-Kern: MIT; Dependabot CLI ist der empfohlene Weg für eigenständigen Betrieb, erzeugt Diffs, öffnet aber keine PRs; Ziel-Plattformen laut README GitHub, GHE, Azure DevOps, GitLab, Bitbucket, CodeCommit | BELEGT | [dependabot-core] |
| bothy nutzt Renovate (`renovate.json`: wöchentlich, `minimumReleaseAge` 7 Tage, Majors über Dashboard-Freigabe, Sicherheitsupdates sofort), dazu `.coderabbit.yaml` und `sonar-project.properties`; bothy-Lizenz Apache-2.0 | BELEGT (selbst gelesen) | [bothy-repo] Commit `4485084b8`, `renovate.json`, `LICENSE` |

**Bewertung eigene Ebene oder Integration (ABGELEITET):**
- Was Renovate tut (Versionen finden, Manifeste und Lockfiles deterministisch ändern, gruppieren, planen, Dashboard, Automerge, Queue), ist kein Agentenproblem und in über 90 Paketmanagern gereift. Ein Nachbau wäre teuer und schlechter.
- Was Renovate nicht tut, ist das, was die Spitzengruppe 2026 dazugebaut hat: Code anpassen, wenn ein Update bricht (GitHub "Assign to Agent", BELEGT [gh-depagent]). Das ist genau ein PR-Fixer-Fall mit der Eingabe "Update-PR plus rote CI".
- Merge Confidence ist proprietär und nicht nachbaubar; eine eigene Ersatzgröße kann nur aus den eigenen Installationen kommen (ABGELEITET).
- Folge: keine eigene Ebene; Renovate (oder Dependabot) als externer Erzeuger, PR-Fixer mit Profil `dependency_update`, das Lockfile und Manifest nicht vom Agenten, sondern vom Paketmanager neu erzeugt.
- **Konflikt mit Renovate:** Ein Fix-Commit auf dem Renovate-Branch beendet dessen Pflege (GESAGT [renovate-rebase]). Deshalb liefert der Fixer bei Bot-PRs standardmäßig einen gestapelten PR auf den Update-Branch oder übernimmt den Branch ausdrücklich mit Vermerk; das ist eine Konfigurationsfrage, keine Owner-Frage.

### 2.7 Öffentliche Benchmarks und Datensätze

| Datensatz | Inhalt | Bezugswert | Lizenz | Einstufung |
|---|---|---|---|---|
| **CI-Repair-Bench** (arXiv 2604.27148, 2026-04) | 567 echte GitHub-Actions-Fehler aus 103 Python-Repos, 12 Fehlerarten; Erfolg nur, wenn der Original-Workflow wieder grün ist | bestes Modell 18,9 %; Format und Lint leicht, Umgebung, Abhängigkeiten, Konfiguration schwer | Paper CC BY 4.0; Daten und Code: Veröffentlichung auf der Abstract-Seite nicht genannt, **ungeprüft** | BELEGT (Abstract) |
| **JetBrains LCA CI Builds Repair** | 68 Fälle (Standard) plus 144 (alt), Python-Repos unter MIT, Apache-2.0, BSD; Bewertung pusht Commits nach GitHub und liest die Workflow-Ergebnisse | Baselines im Paper, **ungeprüft** | Datenlizenz auf der Karte nicht genannt, **ungeprüft** | BELEGT (Datensatzkarte) |
| **BUMP** (SANER 2024) | 571 reproduzierbare Breaking Dependency Updates aus 153 Java/Maven-Projekten, je zwei Docker-Images, über 250 GB | Byam: o3-mini 27 % Build-Erfolg auf 103 Fällen; FSE 2025: agentisch bis 23 % Test-Erfolg | Code MIT (BELEGT); Zenodo-Daten **ungeprüft** | Code BELEGT, Bezugswerte GESAGT (Suchauszug) |
| **ConGra** (arXiv 2409.14121) | 44.948 Konflikte aus 34 Projekten (C, C++, Java, Python), 7 Schwierigkeitsklassen | Ähnlichkeit über 80 % gilt als richtig, laut Merge-Bench semantisch zu schwach | **keine LICENSE-Datei im Repo** (BELEGT), Daten auf figshare **ungeprüft** | Zahlen GESAGT |
| **Merge-Bench** (arXiv 2605.25890) | 7.938 Konflikt-Hunks aus 1.439 Repos | **ungeprüft** | Paper CC BY 4.0, Daten **ungeprüft** | GESAGT (Suchauszug) |
| **c-CRAB** (arXiv 2603.23448) | aus menschlichen Review-Kommentaren werden ausführbare Tests (rot vorher, grün nachher); 184 PRs, 234 Tests, 67 Repos | Kombination der Agenten löst etwa 40 %; Einzelwerte Claude Code 32,1 %, Devin 24,8 %, PR-Agent 23,1 %, Codex 20,1 % (diese Werte messen Reviews, nicht Fixes) | Paper CC BY 4.0, Daten **ungeprüft** | 40 % BELEGT (Abstract), Einzelwerte GESAGT |
| **CodeReviewQA** (ACL 2025 Findings) | 900 geprüfte Beispiele "Code an Review-Kommentar anpassen", 9 Sprachen, Hugging Face | 72 Modelle bewertet | **ungeprüft** | GESAGT (Suchauszug) |
| **OmniCode** (arXiv 2602.02262) | 1.794 Aufgaben, darunter "Responding to code review" | **ungeprüft** | **ungeprüft** | GESAGT (Suchauszug) |
| **Copilot-Autofix-Methode** | kein Datensatz, aber übernehmbares Prüfschema mit vier Fragen | nur verbal | Methode, keine Daten | BELEGT [gh-autofix-ru] |

### 2.8 Eigene Prüfung der bothy-Historie

- `git log --all` im bothy-Repo ([bothy-repo], alle Branches, Stand 2026-10-31, 4.910 Commits): 0 Commits mit Autor oder `Co-authored-by` CodeRabbit; nur 3 Commits, die CodeRabbit im Betreff nennen (Konfigurationsänderungen des Maintainers); 2 Commits von `dependabot[bot]`; 0 Commits mit Autor Renovate (BELEGT, selbst gezählt).
- Folge (ABGELEITET): Die 245 adressierten Befunde in R1/F1 wurden von Menschen (oder Agenten des Maintainers unter dessen Namen) umgesetzt, nicht von CodeRabbit Autofix. F1 bleibt als Testsatz gültig ("gleiches Problem gelöst wie der menschliche Commit"), ein Vergleich mit CodeRabbit Autofix aus der Historie ist aber nicht möglich. Der offene Punkt in [07] Abschnitt 7 ("ob CodeRabbit-Fixe in der bothy-Historie vorliegen: ungeprüft") ist damit beantwortet: nein, soweit an Autor und Trailer erkennbar. Ob Squash-Merges CodeRabbit-Commits unter dem Namen des Maintainers verbergen, ist ungeprüft.

---

## 3. Fähigkeits-Checkliste des Standards

Spalte "bei uns": Fundstelle in `docs/architektur`. "ja" heißt beschrieben, nicht gebaut.

| # | Fähigkeit | wer sie hat | Beleg | bei uns |
|---|---|---|---|---|
| 1 | Einzelnen Review-Thread per Befehl im Thread beheben | Copilot | [copilot-anypr] | ja, `@agent fix thread` ([03] Abschnitt 4, [02] 5) |
| 3 | Beliebige menschliche Review-Kommentare umsetzen | Copilot, Devin | [copilot-anypr], [devin-bots] | teilweise: `source: review_threads` nennt `agent_prompt`; menschliche Threads ohne `agent_prompt` nicht beschrieben ([02] 5 Stufe 1) |
| 4 | Dauerschleife "watch and fix" bis grün | Copilot Agent Merge, Gitar `auto-apply:on` | [copilot-merge], [gitar-ci] | teilweise: nur Agent-PRs (`auto_on: [ci_failed_agent_pr]`, [04]) und Pipeline-Stufe mit `max_rounds: 3` |
| 5 | Watch-Modus als persönlicher Standard für alle eigenen PRs | Copilot | [copilot-merge] | nein |
| 6 | Zusammenspiel mit Auto-Merge des Hosters | Copilot, Renovate | [copilot-merge], [renovate-automerge] | teilweise: eigenes Merge-Gate nur für Agent-PRs ([03] 1a) |
| 7 | Lieferung als Commit oder gestapelter PR, wählbar | Bugbot | [cursor-bugbot] | ja, `commit_mode: agent_branch_or_stacked_pr` ([04]) |
| 9 | Repo-Konfiguration darf Autofix nur senken | Bugbot | [cursor-bugbot] | teilweise: allgemeine Vererbung "nur verschärfend" ([04]), für `prfixer` nicht ausdrücklich |
| 10 | Versuchsgrenze je PR | Bugbot 3, Gitar Recovery 3 | [cursor-bugbot], [gitar-ci] | ja, 3 ([02] 5 Stufe 6) |
| 11 | Recovery: eigener Fix hat grüne CI rot gemacht | Gitar | [gitar-ci] | nein |
| 12 | Fehler dem PR zuordnen oder nicht | Gitar | [gitar-ci] | ja, Stufe 2 "Ursache prüfen" ([02] 5) |
| 13 | Nicht verursachte Fehler einmal je Commit neu starten | Gitar, Nx (Flakes) | [gitar-ci], [nx-shci] | nein (heute `cannot_fix`) |
| 14 | Flake-Erkennung und Quarantäne als Eingang | Trunk, Nx | [trunk-detect], [nx-shci] | nein |
| 15 | Gleiche Fehler über Jobs deduplizieren, veraltete Läufe ignorieren | Gitar | [gitar-ci] | nein |
| 16 | CI-Logs von Fremd-CI (Jenkins, CircleCI, Buildkite, TeamCity ...) | Gitar | [gitar-ci] | nein: nur `ciFailureLogs` im SCMProvider mit `CI_LOGS` ([01] 5) |
| 20 | Echte CI als Wahrheit, nicht Selbstbehauptung | Nx | [nx-shci] | teilweise: Self-Check im Worker; Warten auf echte CI nach Push nicht als Bedingung für `fixed` festgelegt |
| 21 | Auto-Apply nur für Fehlerklassen mit hoher Verifikationsquote | Nx | [nx-shci], [nx-autoapply] | nein |
| 22 | Repo-Anweisungen eigens für Fixes | Nx `.nx/SELF_HEALING.md` | [nx-shci] | teilweise: `.agents/rules/` allgemein ([02] 7) |
| 26 | Code-Scanning-Alarm beheben, Prüfung über erneuten Scan | Copilot Autofix | [gh-autofix] | teilweise: `source: security_alert` im `FixRequest`, keine Stufen, kein Testsatz |
| 27 | Abhängigkeits-Update mit Breaking Change reparieren | Copilot (Dependabot-Zuweisung) | [gh-depagent] | nein |
| 28 | Mehrere Agenten auf denselben Fehler, Ergebnisse vergleichen | GitHub Dependabot-Zuweisung | [gh-depagent] | teilweise: Best-of-N nur beim Coder ([02] 2) |
| 29 | Bot-Kommentare nur aus Allowlist, Schutz vor Bot-Schleifen | Devin | [devin-bots] | teilweise: Router filtert `actor.kind == 'human'` für Reviews ([04]); für den Fixer nicht festgelegt |
| 30 | Eigener Check nur `success`/`neutral` | Bugbot | [cursor-bugbot] | nein (kein Check für den Fixer festgelegt) |
| 31 | Nur Nutzer mit Schreibrecht lösen aus | Copilot | [copilot-reviewprs-search] | ja, `min_permission: { scm: write }` ([04]) |
| 32 | Fork-PRs ausgeschlossen | Copilot | [copilot-anypr] | ja ([05] Abschnitt 3) |
| 33 | Fixe nie auf Default- und Trunk-Branches | Nx | [nx-shci] | ja indirekt (Push nur `agent/*`, [01] 5) |
| 35 | Lokal anwenden statt Commit | Nx `apply-locally`, Bugbot "Fix in Cursor" | [nx-shci], [cursor-bugbot] | teilweise: `agent_prompt` je Befund ([02] 3) |
| 36 | Fehler im Merge-Queue-Lauf beheben | Trunk (als Signal) | [trunk-detect] | nein (kein Ereignis `queue_failed`) |
| 37 | Unterstützte Hoster: GitHub, GitLab, Azure DevOps, Bitbucket | Nx, Gitar | [nx-shci], [gitar] | teilweise: Plugin-Modell vorhanden, `CI_LOGS` je Provider nicht als Matrix belegt ([01]) |

Die Nummern 2, 8, 17, 18, 19, 23, 24, 25 und 34 entfallen in dieser Fassung: sie stützten sich nur auf Herstellerdoku oder private Vorarbeiten, deren Auswertung nach [10](../architecture/10-standards-per-layer.md) Abschnitt 16 nicht weitergeführt wird.

---

## 4. Messung: Benchmarks, Online-Metriken, Gate B konkret

### 4.1 Offline-Testsätze (Ergänzung zu [07] Abschnitt 3.4)

| Satz | Fehlerart | Quelle | Erfolgskriterium | Status |
|---|---|---|---|---|
| F1 | Review-Kommentar umsetzen | 245 adressierte bothy-Befunde (bestehend) | Richter "gleiches Problem gelöst" plus Build und Tests grün plus keine neuen Reviewer-Befunde | bestehend; Vergleich mit CodeRabbit nur per Vergleichslauf (Abschnitt 2.8) |
| F1x (neu) | Review-Kommentar umsetzen, ausführbar | c-CRAB-Prinzip: je Kommentar ein Test, rot vorher, grün nach dem menschlichen Fix; zuerst auf bothy erzeugen (Apache-2.0), c-CRAB-Daten nur nach Lizenzprüfung | Anteil Kommentare, deren Test nach dem Fix grün ist und alle übrigen Tests grün bleiben | neu |
| F2 | rote CI, eigene Repos | bestehend, aber für ein öffentliches Projekt auf öffentliche Repos umstellen (bothy statt Firmen-Repos) | wie [07] | bestehend, anpassen |
| F2p (neu) | rote CI, öffentlich vergleichbar | CI-Repair-Bench (falls Daten veröffentlicht), sonst JetBrains LCA CI Builds Repair | Original-Workflow grün, keine neuen Fehler, Verbote 0 | neu, Lizenz und Konto offen (Abschnitt 6) |
| F3 | Konflikt | Startgröße 20 (bestehend, Schätzung); extern Merge-Bench nach Lizenzprüfung | Build, Tests und Lint grün, keine Marker; bei Sicherheitslogik Ablehnung ohne Commit | bestehend, erweitern |
| F4 (neu) | Breaking Dependency Update | BUMP (Java/Maven), Teilmenge wegen 250 GB; eigene Fälle aus Renovate-PRs mit roter CI | Build und Tests grün, Manifest und Lockfile nur durch Paketmanager geändert, kein Pin zurück auf die alte Version | neu |
| F5 (neu) | Sicherheits- und Analysebefund (Semgrep, CodeQL, SonarQube) | eigene Fälle aus bothy (SonarQube und CodeQL sind dort angeschlossen, BELEGT) | Copilot-Autofix-Schema: Befund weg, keine neuen Befunde, kein Syntaxfehler, Testausgabe unverändert | neu |
| F6 (neu) | Nicht verursachter Fehler | Fälle, in denen der Ziel-Branch oder ein Flake rot ist | Ergebnis `not_caused_by_pr` plus höchstens ein Rerun je Commit, 0 Code-Änderungen | neu |

### 4.2 Online-Metriken je Fix-Art

- **Fix-Annahmequote:** Anteil Fix-Commits bzw. Fix-PRs, die ohne Revert und ohne menschliche Änderung an denselben Zeilen in den Ziel-PR gemerged werden (Bugbot-Definition "merged into the base PR", [cursor-autofix-blog]).
- **Verifikationsquote je Fehlerklasse:** Anteil Fixe, nach denen die echte CI für genau den roten Job grün wird (Nx-Prinzip, [nx-autoapply]).
- **Time to green:** Zeit vom ersten roten Job bis grün, mit und ohne Fixer im selben Repo (Nx-Bezug minus 50 %, GESAGT).
- **Versuche je Erfolg, Recovery-Fälle, Rerun-Quote** (Gitar-Prinzip).
- **Verbotsverstöße und "falsche Grüne"** (Test gelöscht, übersprungen, Schwelle gesenkt): Soll 0.
- **Bot-Schleifen:** Runden zwischen Reviewer und Fixer je PR; Soll höchstens `max_rounds`.

### 4.3 Gate B je Fix-Art (Vorschlag für [07] Abschnitt 4)

| Fix-Art | Gate A | Gate B offline | Gate B online | Bezug und Einstufung |
|---|---|---|---|---|
| Review-Kommentar | F1x nicht schlechter als nacktes Claude Code mit gleichem Modell und dem Kommentar als Prompt | F1x mindestens Wert eines CodeRabbit-Vergleichslaufs auf denselben Fällen (O13) | Fix-Annahmequote mindestens 35 % | Bugbot über 35 % (GESAGT) |
| Rote CI | F2 ohne Verstöße, Erfolg nicht unter nacktem Harness | F2p mindestens 18,9 % (bester veröffentlichter Wert, gleiches oder älteres Modell) | Annahmequote mindestens 60 %, Verifikationsquote je Klasse gemessen | CI-Repair-Bench BELEGT; Nx 60 % GESAGT |
| Konflikt | F3 alle Fälle ohne Marker und mit Build grün oder Ablehnung | Merge-Bench, sobald Lizenz und Bezugswerte geprüft sind | Anteil Konflikt-Fixe ohne Nacharbeit | **Gate B offen** bis Merge-Bench geprüft |
| Dependency | F4 nicht schlechter als nacktes Harness | Build-Erfolg auf BUMP-Teilmenge mindestens 27 % | Anteil reparierter Renovate-PRs, die gemerged werden | Byam o3-mini (GESAGT) |
| Sicherheitsbefund | F5 0 neue Befunde | F5 nach Copilot-Schema; kein öffentlicher Zahlenwert | Annahmequote | **Gate B offen** (GitHub nennt nur Worte) |
| Nicht verursacht | F6 0 Code-Änderungen | entfällt | Rerun höchstens 1 je Commit | Gitar (BELEGT) |

Hinweis: Die Bezugswerte sind Herstellerzahlen auf deren Daten. Sie taugen als Untergrenze, nicht als fairer Vergleich (ABGELEITET).

---

## 5. Was die Anbieter offenlegen und was proprietär bleibt

| Übernehmbar (offengelegt) | Quelle | Wohin bei uns |
|---|---|---|
| Fehlerklassen "vom PR verursacht" gegen "Flake, Infrastruktur, Ziel-Branch", Rerun höchstens einmal je Commit, Recovery höchstens 3 eigene Commits, Dedupe über Jobs, veraltete Läufe ignorieren | [gitar-ci] | [02] 5 Stufen 1 und 2, [03] Fehlerpfade |
| Auto-Apply nur bei Glob-Treffer, hoher Konfidenz und belegter Verifikation; Exclude schlägt Include; Repo-Datei für Fix-Hinweise mit Vorrang | [nx-shci] | [04] `prfixer.auto_apply`, `.agents/rules/fix.md` |
| Repo-Datei darf Modus nur senken; eigener Check nur `success`/`neutral` | [cursor-bugbot] | [04], [02] 5 Ausgang |
| Copilot-Autofix-Prüfschema mit vier Fragen | [gh-autofix-ru] | [07] F5 |
| Bot-Allowlist gegen Endlosschleifen | [devin-bots] | [04] Routing |
| Renovate selbst (AGPL) und Dependabot-Kern (MIT) als Werkzeuge | [renovate], [dependabot-core] | [06] optionaler Begleitdienst |
| Flake-Monitore Pass-on-Retry, Failure Rate, Failure Count, je Branch-Art | [trunk-detect] | [02] 5 Eingang, optional |

**Proprietär bleibt (ABGELEITET aus fehlender Offenlegung):** alle Fix-Prompts und Modelle der Anbieter, Bugbots Auswahl der Fix-Kandidaten, Nx' Kontextextraktion aus dem Projektgraphen (nur als Mechanik beschrieben), Merge Confidence von Mend ("private", BELEGT [renovate-mc]) und Copilot-Autofix-Ergebniszahlen.

---

## 6. Folgen für unsere Architektur (konkret)

| Datei, Abschnitt | Änderung | Grund |
|---|---|---|
| [02-services.md](../architecture/02-services.md) Abschnitt 5 Messlatte | Zeilen ergänzen: Nx Self-Healing CI, Gitar, Copilot `@copilot` auf jedem PR, Dependabot-Zuweisung an Agenten | Korrektur und Spitzengruppe (Abschnitt 2) |
| [02] Abschnitt 5 Eingang | `source` erweitern um `static_analysis` (SARIF, SonarQube, CodeQL, Semgrep), `dependency_update`, `queue_failure`; `security_alert` in `static_analysis` aufgehen lassen | Fähigkeiten 26, 27, 36 |
| [02] Abschnitt 5 Ausgang | `outcome` um `not_caused_by_pr` und `rerun_requested` ergänzen; eigener Check `ai-fix` nur `success` oder `neutral` | Fähigkeiten 13, 30 |
| [02] Abschnitt 5 Stufen | Stufe 2 "Klassifizieren" mit Klassen `caused_by_pr`, `flaky`, `infra`, `target_branch`, `unknown`; nur `caused_by_pr` führt zum Fix, Flake und Infrastruktur führen zu höchstens einem Rerun je Commit; Stufe "Warten auf echte CI": `fixed` erst, wenn der rote Job am neuen SHA grün ist; Recovery-Regel: macht ein eigener Fix eine grüne CI rot, zählt das als Versuch, nach 3 eigenen Commits in Folge Ende | Gitar, Nx |
| [02] Abschnitt 5 Dependency-Profil | Profil `dependency_update`: Eingang ist ein PR von `renovate[bot]` oder `dependabot[bot]` (Allowlist) mit roter CI; der Agent ändert nur Code; Manifest und Lockfile werden höchstens durch den Paketmanager im Worker neu erzeugt (deterministischer Schritt, Ausnahme vom Lockfile-Verbot nur in diesem Profil und nur für die vom Update betroffenen Pakete); Lieferung standardmäßig als Stacked-PR auf den Update-Branch, damit Renovate den Branch weiter pflegt | [gh-depagent], [renovate-rebase] |
| [02] Abschnitt 5 DoD | Zeilen für F1x, F2p, F4, F5, F6 und die Online-Metriken aus Abschnitt 4 | Gate B messbar |
| [07-eval.md](../architecture/07-eval.md) Abschnitt 3.4 | F1x, F2p, F4, F5, F6 aufnehmen; F2 auf öffentliche Repos umstellen; Abschnitt 1 "Eval-Repo (privat)" für ein Open-Source-Projekt neu fassen: öffentliche Testsätze nur mit geklärter Datenlizenz, private Sätze bleiben beim jeweiligen Betreiber | Owner-Vorgabe 2 (Open Source), Abschnitt 2.7 |
| [07] Abschnitt 4 Zeile PR-Fixer | ersetzen durch die Tabelle in Abschnitt 4.3 | Gate B je Fix-Art |
| [07] Abschnitt 7 | offenen Punkt "CodeRabbit-Fixe in bothy-Historie" schließen: keine vorhanden (Abschnitt 2.8) | Beleg |
| [01-plugin-interfaces.md](../architecture/01-plugin-interfaces.md) | neue Plugin-Art `CIProvider` (9. Art): `failedJobs(sha)`, `jobLog(id, maxBytes)`, `rerun(jobId)` mit Fähigkeiten `LOGS`, `RERUN_JOB`, `RERUN_WORKFLOW`, `STATUS_LINK`; Adapter für GitHub Actions, GitLab CI, Azure Pipelines, Bitbucket Pipelines, danach Jenkins, CircleCI, Buildkite. `ciFailureLogs` im SCMProvider wird zum Ersatzweg. Ereignis `what.action` um `queue_failed` ergänzen | Gitar liest elf CI-Systeme; Owner-Vorgabe 4 (fremde Services anflanschen) |
| [01] Abschnitt 5 und [05-security.md](../architecture/05-security.md) Abschnitt 2 | neuer Schreibwunsch `propose_rerun` (nur PR-Fixer, nur Jobs des aktuellen SHA, höchstens einer je Commit); Rechteprofil `ci_rerun` mit nur `actions:write` bzw. dem Gegenstück je CI; ungeprüft, ob GitHub `actions:write` feiner als je Repo vergeben kann | Fähigkeit 13 |
| [04-configuration-and-limits.md](../architecture/04-configuration-and-limits.md) `prfixer` | neue Schlüssel: `watch: { on_agent_prs: true, on_human_prs: opt_in }`, `auto_apply: { include: [...], exclude: [...], min_verification_rate }`, `rerun_unrelated: once_per_commit`, `bot_allowlist: [renovate[bot], dependabot[bot], <eigener Reviewer>]`, `dependency_update: { enabled, delivery: stacked_pr | take_over }`, `sources: [review_threads, ci_failure, merge_conflict, static_analysis, dependency_update]`; Regel: Repo-Datei darf `prfixer`-Modus nur senken | Fähigkeiten 4, 9, 21, 29 |
| [04] Routing | Route `pipeline.ci_failed` für Bot-PRs aus der Allowlist; Bot-Kommentare an den Fixer nur aus Allowlist | Devin-Schleifenschutz |
| [03-flow-and-orchestration.md](../architecture/03-flow-and-orchestration.md) Abschnitt 5 | Fehlerpfade: Fehler nicht vom PR verursacht (Rerun, Status-Kommentar); Recovery-Grenze erreicht; Konflikt abgelehnt (Datei und Grund, kein Commit); Out-of-scope-Änderung nötig (Vorschlag im Kommentar); Renovate-Branch übernommen (Vermerk) | Fehlerpfad-Regel (d) der globalen Vorgaben |
| [03] Abschnitt 1a Merge-Gate | Hinweis: Dependency-PRs merged Renovate selbst über das Plattform-Automerge; das Merge-Gate gilt nur für `agent/*`. Repariert der Fixer einen Renovate-PR per Stacked-PR, braucht dieser den normalen menschlichen Weg | Abgrenzung |
| [06-operations-and-deployment.md](../architecture/06-operations-and-deployment.md) Abschnitt 1 | optionaler Begleitdienst "Renovate CLI" (AGPL, unverändertes Upstream-Image, eigener Container, nicht im Plattform-Code) in allen Installationswegen (Azure, AWS, Google Cloud, Docker auf Hetzner); Plattform liest nur dessen PRs. Mend CE/EE nur als Hinweis, weil Lizenzschlüssel und Mend-ToS nötig sind | Owner-Vorgaben 2 und 4 |
| [08-roadmap.md](../architecture/08-roadmap.md) Stufe 4 | Fertig-Kriterium um F1x, F4, F5, F6 und `CIProvider` für GitHub Actions ergänzen; Dependency-Profil und Fremd-CI-Adapter als Stufe 4b | Reihenfolge |
| [09-decisions.md](../architecture/09-decisions.md) | ADR "Abhängigkeits-Updates keine eigene Ebene, Renovate-Integration plus Fixer-Profil"; ADR "CIProvider als 9. Plugin-Art"; O9 neu vorlegen (Abschnitt 7) | Entscheidungen festhalten |
| [README.md](../architecture/README.md) | Glossar `CIProvider`; Quellenliste um die Kürzel aus Abschnitt 9 dieses Berichts; Titel mit Firmennamen und "Eval-Repo privat" im Licht der Open-Source-Vorgabe umformulieren (gehört zur Gesamtrunde, nicht nur zu diesem Thema) | Folgeliste |

---

## 7. Owner-Entscheidungen

| Frage | Art | Empfehlung | Grund |
|---|---|---|---|
| **O9 neu:** Darf der PR-Fixer auf menschliche PR-Branches committen, wenn der PR-Autor es für seinen PR ausdrücklich einschaltet (Watch-Modus wie Copilot Agent Merge)? | Produkt | Ja, nur als Opt-in je PR durch den Autor mit Schreibrecht; Standard bleibt Stacked-PR; Org kann es sperren | Die Spitzengruppe committet auf den bestehenden Branch (Copilot seit 2026-03-24, Bugbot als Option); ohne das bleibt Fähigkeit 4 nur für Agent-PRs. Risiko begrenzt durch Opt-in, Versuchsgrenze und Verbote |
| Renovate im Installationspaket mitliefern (als unverändertes AGPL-Image in Compose und Helm) oder nur dokumentieren? | Recht | Nur als optionaler, getrennter Dienst mit Upstream-Image, nicht im eigenen Code; Lizenz unseres Projekts davon unabhängig; vor dem ersten Release einmal rechtlich bestätigen lassen | AGPL-Pflichten greifen bei Änderung und Netzangebot des Programms selbst; reines Mitstarten eines unveränderten Images ist nach unserer Lesart Aggregation (ABGELEITET, keine Rechtsberatung) |
| Öffentliche Eval-Läufe auf JetBrains LCA CI Builds Repair pushen Commits nach GitHub. Dafür ein eigenes, öffentliches GitHub-Konto oder eine Org anlegen? | Konto | Ja, eigene Eval-Org mit öffentlichen Repos (Actions-Minuten für öffentliche Repos ohne Kosten, ungeprüft für den Umfang), getrennt von den persönlichen Konten des Owners | Ohne Konto kein F2p auf diesem Datensatz; Trennung schützt die Konten des Owners vor Eval-Lärm |
| Datensätze ohne geklärte Lizenz (ConGra ohne LICENSE, c-CRAB, CI-Repair-Bench, BUMP-Daten, Merge-Bench) in einem öffentlichen Repo nutzen? | Recht | Nicht einchecken; nur per Download-Skript und nur nach geklärter Lizenz oder schriftlicher Erlaubnis der Autoren; bis dahin Gate B dort "offen" | Ein öffentliches Repo darf keine Daten ohne Weitergaberecht verteilen |
| Vergleichslauf gegen CodeRabbit Autofix und Fix CI auf bothy (Gate B für F1 und F2) | Geld, nach außen wirkend | Ja, als begrenzter Lauf auf Kopien alter bothy-PRs in einem eigenen Test-Repo; Kosten vorher als Entscheidungsblatt | Ohne diesen Lauf gibt es für F1 keinen fairen Bezug (Abschnitt 2.8); Schreibwirkung nur im Test-Repo |

---

## 8. Offene Punkte

- Ob CI-Repair-Bench, c-CRAB, Merge-Bench, OmniCode und CodeReviewQA ihre Daten veröffentlichen und unter welcher Lizenz: ungeprüft.
- Baseline-Werte des JetBrains-Datensatzes: ungeprüft.
- Byam 27 % und FSE-2025 23 % nur aus Suchauszug: Paper lesen, bevor die Zahl Gate B wird.
- Copilot Agent Merge: Rundengrenze, Verhalten bei menschlichen Review-Kommentaren in der Cloud-Variante, Commit-Ziel: in der Changelog-Meldung nicht beschrieben, ungeprüft.
- Ob ein Push mit einem GitHub-App-Installations-Token Workflows auslöst (für "echte CI als Wahrheit" nötig): ungeprüft, bei Copilot standardmäßig nicht ([copilot-reviewprs]).
- Ob `actions:write` für Reruns sich auf einzelne Repos begrenzen lässt: ungeprüft.
- Renovate-Verhalten bei fremden Commits nur aus Suchauszug der Doku: die Seite `updating-rebasing` vor dem Bau selbst lesen.
- Squash-Merges in bothy könnten CodeRabbit-Fixe unter dem Namen des Maintainers verbergen: ungeprüft.
- SonarQube als Eingang (`static_analysis`): API, Edition und Lizenz der Instanz in bothy nicht geprüft; gehört zum Thema "Anbindung SonarQube und CodeRabbit an das Entwicklungs-Repo".

---

## 9. Quellen (abgerufen 2026-10-31)

- [copilot-merge] https://github.blog/changelog/2026-10-28-agent-merge-watches-and-fixes-pull-requests-in-the-cloud
- [copilot-merge-search] Suchauszug zu https://github.blog/changelog/2026-03-26-ask-copilot-to-resolve-merge-conflicts-on-pull-requests/, https://github.blog/changelog/2026-04-13-fix-merge-conflicts-in-three-clicks-with-copilot-cloud-agent/, https://github.blog/changelog/2026-10-01-github-copilot-in-vs-code-september-2026-releases (GESAGT)
- [copilot-anypr] https://github.blog/changelog/2026-03-24-ask-copilot-to-make-changes-to-any-pull-request/
- [copilot-reviewprs] https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/review-copilot-prs
- [copilot-reviewprs-search] Suchauszug ältere Fassung https://docs.github.com/en/copilot/how-tos/agents/copilot-coding-agent/reviewing-a-pull-request-created-by-copilot (GESAGT)
- [gh-autofix] https://docs.github.com/en/code-security/concepts/code-scanning/autofix-for-code-scanning
- [gh-autofix-ru] https://docs.github.com/en/enterprise-cloud@latest/code-security/responsible-use/responsible-use-autofix-code-scanning
- [gh-depagent] https://github.blog/changelog/2026-04-07-dependabot-alerts-are-now-assignable-to-ai-agents-for-remediation
- [cursor-bugbot] https://cursor.com/docs/bugbot
- [cursor-autofix-blog] https://cursor.com/blog/bugbot-autofix (GESAGT)
- [nx-shci] https://nx.dev/docs/features/ci-features/self-healing-ci.md
- [nx-autoapply] https://nx.dev/blog/self-healing-ci-auto-apply-suggestions (GESAGT, Suchauszug)
- [nx-diy] https://nx.dev/blog/nx-vs-diy (GESAGT, Suchauszug)
- [nx-ttg] https://nx.dev/blog/stop-babysitting-your-prs-selfhealing-ci-cuts-time-to-green-by-50 (GESAGT, nur Titel)
- [gitar] https://docs.gitar.ai
- [gitar-ci] https://docs.gitar.ai/features/ci-failure-analysis.md
- [gitar-search] Suchauszug zu Gitar-Doku und Blog https://gitar.ai/blog/ai-code-review-without-the-comment-spam (GESAGT)
- [devin-bots] https://docs.devin.ai/product-guides/bot-comment-settings und https://cognition.com/blog/closing-the-agent-loop-devin-autofixes-review-comments (GESAGT, Suchauszug)
- [graphite-chat] https://graphite.com/docs/graphite-chat und https://graphite.com/docs/agents.md (GESAGT, Suchauszug)
- [trunk-flaky] https://docs.trunk.io/flaky-tests
- [trunk-detect] https://docs.trunk.io/flaky-tests/detection
- [mergify-mq] https://docs.mergify.com/merge-queue/
- [renovate] https://github.com/renovatebot/renovate
- [renovate-ce] https://github.com/mend/renovate-ce-ee
- [renovate-mc] https://docs.renovatebot.com/merge-confidence/
- [renovate-automerge] https://docs.renovatebot.com/key-concepts/automerge/
- [renovate-rebase] https://docs.renovatebot.com/updating-rebasing/ (GESAGT, Suchauszug)
- [dependabot-core] https://github.com/dependabot/dependabot-core
- [ci-repair-bench] https://arxiv.org/abs/2604.27148
- [lca-ci] https://huggingface.co/datasets/JetBrains-Research/lca-ci-builds-repair und https://arxiv.org/abs/2406.11612
- [bump] https://github.com/chains-project/bump, https://zenodo.org/records/10041883, Byam https://arxiv.org/abs/2505.07522, FSE 2025 https://conf.researchr.org/details/fse-2025/fse-2025-research-papers/38/Automatically-fixing-dependency-breaking-changes (Bezugswerte GESAGT)
- [congra] https://github.com/HKU-System-Security-Lab/ConGra und https://arxiv.org/abs/2409.14121
- [merge-bench] https://arxiv.org/html/2605.25890 (GESAGT, Suchauszug)
- [c-crab] https://arxiv.org/abs/2603.23448
- [codereviewqa] https://arxiv.org/abs/2503.16167 (GESAGT, Suchauszug)
- [omnicode] https://arxiv.org/abs/2602.02262 (GESAGT, Suchauszug)
- [bothy-repo] öffentliches Repo bothy, Angaben in [bothy-vorlage-projekt-setup](bothy-vorlage-projekt-setup.md) Abschnitt 6; gelesen: `git log --all` (Stand 2026-10-31), `renovate.json` und `LICENSE` auf Commit `4485084b8`
