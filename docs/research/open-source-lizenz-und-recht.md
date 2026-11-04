<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
> Research note, dated 2026-11-01, not binding. Kept in German as written (ADR-53); the binding documents are docs/architecture and docs/design.

# Open Source, Lizenz und Rechtliches (Stand 2026-10-31)

**Dated, not binding.** Datierte Recherche, Stand 2026-10-31, nicht verbindlich und nicht übersetzt; verbindlich ist die Plattform-Doku ([docs/architektur/](../architecture/README.md)).

Recherche zur Owner-Vorgabe der dritten Runde vom 2026-10-31: Das Projekt wird ein öffentliches Open-Source-Repo, das jeder selbst hosten kann, CodeRabbit und SonarQube sollen von Anfang an am Entwicklungs-Repo hängen, und das Abo des Betreibers bleibt Startweg im Testbetrieb.

**Keine Rechtsberatung.** Die Aussagen sind die Lesart der zitierten Originaltexte. Jede Vertragsklausel steht wörtlich mit Fundstelle. Alle Webquellen wurden am 2026-10-31 abgerufen.

**Einstufung** wie in [README](../architecture/README.md) Abschnitt 6:
- **BELEGT:** Primärtext selbst gelesen. Vertragsseiten wurden dafür per `curl` geladen und als Text durchsucht, Lizenzdateien direkt aus den Repos bzw. npm-Paketen gelesen.
- **GESAGT:** Herstelleraussage oder Drittquelle.
- **ABGELEITET:** eigener Schluss.
- **VERMUTET:** plausibel, ohne Beleg.

Quellenkürzel in eckigen Klammern verweisen auf Abschnitt 6.

---

## 1. Urteil (Kurzfassung)

1. **Lizenz: Apache-2.0 mit DCO, ohne CLA, ohne Open Core zum Start.** Gründe:
   - Das Ziel "jeder zieht, installiert und hostet selbst" verträgt keine Nutzungsbeschränkung.
   - FSL, BSL, Sustainable Use License und die geänderte Apache-Lizenz von Dify sind nach der Open Source Definition keine Open-Source-Lizenzen (OSD Punkt 6, [osd]; BSL sagt es selbst, [bsl]).
   - AGPL schreckt Unternehmen ab, die es selbst betreiben wollen.
   - bothy hat dieselbe Wahl schon begründet ([bothy-adr3] BELEGT).
   - Alle Bausteine unter MIT oder Apache-2.0, die für eine Code-Übernahme in Frage kommen (Abschnitt 2.3), sind damit verträglich.
2. **Drei Owner-Vorgaben stoßen auf Vertragsklauseln (BELEGT, wörtlich in Abschnitt 2):**
   - **CodeRabbit** verbietet, "use the Services to develop competing products or services without CodeRabbit's prior written consent", und die Veröffentlichung von Benchmarks ([cr-tos] 4.2 (iv)). CodeRabbit als Helfer beim Nachbau und CodeRabbit-Befunde aus bothy als Ground Truth (R1 in [07](../architecture/07-eval.md)) fallen nach dem Wortlaut darunter (ABGELEITET).
   - **SonarQube Cloud:** Die AUP verbietet die Nutzung durch "a direct competitor of SonarSource" sowie Results Data für konkurrierende "code review systems (whether based on LLM Technologies or not.)" ([sonar-aup] 5, 6).
   - **SonarQube Community Build:** Der Kern steht unter LGPL-3.0. Die mitgelieferten Analyzer stehen unter SSALv1. Diese Lizenz schließt aus, dass eine fremde KI ihre Ergebnisse liest ([ssal] Definition "Non-competitive Purpose" (c)). Genau das ist das bothy-Muster "Befund geht an Claude Code" (ABGELEITET).
3. **Anthropic:**
   - **Abo:** Ein Endnutzer darf das unveränderte Claude-Code-Binary mit seinem eigenen Abo nutzen, auch wenn eine Plattform es hostet. Verboten sind ein eigener Claude.ai-Login in Produkten, Routing "on behalf of their users" und Speichern oder Vermitteln von Tokens ([cc-legal] BELEGT).
   - **Folge für das öffentliche Projekt:** Der Startweg `subscription` bleibt zulässig als persönlicher Betreibermodus. Er ist standardmäßig aus, die Plattform hat keinen eigenen Login, und es gibt nie Mehrnutzer-Routing.
   - **Graubereich (ABGELEITET):** Die Consumer Terms (EWR-Fassung) verbieten automatisierten Zugriff "through a bot, script, or otherwise" außer mit API-Key oder ausdrücklicher Erlaubnis, dazu "any commercial or business purposes" ([an-consumer] BELEGT). Ein autonomer Dauerbetrieb über das Abo ist damit nicht sauber gedeckt.
   - **Ausweg ohne Mehrkosten:** Max, Ultra und Team enthalten seit 2026-10-07 monatliches API-Guthaben für Agent SDK und `claude -p` mit Console-Key ([cc-sdkplan] BELEGT).
4. **Anthropic-Binaries gehören nicht in unsere Artefakte.** Claude Code und das TypeScript-Agent-SDK sind "All rights reserved" und stehen unter den Commercial Terms ([sdk-npm], [cc-npm] BELEGT). Das SDK zieht plattformspezifische Pakete als `optionalDependencies` ([sdk-npm] BELEGT). Unsere Container-Images dürfen sie nicht enthalten; installiert wird beim Betreiber aus der offiziellen Quelle (ABGELEITET aus [cc-legal] "preinstalling or running Claude Code in your products").
5. **Weitere Fallen in der Werkzeugkette (BELEGT):**
   - Die Semgrep-Regeln erlauben nur "your own internal business purposes" und weder Weitergabe noch "as a service" ([semgrep-rules]).
   - Die Opengrep-Regeln tragen die Commons Clause ([opengrep-rules]).
   - Die CodeQL-CLI ist nur für OSI-lizenzierte Codebasen frei ([codeql]).
   - Folge: Für unser eigenes öffentliches Repo ist CodeQL frei. Im Produkt dürfen wir nur die Engines (Opengrep LGPL-2.1, Semgrep CE LGPL-2.1) mit eigenen Regeln mitliefern.
6. **Was aus `docs/` und `data/` nicht öffentlich werden darf:**
   - die nicht veröffentlichten Vorarbeiten und Daten (Firmeninterna, Hostnamen, Kosten, Hinweise auf Leak-Sammlungen, CodeRabbit-Ausgaben);
   - alle Firmen- und Betreiber-Details in `docs/architektur/`.
   Mechanismus wie bei bothy: zwei Repos (öffentliches Produkt, privates Ops-Repo) plus Deny-List-Scanner ([bothy-adr2] BELEGT). Die Lage ist günstig: Das Repo hat noch keinen Commit (`git log`: "does not have any commits yet", selbst geprüft), die öffentliche Historie kann also sauber beginnen.
7. **Name:** Er darf weder "CodeRabbit" noch "Claude" oder "Claude Code" enthalten:
   - CODERABBIT ist eine eingetragene US-Wortmarke (Reg.-Nr. 7548845 laut Markenverzeichnis, GESAGT, [tm-cr]).
   - Anthropic untersagt seine Namen "as part of your own product, feature, or company name" ([cc-legal] BELEGT).
   - Nominative Nennung im Fließtext ("unterstützt Claude Code", "Vergleich mit CodeRabbit") ist üblich. Dabei ohne Logos und ohne Anschein einer Partnerschaft (ABGELEITET).

---

## 2. Befunde mit Quellen

### 2.1 Lizenzoptionen für ein selbst hostbares Agenten-Produkt

