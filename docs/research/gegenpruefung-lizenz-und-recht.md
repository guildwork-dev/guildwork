<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
> Research note, dated 2026-11-01, not binding. Kept in German as written (ADR-53); the binding documents are docs/architecture and docs/design.

# Gegenprüfung: open-source-lizenz-und-recht.md (Stand 2026-10-31)

**Dated, not binding.** Datierte Recherche, Stand 2026-10-31, nicht verbindlich und nicht übersetzt; verbindlich ist die Plattform-Doku ([docs/architektur/](../architecture/README.md)).

Unabhängige Gegenprüfung der Vertrags- und Lizenzaussagen an den Originalquellen. Wo diese Datei korrigiert, gilt die Korrektur.

Gegenprüfung von [open-source-lizenz-und-recht.md](open-source-lizenz-und-recht.md) (Datei unverändert)

Urteil: Fast alle wörtlichen Zitate stimmen mit der Originalquelle überein (Abruf 2026-10-31, per curl als Rohtext oder per WebFetch). Zu korrigieren sind 1 Tatsachenfehler (Art der Marke), 3 ungenaue Aussagen und 2 fehlende Gegenstellen bei Anthropic, die den Graubereich verschärfen. 2 Aussagen, die der Bericht als GESAGT oder VERMUTET führt, sind jetzt belegt.

**A. Anthropic**

