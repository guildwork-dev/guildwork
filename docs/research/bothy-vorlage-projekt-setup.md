<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
> Research note, dated 2026-11-01, not binding. Kept in German as written (ADR-53); the binding documents are docs/architecture and docs/design.

# Vorlage bothy: Projekt-Setup für das öffentliche Repo

**Dated, not binding.** Datierte Recherche, Stand 2026-10-31, nicht verbindlich und nicht übersetzt; verbindlich ist die Plattform-Doku ([docs/architektur/](../architecture/README.md)).

Stand: 2026-10-31. Thema: Wie der Maintainer bei bothy CodeRabbit, SonarQube, Runner, Push-Disziplin, CI-Budget, Red-Team-Gate, Lizenzen, Scorecard, Release und Governance angebunden hat, und welches Projekt-Setup daraus für unser neues öffentliches Repo folgt. Nur Planung, nichts gebaut, im bothy-Checkout nichts geändert.

Einstufung wie in [README](../architecture/README.md) Abschnitt 6: **BELEGT** (Primärquelle selbst gelesen), **GESAGT** (Herstelleraussage, Marketing, Drittbericht), **ABGELEITET** (eigener Schluss), **VERMUTET**. Externe Quellen abgerufen am 2026-10-31.

**Fundstellen-Schreibweise.** `bothy@4485084b8:pfad:zeile` meint die Datei `pfad` im öffentlichen Repo bothy ([bothy-repo]) auf Commit `4485084b8` (Stand `origin/main` vom 2026-10-31, 482 Commits), gelesen mit `git show 4485084b8:<pfad>`. `bothy@7d11c50d6:pfad:zeile` meint einen älteren Planungsstand (Branch `plan/spezifikation`, Commit `7d11c50d6` vom 2026-10-12, 95 Commits), der nicht im öffentlichen Repo liegt; Aussagen, die nur darauf beruhen, sind dort nicht nachprüfbar. Alle Zeilen selbst gelesen (BELEGT).

## 1. Urteil (Kurzfassung)

1. **Der ausgecheckte bothy-Stand ist veraltet; die Vorlage ist `origin/main`.** Der Arbeitsbaum steht auf dem Planungsbranch `plan/spezifikation` (`7d11c50d6`, 2026-10-12). Auf `origin/main` (`4485084b8`) sind mehrere im Auftrag genannte Dateien inzwischen gelöscht (`docs/quality/ci-budget.md`, `docs/quality/self-hosted-runner.md`) oder auf Englisch umbenannt (`docs/spec/16-operations.md`, `23-quality.md`, `11-extensions.md`). Wer bothy als Vorlage liest, muss `origin/main` lesen, nicht den Arbeitsbaum. BELEGT (`git diff --stat HEAD origin/main`, 186 Dateien geändert; `git rev-list --count`).
2. **Die Runner-Weiche privat/öffentlich gibt es bei bothy nicht mehr.** Am 2026-10-11 hat der Maintainer entschieden: Das Repo ist **öffentlich ab dem ersten Push**, jeder Job läuft nur auf GitHub-gehosteten Standard-Runnern mit festem Label, es gibt keine self-hosted Runner (D-W-92, neue ADR 0039). Die Weiche in `runs-on`, das Minutenbudget der privaten Phase und die Anleitung für zwei Runner-Benutzer sind gestrichen. Das ist für uns die richtige Vorlage: einfacher, kostenlos und ohne fremden Code auf eigenen Rechnern. BELEGT (`bothy@4485084b8:docs/adr/0039-only-github-hosted-runners-public-from-the-first-push.md:37-42`, `bothy@4485084b8:docs/DECISIONS-PLANNING.md:926`).
3. **Rechtlicher Stolperstein bei Vorgabe 3: CodeRabbit verbietet die Nutzung zum Bau von Konkurrenzprodukten.** Die Nutzungsbedingungen (Stand "Updated: April 20, 2026") untersagen in 4.2 (iv) wörtlich "disclose the results of any benchmarking of the Services, or use the Services to develop competing products or services without CodeRabbit's prior written consent". Unser Projekt ist ausdrücklich ein CodeRabbit-Ersatz. CodeRabbit am Entwicklungs-Repo "hilft beim Nachbau" ist damit ohne schriftliche Zustimmung ein Vertragsverstoß, und der geplante öffentliche Vergleich mit CodeRabbit (Gate B in [07](../architecture/07-eval.md)) ebenso. BELEGT (Wortlaut selbst aus der Seite gelesen); rechtliche Bewertung ungeprüft, das ist eine Owner-Entscheidung (Abschnitt 4, E1).
4. **Alles Übrige ist eine fertige, getestete Vorlage, die wir fast vollständig übernehmen:** `make check` identisch zu CI mit genau einem Pflicht-Check `ci-ok`, Workflow-Policy per Werkzeug (`check_runners.py`), Actions per SHA, Renovate mit Wartezeit, gitleaks mit eigenen Regeln (darunter jede Anthropic-Credential), Deny-Liste aus einem privaten Ops-Repo (White Label), Apache-2.0 mit DCO, Lizenz-Gate mit Allowlist und ScanCode, SonarQube lokal und in der Cloud aus denselben Dateien, Red-Team-Gate vor jedem Push mit `Urteil: JA`, CodeQL und Scorecard, signierte Releases mit SBOM und Attestation, Portabilitätstest auf frischer Maschine, OpenTofu-Module je Ziel. Projektspezifisch und nicht zu übernehmen sind Go, Dart, Flutter, Apple-, Windows- und Android-Builds, macOS-Runner, Design-Tokens und die Zugänglichkeits-Checklisten (Abschnitt 2.12).
5. **SonarQube passt besser als bei bothy.** Unser Stack ist TypeScript (06 Abschnitt 3). Der Community Build analysiert TypeScript, JavaScript, Python, Go, Docker und Terraform; Dart, YAML und GitHub Actions nur Cloud und Server. Die Lücke, die bei bothy Dart war, entfällt für uns weitgehend. BELEGT ([sonar-langs]).
6. **Folge für die Roadmap:** Vor der Plattform-Stufe 0 braucht [08](../architecture/08-roadmap.md) eine eigene **Stufe R "Repo-Fundament"** mit dem bothy-Ablauf (lokal prüfen, ein Wurzel-Commit, Push, sofort öffentlich, Sonar Cloud, Schutzregeln, Probelauf). Sie kostet kein Geld (öffentliche Standard-Runner und die OSS-Pläne sind kostenlos, BELEGT [gh-runners], [sonar-plans]), braucht aber Konten-Schritte, die nur der Owner tun kann.

## 2. Befunde mit Quellen

### 2.1 Zustand des Vorbilds

| Befund | Fundstelle | Einstufung |
|---|---|---|
| Das Repo bothy ([bothy-repo]) ist öffentlich erreichbar: HTTP 200, Seite zeigt "Public", 482 Commits, keine Releases. Die REST-API antwortete ohne Anmeldung mit 403 (vermutlich Rate-Limit, nicht weiter geprüft) | `curl -s -o /dev/null -w "%{http_code}"` am 2026-10-31; WebFetch der Seite | BELEGT (Status 200); Ursache 403 VERMUTET |
| Erster öffentlicher Commit am 2026-10-11 "initial public baseline (plan M0 + M1-01)", direkt danach "fix: repair the first CI run on GitHub-hosted runners (#2)" | `git log origin/main --reverse` | BELEGT |
| Lehre daraus: Vor dem ersten Push läuft keine CI, der erste CI-Lauf brach. ADR 0039 nennt das selbst als Nachteil ("no CI runs before the first push") | `bothy@4485084b8:docs/adr/0039-...md:92-93` | BELEGT; Lehre ABGELEITET |
| Platzhalter `@OWNER` stehen auf dem öffentlichen `main` noch in `.github/CODEOWNERS` (Schritt 22 der Checkliste offen) | `bothy@4485084b8:.github/CODEOWNERS:5-10`, `docs/quality/public-switch.md:126-129` | BELEGT |
| `docs/REUSE.md` ist **nicht** die REUSE-Spezifikation der FSFE, sondern "Reuse: lessons from three predecessors" (Lehren, Testmuster, Code zum Neuschreiben). Ein `REUSE.toml` oder `reuse lint` gibt es in bothy nicht | `bothy@4485084b8:docs/REUSE.md:1-6`; `git grep -i "reuse lint\|REUSE.toml"` ohne Treffer | BELEGT |