| Option | Kern (Primärtext) | Für unser Ziel | Einstufung |
|---|---|---|---|
| **Apache-2.0** | erlaubend; ausdrückliche Patentlizenz; Beiträge stehen ohne Zusatzvertrag unter derselben Lizenz ("any Contribution intentionally submitted ... shall be under the terms and conditions of this License", §5); keine Markenrechte ("does not grant permission to use the trade names, trademarks", §6) | passt: freie Nutzung, Patentschutz, Marke bleibt geschützt | BELEGT [apache2] |
| **MIT** | erlaubend, kurz, keine ausdrückliche Patentlizenz | geht, schwächer beim Patentschutz | BELEGT [bothy-adr3] |
| **AGPL-3.0** | §13: Wer das Programm ändert, muss allen, die es über ein Netz nutzen, den Quelltext anbieten ("must prominently offer all users interacting with it remotely through a computer network ... an opportunity to receive the Corresponding Source") | schützt vor geschlossenen SaaS-Forks, schreckt aber Firmen ab, die es intern betreiben; widerspricht "jeder soll es selbst hosten" nicht formal, aber praktisch | BELEGT [agpl]; Wirkung ABGELEITET |
| **MPL-2.0** | Copyleft je Datei | Pflichten je Datei belasten Betreiber mit Anpassungen | ABGELEITET, wie [bothy-adr3] |
| **Open Core (`ee/`-Ordner)** | Kern MIT, `ee/` unter Firmenlizenz (Langfuse, PostHog) bzw. AGPL plus `.ee.`-Dateien (Kodus) | nur sinnvoll mit Geschäftsmodell; erzeugt zwei Lizenzwelten im Repo; Beitragende brauchen dann meist ein CLA | BELEGT [langfuse-lic], [posthog-lic], [kodus-lic] |
| **FSL (Fair Source)** | "Permitted Purpose is any purpose other than a Competing Use"; Umwandlung nach Apache-2.0 oder MIT am zweiten Jahrestag je Version | keine Open-Source-Lizenz im Sinne der OSD (Punkt 6: "must not restrict anyone from making use of the program in a specific field of endeavor") | BELEGT [sentry-lic], [fsl], [osd] |
| **BSL 1.1** | nur "non-production use", Produktion nur per "Additional Use Grant"; Umwandlung spätestens am vierten Jahrestag; Selbstauskunft: "is not an Open Source license" | widerspricht der Owner-Vorgabe "Open Source" | BELEGT [bsl] |

### 2.2 Was vergleichbare Projekte gewählt haben

Lizenz über die GitHub-API (`/repos/<r>/license`) und den Lizenztext selbst gelesen, Stand 2026-10-31. CLA/DCO aus `CONTRIBUTING.md` per grep.

| Projekt | Lizenz (Datei) | Beiträge | Muster | Einstufung |
|---|---|---|---|---|
| PR-Agent / The-PR-Agent | MIT | kein CLA/DCO in CONTRIBUTING gefunden | erlaubend | BELEGT |
| Kodus | AGPL-3.0, Dateien mit `.ee.` oder in `ee/` unter "Kodus Enterprise Code License" ("does not permit Community users to modify the Enterprise Code") | kein Treffer | Copyleft plus Open Core | BELEGT [kodus-lic] |
| OpenHands | `main`: MIT (README nennt keinen anderen Teil); Tag `cloud-1.47.1` `enterprise/LICENSE`: PolyForm Free Trial 1.0.0 ("may not distribute copies") | kein Treffer | MIT plus getrennter Enterprise-Teil | BELEGT [oh-lic] |
| Sweep | "Sweep Enterprise Edition (EE) license": Produktion nur mit Abo; Teile "MIT Expat" | | Source-available | BELEGT [sweep-lic] |
| Langfuse | MIT außerhalb `ee/`, `web/src/ee/`, `worker/src/ee/`, `packages/shared/src/server/ee/` | CLA über cla-assistant | Open Core | BELEGT [langfuse-lic] |
| Sentry | FSL-1.1-Apache-2.0 | kein Treffer | Fair Source | BELEGT [sentry-lic] |
| PostHog | MIT außerhalb `ee/` | | Open Core | BELEGT [posthog-lic] |
| Plane | AGPL-3.0 | kein Treffer | Copyleft | BELEGT [plane-lic] |
| Cal.com | Repo `calcom/cal.com` leitet heute auf `calcom/cal.diy` um: MIT, "a fork of Cal.com with all enterprise/commercial code removed", "strictly recommended for personal, non-production use" | | Kommerzieller Kern nicht mehr im öffentlichen Repo | BELEGT [caldiy]; Hintergrund des Wechsels ungeprüft |
| Dify | "modified version of the Apache License 2.0": kein Mehrmandantenbetrieb ohne schriftliche Erlaubnis, Logo im Frontend darf nicht entfernt werden, Beitragende stimmen Lizenzänderungen zu | | Source-available | BELEGT [dify-lic] |
| n8n | "Sustainable Use License": nur "for your own internal business purposes or for non-commercial or personal use"; `.ee.` gesondert | | Source-available | BELEGT [n8n-lic] |
| Continue | Apache-2.0 | **CLA** | erlaubend plus CLA | BELEGT |
| Cline | Apache-2.0 | kein Treffer | erlaubend | BELEGT |
| Aider | Apache-2.0 | **Individual CLA** | erlaubend plus CLA | BELEGT |
| Goose | Apache-2.0; Repo `block/goose` leitet auf `aaif-goose/goose` um | kein Treffer | erlaubend | BELEGT; Bedeutung des Org-Wechsels ungeprüft |
| bothy (Projekt des Owners) | Apache-2.0, NOTICE "The Bothy Authors" | **DCO**, geprüft per commit-msg-Hook und CI | erlaubend plus DCO, zwei Repos | BELEGT [bothy-adr3], [bothy-adr2] |

**Lesart (ABGELEITET):**
- Wer ein Geschäft mit gehosteter Version oder Enterprise-Funktionen schützen will, wählt Open Core (Langfuse, PostHog, Kodus), Fair Source (Sentry) oder eine eigene Lizenz (n8n, Dify).
- Reine Agenten-Werkzeuge ohne eigenes Hosting-Geschäft wählen Apache-2.0 oder MIT (Continue, Cline, Aider, Goose, OpenHands-Kern, PR-Agent).
- Unser Fall ist der zweite, solange der Owner kein Geschäftsmodell vorgibt.

### 2.3 Verträglichkeit mit Bausteinen und SDKs

