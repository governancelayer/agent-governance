# Governance Decision Record (GDR) v0.1-draft

Status: Design Target — schema not yet finalized
Version: 0.1-draft
Date: 2026-03-14
Part of: AGF Phase 2 — Governance Evidence

> This document describes the GDR design target. The JSON schema (`gdr-schema-v0.1.json`) is in the ROADMAP and will be published as part of v0.3. The field definitions and standards mappings below are normative design targets, not yet a finalized schema.

---

## Purpose

The Governance Decision Record (GDR) is a structured, portable, signed record of a governance decision. It is the audit artifact that compliance officers, regulators, and dispute adjudicators receive after an agent transaction has been evaluated.

Phase 1 (DAE, DBA, TCR) defines **what should happen before an agent acts**.
Phase 2 (GDR, Obligation Lifecycle, Evidence Bundle) defines **what did happen after an agent acted**.

The GDR is the primary Phase 2 artifact. It answers: "A governance decision was made. Here is the exact decision, what was evaluated, who had authority, and a signed record that cannot be tampered with."

---

## The Gap GDR Fills

Every agent transaction evaluated against AGF Phase 1 primitives produces a decision: `allow`, `deny`, or `conditional`. That decision needs a record. Specifically:

- A compliance officer needs to know which transactions were denied and why.
- A dispute adjudicator needs to know what the enforcement point evaluated at decision time.
- A regulator (EU AI Act Article 12) needs a log of high-risk AI system decisions.
- A SIEM/SOC tool needs an event to ingest.

No existing standard provides a portable signed governance decision record with the combination of fields required. OSCAL Assessment Results cover security assessment findings. OCSF Authorization Events cover identity authorization. Neither covers agent governance decisions with a full authority chain, primitive evaluation results, and a tamper-evident signature.

---

## Design Target Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `record_id` | string | yes | Unique identifier for this GDR |
| `context_id` | string | yes | Shared transaction correlation identifier — the same value present in the corresponding DAE, DBA, and TCR. This is the primary join key across all four primitives for a single agent transaction. |
| `transaction_id` | string | yes | Internal transaction reference used by the issuing enforcement point |
| `decision` | enum | yes | `allow`, `deny`, or `conditional` |
| `primitives_evaluated` | array[object] | yes | Which of DAE/DBA/TCR were evaluated and their individual results |
| `policy_reference` | object | yes | Policy version and rules that fired |
| `authority_chain` | array[string] | yes | Full delegation path from principal to acting agent |
| `timestamps` | object | yes | `decision_time` (RFC3339), `evaluation_duration_ms` |
| `enforcement_point` | string | yes | Identity of the gateway/proxy that evaluated this |
| `protocol` | string | yes | Transport protocol: `A2A`, `MCP`, `HTTP`, `custom` |
| `signature` | string | yes | Signed by the governance service for tamper evidence |
| `deny_reason` | string | conditional | Present when `decision=deny`; normalized reason code |
| `conditions` | array[string] | conditional | Present when `decision=conditional`; what must hold |

---

## Standards Alignment (Design Target)

### EU AI Act Article 12

GDR is designed to support Article 12 logging requirements for high-risk AI system logging. The table below shows the current design-target field mappings:

| Article 12 Requirement | GDR Field (design target) |
|---|---|
| System identification | `enforcement_point` |
| Date and time | `timestamps.decision_time` |
| Reference data or policy used | `policy_reference` |
| Input data (by reference) | `transaction_id` → Phase 1 contracts |
| Output and the natural person verifying it | `decision` + `authority_chain` |
| Identification of responsible persons | `authority_chain` |
| Duration of operation | `timestamps.evaluation_duration_ms` |

**Important:** This is a design-target mapping, not a finalized compliance checklist. Article 12's precise field requirements depend on the AI system category and are subject to interpretation by national supervisory authorities. Additionally, ISO 24970 (expected Q4 2026) will define a standardized format for Article 12 logging — GDR field definitions may be adjusted to align with that standard once its draft is available. A complete, verified Article 12 compliance mapping will be published alongside the GDR schema in v0.3.