### 2.2 CodeRabbit

| Befund | Fundstelle | Einstufung |
|---|---|---|
| CodeRabbit ist als GitHub-App am Repo, aktiv seit dem Öffentlich-Schalten; Grund "free for public repositories" | `bothy@4485084b8:.coderabbit.yaml:4-5`, `docs/quality/public-switch.md:76` | BELEGT |
| CodeRabbit-Preisseite: "install CodeRabbit on a public repository, and receive free reviews forever for public repositories" | [cr-pricing] | GESAGT (Herstellerseite, Zusammenfassung des Abrufwerkzeugs) |
| Lokale CLI nur mit `BOTHY_CODERABBIT=1` über `make review`, weil der Diff an den Dienst geht | `bothy@4485084b8:.coderabbit.yaml:5-6`, `Makefile:1114-1115`, `docs/quality/push-discipline.md:279-289` | BELEGT (bothy) |
| Profil `chill` statt `assertive` (Owner, CRT-1/1, 2026-10-13): nur Bugs, Sicherheit, gebrochene Verträge, CI-Brüche; keine Stil-Nits. Grund: Nits kosteten Review-Runden | `bothy@4485084b8:.coderabbit.yaml:13-15, 39-53`; `docs/DECISIONS-FOUNDATION.md:668` | BELEGT |
| Quellenpflicht nur noch für `docs/spec/**`, `docs/security/**`, `docs/adr/**` (CRT-1/2). Grund laut Ruling: "cost one to two hours per pull request" | `bothy@4485084b8:.coderabbit.yaml:54-63`; `docs/DECISIONS-FOUNDATION.md:669` | BELEGT (Ruling); die Zeitangabe ist bothy-intern, nicht nachgemessen |
| Wissensbasis an, aber nur lokal (`learnings.scope: local`; Jira, Linear, MCP aus) (CRT-1/3). Grund: mit `opt_out: true` kamen erklärte Kommentare bei jedem PR wieder | `bothy@4485084b8:.coderabbit.yaml:99-114`; `docs/DECISIONS-FOUNDATION.md:670` | BELEGT |
| Zusammenfassung in den Walkthrough-Kommentar statt in den PR-Text, weil der PR-Text der Squash-Commit auf `main` wird und jede Text-Änderung CI neu startet | `bothy@4485084b8:.coderabbit.yaml:18-20`; `push-discipline.md:197-200` | BELEGT |
| Pfad-Anweisungen für Workflows, Go-Code und Werkzeuge spiegeln die lokalen Gates; eingeschaltete Werkzeuge: actionlint, gitleaks, golangci-lint, ruff, zizmor | `bothy@4485084b8:.coderabbit.yaml:64-93` | BELEGT |
| Regel: Ein Befund, den nur CodeRabbit oder SonarQube Cloud findet, wird zu einer lokalen Regel (Semgrep, Test, Linter, Profilregel). Nur diese beiden dürfen nach dem Push etwas finden | `bothy@4485084b8:docs/quality/push-discipline.md:160-163`; `.coderabbit.yaml:7` | BELEGT |
| Nur Blocker und reproduzierte Majors aus CodeRabbit werden vor dem Merge behoben, sonst kurze Antwort und Thread schließen | `bothy@4485084b8:docs/quality/push-discipline.md:291-298` | BELEGT |
| **CodeRabbit-AGB 4.2 (iv):** "disclose the results of any benchmarking of the Services, or use the Services to develop competing products or services without CodeRabbit's prior written consent"; Verstöße gegen Abschnitt 4 sind von der Haftungsbegrenzung ausgenommen (11.1) und erlauben Unterlassungsansprüche (7.3) | [cr-tos], Stand "Updated: April 20, 2026" | BELEGT (4.2 (iv) wörtlich per Abruf des Seitentexts); 7.3 und 11.1 GESAGT (nur Zusammenfassung des Abrufwerkzeugs) |

### 2.3 SonarQube

| Befund | Fundstelle | Einstufung |
|---|---|---|
| Ein Satz Dateien für lokalen Community Build und SonarQube Cloud: `sonar-project.properties` ohne Secrets, Gate und Profile unter `quality/sonar/`, eingespielt und verglichen von `tools/sonarqube/quality_sync.py` (`make sonar-config`, `make sonar-config-check`) | `bothy@4485084b8:sonar-project.properties:3-7`; ADR 0040; `docs/spec/23-quality.md` Abschnitt 7 | BELEGT |
| Gate "Bothy way" mit vier Bedingungen: 0 neue Befunde, 100 % geprüfte Hotspots, 80 % Abdeckung neuer Code, höchstens 3 % Duplikation; jede Schwelle ist ein benannter Wert, ein Test hält beide gleich | `bothy@4485084b8:quality/sonar/quality-gate.json:3-9` | BELEGT |
| `sonar.qualitygate.wait=true`: der Scan scheitert, wenn das Gate rot ist | `bothy@4485084b8:sonar-project.properties:69-70` | BELEGT |
| Keine `.sonarcloud.properties`, automatische Analyse aus; Cloud analysiert nur über CI (R-QA-10) | `bothy@4485084b8:docs/spec/23-quality.md:190` | BELEGT |
| Cloud-Konfiguration per eigenem Workflow `sonar-config.yml`, nur `workflow_dispatch`, nur auf `main`; macht das Projekt öffentlich, weil ein privates Projekt auf dem Free-Plan an Zeilen gedeckelt ist | `bothy@4485084b8:.github/workflows/sonar-config.yml:3-14`; `public-switch.md:60-75` | BELEGT |
| Ein Push auf `main` startet `ci.yml` ebenfalls, damit SonarQube eine Analyse von `main` als Referenz für "neuen Code" hat | `bothy@4485084b8:.github/workflows/ci.yml:6-9` | BELEGT |
| Lokaler Server nur auf `127.0.0.1`, eigene PostgreSQL im internen Netz ohne Host-Port | `bothy@7d11c50d6:docs/quality/sonarqube-local.md:3-6` (auf main gleichlautend auf Englisch, Abschnitte ab `:8`) | BELEGT |
| SonarQube Cloud Free: unbegrenzt öffentliche Projekte, privat bis 50k LOC, nur Main-Branch, PRs nur gegen Main, **keine eigenen Gates und Profile**. OSS-Plan: unbegrenzt öffentliche Repos, keine privaten Projekte, eigene Profile und Gates, alle Branches und PRs | [sonar-plans] | BELEGT (Herstellerdoku, Zusammenfassung des Abrufwerkzeugs) |
| Community Build: TypeScript, JavaScript, Python, Go, Docker, Kubernetes/Helm, Terraform, Secrets ja; Dart, YAML, GitHub Actions nein | [sonar-langs] | BELEGT |

### 2.4 Runner, Öffentlich-Schalten, CI-Budget

