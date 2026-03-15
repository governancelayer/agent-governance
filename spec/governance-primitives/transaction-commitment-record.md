# Transaction Commitment Record (TCR) v0.3

Status: Draft
Version: 0.3.0
Date: 2026-03-14
Supersedes: 0.2.0

## Purpose

TCR defines a machine-readable accountability record for transaction-level commitments, their fulfillment state, and the evidence required to support dispute handling.

TCR is the **most novel of the three Phase 1 AGF primitives**. While W3C PROV and XACML 3.0 Obligations provide partial coverage of related concepts, neither provides a portable commitment lifecycle with time-bound deadlines, breach detection, and a dispute-ready evidence container. TCR extends W3C PROV's provenance model with agent-commerce-specific commitment semantics.

---

## Standards Alignment

### Relationship to W3C PROV

W3C PROV defines a vocabulary for provenance — describing how entities, activities, and agents relate to each other. PROV's core concepts: `Activity`, `Entity`, `Agent`, `wasGeneratedBy`, `used`, `wasAssociatedWith`, `actedOnBehalfOf`.

**Field-level overlap:**

| TCR Field | W3C PROV Equivalent | Notes |
|---|---|---|
| `transaction_id` | PROV `Activity` identifier | The transaction is a PROV Activity |
| `issuer` | PROV `Agent` (`wasAssociatedWith`) | The agent responsible for the activity |
| `counterparty` | PROV `Agent` (`actedOnBehalfOf`) | The principal on whose behalf the agent acted |
| `evidence_refs` | PROV `Entity` references (`used`, `wasGeneratedBy`) | Artifacts produced or consumed by the activity |

**What W3C PROV does not provide:**

PROV records _what happened_. It does not record _what was promised_ or _whether the promise was kept_. PROV has no concept of:

- A **commitment** with a deadline (`due_by`) that must be fulfilled
- A **lifecycle state machine** for commitments (`pending` → `fulfilled` / `breached` / `revoked`)
- A **breach detection rule**: if `due_by` passes and `fulfilled=false`, the record becomes `breached`
- A **dispute window**: a time period during which evidence must be preserved for adjudication
- A **denial semantic**: a breached TCR blocks a finalize/close action

TCR extends PROV's activity + agent model with this commitment lifecycle layer.

**AGF's position:** TCR adopts PROV vocabulary for its core concepts (activity, agent, entity, evidence) and adds the commitment lifecycle that PROV explicitly omits.

### Relationship to XACML 3.0 Obligations

XACML 3.0 defines an Obligations mechanism: a policy decision may include Obligations — actions the PEP must perform for the decision to stand. If the PEP cannot fulfill an Obligation, it must treat the access as denied.

This is the closest existing standard to TCR commitments. However XACML Obligations:

- Are enforced by the PEP in the same request/response cycle — there is no **temporal lifecycle** (no `due_by`, no async fulfillment)
- Have no **persistence layer**: there is no record of whether the Obligation was fulfilled hours or days later
- Have no **dispute window**: there is no concept of preserving evidence for a dispute adjudication period
- Are **not portable**: they exist as policy output within the XACML enforcement context and are not documents that travel with the transaction

TCR takes the structural intuition from XACML Obligations (unfulfilled commitment = access denied) and extends it into a persistent, portable, time-aware lifecycle artifact.

| Property | XACML Obligations | TCR |
|---|---|---|
| Timing | Same request/response cycle | Async; `due_by` deadline, monitored over time |
| Persistence | Not persisted | Persistent document with lifecycle state |
| Portability | In-process, within XACML context | Portable across trust boundaries |
| Dispute support | None | `dispute_window_end` + `evidence_refs` |
| Breach detection | PEP must deny if cannot fulfill | Auto-detects breach when `due_by` passes |

**AGF's position:** TCR is structurally analogous to XACML Obligations but fills the gap that XACML's synchronous model leaves: asynchronous commitments made in autonomous agent transactions cannot be evaluated and fulfilled within a single request/response cycle.

### The Novel Contribution of TCR

The combination of properties that TCR uniquely provides:

1. **Portable pre-signed commitment record** — created at transaction time, travels as evidence
2. **Temporal lifecycle** — commitments have `due_by` deadlines that trigger automatic breach detection
3. **Dispute-ready evidence container** — `evidence_refs` plus `dispute_window_end` ensure that dispute adjudication has the evidence it needs
4. **Denial semantic** — a breached TCR blocks a finalize/close action, not merely annotates it
5. **Explicit breach reason** — machine-readable breach cause (`breach_reason`) for audit and dispute purposes

No existing standard provides this combination. This is why TCR is retained as a first-class AGF primitive rather than replaced by PROV or XACML profiling.

---

## Use Case

A system uses TCR to record what was promised for a transaction, what evidence supports that promise, and whether the commitment is pending, fulfilled, breached, or revoked.

Typical uses:
- Record a promised approval, delivery, redaction, or audit export
- Mark whether required obligations were fulfilled by a deadline
- Preserve evidence references for later review or dispute
- Prevent a transaction from being treated as successfully closed when required commitments are unmet

---

## Normative Fields

- `context_id` (string, required) — Shared transaction correlation identifier. The same `context_id` MUST appear in the DAE, DBA, TCR, and GDR for a single agent transaction. It is the join key that allows an enforcement point or auditor to correlate all governance artifacts for a given transaction.
- `commitment_id` (string, required) — Unique identifier for this record.
- `transaction_id` (string, required) — Links to the transaction. Maps to W3C PROV `Activity` identifier.
- `issuer` (string, required) — The agent responsible for the commitments. Maps to PROV `wasAssociatedWith` agent.
- `counterparty` (string, required) — The principal on whose behalf the agent acted. Maps to PROV `actedOnBehalfOf`.
- `commitments` (non-empty array[object], required)
  - `type` (string, required)
    - Examples: `approval`, `delivery`, `redaction`, `notification`, `audit_export`
  - `target` (string, required)
  - `due_by` (RFC3339 UTC timestamp, optional) — Deadline for fulfillment. If this passes with `fulfilled=false`, the record MUST be treated as breached.
  - `fulfilled` (boolean, required)
  - `required` (boolean, required)
- `evidence_refs` (array[object], required) — References to artifacts produced by or used in the transaction. Maps to PROV `Entity` references.
  - `kind` (string, required)
    - Examples: `trace`, `log`, `receipt`, `attestation`, `snapshot`
  - `ref` (string, required)
- `status` (string enum, required)
  - `pending`
  - `fulfilled`
  - `breached`
  - `revoked`
- `breach_reason` (string, optional) — Machine-readable reason. Required when `status="breached"`.
- `dispute_window_end` (RFC3339 UTC timestamp, optional) — Evidence MUST be preserved through this timestamp.
- `audit_required` (boolean, required)

---

## Validation Rules

1. `commitments` MUST contain at least one entry.
2. If `status="breached"`, `breach_reason` MUST be present and non-empty.
3. If `status="fulfilled"`, all entries where `required=true` MUST have `fulfilled=true`.
4. If any `required=true` commitment has `due_by` in the past and `fulfilled=false`, the record MUST be treated as breached.
5. If a transaction close/finalize action is attempted while the record is `breached` or `revoked`, the result MUST be deny.
6. If `status="pending"` or `status="fulfilled"` and `dispute_window_end` is present, `evidence_refs` MUST be preserved for the duration of the dispute window.

---

## Lifecycle Semantics

Recommended lifecycle:
1. Create TCR when a transaction enters a state that carries obligations.
2. Mark commitments fulfilled as evidence arrives.
3. If any required commitment misses `due_by`, transition to `breached`.
4. If a commitment is invalidated by policy or operator action, transition to `revoked`.
5. When all required commitments are fulfilled, transition to `fulfilled`.
6. Preserve evidence through `dispute_window_end`.

---

## Passive Monitoring Pull Model

TCR lifecycle is computed **at query time** from the `due_by` timestamps and `fulfilled` flags in the commitments array. There is no daemon, cron job, or background process required. There is no event emitted when a deadline passes.

**How it works:**

When an enforcement point or monitoring system evaluates a TCR, it recomputes the lifecycle by applying the following rules against the current wall-clock time:

1. For each commitment where `required=true` and `fulfilled=false`: if `due_by` is in the past, the TCR status MUST be computed as `breached`.
2. If all commitments where `required=true` have `fulfilled=true`: the TCR status MUST be computed as `fulfilled`.
3. Otherwise the TCR status is `pending`.
4. An explicit `revoked` status MUST be honored as authoritative regardless of commitment state.