| Baustein | Lizenz | Mit Apache-2.0-Projekt | Einstufung |
|---|---|---|---|
| Bausteine unter MIT oder Apache-2.0 (etwa PR-Agent, claude-code-security-review, reviewdog; Lizenzen in 2.2 bzw. [ebene-statische-analyse-und-security](ebene-statische-analyse-und-security.md) 2.3 und 2.4) | MIT oder Apache-2.0 | verträglich. Pflichten: Copyright- und Lizenzhinweis; bei Apache-2.0 zusätzlich NOTICE übernehmen und geänderte Dateien kennzeichnen (§4) | Lizenzen BELEGT dort; Pflichten BELEGT [apache2]; Lizenz je Baustein vor Übernahme erneut prüfen |
| Kodus, Sweep, GitNexus, OpenHands `enterprise/` | AGPL-3.0 plus EE, Sweep EE, PolyForm Noncommercial, PolyForm Free Trial | nur Ideen, kein Code (ADR-34 bleibt richtig) | BELEGT |
| GPL-3.0-Code (etwa Serena) | GPL-3.0 | nicht einbinden; Apache-2.0 lässt sich in GPLv3 aufnehmen, umgekehrt nicht | BELEGT [asf-gpl] |
| Vercel AI SDK (`ai` 7.0.159, `@ai-sdk/anthropic` 4.0.94) | Apache-2.0 | verträglich | BELEGT (npm-Registry) |
| pg-boss 12.38.0 | MIT | verträglich | BELEGT (npm-Registry) |
| `@anthropic-ai/sdk` 1.3.0 | Apache-2.0 | verträglich | BELEGT (npm-Registry) |
| **Claude Agent SDK TypeScript** `@anthropic-ai/claude-agent-sdk` 0.3.316 | "SEE LICENSE IN README.md"; `LICENSE.md`: "© Anthropic PBC. All rights reserved. Use is subject to the Legal Agreements outlined here: https://code.claude.com/docs/en/legal-and-compliance."; 8 plattformspezifische `optionalDependencies` | Nutzung als Abhängigkeit ja; mitliefern nein (proprietär). Dass die Plattform-Pakete das native CLI enthalten: VERMUTET, Inhalt nicht entpackt | BELEGT [sdk-npm] |
| Claude Agent SDK Python | Repo-LICENSE MIT, README: "Use of this SDK is governed by Anthropic's Commercial Terms of Service, including when you use it to power products and services that you make available to your own customers"; "The Claude Code CLI is automatically bundled with the package" | Wrapper-Code MIT, gebündeltes CLI proprietär. Für uns irrelevant, weil TypeScript (ADR-03) | BELEGT [sdk-py] |
| Claude Code CLI `@anthropic-ai/claude-code` 2.1.316 | "© Anthropic PBC. All rights reserved. Use is subject to Anthropic's Commercial Terms of Service" | nicht mitliefern, siehe 2.5 | BELEGT [cc-npm] |
| Codex CLI `@openai/codex` 0.166.0, Gemini CLI `@google/gemini-cli` 0.66.0 | Apache-2.0 | Code verträglich; Nutzungsbedingungen des Dienstes getrennt (2.8) | BELEGT (npm-Registry) |
| OpenBao | MPL-2.0 laut [05](../architecture/05-security.md) (dort ungeprüft) | als unveränderter getrennter Dienst unproblematisch | ABGELEITET |
| Opengrep-Engine, Semgrep CE | LGPL-2.1 | als getrenntes Programm aufrufen: verträglich | BELEGT [opengrep], [semgrep] |
| Semgrep-Regeln (`semgrep/semgrep-rules`) | Semgrep Rules License v1.0: "only for your own internal business purposes", "does not allow you to distribute the rules, or to make them available to others as a service" | **nicht mitliefern** | BELEGT [semgrep-rules] |
| Opengrep-Regeln (`opengrep/opengrep-rules`) | "Commons Clause" License Condition v1.0 | nicht mitliefern ohne genaue Prüfung | BELEGT (Kopf der Datei) [opengrep-rules] |
| CodeQL-CLI | nur "Perform analysis on the Open Source Codebase" (OSI-Lizenz), CI nur, wenn auf GitHub.com gehostet; nicht für private Repos außer mit GHAS | für unser eigenes öffentliches Repo erlaubt; als Produktbaustein für private Repos der Betreiber nicht | BELEGT [codeql] |
| SonarQube Community Build | Kern LGPL-3.0; mitgelieferte Analyzer (`sonar-java-plugin` 8.46, `sonar-javascript-plugin` 14.3, `sonar-python-plugin` 5.32 als `bundledPlugin`) unter SSALv1 ("SonarQube analyzers released after November 29, 2024 ... are published under ... SSALv1") | nicht in unser Produkt integrieren, siehe 2.7 | BELEGT [sonarqube], [ssal], [sonarjs] |
| Martian-Datensatz, DBOS | ungeprüft | offen (O12, [09](../architecture/09-decisions.md) Abschnitt 5) | ungeprüft |

**Prompts und Texte aus Fremdquellen** im öffentlichen Repo (ABGELEITET):
- Jede übernommene Prompt-Datei trägt einen SPDX-Kopf und eine Herkunftszeile (Repo@Commit:Pfad).
- Apache-Texte werden als geändert markiert und in `THIRD_PARTY_NOTICES` aufgeführt.
- Geleakte oder proprietäre Prompt-Texte erscheinen im öffentlichen Repo nicht, auch nicht als Zitat.

### 2.4 DCO oder CLA, Governance

- **DCO** ist ein Satz, den Beitragende pro Commit mit `Signed-off-by` bestätigen. Es braucht keinen Vertrag mit einer Firma. Beiträge stehen dann unter Apache-2.0 §5 (inbound = outbound). bothy setzt das per commit-msg-Hook und CI-Gate durch ([bothy-adr3] BELEGT).
- **CLA** (Continue, Aider, Langfuse) erlaubt dem Inhaber späteres Umlizenzieren. Es braucht aber einen Unterschriftsprozess und schreckt ab.
- **Dify** zeigt, wohin ein CLA führen kann: Beitragende stimmen zu, dass "The producer can adjust the open-source agreement to be more strict or relaxed" ([dify-lic] BELEGT).
- **Governance:** Das bothy-Muster ist direkt übertragbar ([bothy-gov] BELEGT):
  - Maintainer in CODEOWNERS;
  - dauerhafte Entscheidungen als ADR per PR;
  - Lazy Consensus bei mehreren Maintainern;
  - Triage-Labels und SECURITY.md;
  - Änderungen an der Governance nur mit Zustimmung aller Maintainer.
- **Wer Lizenzgeber ist, muss vor dem ersten öffentlichen Commit feststehen:** der Owner privat oder sein Arbeitgeber. Schreibt der Owner das Projekt in Arbeitszeit oder mit Firmenmitteln, kann das Recht am Code beim Arbeitgeber liegen. Dann braucht es eine schriftliche Freigabe (ABGELEITET, Rechtsfrage, siehe Owner-Entscheidung L6).

### 2.5 Anthropic: Nutzungsbedingungen am Originaltext

**a) Claude Code Legal and compliance** ([cc-legal], BELEGT, wörtlich):
- Lizenz: "Commercial Terms of Service - for Team, Enterprise, and Claude API users"; "Consumer Terms of Service - for Free, Pro, Max, and Ultra users".
- Claude Code in eigenen Produkten: "preinstalling or running Claude Code in your products or services (e.g. in hosted sandboxes or other agent infrastructure) requires agreeing to our Commercial Terms of Service". Dazu kommen zwei Bedingungen:
  - "The Claude Code binary must not be modified. ... customers may not remove, disable, or restrict any authentication method built into it (including methods that permit signing in with a Claude account or the user's own API key)."
  - "Customers may not pay for, resell, or intermediate Claude usage on their end users' behalf. Each end user must authenticate with their own Anthropic API key, Claude subscription plan credentials, or 3P inference provider credential".
- Name: "You can accurately say, in plain text, that your product has Claude Code preinstalled or that it runs Claude Code. But you can't use the Claude Code or Anthropic names or logos as part of your own product, feature, or company name, in your own logo, or in a way that suggests Anthropic built, endorses, or is partnered with your product."
- Abo-Limits: "Advertised usage limits for Pro, Max, and Ultra plans assume ordinary, individual usage of Claude Code and the Agent SDK."
- Login in Drittprodukten: "Anthropic does not permit third-party developers to offer Claude.ai login into their own applications, or to route requests through Free, Pro, Max, or Ultra plan credentials on behalf of their users. Moreover, developers may not collect, store, or intermediate Claude.ai credentials or session tokens - sign-in to a Claude account must complete through Anthropic's own flow." (Im Original steht statt " - " ein Gedankenstrich; hier gemäß Textregel ersetzt.)
- Ausnahme: Nicht eingeschränkt ist, dass "an end user [signs] in to the unmodified Claude Code binary with their own Claude subscription, including where a platform hosts Claude Code". Ebenso frei ist das Verwalten eigener API-Keys "for use by the customer's own authorized users", solange "billed to the key owner" und "not resold or intermediated".
- Durchsetzung: "Anthropic reserves the right to take measures to enforce these restrictions and may do so without prior notice."

Diese Zitate stimmen mit [05](../architecture/05-security.md) Abschnitt 6 überein; dort fehlen nur der Absatz zum Namen und der Satz zu eigenen API-Keys.

