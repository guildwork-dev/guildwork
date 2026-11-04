<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
> Research note, dated 2026-11-01, not binding. Kept in German as written (ADR-53); the binding documents are docs/architecture and docs/design.

# Recherche: Installation und Hosting als selbst gehostetes Open-Source-Produkt (Stand 2026-10-31)

**Dated, not binding.** Datierte Recherche, Stand 2026-10-31, nicht verbindlich und nicht übersetzt; verbindlich ist die Plattform-Doku ([docs/architektur/](../architecture/README.md)).

Auftrag: Owner-Vorgaben vom 2026-10-31, dritte Runde (Open Source, öffentliches Repo, jeder hostet selbst auf Azure, AWS, Google Cloud, Hetzner und weiteren Basen, eigene Services anflanschen; nur planen). Gelesen vorher: `docs/architektur/README.md`, `06-betrieb-und-deployment.md`, `01-plugin-schnittstellen.md` Abschnitte 1 und 8, `05-sicherheit.md` (Sandbox und Secrets), `09-entscheidungen.md`, dazu als Vorbild des Owners das öffentliche bothy-Repo ([bothy-repo]: `infra/`, `docs/spec/16-betrieb.md`, `.github/workflows/portability.yml`, selbst gelesen; Fundstellen in Abschnitt 6).

Einstufung wie im README der Architektur: **BELEGT** (Primärquelle selbst gelesen, hier über WebFetch-Auszug), **GESAGT** (Herstelleraussage, Forum, Drittbericht), **ABGELEITET** (eigener Schluss), **VERMUTET**. Alle Webquellen abgerufen am 2026-10-31. Hinweis zur Belegqualität: Das Abrufwerkzeug liefert eine Zusammenfassung durch ein kleines Modell; Zitate sind sinngemäß bis wörtlich, aber nicht byte-genau geprüft.

---

## 1. Urteil (Kurzfassung)

1. **Die Architektur trägt das Open-Source-Ziel, aber sie ist heute auf eine Installation (eine Firma, Azure, eigene Runner) zugeschnitten.** Kern, Postgres als einziger Zustand und Pull-Worker sind genau die Bauform, mit der vergleichbare Produkte selbst gehostet werden. Was fehlt: eine zweite Schnittstellenklasse für Infrastruktur (Objektspeicher, Secret-Speicher, Cloud-Identität), ein Installationspaket mit Upgrade-Regeln und eine Testmatrix je Ziel. (ABGELEITET)
2. **Branchenstandard ist eine Treppe aus drei Wegen**, nicht ein Weg: Docker Compose für einen Host (Test, kleine Teams), Helm für Kubernetes (Produktion mit Hochverfügbarkeit), dazu optionale Cloud-Module (Terraform bzw. OpenTofu) oder Marketplace-Einträge. Langfuse, Plane, Infisical, Zitadel, Coder, Mattermost und GitLab machen es so; Sentry und PostHog bieten nur Compose und erklären es ausdrücklich als nicht skalierbar und ohne Support. (BELEGT, Abschnitt 2.1)
3. **Empfehlung: Compose-Bündel mit Installer zuerst (wie bothy), Helm als zweiter Weg, OpenTofu-Module je Cloud als dritter**; Azure-Modul zuerst, weil der Owner dort hostet. Einrichtung der GitHub App über den Manifest-Flow im Setup-Assistenten. Telemetrie standardmäßig aus. (ABGELEITET)
4. **MinIO ist keine Option mehr**: Das Community-Repo ist seit dem 25.04.2026 archiviert, "no longer maintained", nur Quellcode, keine Binaries. (BELEGT) Für den selbst gehosteten S3-Weg empfehle ich SeaweedFS (Apache 2.0) als Standard im Compose-Bündel, Garage (AGPLv3, ohne Versionierung und Object Lock) als leichte Alternative, Ceph RGW nur für Betreiber, die Ceph schon haben. Azure Blob braucht einen eigenen Adapter, weil Blob keine S3-API hat. (BELEGT bzw. GESAGT, Abschnitt 2.6)
5. **pgvector ist auf allen drei großen Clouds verwaltet verfügbar** (Azure Flexible Server 0.8.2, Amazon RDS 0.8.2 auf den aktuellen Minor-Versionen, Cloud SQL 0.8.5); Hetzner hat **keinen** verwalteten Postgres-Dienst. (BELEGT) Folge: Mindestversion an die Testmatrix binden, nicht an die neueste Version.
6. **Die Sandbox ist der härteste Portabilitätspunkt.** Sysbox und gVisor laufen auf jeder Linux-VM ohne Nested Virtualization; Firecracker und Kata brauchen `/dev/kvm`. Hetzner Cloud stellt laut Drittberichten kein KVM bereit; AWS erlaubt Nested Virtualization seit Februar 2026 auf ausgewählten Intel-Familien; Azure (Dsv5, Dsv6 und weitere) und Google (Intel, nicht E2) erlauben sie; AKS bietet Kata als "Pod Sandboxing", GKE bietet gVisor und neu auch MicroVMs. Azure Container Apps, AWS Fargate und Cloud Run erlauben keine privilegierten Container und taugen deshalb nur für die Steuerzentrale, nicht für Worker. (BELEGT bzw. GESAGT, Abschnitt 2.8)
7. **Sysbox ist ein Risiko für ein öffentliches Produkt**: Docker sponsert es, "not officially supported by Docker", Support "best effort", 210 offene Issues. Die Sandbox-Schnittstelle muss deshalb gVisor und MicroVM gleichwertig tragen, nicht nur als spätere Option. (BELEGT, ABGELEITET)

---

## 2. Befunde mit Quellen

### 2.1 Wie vergleichbare OSS-Produkte installiert werden

Gelesen wurden die Installationsseiten der Hersteller. Wo eine Zelle "nicht auf der Seite" sagt, ist das Merkmal nicht belegt, nicht widerlegt.