A GDR instance produced by a compliant enforcement point is intended to support Article 12 logging obligations for AI systems acting autonomously within its scope. Legal review is required before treating any GDR implementation as compliant.

### OSCAL (NIST)

OSCAL Assessment Results (`oscal-ar`) defines a structured format for recording security control assessment findings. GDR maps to OSCAL Assessment Results for organizations requiring FedRAMP or federal compliance alignment.

Planned mapping: GDR `primitives_evaluated` → OSCAL `observation` entries; GDR `decision` → OSCAL `finding` result; GDR `signature` → OSCAL `attestation`.

### OCSF (Open Cybersecurity Schema Framework)

OCSF Authorization Event (class_uid 3002) defines a standardized event for SIEM/SOC ingestion. GDR maps to OCSF Authorization Event for integration with security tooling.

Key difference: OCSF Authorization Events are not signed and do not carry a full authority chain. The GDR provides a richer artifact; OCSF is the target format for SIEM ingestion (a projection of the GDR into OCSF format).

Planned mapping: GDR → OCSF class 3002 field mapping table.

---

## Relationship to Phase 1 Primitives

A GDR is produced after Phase 1 evaluation. It correlates with Phase 1 contracts via the shared `context_id` and references each primitive by its type-specific identifier:

```
GDR.context_id == DAE.context_id == DBA.context_id == TCR.context_id   (shared join key)
GDR.primitives_evaluated[n].id → DAE.delegation_id                     (per-primitive ref)
GDR.primitives_evaluated[n].id → DBA.assertion_id                      (per-primitive ref)
GDR.primitives_evaluated[n].id → TCR.commitment_id                     (per-primitive ref)
GDR.primitives_evaluated[n].result → DAE/DBA/TCR evaluation outcome
GDR.authority_chain → DAE.principal → DAE.delegate (delegation chain)
```

The `context_id` is the authoritative evidence-chain join key. An auditor correlating all governance artifacts for a transaction uses `context_id` as the primary lookup, then resolves each primitive by its type-specific identifier. The GDR does not replace Phase 1 contracts. Both are preserved in the Evidence Bundle.

---

## Signing

The GDR is signed by the governance service that issued it. The signature covers all fields except `signature` itself.

Signing algorithm: JWS (JSON Web Signature, RFC 7515) with RS256 or ES256.

A verifier can validate the signature without access to the originating enforcement point. This is required for cross-organizational audit and regulatory submission.

---

## Planned Milestones

- `gdr-schema-v0.1.json` — finalized JSON Schema
- GDR specification (this document promoted from draft)
- EU AI Act Article 12 compliance mapping table
- OSCAL profile document
- OCSF mapping table
- Reference GDR emitter in the reference implementation

See [ROADMAP.md](../../ROADMAP.md) for timeline.

---

## Open Questions

These are design decisions not yet resolved. Feedback welcome (open an issue).

1. **Signature granularity:** Should the signature cover the full GDR or just the decision + evidence summary? Full-document signing is more tamper-evident but harder to update if metadata fields change.

2. **OSCAL vs OCSF as primary format:** Should the GDR be primarily an OSCAL artifact (with OCSF projection) or primarily an OCSF event (with OSCAL projection)? The primary audience differs: OSCAL targets compliance/GRC teams; OCSF targets SOC/SIEM teams.

3. **`conditional` decision semantics:** What does `conditional` mean precisely? "Allow, but with additional monitoring"? "Allow if condition X is met within Y time"? This needs formal semantics before finalization.

4. **ISO 24970 alignment:** ISO 24970 (expected Q4 2026) will define a standard format for EU AI Act Article 12 compliance logging. GDR should align with ISO 24970 when the draft is available. There is a risk of field-level incompatibility if GDR is finalized before ISO 24970 publishes.
