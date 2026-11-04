<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: The Guildwork Authors
-->
# ADR-43: No MinIO

- Status: Accepted
- Group: ADR-37 to ADR-53 (third round, 2026-10-31)

## Context

MinIO community repo archived since 2026-04-25, without binaries ([minio] VERIFIED); SeaweedFS Apache-2.0 with S3 API ([seaweed] VERIFIED); Garage AGPL-3.0, without versioning and Object Lock ([garage-s3] VERIFIED), remains the operator's choice

## Decision

**No MinIO**; in the Compose bundle optionally SeaweedFS as the S3 service (profile `s3`), otherwise driver `fs`

## Alternatives

MinIO; Garage; Ceph RGW

## Consequences

The decision is applied in the documents listed under Source.

## Source

[09](../architecture/09-decisions.md) section 2.2, row ADR-43; references: [11](../architecture/11-installation-and-hosting.md) section 3.