| Befund | Fundstelle | Einstufung |
|---|---|---|
| Früher (bis 2026-10-11): Weiche `runs-on: ${{ github.event.repository.private && fromJSON('["self-hosted","bothy-ci"]') \|\| 'ubuntu-24.04' }}`, zwei self-hosted Runner-Benutzer (`bothy-ci`, `bothy-release`), Minutenbudget je Release-Tag | `bothy@7d11c50d6:.github/workflows/ci.yml:42`; `docs/quality/self-hosted-runner.md:3-19`; `docs/quality/ci-budget.md:30-49` | BELEGT (historisch) |
| Heute: nur Standard-Runner mit festem Label (`ubuntu-24.04`, `ubuntu-24.04-arm`, `macos-15`, `windows-2025`), keine Liste, keine Gruppe, kein `*-latest`, keine Larger Runner; Repo öffentlich direkt nach dem ersten Push | `bothy@4485084b8:docs/adr/0039-...md:37-42, 63-65`; `docs/spec/23-quality.md:183` (R-QA-03) | BELEGT |
| Durchgesetzt von `tools/ci/check_runners.py`, Regel `runner-not-github-hosted`, dazu `actions-write`, `broad-permissions`, `pull-request-target`, `push-on-branch`, `schedule-without-public-guard`, `unpinned-action`, `missing-timeout`, Release-Regeln | `bothy@4485084b8:tools/ci/check_runners.py:5, 31, 324`; ADR 0039 `:97-109` | BELEGT |
| "Use of the standard GitHub-hosted runners is free and unlimited on public repositories" | [gh-runners] | BELEGT |
| Gleichzeitige Jobs auf Standard-Runnern: Free 20, Pro 40, Team 60, Enterprise 500; macOS 5 (Enterprise 50); höchstens 6 Stunden je Job | [gh-limits] | BELEGT (Zusammenfassung des Abrufwerkzeugs) |
| Öffentlich-Jobs (CodeQL, Scorecard, Pages) laufen nur bei `github.event.repository.visibility == 'public'`, geplante Läufe zusätzlich mit `vars.BOTHY_VISIBILITY == 'public'`, weil `schedule` kein Repository-Objekt trägt | `bothy@4485084b8:docs/adr/0039-...md:46-53`; `.github/workflows/scorecard.yml:25-26`; R-QA-04 `docs/spec/23-quality.md:184` | BELEGT |
| CI-Disziplin: `concurrency` bricht überholte PR-Läufe ab; Caches für uv, npm, Binärdateien, pre-commit; kein Pfadfilter auf Workflow-Ebene (sonst bliebe `ci-ok` offen), der Job `plan` wählt die Komponenten-Gates | `bothy@4485084b8:docs/spec/23-quality.md:118-121` | BELEGT |
| `ci.yml` hat heute 30 Jobs (20 auf `ubuntu-24.04`, 5 `macos-15`, 3 `windows-2025`, 1 `ubuntu-24.04-arm`), `ci-ok` als letzter Job mit `always()` | `bothy@4485084b8:.github/workflows/ci.yml` (Job-Liste ab `:60`, `ci-ok` ab `:1483`) | BELEGT (selbst gezählt per `grep runs-on`) |
| Build-Branches `build/**`: Bau-Teams pushen dorthin, `build-verify.yml` führt alle Gates ohne Secrets auf gehosteten Runnern aus; kein Pflicht-Check | `bothy@4485084b8:docs/quality/push-discipline.md:47-104`; ADR 0039 `:77-81` | BELEGT |
| Flaky Tests: ein gescheiterter Test läuft einmal neu, bestandene Wiederholung ist ein Flake; stündlicher Workflow sammelt sie in einem Issue mit Label `flake` | `bothy@4485084b8:.github/workflows/flakes.yml:3-8` | BELEGT |
| Täglicher Advisory-Scan von `main`; ein PR scheitert an `osv` nur für Abhängigkeiten, die er selbst ändert | `bothy@4485084b8:.github/workflows/advisories.yml:3-7` | BELEGT |

### 2.5 Push-Disziplin und Schutz von `main`

| Befund | Fundstelle | Einstufung |
|---|---|---|
| Ablauf: Branch `<type>/<thema>`, Commits mit DCO, vor dem Push zusammenfassen, lokales unabhängiges Review mit Bericht `.review/<sha>.md`, pre-push-Hook prüft Bericht und `make check`, ein PR je Feature, Titel als Conventional Commit, Squash-Merge | `bothy@4485084b8:docs/quality/push-discipline.md:6-45` | BELEGT |
| Ruleset für `main`: PR Pflicht nur Squash, Pflicht-Check `ci-ok`, lineare Historie, signierte Commits, kein Force-Push, kein Löschen; Squash-Nachricht = PR-Titel und PR-Text | `bothy@4485084b8:docs/quality/push-discipline.md:106-116` | BELEGT |
| Squash statt Rebase-Merge, weil GitHub Rebase-Commits nicht signieren kann | `bothy@4485084b8:docs/quality/push-discipline.md:118-123` (mit GitHub-Quellen) | BELEGT (bothy zitiert Primärquelle; nicht erneut abgerufen) |
| Pre-push nur für betroffene Teile (`tools/hooks/push_plan.py`), CI bleibt Autorität; `PUSH_FULL=1` für alles | `bothy@4485084b8:docs/quality/push-discipline.md:131-146` | BELEGT |
| Roter CI-Lauf nach grünem `make check` ist ein Fehler der Werkzeugkette; "fix CI" auf `main` ist Prozessfehler mit Eintrag in `docs/DECISIONS.md` | `bothy@4485084b8:docs/quality/push-discipline.md:148-158` | BELEGT |
| PR-Titel und -Text laufen durch die Deny-Liste (Variablen `PR_TITLE`, `PR_BODY`, nie im Skript interpoliert); `ci.yml` reagiert auf `edited`; `plan` setzt `ci-ok` sofort auf "in_progress", damit kein altes Grün stehen bleibt | `bothy@4485084b8:docs/quality/push-discipline.md:165-214`; `ci.yml:10-15, 21-29` | BELEGT |
| Bot-PRs (Dependabot, Renovate) laufen wie Fork-PRs mit reduzierten Prüfungen; Bot-Commits ohne DCO nur bei exakt der Bot-Adresse; Maintainer schreibt den PR-Text neu mit eigenem Sign-off | `bothy@4485084b8:docs/quality/push-discipline.md:227-264`; `docs/DECISIONS.md:66` (D-DEPS-3) | BELEGT |

### 2.6 Red-Team-Gate

| Befund | Fundstelle | Einstufung |
|---|---|---|
| Vor jedem Push und lokalen Merge: Diff gegen `main`, Bericht `.review/<sha>.md` (git-ignoriert), letzte Zeile `Urteil: JA` oder `Urteil: NEIN <Grund>`; je Etappe ein Gesamt-Review; vor dem Öffentlich-Schalten über den ganzen Stand | `bothy@4485084b8:docs/quality/red-team-gate.md:8-15` | BELEGT |
| Prüfer unabhängig (frische KI-Sitzung oder zweite Person), nur lesend, ohne Secrets | `bothy@4485084b8:docs/quality/red-team-gate.md:17-23` | BELEGT |
| Hook `tools/hooks/review_gate.py` vergleicht die letzte Zeile exakt mit `Urteil: JA`; `REVIEW_SKIP=1` nur für Fork-Beitragende | `bothy@4485084b8:tools/hooks/review_gate.py:15, 32, 51-52` | BELEGT |
| Der PR nennt nur geprüften Commit, Urteil und Korrekturen in eigenen Worten, nie den Rohbericht (der PR-Text wird Squash-Commit) | `bothy@4485084b8:docs/quality/red-team-gate.md:52-55` | BELEGT |
| Bei zweimal demselben NEIN entscheidet der Owner, keine weitere Runde | `bothy@4485084b8:docs/quality/red-team-gate.md:50-51` | BELEGT |

Abgleich mit den globalen Regeln des Owners (Red Team vor main, ein Prüfer, höchstens zwei Fix-Runden): deckungsgleich. ABGELEITET.

### 2.7 Lizenz, DCO, REUSE, NOTICE