**b) Consumer Terms** ([an-consumer], BELEGT). Ausgeliefert wurde bei Abruf aus Deutschland die EWR-Fassung: Vertragspartner "Anthropic Ireland, Limited", "Effective Oct 8, 2025". Die Fassung für Nicht-EWR-Kunden ist ungeprüft.
- §3: "You may not access or use, or help another person to access or use, our Services in the following ways: ... To develop any products or services that compete with our Services, including to develop or train any artificial intelligence or machine learning algorithms or models or resell the Services."
- §3: "Except when you are accessing our Services via an Anthropic API Key or where we otherwise explicitly permit it, to access the Services through automated or non-human means, whether through a bot, script, or otherwise."
- §2: "You may not share your Account login information, Anthropic API key, or Account credentials with anyone else or make your Account available to anyone else."
- §11: "Non-commercial use only. You agree that you will not use our Services for any commercial or business purposes and we and our Providers have no liability to you for any loss of profit". In der EWR-Fassung steht der Satz im Haftungsabschnitt.
- **Korrektur zu [05](../architecture/05-security.md) Abschnitt 6:** Dort steht "BELEGT laut Recherche, nicht selbst gelesen". Jetzt ist der Text selbst gelesen. Die Fundstelle ist §11 der EWR-Fassung, und die Klauseln zu automatisiertem Zugriff und zu Wettbewerb kommen hinzu.

**c) Commercial Terms** ([an-commercial], BELEGT, "Effective Jun 17, 2025"):
- A.1: "Anthropic gives Customer permission to use the Services, including to power products and services Customer makes available to its own customers and end users".
- B: "Customer (a) retains all rights to its Inputs, and (b) owns its Outputs."
- D.4: "Customer may not and must not attempt to (a) access the Services to build a competing product or service, including to train competing AI models or resell the Services except as expressly approved by Anthropic; (b) reverse engineer or duplicate the Services".

**d) Usage Policy** ([an-aup], BELEGT). Die Seite zeigt "Effective Nov 12, 2026", also eine angekündigte Fassung. Welche Fassung heute gilt, ist ungeprüft.
- "Agentic use cases must comply with the Usage Policy. Users are responsible for ensuring that agents they build or deploy, including actions those agents take through tools, browsers, or connected systems, comply with this Usage Policy."
- Sicherheitsfunktionen (Security-Review, Fix) sind gedeckt: "This section does not prohibit security research, testing, or tool development conducted on systems you own or operate, with the authorization of the system owner".

**e) Agent SDK und Abo** ([cc-sdkplan], BELEGT):
- "Update June 15, 2026: ... Claude Agent SDK, claude -p, and third-party app usage still draw from your subscription limits."
- "Update October 7, 2026: Claude Max, Ultra, and Team plans now include monthly API credits. They cover the Claude API, Claude Managed Agents, and the Claude Agent SDK and claude -p when you run them with an API key from your linked Claude Console organization."

**f) Agent SDK Branding** ([cc-sdk-overview], BELEGT):
- Erlaubt: "{YourAgentName} Powered by Claude".
- Nicht erlaubt: "Claude Code" oder "Claude Code Agent".
- "Your product should maintain its own branding and not appear to be Claude Code or any Anthropic product."

**Was das für ein öffentliches Projekt mit Startweg `subscription` heißt (ABGELEITET):**

| Fall | Lesart | Grund |
|---|---|---|
| Ein Betreiber installiert das Projekt selbst, loggt sich mit `claude /login` oder `claude setup-token` im unveränderten Binary ein und lässt nur eigene Läufe auf eigenen Repos laufen | vermutlich gedeckt | [cc-legal]: Endnutzer mit eigenem Abo im unveränderten Binary, "including where a platform hosts Claude Code". Wir sind nicht der Anbieter eines Logins, das Projekt sieht das Token nicht (ADR-18) |
| Derselbe Betreiber lässt Läufe auslösen, die Kollegen oder fremde Issue-Autoren starten | nicht gedeckt | "route requests ... on behalf of their users"; Consumer Terms §2 "make your Account available to anyone else" |
| Eine Firma betreibt das Projekt für ihr Team mit einem Abo | nicht gedeckt | wie oben; dafür API-Key, WIF, Bedrock, Vertex, Foundry |
| Autonomer Dauerbetrieb (Ticket bis Merge, Cron) über ein Pro-, Max- oder Ultra-Abo | Graubereich | Consumer Terms §3 "automated or non-human means ... except ... where we otherwise explicitly permit it". `claude -p` und das SDK auf dem Abo sind laut [cc-sdkplan] ausdrücklich vorgesehen. Gegen den autonomen Dauerbetrieb sprechen aber "ordinary, individual usage" und, in der EWR-Fassung, "Non-commercial use only" |
| Unser Projekt baut einen eigenen OAuth-Login oder liest `.credentials.json`, um Tokens zu verteilen | verboten | "offer Claude.ai login into their own applications", "collect, store, or intermediate" |
| Unsere Docker-Images enthalten `claude` oder die SDK-Plattformpakete | vermeiden | proprietär ("All rights reserved"). Wer vorinstalliert, braucht die Commercial Terms. Wir als Projekt wären Verbreiter, nicht der Betreiber |
| Wir entwickeln das Produkt mit Claude Code auf dem Abo des Owners | zwei Lesarten | Interaktives Programmieren ist der Normalfall von Claude Code. Consumer Terms §3 untersagt aber "develop any products or services that compete with our Services". Commercial Terms D.4 enthalten dieselbe Klausel. Ob ein Review-Produkt auf Claude als "competing" gilt, ist offen. Es betrifft jedes Produkt auf Claude-Basis und ist kein Sonderrisiko des Abos |

**Folgerung (ABGELEITET):**
- Im öffentlichen Projekt bleibt `subscription` ein persönlicher Betreibermodus, standardmäßig aus.
- Das Einschalten verlangt eine ausdrückliche Bestätigung in der Konfiguration, die auf [cc-legal] verweist.
- Die Auflagen 1 bis 8 aus [05](../architecture/05-security.md) Abschnitt 6 gelten unverändert. Der Resolver erzwingt sie bereits technisch.
- Für den Testbetrieb gibt es einen Weg ohne Graubereich und ohne Mehrkosten: das in Max, Ultra und Team enthaltene API-Guthaben über einen Console-Key ([cc-sdkplan]). Welchen Plan der Owner hat, ist ungeprüft.

### 2.6 CodeRabbit Terms of Service

Quelle [cr-tos], "Updated: April 20, 2026", Vertragspartner CodeRabbit, Inc., kalifornisches Recht (BELEGT):

- **4.2 Limitations:** "Customer and its Users shall not and shall not permit or assist any other party to:
  - (ii) decompile, disassemble, reverse engineer or otherwise attempt to derive the source code, underlying ideas, techniques, structure or algorithms of the Services;
  - (iii) copy, modify, translate, create derivative works of ... the Services or any portion thereof;
  - (iv) disclose the results of any benchmarking of the Services, or use the Services to develop competing products or services without CodeRabbit's prior written consent;
  - ... (vi) use any automated system or software (including robots, spiders, or scripts) to extract data or content from the Services".
- **6.2 Output:** "Subject to Customer's compliance with this Agreement, including but not limited to paying all fees when due, CodeRabbit hereby assigns to Customer all of its rights, title and interest (if any) in and to the Output." Dazu: "Customer agrees that CodeRabbit may use Aggregated Data and Output to (a) provide, maintain, protect and improve the Services".
- **7.1:** "CodeRabbit's software, ... the design and layout of the CodeRabbit Platform user interface, all pricing information ... shall be deemed the Confidential Information of CodeRabbit". Ausgenommen ist, was "is or becomes publicly known".
- **5.4:** Sections 3 bis 13 gelten nach Vertragsende weiter. Der Verzicht gilt also auch nach einer Kündigung.

**Kostenloser Plan für öffentliche Repos (GESAGT, Herstellerseiten):**
- "install CodeRabbit on a public repository, and receive free reviews forever for public repositories" ([cr-pricing]).
- "The repo is public. That's the whole bar CodeRabbit uses." ([cr-oss]).
- Grenzen nennt die Seite nicht.
- Der kostenlose Plan ist kein eigener Vertrag. Es gelten dieselben Terms (ABGELEITET: die ToS gelten "whether as a guest or registered user").