| Produkt | Ein Host (Compose, Skript) | Kubernetes | Cloud-Module, Marketplace | Upgrade und Migration | Telemetrie, Air-Gap | Quelle, Einstufung |
|---|---|---|---|---|---|---|
| **Langfuse** | Docker Compose nur "local use and testing", "Single VM without high availability, scaling, or backups" | Helm als Produktionsweg | eigene Seiten für AWS, Azure, GCP; AWS über offizielles Terraform-Modul `langfuse/langfuse-terraform-aws`; Render und Railway nur Community | semver, lange Migrationen laufen als Hintergrundjob | Telemetrie an, alle 12 h an PostHog; `TELEMETRY_ENABLED=false` (OSS), in Enterprise nicht abschaltbar; Update-Check nicht abschaltbar | [lf-self], [lf-aws], [lf-tel] BELEGT |
| **Sentry self-hosted** | `./install.sh`, dann `docker compose up --wait`; mindestens 4 Kerne, 16 GB RAM plus 16 GB Swap | kein offizieller Weg, "we do not offer any recommendations or guidance around scaling up" | keine | CalVer monatlich am 15.; Hard Stops (zuletzt 25.5.1, 26.5.0, 26.7.0), keine Backports | Installer fragt Opt-in; Beacon mit `SENTRY_BEACON = False` aus; `SENTRY_AIR_GAP = True` für keine Netzaufrufe; Lizenz FSL | [sentry-sh], [sentry-rel] BELEGT |
| **PostHog** | "hobby deploy" per Skript (Compose, Caddy mit Let's Encrypt), MIT | Kubernetes für neue Installationen "no longer supported", Helm "sunsetted" | keine | `upgrade-hobby`, keine getaggten Releases, "always on the latest image" | ohne Support, "officially unsupported" | [ph-self], [ph-hobby] BELEGT |
| **Plane** | Docker Compose "small to medium teams" | Helm für Produktion | nicht auf der Seite | nicht auf der Seite | nicht auf der Seite | [plane] BELEGT; Installer-CLI und Air-Gap ungeprüft |
| **Coder** | Docker, RPM für einen Host | Kubernetes "recommended platform for deployments that others depend on", Rancher, OpenShift | VM auf AWS, Google Cloud, Azure "or a marketplace listing" | Betriebsphase "upgrade and scaling routine"; Postgres-Sicherung liegt beim DBA | Telemetrie standardmäßig an, `CODER_TELEMETRY_ENABLE=false`; Registry-Spiegel für Air-Gap | [coder-inst], [coder-srv], [coder-tel] BELEGT |
| **n8n** | Einzeiler `curl -fsSL https://get.n8n.io \| sh` (braucht Docker), Compose für Produktion | GKE, OpenShift | Anleitungen für AWS, Azure, Google Cloud, Hetzner, DigitalOcean, Heroku | nicht auf der Seite | sendet standardmäßig an n8n (Updates, Templates, Diagnose); Abschalten über `N8N_DIAGNOSTICS_ENABLED=false` und weitere | [n8n-host], [n8n-iso] BELEGT |
| **Dify** | Compose aus Release-Tag, `.env` aus `.env.example`, mindestens 2 Kerne und 4 GiB | nicht auf der Seite | nicht auf der Seite | je Release eigene Anleitung, `.env` gegen `.env.example` abgleichen | nicht auf der Seite | [dify] BELEGT; Helm (Community) ungeprüft |
| **OpenHands** | CLI-Launcher `openhands serve` oder `docker run` mit gemountetem `/var/run/docker.sock` | nicht auf der Seite | nicht auf der Seite | `main` instabil | Docker-Socket-Mount gibt dem Container Kontrolle über den Host-Docker (ABGELEITET) | [oh-local] BELEGT |
| **Renovate** | npm-CLI, Docker-Image, GitHub Action; läuft per Cron und endet | Beispiele separat | Mend CE und EE: geschlossen, zustandsbehaftete App mit Webhooks und Job-Queue | etwa zweiwöchentlich (CE/EE) | nicht auf der Seite | [renovate] BELEGT |
| **Kodus** | `.env`-basiertes Compose mit Postgres, MongoDB, RabbitMQ ("required in 2.0"), separatem Webhook-Dienst | nicht auf der Seite | nicht auf der Seite | nicht auf der Seite | nicht auf der Seite | [kodus-vm] BELEGT |
| **Mattermost** | Docker Compose "evaluation, testing, and development only. Not supported for production" | Operator "recommended approach for production" | Azure Native VM im Marketplace | Operator mit "Automated updates and rollbacks" | eigene Seiten für Air-Gap; FIPS- und STIG-Images | [mm-deploy], [mm-plan] BELEGT |
| **GitLab** | Linux-Paket, Docker, Skripte | Helm, Operator | AWS, GCP, Azure; Referenzarchitekturen | Pflicht-Haltepunkte seit 17.5 bei x.2, x.5, x.8, x.11 | "Offline GitLab" | [gl-inst], [gl-up] BELEGT |
| **Infisical** | Docker standalone, Compose (mit Postgres und Redis), Linux-Paket | offizieller Helm-Chart | AWS (ECS Fargate, RDS, ElastiCache, ALB), GCP (GKE, Cloud SQL, Memorystore) | nicht auf der Seite | "runs on air-gapped bare metal, Kubernetes clusters, and cloud VMs" | [infisical] BELEGT |
| **Supabase** | Docker Compose "recommended way to self-host", "community-supported" | nur Community-Operator und -Helm | keine | nicht auf der Seite | "does not phone home or collect any telemetry" | [supabase] BELEGT |
| **Zitadel** | Linux, macOS, Docker Compose | offizieller Helm-Chart, HA "recommended" auf Kubernetes | nicht auf der Seite | Kanäle `stable` und `latest` | nicht auf der Seite; Datenbank nur PostgreSQL genannt | [zitadel] BELEGT |
| **Temporal** | Compose-Beispiel, zwei Go-Binaries | Helm-Charts, Kompatibilitätsregel Chart zu Image | keine | strikt eine Minor-Version nach der anderen, Schema zuerst; "no guarantee" zwischen nicht aufeinanderfolgenden Versionen | Hosts "should not be exposed to the open internet" | [temporal-dep], [temporal-up] BELEGT |

**Muster daraus (ABGELEITET):**
- **M1 Compose ist der Einstieg, aber selten der Produktionsweg.** Wer Produktion verspricht, liefert Helm oder einen Operator (Langfuse, Plane, Coder, Mattermost, Zitadel, Infisical). Wer nur Compose liefert, schließt Support aus (Sentry, PostHog, Supabase).
- **M2 Cloud-Module sind selten und meist nur für eine Cloud gepflegt** (Langfuse: Terraform nur für AWS belegt; Infisical: AWS und GCP als Vorlagen). Drei Clouds plus Hetzner mit gleicher Qualität zu pflegen ist teuer; der Weg von bothy (ein gemeinsames Modul `generic-vm`, Ziel-Module rufen es auf) hält den Aufwand klein.
- **M3 Upgrade-Regeln sind explizit**: Haltepunkte (Sentry, GitLab), strikt sequenziell (Temporal), Schema-Migration vor Rollout. Ein Produkt ohne veröffentlichte Upgrade-Regel zwingt Betreiber zu Ratespielen.
- **M4 Telemetrie ist bei der Mehrheit standardmäßig an** (Langfuse, Coder, n8n, Sentry-Beacon); Supabase sendet nichts. Für ein Produkt, dessen Kern Code und Tickets verarbeitet, ist "aus" die vertrauensbildende Wahl.
- **M5 Air-Gap ist ein eigener, dokumentierter Modus** (Sentry `SENTRY_AIR_GAP`, Infisical, Mattermost, GitLab offline, Coder Registry-Spiegel), nicht nur "Telemetrie aus".
- **M6 Docker-Socket im App-Container (OpenHands) ist das Gegenbeispiel** zu unserer Trennung von Steuerzentrale und Worker-Sandbox.

### 2.2 Einrichtung der GitHub App: Manifest-Flow

- Ablauf: POST an `https://github.com/settings/apps/new` (Konto) oder `.../organizations/ORG/settings/apps/new` mit dem Parameter `manifest` (JSON) und optional `state`; nach "Create GitHub App" leitet GitHub mit temporärem `code` an `redirect_url`; die Anwendung tauscht den Code per `POST /app-manifests/{code}/conversions` und erhält `id`, `pem` (privater Schlüssel) und `webhook_secret`. Alle drei Schritte müssen "within one hour" passieren. Manifest-Felder: `url` (Pflicht), `redirect_url`, `setup_url`, `hook_attributes.url`, `default_permissions`, `default_events`, `public`. Probot setzt den Flow um. ([gh-manifest] BELEGT; `client_id` und `client_secret` nennt die Seite im Antwortschritt nicht, ungeprüft)
- Folge: Der Setup-Assistent der Admin-UI kann die App mit genau den Rechteprofilen aus [05](../architecture/05-security.md) und O4 erzeugen, ohne dass der Betreiber Rechte von Hand anklickt; Schlüssel und Webhook-Secret landen direkt im Secret-Speicher. Voraussetzung: Die Steuerzentrale ist unter ihrer öffentlichen URL erreichbar (ist sie ohnehin, ADR-08). (ABGELEITET)
- Für GitLab, Bitbucket, Azure DevOps und Gitea gibt es keinen gleichwertigen Flow in den gelesenen Quellen; dort bleibt die Einrichtung eine Anleitung mit Token oder Service Account (ungeprüft je Provider).

### 2.3 Upgrades und Migrationen

- Temporal: Schema-Werkzeug zuerst, dann Server, eine Minor-Version nach der anderen, auf jeder Version etwa 10 Minuten warten. ([temporal-up] BELEGT)
- Sentry: Hard Stops müssen alle durchlaufen werden, bestimmte Versionen sind zu überspringen. ([sentry-rel] BELEGT)
- GitLab: feste Haltepunkte im Quartalstakt, Hintergrundmigrationen zwischen den Haltepunkten abwarten. ([gl-up] BELEGT)
- bothy (Owner-Projekt, selbst gelesen): `migrate` läuft vor `api` und `worker`; Expand/Contract, damit Version N-1 gegen Schema N läuft; keine Down-Migrationen; `migrate` bricht ohne frische Sicherung ab; Start mit zu altem Schema bricht ab, zu neues Schema meldet "nie bereit". (bothy `docs/spec/16-betrieb.md` Abschnitt 10, BELEGT; öffentlich `docs/spec/16-operations.md` Abschnitt 10)
- Amazon RDS: "Extension versions don't automatically upgrade during engine version upgrade workflows." ([rds-ext] BELEGT) Folge: Unsere Migration muss `ALTER EXTENSION vector UPDATE` selbst prüfen oder ausdrücklich nicht voraussetzen. (ABGELEITET)

### 2.4 Telemetrie und Air-Gap

Belege in Tabelle 2.1. Ergänzung: Langfuse schaltet Telemetrie bei der Government-Lizenz zwangsweise ab und lässt den Update-Check immer an ([lf-tel] BELEGT). Das zeigt, dass "Air-Gap" mehr ist als ein Telemetrie-Schalter: Update-Prüfung, Template-Downloads, Bild-Pulls, Doku-Suche und Browser-Ressourcen müssen einzeln abschaltbar sein. (ABGELEITET)

### 2.5 Postgres mit pgvector je Ziel

| Ziel | Verwalteter Dienst | pgvector | Beleg |
|---|---|---|---|
| Azure | Database for PostgreSQL Flexible Server | Erweiterung `vector` nach Freischaltung in `azure.extensions`; Version 0.8.2 auf PG 13 bis 18; zusätzlich `pg_diskann` 0.6.5 | [az-pgvector], [az-extver] BELEGT |
| AWS | RDS for PostgreSQL | 0.8.2 auf 18.4 bis 18.6 und 17.10 bis 17.11, ältere Minor-Versionen 0.8.0 oder 0.8.1; Erweiterung wird beim Engine-Upgrade nicht mitgehoben | [rds-ext] BELEGT; Aurora ungeprüft |
| Google Cloud | Cloud SQL for PostgreSQL | 0.8.5 ab PG 13 | [gcsql-ext] BELEGT; AlloyDB ungeprüft |
| Hetzner | kein eigener verwalteter Dienst (Produktseite nennt keine Datenbanken) | selbst betrieben (Container oder CloudNativePG) | [hz-cloud] BELEGT; Drittanbieter (Ubicloud u. a.) [hz-db] GESAGT |
| Kubernetes generisch | CloudNativePG | Image-Variante `standard` enthält pgvector, `minimal` nicht | [cnpg-img] BELEGT |
| Ein Host | Container | offizielles Image `pgvector/pgvector`, aktuell Tag `0.8.7-pg18-trixie` | [pgv-docker] BELEGT |

Folge: Die Versionen streuen von 0.8.0 bis 0.8.7 (BELEGT oben). Wir dürfen nur Funktionen nutzen, die die kleinste Version der Testmatrix hat, und prüfen die Version beim Start (`SELECT extversion`) mit klarer Fehlermeldung. (ABGELEITET)

### 2.6 Objektspeicher und der Stand von MinIO

**MinIO (Community Edition):**
- Repo `minio/minio` "was archived by the owner on Apr 25, 2026. It is now read-only"; README: "THIS REPOSITORY IS NO LONGER MAINTAINED"; "distributed as source code only"; "We will no longer provide pre-compiled binary releases for the community version"; alte Binaries "will not receive updates"; Lizenz weiter AGPLv3. Kommerziell: "AIStor Free" (Einzelknoten) und "AIStor Enterprise". ([minio] BELEGT)
- Zeitlinie laut Drittberichten: Konsole im Mai 2025 entfernt, Wartungsmodus ab 03.12.2025, erste Archivierung Februar 2026, `minio/operator` am 20.03.2026 archiviert; AIStor Free unter kommerzieller, nicht offener Lizenz. ([minio-news] GESAGT)
- Urteil: kein Baustein für ein neues Open-Source-Produkt (keine Sicherheitsupdates, AGPL, kein Binary). (ABGELEITET)

**Alternativen für den selbst gehosteten S3-Weg:**

| Option | Lizenz | Stärken | Lücken | Beleg |
|---|---|---|---|---|
| SeaweedFS | Apache 2.0 | S3-Gateway mit Objekt-, Bucket-, IAM- und STS-API, vorab signierte URLs; `weed mini` "fine for single-node production" | Enterprise Edition mit Zusatzfunktionen (Lizenz dort ungeprüft); Hauptautor nicht benannt, Finanzierung über Patreon | [seaweed] BELEGT |
| Garage | AGPLv3 | ein Binary ohne Abhängigkeiten, vorab signierte URLs, Multipart vollständig | keine Versionierung, kein Object Lock, Lifecycle nur `Expiration` und `AbortIncompleteMultipartUpload`, SSE nur SSE-C (Seite widersprüchlich) | [garage-gh], [garage-s3] BELEGT |
| RustFS | Apache 2.0 | MinIO-Ersatz, Version 1.0.x | Reife jung (erst seit 1.0.0-beta.11 stabile Webhooks laut README), KMS lokal nur für Tests | [rustfs] BELEGT |
| Ceph RGW | Lizenz ungeprüft | "compatible with a large subset of the Amazon S3 RESTful API", Swift parallel | schwer im Betrieb, lohnt nur bei vorhandenem Ceph | [ceph-rgw] BELEGT |
| Hetzner Object Storage | Dienst | S3-kompatibel auf Ceph, Standorte fsn1, nbg1, hel1; Versionierung und Object Lock vorhanden; bis 750 Anfragen/s je Bucket und je Quell-IP | SSE nur SSE-C; vorab signierte URLs auf der Aktionsseite nicht genannt (ungeprüft) | [hz-os], [hz-os-act] BELEGT |
| Azure Blob Storage | Dienst | Standard auf Azure (06 Abschnitt 1) | keine S3-API; Microsoft Q&A: "Azure Blob Storage does not support S3 API directly"; Umweg nur über Fremd-Proxies | [az-s3] GESAGT (Forum, kein Gegenbeleg in der Doku gefunden) |
| Amazon S3, Google Cloud Storage | Dienst | Standard je Cloud | GCS-Interop über S3-API ungeprüft, daher eigener Adapter | ungeprüft |

bothy hat dasselbe Problem bereits notiert ("Azure Blob Storage bietet keine S3-API [vermutet]", "Der S3-Treiber passt darum auf Azure nur mit SeaweedFS", `16-betrieb.md` Abschnitt 3 Regel 4). Dieser Bericht stützt die Vermutung mit einer Forumsaussage von Microsoft, ein Doku-Beleg fehlt weiter.

Folge (ABGELEITET): Der Speicher-Port braucht drei native Adapter (`s3`, `azure-blob`, `gcs`) plus `fs` für einen Host. Aufbewahrungsfristen (06 Abschnitt 5) setzt die Steuerzentrale selbst per Löschjob durch, nicht über Bucket-Lifecycle, weil Garage nur einen Teil davon kann. Upload-URLs der Work-API (01 Abschnitt 8, `uploadUrl`) brauchen je Adapter vorab signierte URLs (S3, Garage, SeaweedFS BELEGT; Azure über SAS, GCS über Signed URLs ungeprüft).

### 2.7 Secret-Speicher und Identität je Ziel

- **External Secrets Operator** synchronisiert Secrets aus AWS Secrets Manager, Azure Key Vault, Google Secret Manager, HashiCorp Vault, OpenBao, Infisical, Bitwarden und vielen weiteren in Kubernetes-Secrets. ([eso] BELEGT; Lizenz auf der Seite nicht genannt, ungeprüft)
- **OpenBao**: Fork von Vault unter der OpenSSF der Linux Foundation, "Sandbox project"; die FAQ spricht von "existing MPL 2.0 licensed code". ([openbao] BELEGT; Lizenzdatei selbst ungeprüft)
- **Hetzner** bietet keinen Secret- oder KMS-Dienst auf der Produktseite. ([hz-cloud] BELEGT) Dort bleibt `file` (wie bothy) oder OpenBao.
- **Claude API per WIF**: Unterstützte Aussteller sind AWS, Google Cloud, Microsoft Entra ID (Managed Identity, Entra Workload ID auf AKS), GitHub Actions, Kubernetes, SPIFFE, Okta und "Custom OIDC". JWKS per `discovery`, `explicit_url` oder `inline` "for issuers that are not reachable from the public internet". Token-Lebensdauer 60 bis 86.400 s, Standard 3.600 s; Tokens mit `jti` standardmäßig einmalig. ([an-wif] BELEGT, bestätigt und ergänzt README [an-wif])
- Folge (ABGELEITET): Auf jeder Basis gibt es einen Weg ohne statischen Schlüssel: auf den drei Clouds die Workload-Identität der Plattform, auf Hetzner, generischem Kubernetes und einem Host die Steuerzentrale als eigener OIDC-Aussteller (ADR-22) oder projizierte Kubernetes-Service-Account-Tokens. Der Tausch muss den `jti`-Einmalgebrauch beachten (je Tausch ein frisches JWT).

### 2.8 Sandbox: verschachtelte Container und Nested Virtualization je Ziel

**Technik-Voraussetzungen:**
- **Sysbox**: Apache 2.0; "works on all major cloud-based IaaS and Kubernetes services (e.g., EC2, GCP, GKE, EKS, AKS, Rancher, etc.)"; "not officially supported by Docker", Support "best effort", 210 offene Issues; letzte Version v0.7.1 (31. Juli, Jahr auf der Seite nicht genannt, VERMUTET 2026). Kernel: Ubuntu 24.04 ab 6.8, Ubuntu 22.04 ab 5.15; sonst Kernel ab 5.12 ohne shiftfs; RHEL und Flatcar nur EE. Kubernetes: EKS nur mit Ubuntu-AMI, GKE nur mit "Ubuntu with Containerd" und ohne Secure Boot, AKS mit Standardknoten (Doku nennt Ubuntu Bionic, also veraltet), je mindestens 4 vCPU. ([sysbox], [sysbox-rel], [sysbox-distro], [sysbox-k8s] BELEGT; Aktualität der K8s-Doku ABGELEITET als fraglich)
- **gVisor**: Standardplattform `systrap` nutzt seccomp, braucht keine Virtualisierung und ist "a better choice when running inside a VM"; KVM-Plattform nur auf Bare Metal im Vorteil. ([gvisor-plat] BELEGT) Folge: gVisor läuft auf jeder Linux-VM, auch auf Hetzner Cloud. (ABGELEITET)
- **Firecracker**: braucht Lese- und Schreibzugriff auf `/dev/kvm`; die Doku sagt noch "EC2 only supports KVM on `.metal` instance types". ([fc-start] BELEGT, durch [aws-nested] überholt)
- **Kata Containers**: "requires nested virtualization or bare metal"; Installation auf Kubernetes über den Kata-Deploy-Helm-Chart. ([kata-inst] BELEGT)
- **E2B Embed**: ganzer Stack mit Firecracker auf einem Linux-Host mit KVM per `docker compose up`, als Terraform für GCP, AWS und Azure und als Kubernetes-Manifest; Apache 2.0; mehrere Knoten nur als verwalteter Dienst von E2B im Konto des Kunden. ([e2b] BELEGT; ergänzt README [e2b])

**Je Ziel:**

| Ziel | Nested Virtualization / KVM | Sysbox | gVisor | MicroVM (Firecracker, Kata) | Beleg |
|---|---|---|---|---|---|
| Azure VM | unterstützt u. a. auf Dsv5, Dsv6, Dv5, Ddsv5, Dasv5, Dasv6 | ja (VM mit Ubuntu) | ja | ja auf diesen Serien | [az-dsv6], [az-dsv5] GESAGT (Suchauszug der Learn-Seiten) |
| AKS | Pod Sandboxing mit Kata und Cloud Hypervisor, `runtimeClassName: kata-vm-isolation`, nur Azure Linux, Gen2-VM mit Nested Virtualization, kein Arm64, kein FIPS | laut Sysbox-Doku ja | nicht als Dienst | ja (Kata) | [aks-sandbox] BELEGT |
| Azure Container Apps, ACI | "doesn't allow privileged containers mode" | nein | nein (ungeprüft) | Dynamic Sessions mit Hyper-V-Isolation und eigenen Containern, ob Docker darin geht ungeprüft | [aca-priv] GESAGT, [aca-sessions] BELEGT |
| AWS EC2 | seit 02/2026 auf C8i, M8i, R8i, seit 06/2026 zusätzlich C7i, M7i, R7i, I7i, X8i und Flex-Varianten; kein AMD, kein Graviton in den Meldungen; Bare Metal immer | ja | ja | ja auf diesen Typen oder `.metal` | [aws-nested] BELEGT (Herstellermeldung) |
| AWS Fargate (ECS, EKS) | `privileged` "not valid", nur `CAP_SYS_PTRACE` zusätzlich | nein | nein | nein | [fargate] BELEGT |
| EKS (EC2-Knoten) | wie EC2 | ja mit Ubuntu-AMI | selbst installiert | Kata selbst auf geeigneten Typen | [sysbox-k8s] BELEGT, Rest ABGELEITET |
| Google Compute Engine | Nested Virtualization auf Intel, AMD nur N4D, nicht E2, nicht speicheroptimiert, nicht Arm; Organisationsrichtlinie kann sie sperren; mindestens 10 % Leistungsverlust bei CPU-Last | ja | ja | ja | [gce-nested] BELEGT |
| GKE | GKE Sandbox mit gVisor ("Enabled by default in Autopilot clusters") und MicroVMs (Kata, Cloud Hypervisor, nur mit Nested Virtualization) | ja mit Ubuntu-Knoten | ja (Dienst) | ja (Dienst) | [gke-sandbox], [sysbox-k8s] BELEGT |
| Cloud Run | gen1 auf gVisor, gen2 als MicroVM; Jobs und Worker Pools nur gen2; kein privilegierter Modus dokumentiert | nein | nur als Plattform-Sandbox | nur als Plattform-Sandbox | [cloudrun-env] GESAGT (Suchauszug der Doku) |
| Hetzner Cloud | kein `/dev/kvm` auf CCX, CPX, CAX laut Drittbericht (Mai 2026); keine offizielle Aussage gefunden | ja (VM mit Ubuntu) | ja (systrap) | nein | [hz-kvm] GESAGT |
| Hetzner dediziert | Bare Metal, KVM direkt | ja | ja | ja | ABGELEITET |
| Generisches Kubernetes | je Knoten | `sysbox-deploy-k8s` (Ubuntu-Knoten) | RuntimeClass `runsc` | Kata-Deploy-Helm, nur mit KVM | [sysbox-k8s], [kata-inst] BELEGT |
| Ein Linux-Host | je Hardware | ja (Kernel ab 5.12) | ja | nur mit KVM | [sysbox-distro], [fc-start] BELEGT |
| GitHub-gehostete Linux-Runner (CI) | KVM auf Standard-Linux-Runnern ab 2 vCPU nach udev-Regel nutzbar; `ubuntu-slim` unprivilegiert ohne Docker-in-Docker | installierbar (sudo vorhanden) | ja | ja | [gh-kvm], [gh-runners] BELEGT |

### 2.9 Ingress, TLS, SSO, OTel

- Ein Host: Reverse Proxy mit automatischem TLS ist Branchenmuster (PostHog nutzt Caddy mit Let's Encrypt, [ph-self] BELEGT; bothy verlangt "nur der Rand ist öffentlich", Datenbank und Speicher nur im privaten Netz, `infra/tofu/README.md` Regel 3, BELEGT).
- Kubernetes: Ingress mit TLS (bothy `infra/helm/README.md`); welcher Controller und cert-manager ist Betreibersache. (ABGELEITET)
- SSO: Die Admin-UI braucht nur einen generischen OIDC-Client; Entra ID, Google, Okta, Zitadel und Keycloak sind dann Konfiguration, kein Plugin. Zitadel ist selbst ein selbst hostbarer OIDC-Anbieter mit Postgres ([zitadel] BELEGT). (ABGELEITET)
- OTel: unverändert OTLP-Export an beliebige Backends (06 Abschnitt 4); bothy liefert einen Collector mit Exportern je Backend (`infra/otel`). (BELEGT, selbst gelesen)

### 2.10 Vorbild bothy (Owner-Projekt, selbst gelesen)

bothy hat genau diese Planung schon gemacht und teilweise gebaut (BELEGT, [bothy-repo]):
- `infra/compose/` mit `install.sh` als Einrichtungsassistent: Vorprüfung ohne Schreiben, Bündel mit eingebauter SHA-256 und optional cosign prüfen, Fragen nur mit Terminal, jede Frage auch als Option, `--yes`, kein `sudo`, keine Paketinstallation, zweiter Lauf überschreibt weder `.env` noch `secrets/` (`16-betrieb.md` Abschnitt 3.1).
- `infra/tofu/modules/{generic-vm,hetzner,aws,azure}`: Ziel-Module erzeugen Netz, Host, Speicher und rufen `generic-vm`; Geheimnisse sind nie Ein- oder Ausgaben, State verschlüsselt, Provider gepinnt; echte Modultests kosten Geld und laufen nur mit Owner-Freigabe (`infra/tofu/README.md`).
- `infra/helm/`: "optional und später", mit Vorgaben (getrennte Rollen aus einem Image, Migrations-Job vor Rollout, keine Datenbank im Chart).
- Secret-Verweise `<schema>:<pfad>` mit Treibern `file`, `env`, `azkv`, `awssm`; Schnittstelle `Get(ref) -> (Wert, Version)`, optional `Put` (`16-betrieb.md` Abschnitt 5.2).
- Portabilitätstest: nach jedem Produkt-Release auf einem frischen GitHub-gehosteten Runner, amd64 und arm64, Images per Signatur geprüft, Installation mit genau den dokumentierten Optionen, dann Smoke-Test (`.github/workflows/portability.yml`).

Es gibt keinen Grund, das neu zu erfinden. Übernahme mit Verweis ist die billigste und schon geprüfte Lösung. (ABGELEITET)

---

## 3. Folgen für unsere Architektur

Jede Folge nennt Datei und Abschnitt in `docs/architektur/`. Nichts davon ist umgesetzt; dieser Bericht ändert nur sich selbst.

### 3.1 Neue Schnittstellenklasse "Infrastruktur-Treiber" (01, neuer Abschnitt 12; README Glossar)

Die 8 Plugin-Arten sind Adapter zu Fremdsystemen, deren Inhalte die Fachlogik braucht. Speicher, Secrets und Cloud-Identität sind etwas anderes: Sie hängen an der Basis, auf der eine Installation läuft. Vorschlag: eine eigene Klasse **Treiber** mit gleichem Manifest-, Contract-Test- und Fähigkeiten-Rahmen wie 01 Abschnitt 1.1, aber getrennt gezählt (ABGELEITET):

| Treiber-Art | Methoden (Skizze) | Fähigkeiten | Implementierungen Stufe 1 | später |
|---|---|---|---|---|
| `BlobStore` | `put`, `get`, `delete`, `list(prefix)`, `presignPut(key, ttl)`, `presignGet(key, ttl)` | `PRESIGN`, `VERSIONING`, `OBJECT_LOCK`, `SSE_KMS` | `fs`, `s3` (AWS S3, Hetzner, SeaweedFS, Garage, RustFS, Ceph RGW), `azure-blob` | `gcs` |
| `SecretStore` | `get(ref) -> {value, version}`, optional `put(ref, value)`, optional `sign(keyRef, payload)` für KMS-Schlüssel | `WRITE`, `SIGN`, `ROTATION_EVENT` | `file`, `env` (nur lesen), `azure-keyvault` | `aws-secretsmanager`, `gcp-secretmanager`, `openbao`; auf Kubernetes zusätzlich jedes ESO-Backend über Dateien |
| `CloudIdentity` | `ambientToken(audience)`, `exchange(target)` für Bedrock (AWS STS), Vertex (GCP STS), Foundry (Entra), Claude API (WIF) | `AMBIENT`, `SELF_ISSUER` | `self-issuer` (Steuerzentrale als OIDC-Aussteller, ADR-22), `azure-managed-identity` | `aws-irsa`/Pod Identity, `gcp-workload-identity`, `k8s-projected-token` |

Bewusst **kein** Port für (ABGELEITET):
- **Queue und Ablaufsteuerung**: bleibt Postgres mit pg-boss (ADR-04). Ein Queue-Port würde einen zweiten Zustandsspeicher einladen; das widerspricht ADR-02. Austauschbar bleibt nur die Work-API-Schnittstelle (06 Abschnitt 3, schon vorhanden).
- **Datenbank**: nur PostgreSQL mit pgvector; der Betreiber wählt "verwaltet" oder "mitgeliefert", das ist Konfiguration, kein Treiber.
- **Ingress, TLS, SSO, OTel**: Standards (HTTP hinter Proxy, OIDC-Client, OTLP), damit Konfiguration statt Plugin.

`ExecutionBackend` (01 Abschnitt 8) bleibt die Plugin-Art für die Container-Laufzeit, braucht aber Änderungen (3.3).

### 3.2 06 Betrieb und Deployment: von Firmen-Varianten zu Installationsprofilen

- **Abschnitt 1 (Gemeinsamer Betriebskern):** "Objektspeicher ... Azure Blob Storage auf Azure, sonst S3-kompatibel" ergänzen um: `BlobStore`-Treiber, MinIO ausdrücklich ausgeschlossen (Grund 2.6), mitgelieferter S3-Dienst im Compose-Bündel ist SeaweedFS. pgvector-Mindestversion an die Testmatrix binden und beim Start prüfen (2.5).
- **Abschnitt 2 (Deployment-Varianten):** Die Varianten A, B, T sind Betreiberprofile einer Firma bzw. des Owners. Vorschlag: Abschnitt teilen in **2a Installationsprofile des Produkts** (Tabelle unten) und **2b Betreiberprofil der ersten Installation** (heutige Varianten A, B, T, D unverändert, Variante C geht in 2a auf).

| Profil | Steuerzentrale | Zustand | Worker-Pool und Isolation | Secrets, Identität | Paket |
|---|---|---|---|---|---|
| `single-host` | Compose auf einer Linux-VM oder Hardware | Postgres-Container mit pgvector, `fs` oder SeaweedFS | Worker im selben Host, Sysbox oder gVisor; MicroVM nur mit KVM | `file`, `self-issuer` | Compose-Bündel plus Installer |
| `kubernetes` | Helm-Chart, Rollen `web`, `orchestrator` getrennt | externes Postgres oder CloudNativePG `standard` | Worker als Deployment je Pool, Sandbox-Pods per RuntimeClass (`sysbox-runc`, `runsc`, `kata`) | Kubernetes-Secrets (über ESO), projizierte Tokens | Helm-Chart |
| `azure` | Container Apps (kein privilegierter Modus nötig) | Flexible Server mit `vector`, Blob Storage | VM-Pool (Dsv5/Dsv6) mit Sysbox, gVisor oder MicroVM; oder AKS mit Pod Sandboxing; nie Container Apps | Key Vault, Managed Identity, Entra-SSO | OpenTofu-Modul `azure` |
| `aws` | ECS Fargate oder EC2 | RDS mit pgvector, S3 | EC2-Pool (MicroVM nur auf nested-fähigen Intel-Typen oder `.metal`), nie Fargate | Secrets Manager, IRSA/Pod Identity | OpenTofu-Modul `aws` |
| `gcp` | Cloud Run | Cloud SQL mit pgvector, GCS | GCE-Pool (Intel, nicht E2) oder GKE Sandbox (gVisor, MicroVM) | Secret Manager, Workload Identity | OpenTofu-Modul `gcp` |
| `hetzner` | Cloud-Server mit Compose | Postgres selbst betrieben, Hetzner Object Storage | Cloud-Server mit Sysbox oder gVisor; MicroVM nur auf dedizierten Servern | `file` oder OpenBao, `self-issuer` | OpenTofu-Modul `hetzner` (ruft `generic-vm`) |

  Alle Einträge stützen sich auf 2.5 bis 2.8; wo dort "ungeprüft" steht, gilt die Zelle als Plan, nicht als Beleg.
- **Abschnitt 3 (Technikwahl), Zeile Sandbox:** "Docker plus Sysbox" als Standard nur für `office` und `single-host` belassen; für das Produkt gVisor gleichwertig (läuft überall ohne KVM, 2.8) und MicroVM über E2B Embed oder Kata als Pflicht für fremden Code (bestätigt 05 Abschnitt 2). Risiko Sysbox (Support "best effort") als Grund eintragen.
- **Abschnitt 3, Zeile Secrets:** "Broker mit KMS (auf Azure: Key Vault) oder verschlüsselter Datei" ersetzen durch Verweis auf `SecretStore`-Treiber (3.1).
- **Abschnitt 6 (Betriebsroutinen), Punkt Upgrade:** ergänzen um Upgrade-Regeln (3.5).
- **Neuer Abschnitt 8 "Installationspaket"** mit dem Inhalt aus 3.4 und **neuer Abschnitt 9 "Telemetrie und Air-Gap"** (3.6).

### 3.3 01 Abschnitt 8 ExecutionBackend und Sandbox

- `SandboxSpec.isolation: "sysbox" | "gvisor" | "microvm"` bleibt; `microvm` deckt Firecracker (E2B Embed) und Kata (AKS, GKE, Kata-Deploy) ab. Neu: Der Worker meldet beim `claim` eine **geprüfte** Fähigkeit (`/dev/kvm` les- und schreibbar, `sysbox-runc` bzw. `runsc` registriert, RuntimeClass vorhanden), nicht eine konfigurierte. Grund: Hetzner Cloud, Fargate und Container Apps sehen aus wie normale Linux-Umgebungen, können aber KVM bzw. privilegierte Container nicht (2.8). (ABGELEITET)
- Policy-Regel: Mindest-Isolation je Repo-Klasse (`private_own` mindestens `sysbox` oder `gvisor`, `external_code` nur `microvm`), durchgesetzt beim Routing auf Pools; ein Pool ohne passende Fähigkeit bekommt das Item nie. Ergänzt 05 Abschnitt 2 und ADR-19. (ABGELEITET)
- Implementierungsliste in 01 Abschnitt 8 ergänzen: `docker-sysbox`, `docker-gvisor`, `microvm-e2b` (statt nur "erst mit fremdem Code"), `k8s` mit RuntimeClass, `office-actions`, `operator-local`. `aca-sessions` (Azure Dynamic Sessions, Hyper-V) als zu prüfende Option für Services ohne Docker-in-Docker (ungeprüft).

### 3.4 Installationspaket (Vorschlag, neu in 06 Abschnitt 8)

Was das Projekt ausliefert (ABGELEITET, Muster aus 2.1 und bothy 2.10):
1. **Container-Images** für amd64 und arm64, signiert (cosign) mit SBOM: `control-plane` (Rollen über Argument), `agent-worker`, `egress-proxy`, `sandbox-base`; Migration als Unterbefehl `migrate` des `control-plane`-Images.
2. **CLI** (ein Binary): `install` (Assistent für `single-host`), `doctor` (prüft Postgres-Version, pgvector, Speicher, KVM, Sysbox, gVisor, Ausgehend-HTTPS, öffentliche URL, Webhook-Erreichbarkeit), `upgrade`, `backup`, `restore`, `worker register` (Pool-Schlüssel für eigene Hardware), `github-app create` (Manifest-Flow ohne UI).
3. **Setup-Assistent in der Admin-UI** beim ersten Start: Admin anlegen, SSO verbinden, GitHub App über den Manifest-Flow erzeugen (2.2), Provider-Credential bzw. WIF einrichten, ersten Pool registrieren, Probe-Run im Modus `shadow`.
4. **Compose-Bündel** (`single-host`): Steuerzentrale, Postgres mit pgvector, optional SeaweedFS, Caddy mit TLS, OTel-Collector, Worker mit wählbarer Isolation. Installer nach bothy-Regeln (kein `sudo`, Vorprüfung ohne Schreiben, Prüfsumme und Signatur, idempotent).
5. **Helm-Chart** (`kubernetes`): getrennte Deployments je Rolle aus einem Image, `migrate` als Job vor dem Rollout, keine Datenbank im Chart, Worker-Pools mit RuntimeClass-Wahl, NetworkPolicy für den Egress-Proxy.
6. **OpenTofu-Module**: `generic-vm`, `azure`, `aws`, `gcp`, `hetzner`, Aufbau wie bothy (Ziel-Modul baut Infrastruktur und ruft `generic-vm` oder installiert den Chart); Geheimnisse nie als Ein- oder Ausgabe.
7. **Worker-Paket für eigene Hardware** (systemd-Einheit), entspricht Pool `operator-local`.
8. **Doku**: Support-Matrix (welches Profil wird mit welcher Version getestet), Upgrade-Pfad, Sicherung und Wiederherstellung, Air-Gap, Ports und ausgehende Ziele je Dienst.

Reihenfolge (ABGELEITET): Compose-Bündel und CLI zuerst (gleicher Weg für den Testbetrieb des Owners und für Fremde), dann OpenTofu `azure` (Instanz des Owners), dann Helm, dann `aws`, `gcp`, `hetzner`. Eintrag in [08](../architecture/08-roadmap.md) als eigene Stufe "Installierbarkeit" mit Fertig-Kriterium "Portabilitätstest grün auf `single-host` amd64 und arm64".

### 3.5 Upgrade-Regeln (06 Abschnitt 6, ergänzt)

Übernahme der bothy-Regeln (2.3), ergänzt um Haltepunkte (ABGELEITET):
- Expand/Contract, keine Down-Migrationen, `migrate` vor Rollout, Abbruch ohne frische Sicherung.
- Unterstützt wird nur N-1 nach N je Minor-Version; Versionen mit Haltepunkt stehen in den Release-Notes und prüft `migrate` selbst (Sentry- und GitLab-Muster).
- Start mit zu altem Schema bricht ab; zu neues Schema meldet "nicht bereit".
- `ALTER EXTENSION vector UPDATE` ist kein stiller Teil der Migration; `doctor` meldet die Version, die Migration verlangt nur die Mindestversion (RDS hebt sie nicht mit, 2.3).
- Plugin- und Treiber-`apiVersion` wie 01 Regel 6 (aktuelle und vorige Major-Version).

### 3.6 Telemetrie und Air-Gap (06, neuer Abschnitt 9)

- Produkt-Telemetrie an das Projekt: **standardmäßig aus**, Opt-in im Setup-Assistenten, Inhalt öffentlich dokumentiert, nie Code, Tickets, Prompts oder Namen (Begründung M4).
- Modus `air_gap: true` schaltet alle Ausgänge außer den konfigurierten SCM-, Ticket- und LLM-Endpunkten ab (Update-Prüfung, Image-Pulls aus öffentlichen Registries, Doku-Links mit Fremdinhalten); Images aus einem eigenen Registry-Spiegel. Der Egress-Proxy (ADR-20) setzt das technisch durch, nicht nur ein Flag. (ABGELEITET)
- Grenze: Mit einem Cloud-LLM ist keine Installation vollständig air-gapped; voll offline nur mit selbst gehostetem Modell (ModelProvider, Gate in 07). (ABGELEITET)

### 3.7 Folgeliste weiterer Stellen (Fakt "Produkt ist Open Source und nicht firmenspezifisch")

| Stelle | Was heute steht | Vorschlag |
|---|---|---|
| README Titel und Abschnitt 1 | Titel mit Firmennamen | neutraler Produktname; die Firma wird Betreiber und erster Nutzer |
| 01 Abschnitt 1.1 | `apiVersion` mit Firmendomain | neutrale API-Gruppe vor der ersten Veröffentlichung, weil sie danach nur mit Abkündigung änderbar ist (01 Regel 6) |
| 06 Abschnitt 2 | Varianten A bis D firmenbezogen | Teilung in 2a und 2b (3.2) |
| 06 Abschnitt 3, Beobachtbarkeit | "Export an vorhandenes Grafana oder New Relic" | "an beliebiges OTLP-Backend; bei der ersten Installation Grafana oder New Relic" |
| 09 O14 | "Wird die Plattform an Dritte ausgeliefert?" Empfehlung "zunächst nur intern" | durch Owner-Vorgabe 3. Runde entschieden: ja, Open Source; die Claude-Code-Bedingungen aus [cc-legal] bleiben zu prüfen (Thema eines anderen Berichts) |
| 09 ADR-25 | Verbot eines bestimmten Hosts | bleibt für den Betrieb des Owners; im Produkt ist das kein Thema |
| 09 ADR-19 | Sysbox je Work-Item, MicroVM vor fremdem Code | ergänzen: gVisor gleichwertig, Isolation je Repo-Klasse geprüft (3.3) |
| 09 neu | | ADR-37 Installationstreppe Compose, Helm, OpenTofu; ADR-38 Treiber-Klasse `BlobStore`, `SecretStore`, `CloudIdentity`, kein Queue-Port; ADR-39 kein MinIO, SeaweedFS im Bündel; ADR-40 Telemetrie aus, Air-Gap-Modus; ADR-41 GitHub App per Manifest-Flow |
| backlog-minors.md | | nichts, alle Punkte hier sind Architektur, keine Minors |

Nicht durchsucht wurden Wissensablagen außerhalb des Repos (keine Tickets oder Wiki zu diesem Projekt bekannt; ungeprüft).

### 3.8 Testmatrix je Ziel (neu, 07 oder 06)

| Ziel | Was wird geprüft | Wo | Wann | Kosten |
|---|---|---|---|---|
| `single-host` amd64, arm64 | Installer ohne Terminal mit dokumentierten Optionen, Smoke-Run (Webhook-Fixture, Shadow-Review), Upgrade N-1 nach N mit Daten, Backup und Restore | GitHub-gehostete Runner (bothy-Muster) | jede Release, Upgrade-Test zusätzlich bei Schema-Änderung | im öffentlichen Repo nach GitHub-Angaben frei (ungeprüft); privat Minuten |
| Isolation | dieselbe Sandbox-Suite S1 bis S6 (07) unter Sysbox, gVisor und Firecracker | Standard-Linux-Runner (KVM nach udev-Regel nutzbar, [gh-kvm]) | jeder PR, der Worker oder Sandbox ändert | wie oben |
| Postgres | kleinste und neueste pgvector-Version der Matrix (heute 0.8.2 und 0.8.7) je unterstützter PG-Hauptversion | Container in CI | jeder PR mit Migration | frei |
| `BlobStore` | Contract-Suite gegen SeaweedFS und Garage (Container), `azure-blob` gegen Emulator (Azurite, ungeprüft), Aufzeichnungen echter Antworten wie 01 Regel 1 | CI | jeder PR am Treiber | frei |
| `SecretStore`, `CloudIdentity` | `file`, OpenBao-Container; Cloud-Treiber gegen aufgezeichnete Antworten | CI | jeder PR am Treiber | frei |
| `kubernetes` | Helm-Install auf kind oder k3d mit RuntimeClass `runsc`; Sysbox auf kind ungeprüft | CI | jede Release | frei |
| OpenTofu-Module | `tofu validate`, `plan` gegen Attrappen-Credentials | CI | jeder PR am Modul | frei |
| `azure` echt | Apply in Wegwerf-Umgebung, Portabilitätstest, Destroy; zusätzlich die Instanz des Owners als Dauerbetrieb | Azure-Abo | vor Major- und Minor-Releases, mit Owner-Go | Geld (O-neu-2) |
| `aws`, `gcp`, `hetzner` echt | wie `azure` | jeweiliges Konto | vor Releases, die das Modul ändern, mit Owner-Go | Geld, Konten (O-neu-2) |

---

## 4. Owner-Entscheidungen

| Nr. | Frage | Art | Empfehlung | Grund |
|---|---|---|---|---|
| O-neu-1 | Lizenz des Produkts | Recht, Produkt | Apache 2.0 (wie bothy und Sysbox, SeaweedFS, E2B) | erlaubt jedem Betrieb und Anflanschen ohne Offenlegungspflicht; deckt sich mit ADR-34 (kein AGPL-Code). AGPL würde gegen Hoster schützen, schreckt aber Firmen ab. Falls ein anderer Bericht dieses Thema führt, gilt dessen Empfehlung nach Abgleich der Belege |
| O-neu-2 | Budget und Konten für echte Cloud-Tests (Azure, AWS, Google Cloud, Hetzner) | Geld, Konten | Azure über das vorhandene Abo des Owners mit Budget-Alarm; AWS, GCP, Hetzner erst, wenn das jeweilige Modul gebaut ist, je Wegwerf-Umgebung nur vor Releases | CI-Tests (Compose, kind, `tofu plan`) decken den größten Teil kostenlos ab; echte Applies kosten Geld je Lauf (Schätzung, nicht gemessen) |
| O-neu-3 | Marketplace-Einträge (Azure Marketplace, AWS Marketplace) | Konten, Recht | jetzt nicht; frühestens nach stabiler 1.0 | Publisher-Konten und Verträge nötig; Coder und Mattermost zeigen, dass das ein später Schritt ist (2.1) |
| O-neu-4 | Produkt-Telemetrie an das Projekt | Produkt, Datenschutz | standardmäßig aus, Opt-in | Produkt verarbeitet Code und Tickets; Vertrauen wiegt mehr als Nutzungsdaten (M4) |
| O-neu-5 | Veröffentlichungsort für Images und Releases | Konten | GitHub Releases und ghcr.io des öffentlichen Repos | ein Konto, das ohnehin existiert; Kosten bei öffentlichen Paketen nach GitHub-Angaben keine (ungeprüft) |
| O-neu-6 | Produktname und API-Gruppe vor der ersten Veröffentlichung | Produkt, Recht (Marke) | neutralen Namen wählen, Markenprüfung vor Veröffentlichung | `apiVersion` ist nach der ersten Veröffentlichung nur mit Abkündigung änderbar (01 Regel 6) |

O1 (Azure für die Steuerzentrale des Owners) und O6 (eigene Hardware für `operator-local`) bleiben wie entschieden bzw. offen; dieser Bericht ändert sie nicht. Neu ist nur der Hinweis: Worker auf Azure gehen nicht auf Container Apps, sondern auf VMs oder AKS (2.8), das kostet zusätzlich zur Steuerzentrale (Schätzung, nicht gemessen).

---

## 5. Offene Punkte (ungeprüft)

1. Hetzner Cloud ohne KVM: nur Drittbelege ([hz-kvm]); eine offizielle Aussage fehlt. Vor dem Hetzner-Modul mit `kvm-ok` auf einer Testinstanz prüfen.
2. Azure Nested Virtualization je Serie: nur aus Suchauszügen der Learn-Seiten ([az-dsv5], [az-dsv6]); Seiten vor dem Azure-Modul selbst lesen.
3. Sysbox auf aktuellen AKS-, EKS-, GKE-Knotenbildern: Doku nennt veraltete Bilder (Ubuntu Bionic, EKS 1.20); Release-Jahr von v0.7.1 nicht auf der Seite.
4. Azure Container Apps Dynamic Sessions als Sandbox für Services ohne Docker-in-Docker: Isolation belegt, Eignung für unsere Worker ungeprüft.
5. Kata auf EKS mit nested-fähigen Intel-Typen: keine Herstelleranleitung gelesen.
6. Vorab signierte URLs bei Hetzner Object Storage; GCS über S3-Interop; Azure SAS für unseren `presignPut`.
7. Lizenz von Ceph, External Secrets Operator und OpenBao nicht an der Lizenzdatei geprüft.
8. Aurora und AlloyDB pgvector-Versionen; Postgres 18 als Mindestversion auf allen drei Clouds (RDS und Azure führen 18, Cloud SQL nicht geprüft).
9. Dify-Helm (Community), Plane-Installer-CLI und Air-Gap, n8n-Queue-Modus, Kodus-Helm: auf den gelesenen Seiten nicht belegt.
10. Kostenfreiheit von GitHub-gehosteten Runnern und ghcr.io für öffentliche Repos: hier nicht nachgelesen.
11. Azure Blob ohne S3-API: nur Forumsaussage von Microsoft, kein Doku-Beleg; wirkt sich nicht aus, weil der Plan ohnehin einen nativen Adapter vorsieht.
12. Der Arbeitsbaum des Projekts hatte zu Beginn unversionierte Ordner `data/` und `docs/` (Projektstand vor dem ersten Commit, Teil derselben Planungsarbeit); dieser Bericht hat nur die eigene Datei geschrieben.

---

## 6. Quellen (alle abgerufen 2026-10-31)

**Vergleichsprodukte**
- [lf-self] https://langfuse.com/self-hosting
- [lf-aws] https://langfuse.com/self-hosting/deployment/aws
- [lf-tel] https://langfuse.com/self-hosting/security/telemetry
- [sentry-sh] https://develop.sentry.dev/self-hosted/
- [sentry-rel] https://develop.sentry.dev/self-hosted/releases/
- [ph-self] https://posthog.com/docs/self-host
- [ph-hobby] https://posthog.com/docs/self-host/deploy/hobby
- [plane] https://developers.plane.so/self-hosting/overview
- [coder-inst] https://coder.com/docs/install
- [coder-srv] https://coder.com/docs/install/server/
- [coder-tel] https://coder.com/docs/admin/setup/telemetry
- [n8n-host] https://docs.n8n.io/hosting/
- [n8n-iso] https://docs.n8n.io/hosting/configuration/configuration-examples/isolation/
- [dify] https://docs.dify.ai/en/self-host/quick-start/docker-compose
- [oh-local] https://docs.openhands.dev/openhands/usage/run-openhands/local-setup
- [renovate] https://docs.renovatebot.com/getting-started/running/
- [kodus-vm] https://docs.kodus.io/how_to_deploy/en/deploy_kodus/generic_vm
- [mm-plan] https://docs.mattermost.com/deployment-guide/server/server-deployment-planning.html
- [mm-deploy] https://docs.mattermost.com/deployment-guide/server/deploy-server.html
- [gl-inst] https://docs.gitlab.com/install/
- [gl-up] https://docs.gitlab.com/update/upgrade_paths/
- [infisical] https://infisical.com/docs/self-hosting/overview
- [supabase] https://supabase.com/docs/guides/self-hosting
- [zitadel] https://zitadel.com/docs/self-hosting/deploy/overview
- [temporal-dep] https://docs.temporal.io/self-hosted-guide/deployment
- [temporal-up] https://docs.temporal.io/self-hosted-guide/upgrade-server

**GitHub**
- [gh-manifest] https://docs.github.com/en/apps/sharing-github-apps/registering-a-github-app-from-a-manifest
- [gh-kvm] https://github.blog/changelog/2024-04-02-github-actions-hardware-accelerated-android-virtualization-now-available/ (Suchauszug)
- [gh-runners] https://docs.github.com/en/actions/reference/runners/github-hosted-runners (Suchauszug)

**Datenbank**
- [az-pgvector] https://learn.microsoft.com/en-us/azure/postgresql/extensions/how-to-use-pgvector
- [az-extver] https://learn.microsoft.com/en-us/azure/postgresql/extensions/concepts-extensions-versions
- [rds-ext] https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-extensions.html
- [gcsql-ext] https://docs.cloud.google.com/sql/docs/postgres/extensions
- [cnpg-img] https://github.com/cloudnative-pg/postgres-containers
- [pgv-docker] https://hub.docker.com/r/pgvector/pgvector
- [hz-db] Suche "Hetzner managed PostgreSQL" mit Treffern u. a. https://www.ubicloud.com/use-cases/hetzner (GESAGT)

**Objektspeicher**
- [minio] https://github.com/minio/minio
- [minio-news] https://www.glukhov.org/data-infrastructure/object-storage/minio-dead/, https://blog.vonng.com/en/db/minio-resurrect/, https://wz-it.com/en/blog/minio-successor-s3-storage-comparison/ (GESAGT)
- [seaweed] https://github.com/seaweedfs/seaweedfs
- [garage-gh] https://github.com/deuxfleurs-org/garage
- [garage-s3] https://garagehq.deuxfleurs.fr/documentation/reference-manual/s3-compatibility/
- [rustfs] https://github.com/rustfs/rustfs
- [ceph-rgw] https://docs.ceph.com/en/latest/radosgw/
- [hz-os] https://docs.hetzner.com/storage/object-storage/overview/
- [hz-os-act] https://docs.hetzner.com/storage/object-storage/supported-actions
- [az-s3] https://learn.microsoft.com/en-us/answers/questions/1183760/s3-api-support-over-azure-blob-storage (GESAGT, Suchauszug)

**Secrets und Identität**
- [eso] https://external-secrets.io/latest/
- [openbao] https://openbao.org/
- [an-wif] https://platform.claude.com/docs/en/manage-claude/workload-identity-federation

**Rechenplattformen und Sandbox**
- [hz-cloud] https://www.hetzner.com/cloud
- [hz-kvm] https://mvm-deployment-docs.pages.dev/providers/hetzner/ (GESAGT, Suchauszug)
- [aws-nested] https://aws.amazon.com/about-aws/whats-new/2026/02/amazon-ec2-nested-virtualization-on-virtual/ und https://aws.amazon.com/about-aws/whats-new/2026/06/nested-virtualization-intel-us-gov-cloud/ (Suchauszug)
- [fargate] https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-tasks-services.html (Suchauszug)
- [az-dsv5] https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/dsv5-series (Suchauszug)
- [az-dsv6] https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/dsv6-series (Suchauszug)
- [aks-sandbox] https://learn.microsoft.com/en-us/azure/aks/use-pod-sandboxing
- [aca-priv] https://learn.microsoft.com/en-us/azure/container-apps/containers (Suchauszug)
- [aca-sessions] https://learn.microsoft.com/en-us/azure/container-apps/sessions
- [gce-nested] https://docs.cloud.google.com/compute/docs/instances/nested-virtualization/overview
- [gke-sandbox] https://docs.cloud.google.com/kubernetes-engine/docs/concepts/sandbox-pods
- [cloudrun-env] https://docs.cloud.google.com/run/docs/configuring/execution-environments (Suchauszug)
- [sysbox] https://github.com/nestybox/sysbox
- [sysbox-rel] https://github.com/nestybox/sysbox/releases
- [sysbox-distro] https://github.com/nestybox/sysbox/blob/master/docs/distro-compat.md
- [sysbox-k8s] https://github.com/nestybox/sysbox/blob/master/docs/user-guide/install-k8s-distros.md
- [gvisor-plat] https://gvisor.dev/docs/architecture_guide/platforms/
- [fc-start] https://github.com/firecracker-microvm/firecracker/blob/main/docs/getting-started.md
- [kata-inst] https://github.com/kata-containers/kata-containers/blob/main/docs/install/README.md
- [e2b] https://github.com/e2b-dev/infra

**Lokal (selbst gelesen)**
- [bothy-repo] öffentliches Repo bothy (Angaben in [bothy-vorlage-projekt-setup](bothy-vorlage-projekt-setup.md) Abschnitt 6): ursprünglich an einem nicht veröffentlichten Planungsstand gelesen; dieselben Dateien liegen öffentlich auf Commit `4485084b8`: `infra/README.md`, `infra/tofu/README.md`, `infra/helm/README.md`, `docs/spec/16-operations.md` (früher `16-betrieb.md`; Abschnitte 3, 3.1, 5.2, 10, 11, Abschnittsnummern am 2026-11-01 nachgeprüft), `.github/workflows/portability.yml`
- Architektur: `docs/architektur/README.md`, `01-plugin-schnittstellen.md`, `05-sicherheit.md`, `06-betrieb-und-deployment.md`, `09-entscheidungen.md`