| Befund | Fundstelle | Einstufung |
|---|---|---|
| Apache-2.0 mit DCO statt CLA; Grund: Patentlizenz, erlaubend, Herkunftsnachweis je Commit ohne Vertrag | `bothy@4485084b8:docs/adr/0003-license-apache-2-0-with-dco-instead-of-cla.md`; Fassung `bothy@7d11c50d6:docs/adr/0003-lizenz-apache-2-0-mit-dco-statt-cla.md:30-45` | BELEGT |
| Lizenz-Gate: `LICENSE` byteweise gleich dem Apache-Text (sha256), SPDX-Kopfzeile in den ersten 5 Zeilen jeder handgeschriebenen Datei, Abhängigkeiten gegen `quality/licenses/allowed.txt` | `bothy@7d11c50d6:tools/ci/license_check.py:1-25`; `bothy@4485084b8:docs/quality/licenses.md:40-54` | BELEGT |
| Allowlist: 0BSD, Apache-2.0, BSD-2/3-Clause, BSL-1.0, CC0-1.0, ISC, MIT, MIT-0, MPL-2.0, PSF-2.0, Python-2.0, Unicode, Zlib; GPL, AGPL, SSPL, BUSL nur als getrennter Prozess mit Begründung | `bothy@7d11c50d6:quality/licenses/allowed.txt:9-23`; `docs/quality/licenses.md:31-35` | BELEGT |
| ScanCode Toolkit vor jedem Release und vor dem Öffentlich-Schalten über `git archive HEAD` im Container, Policy-Skript, Ausnahmen mit Grund in `quality/licenses/scancode-exceptions.txt`; ein Fund stoppt das Release vor jedem Image-Tag | `bothy@4485084b8:docs/quality/licenses.md:67-78` | BELEGT |
| `NOTICE` nennt mitgelieferte Fremdteile (Schriften OFL-1.1, Icons MIT) | `bothy@4485084b8:NOTICE:1-24` | BELEGT |
| REUSE-Spezifikation 3.3 (2024-11-14): Lizenztexte in `LICENSES/<SPDX>.txt`, je Datei `SPDX-FileCopyrightText` und `SPDX-License-Identifier`, optional `REUSE.toml`; Prüfwerkzeug "REUSE Tool" | [reuse-spec] | BELEGT |
| bothy erfüllt REUSE nicht formal (kein `LICENSES/`, kein `SPDX-FileCopyrightText`), prüft aber das Wesentliche (Lizenzkennung je Datei) mit eigenem Skript | Abschnitt 2.1; `license_check.py` | ABGELEITET |

### 2.8 Scorecard und CodeQL

| Befund | Fundstelle | Einstufung |
|---|---|---|
| `scorecard.yml`: Trigger `branch_protection_rule`, wöchentlich, manuell; nur öffentlich; Job ohne `env`, nur genehmigte Actions, Ubuntu-Runner; SARIF-Upload | `bothy@7d11c50d6:.github/workflows/scorecard.yml:9-49`; auf main Bedingung `:25-26` | BELEGT |
| Scorecard-Action: frei für öffentliche Repos, privat nur mit GitHub Advanced Security; bei `publish_results: true` keine Workflow-`env`, keine Schreibrechte auf Workflow-Ebene, nur Ubuntu-Runner, nur fünf erlaubte Actions, keine `run`-Schritte | [scorecard] | BELEGT |
| `codeql.yml`: nur öffentlich, Sprachen `actions`, `go`, `javascript-typescript`, `python`, `security-extended` | `bothy@4485084b8:.github/workflows/codeql.yml:43-49`; Abfrage-Suite `bothy@7d11c50d6:.github/workflows/codeql.yml:46` | BELEGT |
| Semgrep nur mit eigenen Projektregeln samt Regeltests, ohne Registry-Regelsätze (R-QA-05); Beispiel: der Server liest nie `ANTHROPIC_*`/`CLAUDE_*` | `bothy@4485084b8:docs/spec/23-quality.md:185`; `bothy@7d11c50d6:.semgrep/bothy-go-no-model-credentials.yaml:1-14` | BELEGT |

### 2.9 Release

| Befund | Fundstelle | Einstufung |
|---|---|---|
| Version und Changelog je Komponente, Tags `<komponente>/vX.Y.Z`, Produkt `vX.Y.Z`; kein `latest` | `bothy@7d11c50d6:docs/spec/18-release.md:16-44, 318-319` (main: `docs/spec/18-release.md`, umgebaut) | BELEGT |
| Lieferkette: SBOM (Syft), Image erst per Digest, dann Trivy, dann Tag; cosign keyless und `actions/attest` (Attestations auf Free/Pro nur für öffentliche Repos) | `bothy@4485084b8:docs/spec/23-quality.md:154-167`; `bothy@7d11c50d6:docs/spec/18-release.md:170-199` | BELEGT |
| Release-Jobs mit Signier-Secrets nur in Umgebungen `release*` mit Pflicht-Reviewern; Ausgaben fremder Jobs nur im `if:`, Artefakte nur per ID (R-QA-12) | `bothy@4485084b8:docs/spec/23-quality.md:192`; `public-switch.md:87-88` | BELEGT |
| Trivy auf 0.69.3 gepinnt wegen kompromittierter Version 0.69.4 vom 2026-03-19; Renovate für Trivy aus | `bothy@7d11c50d6:docs/quality/toolchain.md:85-103`; `renovate.json:48-52` | BELEGT (bothy zitiert das Advisory; nicht erneut abgerufen) |
| Portabilitätstest: frischer Linux-Runner (amd64 und arm64), `install.sh` per dokumentiertem `curl` ohne Anmeldung, Signaturprüfung der Images, Smoke-Tests, Wiederherstellungstest | `bothy@7d11c50d6:docs/spec/16-betrieb.md:747-800`; `bothy@4485084b8:docs/quality/public-switch.md:108-125` | BELEGT |
| Hosting-Ziele Mac, Linux-VM, Azure, AWS, Hetzner, Kubernetes später; Installation in einem Befehl (`curl ... install.sh \| sh`) | `bothy@4485084b8:docs/spec/16-operations.md:56-65, 115-131` | BELEGT |
| OpenTofu: `generic-vm` richtet jeden Linux-Host ein, Zielmodule `hetzner`, `aws`, `azure` setzen darauf auf; keines gegen ein echtes Konto angewendet, weil das Geld kostet und auf Owner-Freigabe wartet; Google Cloud fehlt | `bothy@4485084b8:infra/tofu/README.md:3-6` und Modultabelle | BELEGT |

### 2.10 Governance und Community-Dateien

| Befund | Fundstelle | Einstufung |
|---|---|---|
| GOVERNANCE: Maintainer in CODEOWNERS, Start mit einem Maintainer; dauerhafte Entscheidungen als ADR (MADR), kleinere in `docs/DECISIONS.md`; Lazy Consensus; Triage mit Labels und Zielzeiten als benannte Werte | `bothy@7d11c50d6:GOVERNANCE.md:3-43` (main: nur Dateinamen geändert) | BELEGT |
| SECURITY: einziger Meldeweg ist GitHub Private Vulnerability Reporting, keine Mail-Adresse; Zielzeiten als benannte Werte; keine Bounties | `bothy@4485084b8:SECURITY.md` (Diff gegenüber `7d11c50d6:SECURITY.md:8-31`) | BELEGT |
| SUPPORT: Gemeinschaftsprojekt ohne kommerziellen Support; Fragen zu einer Installation an deren Betreiber | `bothy@7d11c50d6:SUPPORT.md:3-19` | BELEGT |
| CONTRIBUTING: `make bootstrap`, `make check`; Fork-Schalter `DENYLIST_FLAGS=--allow-missing`, `SONAR_SKIP=1`, `REVIEW_SKIP=1`; DCO; Doku gehört zur Änderung; keine Gedankenstriche | `bothy@4485084b8:CONTRIBUTING.md:52-53, 76, 98, 110`; `bothy@7d11c50d6:CONTRIBUTING.md:86-104` | BELEGT |
| Zwei Repos: öffentliches Produkt, privates Ops-Repo mit Instanzwerten und der privaten Deny-Liste (ADR 0002); Deny-Scanner prüft Inhalte, Dateinamen, Commits, Identitäten, Refs; `denylist-main.yml` prüft jeden Push auf `main` | `bothy@7d11c50d6:docs/adr/0002-zwei-repos-oeffentliches-produkt-privates-ops-repo.md:32-54`; `bothy@4485084b8:docs/spec/23-quality.md` Abschnitt 6 | BELEGT |
| Gesamter Repo-Inhalt auf Englisch (D-W-94), seit Commit "docs: translate the repository to English (#4)" am 2026-10-11 | `bothy@4485084b8:.coderabbit.yaml:56`; `git log` | BELEGT |
| Secret Scanning und Push Protection für öffentliche Repos kostenlos; Push Protection auf Repo-Ebene laut bothy nur per Changelog 2023 belegt | `bothy@4485084b8:docs/quality/public-switch.md:50-54` | GESAGT (von bothy zitiert, nicht erneut abgerufen) |