**Antworten auf die Fragen des Auftrags (ABGELEITET, Wortlaut oben):**

1. **Darf CodeRabbit am Entwicklungs-Repo beim Nachbau helfen?** Nach 4.2 (iv) nicht ohne vorherige schriftliche Zustimmung. Das Repo entwickelt ausdrücklich einen CodeRabbit-Ersatz, und die Owner-Vorgabe sagt selbst "CodeRabbit hilft beim Nachbau". Die bothy-Lösung lässt sich hier nicht übertragen: bothy ist kein Konkurrenzprodukt.
2. **Dürfen CodeRabbit-Kommentare aus bothy und unserem Repo als Eval-Daten dienen?** Das Recht am Output liegt beim Owner, "subject to Customer's compliance". Die Nutzung als Ground Truth für ein Konkurrenzprodukt ist aber eine Nutzung der Dienste "to develop competing products". R1 in [07](../architecture/07-eval.md) Abschnitt 3.1 stützt sich genau darauf. Ein öffentlicher Vergleich "unser Reviewer gegen CodeRabbit" wäre zusätzlich "disclose the results of any benchmarking". Das berührt Gate B und O13.
3. **Was erlaubt bleibt:**
   - Öffentlich zugängliche Herstellerdoku lesen und Funktionen beschreiben. Das ist Wissen, keine Nutzung der Dienste. **Überholt (Red Team 2026-10-31):** [cr-tos] 1.9 zählt Website und Inhalte zu den "Services", [sonar-aup] §5 nennt "Documentation"; auch das Auswerten der Doku für den Nachbau kann darunter fallen, es gilt [10](../architecture/10-standards-per-layer.md) Abschnitt 16.
   - Fremde, von Dritten veröffentlichte Benchmarks zitieren (etwa Martian, GESAGT).
   - Eigene Messungen auf Datensätzen ohne CodeRabbit-Ausgaben.
4. **Reverse Engineering:** Sichtbare Artefakte aus Kommentaren (Marker, Kopfzeilen) zu sammeln, ist Beobachtung öffentlicher Inhalte. Die Klausel (ii) verbietet aber auch, "underlying ideas, techniques, structure or algorithms" abzuleiten. Für Kunden ist das eine ausdrückliche Vertragspflicht. Ob sie nach deutschem Recht hält (§ 69d, § 69e UrhG gelten nur für Programme, nicht für Dienste), ist eine Rechtsfrage. Empfehlung: keine weiteren Ableitungen aus CodeRabbit-Ausgaben, solange ein Kundenverhältnis besteht.

### 2.7 SonarQube Cloud und Community Build

**SonarQube Cloud.** Seit 2026 gilt das "SonarSource Primary Customer Agreement" ([sonar-pca] "Updated August 27, 2026") mit Supplemental Terms. Die frühere Cloud-ToS mit KI-Klausel liegt im Archiv (GESAGT, Suchauszug [sonar-archive]).
- **PCA 2.2:** Rechte nur "conditioned on ... the SonarSource Acceptable Use Policy ..., including use of the Products and Alerts solely for Customer's and its Affiliates' internal development purposes."
- **PCA Definitionen:** "SonarSource's no-cost software downloads (such as SonarQube Community Build and SonarQube for IDE) are not Products covered by this Agreement."
- **Free-Tier-Bedingungen** ([sonar-free], BELEGT):
  - "SonarSource may modify or discontinue the Free Tier at any time without liability".
  - "Customer shall ensure that Customer Data provided to Free and Team Plans does not contain Personal Data".
  - "SonarSource may use Customer Data and Usage Data provided to Free and Team Plans to develop, train, tune, and improve SonarSource's products, services, and machine learning models".
- **AUP** ([sonar-aup], "Last updated November 7, 2025", BELEGT), jeweils "without prior written consent":
  - §5: "Access or use the Products or Documentation if you are a direct competitor of SonarSource."
  - §5: "Disclose, publish, or otherwise make publicly available any benchmark, comparative, or performance tests or evaluations of the Products."
  - §6: "Use Results Data to train, fine-tune, or otherwise improve any LLM Technologies, including but not limited to models or systems for code analysis, code quality assessment, code generation, or code improvement."
  - §6: "Use Results Data to develop, build, or enhance products or services that compete with the Products, including but not limited to static code analysis tools, code quality platforms, security scanning tools, or code review systems (whether based on LLM Technologies or not.)"
  - Ausnahme: "nothing in this section prohibits Customer from: (a) using Results Data in conjunction with general-purpose AI coding assistants ... for Customer's internal software development purposes; or (b) using Results Data to improve Customer's own code or software products that are not competitive with the Products".
- **Plan für öffentliche Projekte** (GESAGT, [sonar-oss]): Im Forum am 2026-01-27 angekündigt. Für die Teilnahme reiche, dass ein Projekt öffentlich ist: "It is the latter. The plan is available for public projects." Eigene Bedingungen für diesen Plan nennt die Seite nicht.

**SonarQube Community Build** ([sonarqube], [ssal], BELEGT):
- Der Kern steht unter LGPL-3.0.
- Die gebündelten Analyzer stehen unter SSALv1. Ihre Rechte gelten nur für "Non-competitive Purpose", und der schließt aus:
  - "(a) providing to others any product or service that includes or offers the same or substantially similar functionality as SonarQube,
  - (b) Competing with SonarQube, and/or
  - (c) employing, using, or engaging artificial intelligence technology that is not part of the Program to ingest, interpret, analyze, train on, or interact with the data provided by the Program".
- "Competing" heißt dort "marketing a product or service as a substitute for the functionality or value of SonarQube ... even if it is provided free of charge."

**Lesart (ABGELEITET):**
1. **Cloud am Entwicklungs-Repo:** Unser Produkt ist ein KI-Code-Review-System, und Sonar vermarktet selbst "AI code review" (Navigationsleiste von sonarsource.com). Damit greifen §5 ("direct competitor") und §6 ("code review systems"). Die Ausnahme (b) gilt nur für Produkte, die "not competitive" sind. Ohne schriftliche Zustimmung ist der Anschluss ein Vertragsrisiko.
2. **Community Build am Entwicklungs-Repo:** Lokal oder in CI für den eigenen Code laufen zu lassen, ist kein "providing to others". Unser Ablauf gibt aber Befunde an Claude Code zum Beheben ("A finding that only CodeRabbit sees becomes a local rule", bothy `.coderabbit.yaml`). Das ist nach (c) ausgeschlossen. Ob unser Produkt "Competing" im Sinne der SSAL ist, hängt vom Marketing ab. Wir sollten es nie als Ersatz für SonarQube darstellen.
3. **Sonar im Produkt** (ein Plugin, das Sonar-Ergebnisse in den Reviewer oder Fixer speist): Für die Analyzer verbietet das SSAL (c). Bei Cloud ist es nur für "general-purpose AI coding assistants ... internal" frei, und ob unser Produkt darunter fällt, ist offen. **Kein mitgeliefertes Sonar-Plugin.** Allenfalls ein neutraler SARIF-Import, für den der Betreiber selbst verantwortlich ist.
4. **Für bothy** (kein Konkurrenzprodukt) gelten diese Grenzen nur teilweise. Das bothy-Muster ist also nicht eins zu eins übertragbar.

### 2.8 OpenAI Codex und Google Gemini CLI (kurz)

**Codex** ([codex-auth], BELEGT):
- "Use API key authentication for programmatic Codex CLI workflows, such as CI/CD jobs. Don't expose Codex execution in untrusted or public environments."
- Für Automatisierung mit ChatGPT-Konto gibt es Access Tokens nur in ChatGPT-Enterprise-Workspaces: "intended for trusted scripts, schedulers, and private CI runners".
- `~/.codex/auth.json` "contains access tokens. Don't commit it, paste it into tickets, or share it in chat."
- Die OpenAI Terms of Use selbst ließen sich nicht lesen (HTTP 403 bei `curl` und WebFetch): **ungeprüft**.
- Folge (ABGELEITET): Credential-Art `chatgpt` nur als persönlicher Betreibermodus wie `subscription`; für Pipelines `openai` (API-Key) bzw. `azure_openai`.