1. **cc-legal** (https://code.claude.com/docs/en/legal-and-compliance.md): bestätigt.
   - Geprüft wurden alle Zitate aus 2.5a: Lizenzzuordnung, "preinstalling or running ...", "binary must not be modified", "may not pay for, resell, or intermediate", Namensabsatz, "ordinary, individual usage", Login-Absatz, Ausnahme für eigene API-Keys und für "an end user from signing in to the unmodified Claude Code binary", "reserves the right ... without prior notice". Alles wörtlich vorhanden.
   - Ergänzung, die gegen die Lesart des Berichts spricht und dort fehlt (Abschnitt "Authentication and credential use"):
     - "OAuth authentication is intended exclusively for purchasers of Claude Free, Pro, Max, Ultra, Team, and Enterprise subscription plans and is designed to support ordinary use of Claude Code and other native Anthropic applications."
     - "Developers building products or services that interact with Claude's capabilities, including those using the Agent SDK, should use API key authentication through Claude Console or a supported cloud provider."
   - Folge: Die Aussage in Tabelle 2.5 (Zeile "Autonomer Dauerbetrieb"), `claude -p` und das SDK auf dem Abo seien "ausdrücklich vorgesehen", gilt nur für die Abrechnung laut Support-Artikel. Für Entwickler von Produkten empfiehlt cc-legal ausdrücklich einen API-Key. Der Graubereich ist damit enger, als der Bericht ihn darstellt. 05-sicherheit.md Zeile 82 zitiert diesen Satz, der Recherchebericht nicht.

2. **Consumer Terms, EWR-Fassung** (https://www.anthropic.com/legal/consumer-terms): bestätigt.
   - "Anthropic Ireland, Limited" und "Effective Oct 8, 2025" stimmen.
   - Die Fundstellen stimmen: §2 "You may not share your Account login information ...", §3 "To develop any products or services that compete with our Services ..." und "Except when you are accessing our Services via an Anthropic API Key ... whether through a bot, script, or otherwise.", §11 (Überschrift "Disclaimer of warranties, limitations of liability, and indemnity") "Non-commercial use only. You agree that you will not use our Services for any commercial or business purposes ...".
   - Ergänzung, die im Bericht fehlt: Die Fassung gilt nur für Verbraucher: "These Terms apply to you if you are a consumer who is resident in the European Economic Area or Switzerland. You are a consumer if you are acting wholly or mainly outside your trade, business, craft or profession". Dazu §1: "Use of our Services for evaluation purposes are for your personal, non-commercial use only."
   - Welche Fassung gilt, wenn der Owner geschäftlich handelt: nicht prüfbar (die Nicht-EWR-Fassung wurde nicht ausgeliefert).

3. **Commercial Terms** (https://www.anthropic.com/legal/commercial-terms): bestätigt. "Effective Jun 17, 2025", A.1, B und D.4 stehen wörtlich so.

4. **Usage Policy** (https://www.anthropic.com/legal/aup): bestätigt.
   - "Effective Nov 12, 2026" und beide Zitate ("Agentic use cases must comply ...", "This section does not prohibit security research ...") stimmen.
   - Welche Fassung heute gilt: nicht prüfbar. Die Seite liefert nur diese Fassung, eine Versionsliste war per curl nicht erreichbar.

5. **cc-sdkplan** (support.claude.com, Artikel 15036540): beide Update-Zitate (15. Juni und 7. Oktober 2026) bestätigt.
   - Korrigiert wird die Folgerung "Ausweg ohne Mehrkosten" bzw. "kostet also nichts extra" (Abschnitt 1 Punkt 3 und L5). Das Guthaben ist gedeckelt. Laut https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-ultra-and-team-plans:
     - Max "$100", Ultra "$200", Team "$20 per seat" bzw. "$100 per seat", "capped at $500".
     - "Doesn't roll over."
     - "If the organization has no other credits, API requests stop until your next monthly credits arrive."
     - "Free, Pro, and Enterprise plans aren't eligible."
     - Abgerechnet wird nach den "Supplemental Credit Terms" (anthropic.com/legal/credit-terms).
   - Richtig ist also: ohne Mehrkosten nur bis zur Monatsgrenze und nur, solange kein Auto-Reload eingeschaltet ist.

6. **cc-sdk-overview** (Abschnitt Branding): bestätigt. "{YourAgentName} Powered by Claude", nicht erlaubt "Claude Code" oder "Claude Code Agent", "Your product should maintain its own branding ..." stehen so da.

7. **sdk-npm** (`@anthropic-ai/claude-agent-sdk` 0.3.316): bestätigt.
   - Registry-Feld "SEE LICENSE IN README.md".
   - `LICENSE.md` aus dem Tarball wörtlich wie zitiert.
   - 8 `optionalDependencies` (linux-x64, linux-arm64, beide musl, darwin-x64, darwin-arm64, win32-x64, win32-arm64).
   - Der als VERMUTET geführte Inhalt der Plattformpakete ist jetzt belegt. Die Registry-Beschreibung von `@anthropic-ai/claude-agent-sdk-darwin-arm64@0.3.316` lautet "Native CLI binary for @anthropic-ai/claude-agent-sdk on darwin-arm64", entpackt rund 310 MB, Lizenz "SEE LICENSE IN LICENSE.md". Die Einstufung kann auf BELEGT (Registry-Metadaten) steigen.

8. **cc-npm** (`@anthropic-ai/claude-code` 2.1.316): bestätigt. Registry-Lizenz "SEE LICENSE IN README.md". GitHub `LICENSE.md` wörtlich "© Anthropic PBC. All rights reserved. Use is subject to Anthropic's Commercial Terms of Service." Ebenfalls 8 optionalDependencies.

9. **sdk-py**: bestätigt. LICENSE ist MIT ("Copyright (c) 2025 Anthropic, PBC"). Die README enthält wörtlich "The Claude Code CLI is automatically bundled with the package" und den Satz zu den Commercial Terms.

10. **an-tm** "Effective Aug 1, 2024": bestätigt.

11. **OpenCode** "Anthropic explicitly prohibits this": bestätigt, allerdings nur über Drittquellen (WebSearch, Zitat aus der OpenCode-Provider-Doku; Plugin in v1.3.0 entfernt). Die Primärquelle habe ich nicht selbst abgerufen.

**B. CodeRabbit**

12. **cr-tos** (https://www.coderabbit.ai/legal/terms-of-service): bestätigt.
    - "Updated: April 20, 2026", CodeRabbit, Inc., Recht von Kalifornien mit Gerichtsstand San Francisco.
    - 4.2 (ii), (iii), (iv) und (vi) wörtlich; "whether as a guest or registered user" vorhanden.
    - 7.1 mit Ausnahme "is or becomes publicly known" vorhanden.
    - Korrigiert: Die Überschrift von 6.2 lautet "6.2 Customer IP Rights", nicht "Output". Der zitierte Wortlaut stimmt. Der zweite Satz geht weiter: "... to (a) provide, maintain, protect and improve the Services or operate its business; (b) comply with applicable law; and (c) enforce this Agreement."
    - 5.4 ("Effect of Termination") bestätigt mit Nuance. Wörtlich: "any terms or conditions that by their nature should survive such termination will survive, including Sections 3-13."
    - Ergänzung: 4.2 (i) verbietet zusätzlich die Nutzung "for any purpose other than as expressly permitted under this Agreement".

13. **cr-pricing** "install CodeRabbit on a public repository, and receive free reviews forever for public repositories": bestätigt. Die Aussage "Grenzen nennt die Seite nicht" ist für den OSS-Plan bestätigt. Für bezahlte Pläne nennt die Seite "PR reviews per developer each hour".

14. **cr-oss** "The repo is public. That's the whole bar CodeRabbit uses.": bestätigt.

15. **Marke tm-cr**: korrigiert.
    - USPTO TSDR selbst abgerufen (https://tsdr.uspto.gov/statusview/sn98229118): "Mark: CODERABBIT", Serial 98229118, "US Registration Number: 7548845", "Registration Date: Oct. 29, 2024", "LIVE/REGISTRATION/Issued and Active", "Mark Type: Service Mark", "Standard Character Claim: No", "The mark consists of a silouette of a rabbit within the center of a circle with the letters CodeRabbit to the right of the circle."
    - Laut Drittquelle Klasse 42 (automatisierte Code-Reviews).
    - Es ist also keine reine Wortmarke, sondern eine eingetragene US-Dienstleistungsmarke mit Bildanteil (Wort-Bild-Marke). Die Nummer stimmt.
    - Einstufung von GESAGT auf BELEGT (USPTO) anheben. Abschnitt 5 "nicht in USPTO-TSDR selbst nachgesehen" ist damit erledigt.

**C. SonarSource**

16. **sonar-pca** (https://www.sonarsource.com/legal/primary-agreement/): bestätigt. "Updated August 27, 2026", die Bedingung in 2.2 ("conditioned on ... internal development purposes") und die Definition "no-cost software downloads ... are not Products" stimmen. Die Seite sagt dazu: "These terms apply to new customers as of this date ... For the prior version, see the September 2026 Archive."

17. **sonar-archive**: jetzt belegt, nicht mehr nur GESAGT. Das Archiv `sonarcloud-terms-of-service-2026-06` enthält wörtlich:
    - "(xv) employ, use, or engage artificial intelligence technology that is not part of the Service to ingest, interpret, analyze, train on, or interact with the data provided by the Service ..."
    - "(xviii) access or use the Service ... if you are a direct competitor of SonarSource".
    - Die heutigen Supplemental Terms (sonarcloud/terms-of-service) sind ein Stub ohne KI-, Wettbewerbs- oder Benchmark-Klausel (WebFetch).

18. **sonar-free**: alle drei Zitate bestätigt.

19. **sonar-aup**: bestätigt. "Last updated November 7, 2025", §5 ("Engage in Unfair Trade Practices") mit "direct competitor" und "Disclose, publish ... benchmark", §6 mit beiden Results-Data-Sätzen und der Ausnahme (a) und (b), alles mit "without prior written consent".
    - Ergänzung für L4 und das Sonar-Plugin, im Bericht nicht zitiert:
      - §5 "Create, market, or distribute add-ons or enhancements to the Products, or incorporate the Products into another product."
      - §5 "Perform ... any benchmark ... for competitive advantage."
      - §6 "Use LLM Technologies to systematically extract, aggregate, or repurpose Results Data ..." und "Use Results Data unless the relevant Customer Data is active in the Products."
      - Ausnahme (b) endet mit "(subject to Section 5's restrictions on product enhancements and integrations)".
    - "AI code review" in der Navigation von sonarsource.com: bestätigt.

20. **sonar-oss**: korrigiert (Präzisierung).
    - Ankündigung am 2026-01-27: bestätigt.
    - Das Zitat "It is the latter. The plan is available for public projects." stammt aus einer späteren Antwort von Ilham Mayou vom 2026-03-09. Die Frage dazu nannte als "latter" die Variante "publicly available with an open-source license attached to it".
    - Richtig ist also: öffentlich und mit Open-Source-Lizenz. "Öffentlich" allein reicht laut dieser Antwort nicht.

21. **SSALv1** (sonar-java `LICENSE.txt`): bestätigt. Die Definitionen "Competing" und "Non-competitive Purpose" (a) bis (c) stehen wörtlich so.
    - Ergänzung: Die Lizenz trägt "Last Updated November 13, 2024".
    - (c) endet mit "or to engage with the Program in any manner".
    - Die Beschränkung hängt an der Urheberrechtslizenz (reproduce, Derivative Works, Distribute) und an der Patentlizenz ("make, use ..."), beide "for any Non-competitive Purpose".

22. **SonarQube Community Build**: bestätigt.
    - README "Licensed under the GNU Lesser General Public License, Version 3.0".
    - `build.gradle` Zeilen 383, 385 und 387: sonar-java-plugin 8.46.0, sonar-javascript-plugin 14.3.0, sonar-python-plugin 5.32.0.
    - `bundledPlugin` in `sonar-application/build.gradle`.
    - SonarJS-README: "SonarQube analyzers released after November 29, 2024, including patch fixes for prior versions, are published under the ... SSALv1".

**D. Werkzeuge und Lizenztexte**

23. **Semgrep-Regeln**: bestätigt. Die LICENSE-Datei verweist nur auf die Seite. Die Rules License sagt wörtlich "Last updated: December 13th, 2024", "You may use the rules only for your own internal business purposes. This license does not allow you to distribute the rules, or to make them available to others as a service."

24. **Opengrep-Regeln**: bestätigt mit Präzisierung.
    - Die LICENSE ist "Commons Clause" License Condition v1.0 auf "License: LGPL 2.1", "Licensor: Semgrep, Inc.", Software "semgrep-rules".
    - Die Klausel verbietet nur "Sell" (Weitergabe "for a fee or other consideration", auch Hosting- und Support-Gebühren).
    - Damit ist sie keine reine Weitergabesperre. Die Folgerung "nicht mitliefern ohne genaue Prüfung" bleibt vertretbar. Die Begründung in Abschnitt 1 Punkt 5 sollte aber das Verkaufsverbot nennen, nicht ein generelles Verbot.

25. **Opengrep-Engine und Semgrep CE**: LGPL-2.1 bestätigt.

26. **CodeQL**: bestätigt. "Perform analysis on the Open Source Codebase", CI nur "If the Open Source Codebase is hosted and maintained on GitHub.com", die Ausnahme für GHAS, das Verbot "provide or make available the Software as a hosted solution".

27. **Codex-Authentifizierung** (learn.chatgpt.com/docs/auth): alle drei Zitate bestätigt, ebenso die Bindung der Access Tokens an "ChatGPT Enterprise workspaces". Die OpenAI Terms of Use: nicht prüfbar (HTTP 403, erneut geprüft).

28. **Gemini CLI**: bestätigt. "Last updated: Apr 10, 2026", das OpenClaw-Zitat und der Hinweis auf Antigravity CLI vom 18. Juni 2026 stehen so da.

29. **Lizenztexte**: alle bestätigt.
    - Apache-2.0 §5 und §6 wörtlich, AGPL-3.0 §13 wörtlich, OSD Punkt 6 wörtlich.
    - BSL 1.1: "is not an Open Source license", "non-production use", "Additional Use Grant", "fourth anniversary" stimmen.
    - ASF: "Apache 2 software can therefore be included in GPLv3 projects", umgekehrt nicht.
    - FSL (Sentry `LICENSE.md`): "FSL-1.1-Apache-2.0", "A Permitted Purpose is any purpose other than a Competing Use", Apache-2.0 "on the second anniversary".

**E. Vergleichsprojekte und npm** (GitHub-API und Rohtexte)

30. Lizenzen und Zitate: bestätigt.
    - PR-Agent MIT, OpenHands MIT, Plane AGPL-3.0, Continue, Cline, Aider und Goose Apache-2.0 (block/goose leitet auf aaif-goose/goose um), cal.com leitet auf cal.diy um (MIT).
    - Kodus: AGPL plus "Kodus Enterprise Code License", "does not permit Community users to modify the Enterprise Code".
    - Dify: "modified version of the Apache License 2.0", Mehrmandantenbetrieb, Logo, "The producer can adjust the open-source agreement to be more strict or relaxed".
    - n8n: "only for your own internal business purposes or for non-commercial or personal use".
    - Sweep: EE-Lizenz, "MIT Expat".
    - Langfuse: vier `ee`-Pfade, sonst MIT.
    - PostHog: `ee/`, sonst MIT.
    - OpenHands `cloud-1.47.1/enterprise/LICENSE`: PolyForm Free Trial 1.0.0, "may not distribute copies".
    - CLA- bzw. DCO-Treffer in CONTRIBUTING: Continue, Aider und Langfuse ja; Cline, PR-Agent und Goose keine.

31. **npm-Versionen und Lizenzen**: alle bestätigt. ai 7.0.159, @ai-sdk/anthropic 4.0.94, @anthropic-ai/sdk 1.3.0 (alle Apache-2.0); pg-boss 12.38.0 (MIT); @openai/codex 0.166.0 und @google/gemini-cli 0.66.0 (Apache-2.0).

**F. Lokale Belege**

32. Bestätigt:
    - `git log` liefert "does not have any commits yet".
    - bothy ADR-0003 (Apache-2.0 mit DCO, "Zustimmung aller Beitragenden" in Zeile 42).
    - Das Zitat zur Konfigurationsreferenz steht in ADR-0002 Zeile 47 (richtig zugeordnet).
    - NOTICE "The Bothy Authors".
    - `.coderabbit.yaml` Zeile 7 "A finding that only CodeRabbit sees becomes a local rule".
    - 05-sicherheit.md Zeile 86 "nicht selbst gelesen".

**Zusammenfassung der Korrekturen für den Bericht**

1. Marke: Wort-Bild-Dienstleistungsmarke, nicht Wortmarke. Belegt über USPTO TSDR.
2. API-Guthaben: gedeckelt (Max 100 $, Ultra 200 $, Team bis 500 $), ohne Übertrag, bei leerem Guthaben ohne Auto-Reload stoppt es. Pro ist ausgeschlossen. "Ohne Mehrkosten" stimmt nur innerhalb dieser Grenze.
3. cc-legal: Die Sätze "OAuth ... intended exclusively ... ordinary use" und "Developers ... including those using the Agent SDK, should use API key authentication" fehlen. Sie schwächen die Lesart "SDK auf dem Abo ausdrücklich vorgesehen".
4. Consumer Terms EWR: gelten nur für Verbraucher. Wer geschäftlich handelt, fällt nicht darunter. Welche Fassung dann gilt, ist nicht prüfbar.
5. CodeRabbit 6.2 heißt "Customer IP Rights". 5.4 überlebt "by their nature ... including Sections 3-13".
6. Sonar-OSS-Plan: Die Antwort stammt vom 2026-03-09 und meint öffentlich und mit Open-Source-Lizenz.
7. Opengrep-Regeln: Commons Clause auf LGPL-2.1, verboten ist nur der Verkauf.
8. Einstufungen anheben: Inhalt der SDK-Plattformpakete (natives CLI) und Sonar-Archiv (KI- und Wettbewerbsklausel) sind belegt.

Die Rohtexte der Quellen lagen nur temporär vor und sind nicht Teil dieser Ablage.

Quellen der WebSearch-Ergebnisse: [trademarkdir coderabbit 98229118](https://trademarkdir.com/trademark/coderabbit-98229118), [markinton coderabbit 98229118](https://markinton.com/trademark/coderabbit-98229118), [The Register 2026-02-20](https://www.theregister.com/2026/02/20/anthropic_clarifies_ban_third_party_claude_access), [developersdigest OpenCode error](https://www.developersdigest.tech/errors/opencode/claude-code-credential-only), [80aj OpenCode removal](https://www.80aj.com/2026/03/20/opencode-claude-removal/)