### 2.11 Werkzeugkette (Auszug, was wir brauchen)

| Werkzeug | Zweck bei bothy | Lizenz laut bothy | Für uns |
|---|---|---|---|
| pre-commit | Hooks pre-commit, commit-msg, pre-push | MIT | übernehmen |
| gitleaks (als CLI, nicht als Action) | Secrets in allen Commits, eigene Regeln | MIT | übernehmen samt Regel `anthropic-credential-any` (`bothy@7d11c50d6:.gitleaks.toml:29-39`) |
| actionlint, zizmor | Workflow-Syntax und -Sicherheit | MIT | übernehmen |
| Semgrep | nur Projektregeln | LGPL-2.1 | übernehmen (Entwicklungswerkzeug, nicht ausgeliefert) |
| OSV-Scanner | Schwachstellen und Lizenzen der Lock-Dateien | Apache-2.0 | übernehmen |
| Trivy | Fehlkonfiguration, Image-Scan | Apache-2.0 | übernehmen, Version-Pin-Regel beibehalten |
| `@sonar/scan`, SonarQube Community Build | Analyse lokal und CI | LGPL-3.0 | übernehmen |
| Renovate | Updates gruppiert, `minimumReleaseAge` 7 Tage, Montag früh, höchstens 5 offene PRs | AGPL-3.0 laut [ebenen-landkarte](ebenen-landkarte.md) | als gehostete GitHub-App nutzen, nicht bündeln |
| ScanCode Toolkit | Lizenztexte und Copyright im Baum | (nicht bei bothy genannt, ungeprüft) | übernehmen vor Release und Öffentlich-Schalten |
| mkdocs, mkdocs-material | Doku-Site | BSD, MIT | übernehmen, sobald Doku-Site gebraucht wird |

Quellen der Tabelle: `bothy@7d11c50d6:docs/quality/toolchain.md:13-43`, `bothy@4485084b8:renovate.json:10-19`. Lizenzangaben bothy-intern BELEGT (dort mit Abrufdatum 2026-10-10), von uns nicht erneut geprüft.

### 2.12 Was bei bothy projektspezifisch ist

| bothy-spezifisch (nicht übernehmen) | Grund |
|---|---|
| Go-Server, sqlc, golangci-lint, govulncheck, go-licenses, Go-Shards | unser Kern ist TypeScript ([06](../architecture/06-operations-and-deployment.md) Abschnitt 3) |
| Dart und Flutter (Apps, Pakete, `custom_lint`, Dart nur in Sonar Cloud) | keine Apps im Plan |
| Apple-, Windows-, Android-Builds, macOS- und Windows-Runner, Umgebungen `release-apple`, `release-windows`, `release-android`, Sparkle, MSIX, TestFlight | keine Desktop- oder Mobil-Apps |
| Design-Tokens, Mermaid-Thema-Stempel, Zugänglichkeits-Checklisten, Grafana-Panel-Plugin, Terminal, ClamAV | Produktteile von bothy |
| Komponentenliste in `tools/ci/components.py` mit zehn Komponenten | wir starten mit wenigen Komponenten (Steuerzentrale, Worker, Plugins) |
| `sonar-project.properties` mit langen Ausnahmelisten | entsteht erst mit Code; wir starten mit kurzer Fassung |

| Übernehmen (mit Anpassung) | Anpassung |
|---|---|
| `make check` = CI, ein Pflicht-Check `ci-ok`, Komponenten-Erkennung an Manifesten, `SKIP` nur ohne Code | Komponenten: `package.json` unter `core/`, `worker/`, `plugins/*` (Namen in Stufe R festlegen) |
| `check_runners.py`, SHA-Pinning, Timeouts, `permissions: contents: read` | Labels nur `ubuntu-24.04` und `ubuntu-24.04-arm` |
| Red-Team-Gate mit `.review/<sha>.md` | Prüfliste auf unsere Sicherheitsregeln ([05](../architecture/05-security.md)) umschreiben: Effect Gateway einzige Schreibstelle, kein Credential in der Sandbox, Befehl deckt Effekt |
| Deny-Liste und Ops-Repo | Liste enthält Firmennamen, Hostnamen, Personen und Runner-Details der Installation |
| SonarQube lokal und Cloud aus denselben Dateien | ohne Dart-Sonderweg |
| Lizenz-Gate, Allowlist, ScanCode, NOTICE, DCO | zusätzlich REUSE-3.3-Form (Abschnitt 3.3) |
| Release mit SBOM, cosign keyless, Attestation, Trivy vor Tag | Images `control-plane`, `agent-worker`, `egress-proxy` |
| Portabilitätstest und OpenTofu `generic-vm` plus Zielmodule | Zielmodule zusätzlich `gcp`; Azure als Ziel des Owners zuerst |
| CodeRabbit-Konfiguration (`chill`, lokale Wissensbasis, Walkthrough) | erst nach Owner-Entscheidung E1 |

## 3. Folgen für unsere Architektur

### 3.1 Neue Datei `docs/architektur/10-repo-und-qualitaet.md`

Inhalt (ABGELEITET aus Abschnitt 2, Vorlage `bothy@4485084b8`):

**a) Dateien im öffentlichen Produkt-Repo ab dem ersten Push**

| Datei | Inhalt | Vorlage |
|---|---|---|
| `LICENSE`, `NOTICE` | Lizenztext unverändert; Fremdteile | `NOTICE:1-24` |
| `LICENSES/` | Lizenztexte nach REUSE 3.3 | [reuse-spec] |
| `README.md`, `CONTRIBUTING.md`, `GOVERNANCE.md`, `SECURITY.md`, `SUPPORT.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md` | Community-Dateien, Zielzeiten als benannte Werte | Abschnitt 2.10 |
| `.github/CODEOWNERS`, `.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE/`, `.github/labels.yml` | Maintainer, PR-Vorlage mit Abschnitt "Review", Formulare mit `status: triage` | `bothy@7d11c50d6:.github/PULL_REQUEST_TEMPLATE.md` |
| `Makefile` | `bootstrap`, `check` = `gates` + `denylist` + `sonar`, `review`, `sonar-up`, `sonar-config(-check)`, `licenses`, `scancode`, `release-build`, `portability` | `bothy@4485084b8:Makefile:213-219, 834, 1114` |
| `.pre-commit-config.yaml` | Text-Regeln (keine Gedankenstriche), Datei-Hygiene, gitleaks staged, commit-msg (Conventional Commits, DCO), pre-push (Review-Nachweis, `make check`) | `bothy@7d11c50d6:.pre-commit-config.yaml:9-81` |
| `.gitleaks.toml` | Standardregeln plus `anthropic-credential-any`, später OpenAI-, GitHub-App-, Azure-Formate | `bothy@7d11c50d6:.gitleaks.toml:14-39` |
| `.semgrep/` | Projektregeln mit Regeltests, erste Regeln aus [05](../architecture/05-security.md): nur das Effect Gateway importiert den SCM-Schreib-Client; die Sandbox-Seite liest keine `ANTHROPIC_*` | `bothy@7d11c50d6:.semgrep/` |
| `renovate.json` | `config:best-practices`, Montag früh, `minimumReleaseAge` 7 Tage, Majors per Dashboard | `bothy@4485084b8:renovate.json:10-19` |
| `.coderabbit.yaml` | nur nach E1; Inhalt wie bothy (`chill`, Walkthrough, lokale Wissensbasis) | `bothy@4485084b8:.coderabbit.yaml` |
| `sonar-project.properties`, `quality/sonar/quality-gate.json`, `quality/sonar/profiles.json`, `quality/sonar/quality-profile-{ts,js,py,docker}.xml` | Gate mit vier Bedingungen, Schwellen als benannte Werte | Abschnitt 2.3 |
| `quality/licenses/allowed.txt`, `quality/licenses/scancode-exceptions.txt` | Allowlist und Ausnahmen mit Grund | Abschnitt 2.7 |
| `tools/ci/` (`check_runners.py`, `components.py`, `license_check.py`, `ci_ok.py`, `pr_mode.py`), `tools/hooks/` (`review_gate.py`, `commit_msg.py`, `text_rules.py`, `push_plan.py`), `tools/denylist/`, `tools/sonarqube/` | Werkzeuge samt Tests; aus bothy unter Apache-2.0 übernommen, Herkunft in `NOTICE` | Abschnitt 2.4 bis 2.7 |
| `docs/quality/` | `gates.md`, `toolchain.md`, `push-discipline.md`, `red-team-gate.md`, `sonarqube-local.md`, `public-switch.md`, `licenses.md` | `bothy@4485084b8:docs/quality/README.md:7-17` |
| `docs/adr/`, `docs/DECISIONS.md` | ADRs (MADR) und Ruling-Log; unsere ADR-01 bis ADR-36 aus [09](../architecture/09-decisions.md) wandern dorthin | `bothy@7d11c50d6:docs/DECISIONS.md:1-25` |