**Gemini CLI** ([gemini-tos], "Last updated: Apr 10, 2026", BELEGT):
- "Directly accessing the services powering Gemini CLI (for example, the Gemini Code Assist service) using third-party software, tools, or services (for example, using OpenClaw with Gemini CLI OAuth) is a violation of applicable terms and policies. Such actions may be grounds for suspension or termination of your account."
- Hinweis auf derselben Seite: "Unpaid tier and Google One users: Gemini CLI was replaced by Antigravity CLI on June 18th, 2026."
- Folge (ABGELEITET): Google-Login nur im unveränderten CLI, nie dessen Token in eigenem Code. Für Pipelines Gemini-API-Key oder Vertex. Ob die Gemini-CLI-Runtime aus [01](../architecture/01-plugin-interfaces.md) auf Antigravity CLI umziehen muss, ist offen (Thema der Harness-Recherche).

**OpenCode** hat die Claude-Abo-Plugins entfernt ("Anthropic explicitly prohibits this", [opencode] in [README](../architecture/README.md), dort BELEGT). Das bestätigt die Lesart aus 2.5.

### 2.9 Was aus `docs/` und `data/` nicht ins öffentliche Repo darf

Stand 2026-10-31 (ABGELEITET); die verbindliche Liste steht in [12](../architecture/12-open-source-and-project.md) Abschnitt 4.2.

| Inhalt | Problem | Behandlung |
|---|---|---|
| nicht veröffentlichte Vorarbeiten und Daten | Firmeninterna, Hostnamen, Kosten, lokale Pfade, Hinweise auf Leak-Sammlungen; CodeRabbit-Ausgaben aus einem eigenen Projekt, deren Nutzung für ein Konkurrenzprodukt nach [cr-tos] 4.2 (iv) fraglich ist (2.6) | privat; CodeRabbit-Ausgaben nie als Ground Truth ohne Owner-Entscheidung L3 |
| `docs/architektur/*.md` | Firmen- und Betreiberdetails einer Installation | öffentlich erst nach Neutralisierung; Instanzwerte ins Ops-Repo (Muster [bothy-adr2]: "Die Konfigurationsreferenz im Produkt beschreibt jeden Schlüssel, das Ops-Repository setzt nur Werte") |
| Eval-Daten aus privaten Repos und Transkripte | Firmencode und personenbezogene Daten | nie öffentlich; der Eval-Dienst braucht eine getrennte private Ablage (in [07](../architecture/07-eval.md) Abschnitt 1 schon als privat geplant) |

**Trennung (ABGELEITET, nach [bothy-adr2]):**
- Zwei Repos:
  - öffentliches Produkt mit neutralen Beispielwerten (`example.com`, generische Org);
  - privates Ops-Repo mit Instanzkonfiguration, Runbooks für die Azure-Instanz des Owners, Vorrecherchen, Eval-Daten und der Deny-Liste.
- Ein Deny-List-Scanner mit der privaten Liste prüft jeden Push und vor dem Öffentlich-Schalten die ganze Historie. Dazu kommt gitleaks.
- Da es noch keinen Commit gibt, beginnt das öffentliche Repo leer. Der heutige Ordner wird zum Ops-Repo oder in eins verschoben. Was davon öffentlich wird, übernimmt das Produkt-Repo neu, ohne Historie.

---

## 3. Folgen für unsere Architektur

| Datei | Abschnitt | Was neu oder anders |
|---|---|---|
| [README.md](../architecture/README.md) | Titel, Abschnitt 1 | Der Titel mit Firmennamen wird zu einem neutralen Projektnamen (Owner-Entscheidung L2). Abschnitt 1 nennt die dritte Runde: Open Source, selbst hostbar, mehrere Clouds. Die Firma erscheint nur noch als erste Installation im Ops-Repo |
| README.md | Abschnitt 6 Quellen | ergänzen: [cc-legal] (jetzt mit Namens- und API-Key-Absatz), [an-consumer] (selbst gelesen, EWR-Fassung), [an-commercial], [an-aup], [cr-tos], [sonar-aup], [ssal], [semgrep-rules], [codeql], [apache2] |
| README.md | Abschnitt 7 Vorrang | dritte Runde aufnehmen; Installationsquellen und lokale Pfade nur im Ops-Repo |
| [01-plugin-interfaces.md](../architecture/01-plugin-interfaces.md) | Abschnitt 1 Manifest | Feld `license` (SPDX) je Plugin. Mitgelieferte Plugins nur mit Lizenzen der Allowlist (Apache-2.0, MIT, BSD, ISC, MPL-2.0 unverändert). Plugins, die der Betreiber selbst nachlädt, laufen außerhalb des Prozesses und dürfen jede Lizenz haben; die Admin-UI zeigt sie an |
| 01 | Abschnitt 6 Zeile `subscription`, Zeile `chatgpt` | Zusatz "persönlicher Betreibermodus, standardmäßig aus, die Plattform implementiert keinen Login und liest kein Token". Dieselbe Regel für `chatgpt` (2.8) und für Google-Login. Gemini CLI: Hinweis auf Antigravity CLI prüfen lassen |
| 01 | Abschnitt 11 | Spalte "Nutzungsbedingungen" je Credential-Art mit Fundstelle (2.5, 2.8) |
| [02-services.md](../architecture/02-services.md) | Abschnitt 2 Coder, Punkt 4 Self-Check-Bündel | "Semgrep oder Opengrep" wird zu: Engine Opengrep oder Semgrep CE (LGPL-2.1) als getrenntes Programm, nur mit eigenen Regeln unter Apache-2.0 bzw. Regeln, die der Betreiber selbst einbindet. `semgrep-rules` und `opengrep-rules` werden nicht mitgeliefert. CodeQL nur, wenn der Betreiber GHAS hat oder das Ziel-Repo OSI-lizenziert und auf GitHub.com ist. Kein SonarQube-Plugin im Lieferumfang |
| 02 | Abschnitt 3 Reviewer, Gate B | Vergleichswerte nur aus von Dritten veröffentlichten Benchmarks. Keine eigenen veröffentlichten Vergleichsläufe gegen CodeRabbit oder SonarQube ohne Zustimmung |
| [04-configuration-and-limits.md](../architecture/04-configuration-and-limits.md) | Abschnitt 3 und 3a | `credential.kind: subscription` und `chatgpt` verlangen `acknowledge_terms: <Fassung>` mit Verweis auf [cc-legal] bzw. [codex-auth]. Der Plattform-Default sperrt beide. Beispiel 3a ist eine Instanzkonfiguration und wandert ins Ops-Repo; im Produkt bleibt ein neutrales Beispiel |
| [05-security.md](../architecture/05-security.md) | Abschnitt 6 | Zitat Consumer Terms als selbst gelesen markieren (EWR-Fassung §11), dazu §3 "automated or non-human means" und "compete", §2 "make your Account available". Den Absatz zum Namen aus [cc-legal] ergänzen. Satz zum öffentlichen Projekt: "Die Auflagen gelten in jeder Installation; das Projekt liefert keinen Login und kein Token" |
| [06-operations-and-deployment.md](../architecture/06-operations-and-deployment.md) | Abschnitt 3 Technikwahl, neuer Abschnitt "Artefakte und Lizenzen" | Container-Images ohne `@anthropic-ai/claude-code`, ohne `@anthropic-ai/claude-agent-sdk-*`-Plattformpakete und ohne andere proprietäre CLIs. Der Worker installiert die gepinnte Version beim Betreiber aus npm beim ersten Start oder per Init-Container; die Prüfsumme kommt aus der Konfiguration. Jede Veröffentlichung trägt SBOM, `LICENSE`, `NOTICE`, `THIRD_PARTY_NOTICES`. Ein Lizenz-Gate in CI prüft Abhängigkeiten gegen die Allowlist (ScanCode o. ä.) |
| [07-eval.md](../architecture/07-eval.md) | Abschnitt 1, Abschnitt 3.1 R1 | Jeder Fall trägt Lizenz und Herkunft (steht schon da); neu: Herkunft `vendor_output` (CodeRabbit, Sonar) ist bis zur Owner-Entscheidung L3 gesperrt. R1 kann ohne diese Daten auf eigene, von Hand gelabelte bothy-Befunde (Mensch als Quelle) umgestellt werden. Das Eval-Repo bleibt privat; öffentliche Eval-Sätze nur aus Quellen mit passender Lizenz |
| [08-roadmap.md](../architecture/08-roadmap.md) | Abschnitt 4, Stufe 0 | Fertig-Kriterium ergänzen: Produkt-Repo mit LICENSE (Apache-2.0, Prüfsumme), NOTICE, DCO-Hook und CI-Gate, CODEOWNERS, GOVERNANCE.md, SECURITY.md, CONTRIBUTING.md, Lizenz-Gate, Deny-List-Scanner gegen die private Liste, gitleaks. Erst danach öffentlich schalten |
| [09-decisions.md](../architecture/09-decisions.md) | Abschnitt 2 ADR | ADR-37: Apache-2.0 mit DCO, kein CLA, kein Open Core zum Start. ADR-38: zwei Repos (Produkt öffentlich, Ops privat) mit Deny-List-Scanner. ADR-39: keine proprietären Binaries in Artefakten. ADR-34 erweitern um SSAL, Commons Clause, Semgrep Rules License, PolyForm, FSL, BSL, Sustainable Use License und die Dify-Lizenz |
| 09 | Abschnitt 3 | O14 ("zunächst nur intern") ist durch die Owner-Vorgabe der dritten Runde überholt. O13 (Vergleichsläufe gegen CodeRabbit) um [cr-tos] 4.2 (iv) und [sonar-aup] 5 ergänzen. Neue Punkte L1 bis L6 aus Abschnitt 4 |
| 09 | Abschnitt 6 Folgeliste | Korrekturen: [05] Abschnitt 6 (Consumer Terms jetzt selbst gelesen); Python-SDK-Repo MIT, aber Commercial Terms und gebündeltes CLI (2.3); Semgrep Rules License für unser Produkt kritisch (2.3) |