This means a TCR document stored with `status="pending"` may evaluate as `breached` at a later time without any write to the stored document. The stored `status` field reflects the last explicitly written state. The **effective status** at any point in time is the value computed from the rules above.

**Why pull, not push:**

Agent governance transactions are asynchronous and may span multiple organization boundaries, time zones, and system availability windows. A push model requiring a daemon or timer would create availability coupling between enforcement points and a monitoring system. The pull model allows any enforcement point — including offline systems and cross-org verifiers — to independently compute the authoritative lifecycle state from the document alone.

**Implementation note:**

When a system emits a breach event for external systems, it SHOULD update the stored `status` and `breach_reason` fields at that time. The stored document then reflects the computed state. The pull model remains valid regardless of whether the stored document is updated, because enforcement always recomputes.

**Known limitation — clock synchronization:** The pull model requires that all enforcement points evaluating the same TCR agree on the current time relative to `due_by` timestamps. In practice, clock skew between enforcement points in different organizations or regions can cause them to reach different lifecycle conclusions for the same TCR at the same moment. This is a known distributed systems constraint. Implementations SHOULD use NTP-synchronized UTC clocks and document their clock tolerance. A future version will define explicit clock tolerance semantics (e.g., maximum allowed skew) and a recommended practice for cross-org evaluation consistency. This is an open specification problem, not a solved one.

---

## Enforcement Semantics

For each transaction close, settlement, or accountability check:
1. Validate TCR schema.
2. Recompute lifecycle status from commitments and deadlines.
3. If the recomputed status is `breached`, emit deny with breach reason.
4. If the status is `revoked`, emit deny.
5. If the status is `fulfilled`, emit allow and retain evidence for the dispute window.
6. If the status is `pending`, emit a non-terminal lifecycle result and continue monitoring.
7. Emit audit evidence if `audit_required=true`.

---

## Reason Codes (v0.3)

- `ERR_TCR_MISSING`
- `ERR_TCR_REQUIRED_COMMITMENT_UNFULFILLED`
- `ERR_TCR_BREACH_RECORDED`
- `ERR_TCR_REVOKED`
- `ERR_TCR_DISPUTE_WINDOW_CLOSED`
- `OK_TCR_PENDING`
- `OK_TCR_FULFILLED`

---

## Evidence Expectations

A compliant implementation SHOULD be able to emit evidence containing:
- `transaction_id`
- `commitment_id`
- `decision`
- `reason_code`
- `status`
- `timestamp`
- `evidence_ref_count`

---

## Relationship To DAE and DBA

- DAE constrains delegated authority.
- DBA constrains data handling boundaries.
- TCR records whether the promised obligations of the transaction were actually met.

These primitives layer together:
- DAE authorizes the actor.
- DBA constrains the data.
- TCR proves whether the transaction obligations were satisfied.

---

## Example Evaluation

Given a TCR with:
- One required `approval` commitment, `fulfilled=true`
- One required `audit_export` commitment, `fulfilled=false`
- `audit_export.due_by` in the past
- `status="pending"` in the stored record

At evaluation time, the recomputed lifecycle MUST become `breached`, and a finalize/close action MUST be denied with `ERR_TCR_REQUIRED_COMMITMENT_UNFULFILLED` (or `ERR_TCR_BREACH_RECORDED` if the implementation records the breach first and then re-evaluates).

---

## Conformance Hooks

A system claiming TCR support MUST pass at least:
- Required commitment breach denial with evidence
- Fulfilled commitment allow with evidence
- Revoked record denial with evidence
- Evidence preservation across an open dispute window

---

## Version History

| Version | Changes |
|---|---|
| 0.3.0 | Added Passive Monitoring Pull Model section. Lifecycle is computed at query time from `due_by` timestamps; no daemon or push mechanism required. Documents effective vs stored status distinction. Explains why pull model is correct for cross-boundary async agent governance. |
| 0.2.0 | Added Standards Alignment section. Explicit W3C PROV field mapping (Activity/Agent/Entity). Explicit XACML 3.0 Obligations comparison (synchronous vs async lifecycle). Documented novel contribution: temporal lifecycle + dispute-ready evidence container + denial semantic. No field changes — alignment is additive documentation. |
| 0.1.0 | Initial draft. |