**b) Workflows**

| Workflow | Trigger | Zweck | ab |
|---|---|---|---|
| `ci.yml` | `pull_request` (auch `edited`), `push` auf `main`, `workflow_dispatch`, `workflow_call` | Jobs `plan`, `gates`, `denylist`, `denylist-fork`, `sonar`, `ci-ok`; einziger Pflicht-Check `ci-ok` | Stufe R |
| `denylist-main.yml` | `push` auf `main` | private Deny-Liste über die gepushten Commits | Stufe R |
| `codeql.yml` | PR, wöchentlich, manuell | `actions`, `javascript-typescript`, `python` (Werkzeuge) | Stufe R |
| `scorecard.yml` | `branch_protection_rule`, wöchentlich | OpenSSF Scorecard mit SARIF | Stufe R |
| `sonar-config.yml` | nur `workflow_dispatch` auf `main` | Gate und Profile in SonarQube Cloud einspielen und prüfen | Stufe R |
| `advisories.yml` | täglich | voller Schwachstellen-Scan von `main` | Stufe R |
| `release.yml` | nur Tag-Push | Gates, Build, Trivy vor Tag, SBOM, cosign keyless, Attestation; Umgebung `release` mit Pflicht-Reviewer | erstes Release |
| `portability.yml` | Aufruf aus `release.yml`, manuell mit Tag | frischer Runner amd64 und arm64: Installation per dokumentiertem Befehl, Smoke-Test Steuerzentrale plus Dummy-Worker | erstes Release |
| `docs.yml` | Tag, täglich, manuell | Doku-Site auf Pages | wenn Doku-Site gewünscht |
| `flakes.yml`, `build-verify.yml` | stündlich bzw. `push` auf `build/**` | Flake-Liste; Gates für Bau-Teams ohne Secrets | erst bei Bedarf |

Regeln für alle Workflows (aus ADR 0039 und R-QA-03/04/12, durchgesetzt von `check_runners.py`): feste Standard-Labels, keine self-hosted Runner, `permissions: contents: read` oben, kein `actions: write`, kein `pull_request_target`, kein `push` außer `main` in `denylist-main.yml` und `ci.yml`, `timeout-minutes` an jedem Job, Actions per SHA, nicht vertrauenswürdige Werte nur über `env`.

**c) Gates von `make check`** (ABGELEITET, Startmenge für TypeScript):

`fmt-check` (Prettier oder Biome), `lint` (pre-commit-Hooks, ESLint, ruff für `tools/`, actionlint, zizmor, check-jsonschema für Renovate und CodeRabbit), `typecheck` (tsc, mypy strict für `tools/`), `test` und `coverage` (Vitest oder Node-Test-Runner mit Schwelle als benanntem Wert), `commitlint` (Conventional Commits, DCO), `docs` und `linkcheck` (lychee offline), `runners-check`, `gitleaks`, `semgrep`, `trivy` (sobald Dockerfiles existieren), `osv`, `licenses`, `denylist`, `sonar`. Fork-Schalter wie bothy (R-QA-02). Werkzeugwahl Prettier/Biome und Vitest ist offen (Abschnitt 5).

**d) Ruleset und Repo-Einstellungen**: wie `bothy@4485084b8:docs/quality/push-discipline.md:106-116`; zusätzlich "Require actions to be pinned to a full-length commit SHA", Private Vulnerability Reporting, Secret Scanning mit Push Protection, Umgebungen `denylist` und `release` (Pflicht-Reviewer, Tag-Regel `v*` und `*/v*`).

**e) CI-Budget und Gleichzeitigkeit** (globale Regel des Owners "Zahl gleichzeitiger PR-Läufe je Projekt begrenzt, Wert festlegen und messen"): Öffentliche Standard-Runner kosten nichts ([gh-runners] BELEGT); die Grenze ist die Gleichzeitigkeit des Kontos (Free 20, Pro 40 Jobs, [gh-limits] BELEGT). Startwert (Schätzung): höchstens 2 gleichzeitige PR-Läufe mit je höchstens 6 Jobs, `concurrency` mit Abbruch überholter Läufe; gemessen wird die Wartezeit je Lauf über die Actions-API. Keine Larger Runner, kein macOS (`check_runners.py` verbietet beides).

### 3.2 `08-roadmap.md`

- **Neue Stufe R "Repo-Fundament" vor Stufe 0**, mit dem Ablauf von `bothy@4485084b8:docs/quality/public-switch.md`:
  1. Lokal (ohne Remote): Gerüst aus 3.1 a, `make bootstrap` und `make check` grün, Deny-Liste im privaten Ops-Repo angelegt, Text-Regeln und gitleaks aktiv, `check_runners.py` mit Tests.
  2. Red Team über den ganzen Stand mit `Urteil: JA`; **ein** Wurzel-Commit mit der gewählten Identität (Planungshistorie bleibt privat, wie bothy D-W-93); `make denylist`, `make denylist-history`, `make gitleaks GITLEAKS_LOG_OPTS=--all` in einem frischen Klon grün; Lizenz-Gate und ScanCode grün; Platzhalter vorher ersetzen (Lehre aus `@OWNER`, Abschnitt 2.1).
  3. Umgebung `denylist` im leeren Repo anlegen, Push als `main`, sofort öffentlich, `*_VISIBILITY=public`, Private Vulnerability Reporting, Secret Scanning mit Push Protection.
  4. SonarQube Cloud (OSS-Plan, Projekt, automatische Analyse aus, Variablen und `SONAR_TOKEN`, `sonar-config.yml` mit Ergebnis "check ok"); CodeRabbit nur nach E1.
  5. Ruleset für `main`, Umgebungen, Renovate, CodeQL-Lauf auf `main`.
  6. Probelauf: ein PR aus dem Repo (voll), ein PR aus einem Fork (generische Regeln), ein PR ohne Sign-off scheitert an `ci-ok`.