---

## 4. Owner-Entscheidungen

| # | Frage | Art | Empfehlung | Grund |
|---|---|---|---|---|
| L1 | Lizenz | Recht, Produkt | **Apache-2.0 mit DCO**, kein CLA, kein Open Core zum Start | erfüllt "jeder zieht, installiert, hostet selbst"; Patentlizenz; Markenschutz bleibt (§6); gleiche Wahl und gleiche Werkzeuge wie bothy; FSL/BSL wären keine Open Source nach OSD. Ein späteres Open Core wäre ohne CLA nur für neuen, eigenen Code möglich. Das ist gewollt |
| L2 | Projektname und Marke | Recht, eventuell Geld | neutraler Name ohne "CodeRabbit", "Rabbit"-Anspielung, "Claude" oder "Code Review AI"-Gattungswort; vor Veröffentlichung Recherche in EUIPO, DPMA und USPTO; Eintragung erst bei Bedarf | CODERABBIT ist US-Wortmarke (GESAGT); Anthropic verbietet seine Namen im Produktnamen ([cc-legal] BELEGT); Umbenennung nach Veröffentlichung ist teuer |
| L3 | CodeRabbit am Entwicklungs-Repo und CodeRabbit-Ausgaben als Eval-Daten | Recht, Konto | **nicht anschließen**, solange keine schriftliche Zustimmung vorliegt; Der Owner fragt bei CodeRabbit an, ob ein Open-Source-Konkurrenzprojekt den OSS-Plan nutzen und Ausgaben als Eval verwenden darf. Bis dahin: Review am Repo durch den eigenen Reviewer (Dogfooding) plus Claude Code Review bzw. claude-code-action mit API-Key; R1 auf menschlich gelabelte Fälle umstellen | [cr-tos] 4.2 (iv) wörtlich: "use the Services to develop competing products or services without CodeRabbit's prior written consent"; Sektion 4 überlebt die Kündigung (5.4) |
| L4 | SonarQube am Entwicklungs-Repo und im Produkt | Recht, Konto | **SonarQube Cloud nicht anschließen** ohne schriftliche Zustimmung von SonarSource; **Community Build nicht in den Agenten-Kreislauf** (keine Befunde an Claude). Ersatz am Repo: CodeQL (für OSI-Repos auf GitHub.com frei), Opengrep mit eigenen Regeln, Sprach-Linter. Im Produkt kein Sonar-Plugin, höchstens neutraler SARIF-Import in Verantwortung des Betreibers | [sonar-aup] §5 "direct competitor", §6 "code review systems (whether based on LLM Technologies or not.)"; [ssal] (c) verbietet KI-Verarbeitung der Analyzer-Ergebnisse |
| L5 | Startweg `subscription` im öffentlichen Projekt und im eigenen Testbetrieb | Recht, Geld | im Produkt behalten als persönlicher Betreibermodus, standardmäßig aus, mit ausdrücklicher Bestätigung; für den eigenen autonomen Testbetrieb auf das in Max, Ultra oder Team enthaltene API-Guthaben per Console-Key umstellen, sobald Coder, QA oder PR-Fixer autonom laufen | [cc-legal] erlaubt das Abo im unveränderten Binary; Consumer Terms §3 und §11 (EWR) machen autonomen Dauerbetrieb zum Graubereich; das API-Guthaben ist laut [cc-sdkplan] im Plan enthalten, kostet also nichts extra. Löst nebenbei O2 (Prüf-Proxy als "intermediate") |
| L6 | Wer ist Lizenzgeber und Copyright-Inhaber | Recht | vor dem ersten öffentlichen Commit festlegen: der Owner privat mit "The <Projekt> Authors" in NOTICE wie bei bothy, oder sein Arbeitgeber; wenn Firmenzeit oder Firmenmittel einfließen, schriftliche Freigabe des Arbeitgebers einholen | Rechte an Arbeitsergebnissen können beim Arbeitgeber liegen (ABGELEITET, Rechtsfrage); ein späterer Wechsel bräuchte die Zustimmung aller Beitragenden ([bothy-adr3]) |

---

## 5. Offene Punkte

- **Fassungen:**
  - Die OpenAI Terms of Use sind ungelesen (HTTP 403).
  - Die Nicht-EWR-Fassung der Anthropic Consumer Terms ist ungeprüft.
  - Welche Fassung der Anthropic Usage Policy heute gilt, ist ungeprüft; die Seite zeigt "Effective Nov 12, 2026".
- **Wettbewerb mit Anthropic:** Ob Anthropic ein Review- oder Agenten-Produkt auf Claude als "compete with our Services" (Consumer §3) bzw. "competing product" (Commercial D.4) wertet, ist ungeklärt. Es betrifft jede Credential-Art, auch API-Keys. Klären ließe es nur Anthropic (Vertrieb, [cc-legal] "contact sales").
- **CodeRabbit:**
  - Grenzen des OSS-Plans: Die Herstellerseite nennt keine.
- **SonarSource:** Ob "direct competitor" ein Open-Source-Projekt ohne Vertrieb erfasst, ist offen. Zu klären nur mit SonarSource.
- **SDK-Pakete:** Inhalt der Plattformpakete `@anthropic-ai/claude-agent-sdk-<os>-<arch>`, also ob sie das native CLI enthalten: VERMUTET, nicht entpackt.
- **Lizenzen weiterer Kandidaten:**
  - Martian-Datensatz (O12), DBOS ([09](../architecture/09-decisions.md) Abschnitt 5) und Opengrep-Regeln im Detail (nur der Kopf mit Commons Clause gelesen).
  - Weitere Projekte, die die anderen Recherchen dieser Runde vorschlagen (etwa für Deployment auf AWS, GCP und Hetzner): jeweils gegen die Allowlist aus Abschnitt 3 prüfen.
- **Marke:** CODERABBIT ist nur über ein Markenverzeichnis belegt (GESAGT), nicht in USPTO-TSDR selbst nachgesehen. EU-Marken von CodeRabbit sind ungeprüft.

---

## 6. Quellen (abgerufen 2026-10-31)

**Eigenes Projekt und Vorbild:**
- `docs/architektur/README.md`, `05-sicherheit.md`, `07-eval.md`, `09-entscheidungen.md`
- [bothy-repo] öffentliches Repo bothy (Angaben in [bothy-vorlage-projekt-setup](bothy-vorlage-projekt-setup.md) Abschnitt 6; HTTP 200 ohne Anmeldung, also öffentlich, selbst geprüft). Gelesen wurde ein älterer, nicht veröffentlichter Planungsstand mit deutschen Dateinamen; am 2026-11-01 auf dem öffentlichen Commit `4485084b8` nachgeprüft, dort mit englischen Dateinamen:
- [bothy-adr3] `docs/adr/0003-license-apache-2-0-with-dco-instead-of-cla.md` (früher `0003-lizenz-apache-2-0-mit-dco-statt-cla.md`)
- [bothy-adr2] `docs/adr/0002-two-repos-public-product-private-ops-repo.md` (früher `0002-zwei-repos-oeffentliches-produkt-privates-ops-repo.md`; das Zitat in 2.9 stammt aus der früheren deutschen Fassung)
- [bothy-gov] `GOVERNANCE.md`
- bothy `CONTRIBUTING.md` (DCO; die frühere Zeilenangabe 51 bis 59 galt für den älteren Stand), `.coderabbit.yaml`, `sonar-project.properties`, `NOTICE`

**Anthropic:**
- [cc-legal] https://code.claude.com/docs/en/legal-and-compliance (als `.md` geladen, wörtlich)
- [an-consumer] https://www.anthropic.com/legal/consumer-terms (EWR-Fassung, "Effective Oct 8, 2025")
- [an-commercial] https://www.anthropic.com/legal/commercial-terms ("Effective Jun 17, 2025")
- [an-aup] https://www.anthropic.com/legal/aup ("Effective Nov 12, 2026")
- [an-tm] https://www.anthropic.com/legal/trademark-guidelines ("Effective Aug 1, 2024")
- [cc-sdkplan] https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan
- [cc-sdk-overview] https://code.claude.com/docs/en/agent-sdk/overview (Abschnitte "Branding guidelines", "License and terms")
- [sdk-npm] npm `@anthropic-ai/claude-agent-sdk` 0.3.316, Tarball entpackt: `package/LICENSE.md`, `package/package.json`, `package/README.md`
- [cc-npm] npm `@anthropic-ai/claude-code` 2.1.316 (Registry-Feld `license`); https://raw.githubusercontent.com/anthropics/claude-code/main/LICENSE.md
- [sdk-py] https://github.com/anthropics/claude-agent-sdk-python (LICENSE, README Abschnitt "License and terms"); PyPI `claude-agent-sdk` 0.2.176

**CodeRabbit:**
- [cr-tos] https://www.coderabbit.ai/legal/terms-of-service ("Updated: April 20, 2026")
- [cr-pricing] https://www.coderabbit.ai/pricing (GESAGT)
- [cr-oss] https://www.coderabbit.ai/oss (GESAGT)
- [tm-cr] https://trademarkdir.com/trademark/coderabbit-98229118 (GESAGT, Drittverzeichnis)

**SonarSource:**
- [sonar-pca] https://www.sonarsource.com/legal/primary-agreement/ ("Updated August 27, 2026")
- [sonar-free] https://www.sonarsource.com/legal/cloud-free-and-team/
- https://www.sonarsource.com/legal/sonarcloud/terms-of-service/ (Supplemental Terms)
- [sonar-aup] https://www.sonarsource.com/legal/aup/ ("Last updated November 7, 2025")
- [sonar-archive] https://www.sonarsource.com/legal/archive/sonarcloud-terms-of-service-2026-06/ (nur Suchauszug, GESAGT)
- [sonar-oss] https://community.sonarsource.com/t/introducing-the-new-free-oss-plan-in-sonarqube-cloud/176923 (GESAGT)
- [sonarqube] https://github.com/SonarSource/sonarqube (README Abschnitt License, `LICENSE.txt`, `build.gradle` Zeilen 383 bis 387, `sonar-application/build.gradle` `bundledPlugin`)
- [ssal] https://raw.githubusercontent.com/SonarSource/sonar-java/master/LICENSE.txt
- [sonarjs] https://github.com/SonarSource/SonarJS (README Abschnitt License)

**Andere Werkzeuge:**
- [codex-auth] https://learn.chatgpt.com/docs/auth
- https://openai.com/policies/row-terms-of-use/ (403, ungelesen)
- [gemini-tos] https://geminicli.com/docs/resources/tos-privacy/
- [semgrep-rules] https://github.com/semgrep/semgrep-rules/blob/develop/LICENSE und https://semgrep.dev/legal/rules-license (WebFetch-Zusammenfassung, Zitate sinngemäß geprüft; "Last updated: December 13th, 2024")
- [semgrep] https://github.com/semgrep/semgrep/blob/develop/LICENSE
- [opengrep] https://github.com/opengrep/opengrep/blob/main/LICENSE
- [opengrep-rules] https://github.com/opengrep/opengrep-rules/blob/main/LICENSE
- [codeql] https://github.com/github/codeql-cli-binaries/blob/main/LICENSE.md

**Lizenztexte:**
- [apache2] https://www.apache.org/licenses/LICENSE-2.0.txt (§4, §5, §6)
- [agpl] https://www.gnu.org/licenses/agpl-3.0.txt (§13)
- [asf-gpl] https://www.apache.org/licenses/GPL-compatibility.html
- [osd] https://opensource.org/osd (Punkt 6)
- [fsl] https://fsl.software/ (WebFetch-Zusammenfassung)
- [bsl] https://mariadb.com/bsl11/
- DCO 1.1: https://developercertificate.org/ (über [bothy-adr3], dort belegt)

**Lizenzen vergleichbarer Projekte** (GitHub-API `/repos/<r>/license` und Rohtext der Lizenzdatei):
- https://github.com/The-PR-Agent/pr-agent/blob/main/LICENSE
- [kodus-lic] https://github.com/kodustech/kodus-ai/blob/main/license.md
- [oh-lic] https://github.com/OpenHands/OpenHands/blob/main/LICENSE und `.../cloud-1.47.1/enterprise/LICENSE`
- [sweep-lic] https://github.com/sweepai/sweep/blob/main/LICENSE
- [langfuse-lic] https://github.com/langfuse/langfuse/blob/main/LICENSE und `ee/LICENSE`
- [sentry-lic] https://github.com/getsentry/sentry/blob/master/LICENSE.md
- [posthog-lic] https://github.com/PostHog/posthog/blob/master/LICENSE
- [plane-lic] https://github.com/makeplane/plane/blob/preview/LICENSE.txt
- [caldiy] https://github.com/calcom/cal.diy (LICENSE, README)
- [dify-lic] https://github.com/langgenius/dify/blob/main/LICENSE
- [n8n-lic] https://github.com/n8n-io/n8n/blob/master/LICENSE.md
- https://github.com/continuedev/continue (LICENSE, CONTRIBUTING Abschnitt CLA)
- https://github.com/cline/cline/blob/main/LICENSE
- https://github.com/Aider-AI/aider (LICENSE.txt, CONTRIBUTING Zeile 37)
- https://github.com/aaif-goose/goose/blob/main/LICENSE
- npm-Registry (`/latest`) für `ai`, `@ai-sdk/anthropic`, `pg-boss`, `@anthropic-ai/sdk`, `@openai/codex`, `@google/gemini-cli`