- **Fertig-Kriterium Stufe R** (mit Beleg): `ci-ok` grün auf dem Probe-PR, alle Jobs auf Standard-Runnern (Job-Protokoll), `sonar-config` meldet "check ok", Scorecard und CodeQL liefen, Fork-PR grün mit "Reduced checks", DCO-Probe rot, `denylist-main.yml` grün für den ersten Push. Geld: 0 (Schätzung bei Standard-Runnern und OSS-Plänen).
- Lehre aus bothy (Commit #2): Vor dem ersten Push den Workflow-Satz einmal lokal gegen die Policy prüfen; ein roter erster CI-Lauf ist erwartbar und wird als Fix-PR, nicht als Direkt-Commit behoben.
- Stufe 0 bekommt als Voraussetzung "Stufe R fertig". Das bestehende Fertig-Kriterium von Stufe 0 bleibt.

### 3.3 `09-entscheidungen.md`

Neue ADR-Vorschläge (ABGELEITET):

| Nr | Entscheidung | Grund |
|---|---|---|
| ADR-37 | Produkt-Repo öffentlich ab dem ersten Push; nur GitHub-gehostete Standard-Runner mit festem Label; keine self-hosted Runner am Entwicklungs-Repo | bothy ADR 0039 (neu); kostenlos ([gh-runners]); kein fremder Code auf eigener Hardware |
| ADR-38 | `make check` identisch zu CI, ein Pflicht-Check `ci-ok`, Policy der Workflows per Werkzeug | bothy ADR 0038, R-QA-01 |
| ADR-39 | Zwei Repos: öffentliches Produkt, privates Ops-Repo je Installation (Werte der Installation, Deny-Liste, Runbooks) | bothy ADR 0002; Vorgabe 2 verlangt ein firmenneutrales Produkt |
| ADR-40 | Lizenz des Produkts und DCO (Empfehlung Apache-2.0 mit DCO wie bothy ADR 0003), REUSE-3.3-Form, Allowlist für Ausgeliefertes, ScanCode vor Release | endgültig nach der Lizenz-Recherche ([ebenen-landkarte](ebenen-landkarte.md) Abschnitt 4.3) |
| ADR-41 | SonarQube Community Build lokal und SonarQube Cloud (OSS-Plan) mit denselben Gate- und Profildateien | bothy ADR 0040; Free-Plan erlaubt keine eigenen Gates ([sonar-plans]) |
| ADR-42 | Red-Team-Gate vor jedem Push mit `.review/<sha>.md` und `Urteil: JA` im pre-push-Hook | bothy R-QA-13; deckt die globale Regel des Owners |
| ADR-43 | Externe KI-Reviewer am Entwicklungs-Repo nur, wenn deren Nutzungsbedingungen den Bau eines Konkurrenzprodukts erlauben oder eine schriftliche Zustimmung vorliegt | [cr-tos] 4.2 (iv) |

Owner-Entscheidungen E1 bis E5 aus Abschnitt 4 als O16 bis O20 aufnehmen. **O14** ("zunächst nur intern") ist durch Vorgabe 2 überholt; Vermerk "abgelöst durch Owner-Vorgabe 2026-10-31 (dritte Runde)". Die bestehende **O13** (Vergleichsläufe gegen CodeRabbit) bekommt den Hinweis auf [cr-tos] 4.2 (iv) und wird mit E2 zusammengeführt.

### 3.4 `05-sicherheit.md`

- Abschnitt 2 (Öffentliche Repos und fremder Code, Zeile 57): Das eigene Entwicklungs-Repo ist öffentlich und bekommt fremde Issues und PRs. Dogfooding der Plattform auf diesem Repo fällt damit unter "fremder Code": auf `office` nie, `operator_test` mit Abo nie (S2-Fall "öffentliches Repo" ergibt laut [07](../architecture/07-eval.md) 0 Läufe). Neu festhalten: Dogfooding auf dem eigenen öffentlichen Repo nur (a) für PRs von Maintainern, (b) im Modus `shadow` mit Effect Gateway `record`, bis das MicroVM-Backend steht. ABGELEITET.
- Neuer Absatz "Lieferkette des Entwicklungs-Repos": Verweis auf 10 (SHA-Pins, gitleaks-Regel für jede Anthropic-Credential, Trivy-Pin, Release-Secrets nur in Umgebungen).

### 3.5 `06-betrieb-und-deployment.md`

- Abschnitt 2: Variante A trägt den Namen einer Firma und nennt firmeninterne Fakten; im öffentlichen Produkt gehört sie als Beispiel-Installation ins private Ops-Repo (ADR-39 neu), im Produkt bleibt eine neutrale Beschreibung "Steuerzentrale auf Azure mit eigener Runner-Flotte".
- Neuer Abschnitt "Installationsweg" nach bothy-Muster: Installation in einem Befehl, Portabilitätstest auf frischem Runner, OpenTofu `generic-vm` plus Zielmodule `azure`, `aws`, `gcp`, `hetzner`. Die Wahl von Diensten je Cloud gehört zur parallelen Hosting-Recherche; hier nur das Muster. Lehre aus bothy: Zielmodule wurden nur mit gemockten Providern geprüft, ein Lauf gegen ein echtes Konto wartet auf Owner-Freigabe (`infra/tofu/README.md:3-6`).

### 3.6 `07-eval.md`

- Abschnitt R2/Gate B Reviewer und Zeile 81: Ein veröffentlichter Vergleich mit CodeRabbit ist nach [cr-tos] 4.2 (iv) ohne Zustimmung verboten ("disclose the results of any benchmarking"). Messung intern bleibt möglich, Veröffentlichung nur nach E2.

### 3.7 `04-konfiguration-und-limits.md`, `01-plugin-schnittstellen.md`, README

- Firmenspezifische Namen (`apiVersion` mit Firmendomain, Pfad der Org-Konfiguration im Firmen-Repo, README-Titel mit Firmennamen) bereits in [ebenen-landkarte](ebenen-landkarte.md) vermerkt; hier ergänzt: die Deny-Liste des Produkt-Repos würde jede dieser Stellen ab Stufe R als Fund melden. Umbenennung ist Voraussetzung für den ersten Push.
- README Abschnitt 4 (Lesereihenfolge): Zeile für `10-repo-und-qualitaet.md` ergänzen.

### 3.8 Folgeliste (geprüft, was diese Fakten nennt)

| Stelle | Stand |
|---|---|
| `docs/architektur/09-entscheidungen.md` O13, O14 | anzupassen (3.3) |
| `docs/architektur/07-eval.md` Zeilen 36, 81 (Gate B gegen CodeRabbit) | anzupassen (3.6) |
| `docs/architektur/05-sicherheit.md` Zeile 57 | anzupassen (3.4) |
| `docs/architektur/06-betrieb-und-deployment.md` Variante A | anzupassen (3.5) |
| `docs/architektur/08-roadmap.md` Stufe 0 | Stufe R davor (3.2) |
| `docs/recherche/ebenen-landkarte.md` 4.3 (Renovate AGPL, nur Betreiber-Image) | passt: Renovate als gehostete App am Entwicklungs-Repo ist keine Bündelung; belassen |
| bothy-Arbeitsbaum `plan/spezifikation` | veraltet gegenüber `origin/main`; nicht geändert (Auftrag: nur lesen) |

## 4. Owner-Entscheidungen

| # | Frage | Art | Empfehlung | Grund |
|---|---|---|---|---|
| E1 | CodeRabbit am Entwicklungs-Repo trotz AGB 4.2 (iv)? | Recht | **Nicht installieren und die CLI nicht nutzen, bis eine schriftliche Zustimmung von CodeRabbit vorliegt.** Der Owner fragt CodeRabbit selbst schriftlich an (Text liefert der Planungslauf auf Wunsch). Bis dahin übernehmen SonarQube Cloud, CodeQL, Semgrep, das Red-Team-Gate und ab Stufe 1 unser eigener Reviewer im Schattenmodus (Dogfooding) die Rolle | Der Wortlaut verbietet "use the Services to develop competing products or services" ohne Zustimmung ([cr-tos] BELEGT); Verstöße gegen Abschnitt 4 sind laut Zusammenfassung von der Haftungsgrenze ausgenommen (GESAGT); ein öffentliches Repo macht die Nutzung sichtbar. Rechtliche Bewertung ungeprüft |
| E2 | Veröffentlichen wir Vergleiche mit CodeRabbit (Gate B, README, Blog)? | Recht, Produkt | Nur intern messen; veröffentlichen erst mit Zustimmung von CodeRabbit oder nach rechtlicher Prüfung. Öffentlich nur Vergleiche auf offenen Benchmarks ohne CodeRabbit-Lauf durch uns | [cr-tos] 4.2 (iv) "disclose the results of any benchmarking" (BELEGT) |
| E3 | Unter welchem Konto und Namen liegt das öffentliche Repo? | Konten, Produkt | Wie bothy unter dem persönlichen Konto des Owners, Name vor dem ersten Push festlegen, damit keine `OWNER`-Platzhalter öffentlich werden; spätere Übertragung in eine Organisation bleibt möglich (Weiterleitungen dabei ungeprüft) | kein Geld; bothy-Lehre Abschnitt 2.1; Vorgabe 2 verlangt Neutralität, ein Firmenkonto wäre das Gegenteil |
| E4 | Sprache des öffentlichen Repos | Produkt | Repo-Inhalt Englisch (wie bothy D-W-94); diese Planungsdokumente bleiben deutsch im privaten Planungsrepo und werden vor dem ersten Push übersetzt | internationale Beitragende; bothy hat am Tag des Öffentlich-Schaltens übersetzt (`git log`, Commit #4) |
| E5 | SonarQube Cloud: Organisation mit OSS-Plan anlegen, Token als Secret | Konten | ja, unter dem Konto des Repos, OSS-Plan | kostenlos für öffentliche Repos mit eigenen Gates ([sonar-plans] BELEGT); ohne OSS-Plan keine eigenen Gates |

Nicht als Owner-Entscheidung geführt (selbst entschieden, ABGELEITET): öffentlich ab erstem Push statt Runner-Weiche (der Maintainer hat das für bothy schon entschieden, D-W-92); Profil `chill` statt `assertive` (bothy, CRT-1/1); Werkzeuge aus bothy übernehmen statt neu schreiben.

## 5. Offene Punkte

1. **Lizenz des Produkts:** Empfehlung Apache-2.0 mit DCO wie bothy, endgültig mit der parallelen Lizenz-Recherche abgleichen (Verhältnis zu AGPL-Werkzeugen, Bedingungen aus [cc-legal] für Auslieferung an Dritte).
2. **SonarQube-AGB:** Ob die Nutzungsbedingungen von SonarQube Cloud eine ähnliche Klausel zu Konkurrenzprodukten enthalten, ist **ungeprüft**. Die Supplemental Terms lieferten beim Abruf keinen Treffer für "compet" oder "benchmark"; die allgemeinen Bedingungen wurden nicht gelesen. Wir bauen keinen Sonar-Ersatz, aber ein `Analyzer`-Plugin mit Sonar-Anbindung; vor Stufe R einmal lesen.
3. **CodeRabbit-AGB im Detail:** 7.3 und 11.1 nur als Zusammenfassung gelesen; ob die OSS-Nutzung unter denselben AGB oder einem eigenen Programm läuft, ist ungeprüft.
4. **Werkzeugwahl TypeScript:** Prettier oder Biome, Vitest oder Node-Test-Runner, ESLint-Regelsatz; in Stufe R festlegen und in `toolchain.md` mit Lizenz führen.
5. **Werkzeug-Sprache:** bothy-Werkzeuge sind Python mit Tests; Übernahme per Kopie unter Apache-2.0 ist schnell, bringt aber eine zweite Werkzeugkette (uv, mypy). Alternative Port nach TypeScript. Empfehlung: Kopie zuerst, Port nur bei Bedarf.
6. **REUSE-Werkzeug:** Lizenz des REUSE Tools (Codeberg) ungeprüft; als nicht ausgeliefertes Entwicklungswerkzeug unkritisch, vor Aufnahme in `toolchain.md` prüfen.
7. **Gleichzeitigkeit:** Startwert 2 PR-Läufe mit je höchstens 6 Jobs ist eine Schätzung; nach den ersten zehn PRs messen.
8. **Push Protection kostenlos auf Repo-Ebene:** bothy hält das nur über einen Changelog von 2023 für belegt; vor Stufe R an der GitHub-Doku prüfen.
9. **Dogfooding-Pfad:** Wie die eigene Plattform am eigenen öffentlichen Repo läuft (Credential, Pool, nur Maintainer-PRs), gehört in [05](../architecture/05-security.md) und die Hosting-Recherche; hier nur die Kollision mit `operator_test` festgestellt.
10. **bothy-Stand:** Gelesen wurde Commit `4485084b8`; wer bothy künftig als Vorlage liest, liest `origin/main` des öffentlichen Repos, nicht einen älteren Planungsbranch.

## 6. Quellen

Repo-Stände (selbst gelesen, BELEGT):
- bothy `origin/main` = `4485084b8` (2026-10-31): `.coderabbit.yaml`, `sonar-project.properties`, `quality/sonar/quality-gate.json`, `quality/release/README.md`, `NOTICE`, `docs/quality/README.md`, `public-switch.md`, `push-discipline.md`, `red-team-gate.md`, `sonarqube-local.md` (Gliederung), `licenses.md` (Abschnitte), `docs/adr/0039-only-github-hosted-runners-public-from-the-first-push.md`, `docs/spec/23-quality.md` Abschnitte 4 bis 10, `docs/spec/16-operations.md` Abschnitt 3, `docs/DECISIONS.md:66`, `docs/DECISIONS-FOUNDATION.md:668-670`, `docs/DECISIONS-PLANNING.md:926`, `.github/workflows/ci.yml`, `codeql.yml`, `scorecard.yml`, `advisories.yml`, `sonar-config.yml`, `flakes.yml`, `tools/ci/check_runners.py`, `tools/hooks/review_gate.py`, `Makefile`, `renovate.json`, `infra/tofu/README.md`, `docs/REUSE.md`, `CONTRIBUTING.md`, Diffs von `GOVERNANCE.md`, `SECURITY.md`, `SUPPORT.md`; `git log origin/main`.
- bothy Arbeitsbaum `plan/spezifikation` = `7d11c50d6` (2026-10-12): `docs/quality/*` (inklusive der auf main gelöschten `ci-budget.md` und `self-hosted-runner.md`), `.github/workflows/*`, `tools/ci/*` (Kopfzeilen), `.pre-commit-config.yaml`, `.gitleaks.toml`, `.semgrep/`, `renovate.json`, `mkdocs.yml`, `docs/spec/11-erweiterungen.md`, `16-betrieb.md`, `18-release.md`, `21-dev-isolation.md`, `23-qualitaet.md`, `docs/DECISIONS.md`, ADR 0002, 0003, 0039 (alt), 0040, 0044, `infra/README.md`, `README.md`, `GOVERNANCE.md`, `SECURITY.md`, `CONTRIBUTING.md`, `SUPPORT.md`, `quality/licenses/allowed.txt`.
- Eigenes Projekt: `docs/architektur/README.md`, `05`, `06`, `07`, `08`, `09`, `backlog-minors.md`, `docs/recherche/ebenen-landkarte.md`.

Web (abgerufen 2026-10-31):
- [bothy-repo] öffentliches Repo bothy auf GitHub, gelesen auf Commit `4485084b8` (`origin/main` vom 2026-10-31; der ältere Planungsstand `7d11c50d6` ist nicht veröffentlicht) (HTTP 200, "Public"; REST-API ohne Anmeldung 403); Konto-URL in der öffentlichen Fassung entfernt (Deny-Liste)
- [cr-tos] https://www.coderabbit.ai/terms-of-service ("Updated: April 20, 2026"; Abschnitt 4.2 (iv) wörtlich aus dem Seitentext gelesen) BELEGT
- [cr-pricing] https://www.coderabbit.ai/pricing GESAGT
- [sonar-plans] SonarSource-Dokumentation, SonarQube Cloud "Subscription plans", abgerufen 2026-10-31, BELEGT (Zusammenfassung des Abrufwerkzeugs; URL der Herstellerdoku in der öffentlichen Fassung entfernt)
- [sonar-langs] SonarSource-Dokumentation, SonarQube Community Build "Languages overview", abgerufen 2026-10-31, BELEGT (Zusammenfassung; URL der Herstellerdoku in der öffentlichen Fassung entfernt)
- [sonar-tos] https://www.sonarsource.com/legal/sonarcloud/terms-of-service/ (Supplemental Terms, Textsuche ohne Treffer, allgemeine Bedingungen ungeprüft)
- [gh-runners] https://docs.github.com/en/actions/reference/runners/github-hosted-runners BELEGT
- [gh-limits] https://docs.github.com/en/actions/reference/limits BELEGT (Zusammenfassung)
- [scorecard] https://github.com/ossf/scorecard-action BELEGT (Zusammenfassung)
- [reuse-spec] https://reuse.software/spec-3.3/ BELEGT (Zusammenfassung)
- [cc-legal] https://code.claude.com/docs/en/legal-and-compliance (aus [README](../architecture/README.md), hier nicht erneut abgerufen)
