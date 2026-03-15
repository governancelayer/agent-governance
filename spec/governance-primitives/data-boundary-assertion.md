# Data Boundary Assertion (DBA) v0.2

Status: Draft
Version: 0.2.0
Date: 2026-03-14
Supersedes: 0.1.0

## Purpose

DBA defines a machine-readable boundary contract for how data in a transaction may be processed, transferred, retained, and redacted.

DBA is **architecturally distinct from runtime authorization APIs** (such as AuthZEN or OPA). It is a portable pre-signed assertion — a document, not an API call. DBA is created at delegation time, travels with the transaction across trust boundaries, and is evaluated deterministically at any enforcement point without a server round-trip.

---

## Standards Alignment

### Relationship to AuthZEN (OpenID Foundation)

AuthZEN defines a standardized request/response API between a Policy Enforcement Point (PEP) and a Policy Decision Point (PDP). The PEP sends a context object — including `subject`, `resource`, `action`, and environmental context — and receives an authorization decision.

**Partial field overlap:**

| DBA Field | AuthZEN Equivalent | Notes |
|---|---|---|
| `subject_id` / `subject_type` | AuthZEN `resource` object | The data artifact being governed |
| `permitted_operations` | AuthZEN `action` type | What may be done to the resource |
| `boundary_constraints.allowed_regions` | AuthZEN environmental context | Regions can be passed as context in AuthZEN; not a first-class field |

**Where DBA diverges structurally from AuthZEN:**

AuthZEN is a **request/response API**. To make an authorization decision, the enforcement point calls the PDP. This requires:
- A reachable PDP endpoint at enforcement time
- A live network connection
- A policy engine holding the policy

DBA is a **portable signed contract**. It:
- Travels with the transaction as a document
- Is evaluated by any enforcement point directly
- Works across network boundaries, offline, and in asynchronous workflows
- Carries the policy constraints as data — not as a policy engine

The structural consequence is that DBA and AuthZEN solve different parts of the same problem. AuthZEN answers "call this endpoint to get a decision." DBA answers "this document contains the pre-authorized terms — evaluate them here."

**AGF's position:** DBA does not replace AuthZEN. Where a system has a live PDP, AuthZEN is a better choice for real-time decisions. DBA is the right model when:
- The contract must cross organizational boundaries as a portable artifact
- The enforcement point may not have connectivity to a central PDP
- The data governance terms must be attached to an audit trail as evidence
- The contract must be verifiable by a third party without access to the originating system

### Relationship to OPA / Rego

OPA (Open Policy Agent) can evaluate every DBA constraint as Rego policy. DBA's region restrictions, egress controls, retention limits, and redaction requirements can all be expressed as Rego rules.

The architectural difference is the same as with AuthZEN: OPA is a **runtime policy engine**; DBA is a **portable document**.

| Property | DBA | OPA/Rego |
|---|---|---|
| Evaluated where | Any enforcement point with the document | Requires OPA instance |
| Portability | Document travels with transaction | Policy is centrally stored in OPA |
| Audit evidence | Inline with the contract | Separate decision log |
| Third-party verification | Document is self-contained | Requires access to OPA and policy bundle |

**AGF's position:** DBA and OPA are complementary. A reference implementation of DBA evaluation can be written as a Rego policy bundle. The DBA document is the governance artifact; OPA is one possible evaluation runtime for it.

### Relationship to GDPR / Data Residency Regulations

DBA's `allowed_regions`, `max_retention_hours`, and `redaction_required` fields directly encode data governance obligations that arise from GDPR, data residency laws, and data processing agreements.

DBA does not replace legal compliance review. It provides a machine-readable format to express data governance terms so they can be evaluated programmatically at the enforcement point rather than deferred to human review.

---

## Use Case

A system uses DBA to decide whether a request, response, prompt, tool payload, or evidence artifact may cross a trust boundary under specific constraints.

Typical uses:
- Restrict cross-org data egress
- Restrict processing to approved jurisdictions
- Enforce redaction before export
- Limit requested retention duration
- Attach data governance terms to a transaction audit trail

---

## Normative Fields

- `context_id` (string, required) — Shared transaction correlation identifier. The same `context_id` MUST appear in the DAE, DBA, TCR, and GDR for a single agent transaction. It is the join key that allows an enforcement point or auditor to correlate all governance artifacts for a given transaction.
- `assertion_id` (string, required) — Unique identifier for this assertion.
- `issuer` (string, required) — Identity of the party issuing the data governance terms.
- `subject_id` (string, required) — Identifier of the data artifact being governed.
- `subject_type` (string, required)
  - Examples: `request`, `response`, `prompt`, `completion`, `artifact`
- `data_classes` (non-empty array[string], required)
  - Examples: `pii`, `financial`, `confidential`, `customer_content`
  - **v0.1 limitation:** `data_classes` values are currently free-form strings with no enforced vocabulary. Two implementations may use different strings for the same class (e.g., `pii` vs `personal_data`). This limits interoperability between organizations. v0.2 will align `data_classes` with a reference vocabulary (NIST SP 800-188 / NIST Privacy Framework). See [ROADMAP.md](../../ROADMAP.md).
- `permitted_operations` (non-empty array[string], required)
  - Examples: `store`, `transform`, `infer`, `forward`, `audit_export`
- `boundary_constraints` (object, required)
  - `allowed_regions` (array[string], optional) — ISO 3166-1 alpha-2 country codes or named regions (e.g., `EU`, `US-EAST`). **v0.1 limitation:** Named regions like `EU` or `US-EAST` are not standardized — two implementations may define their boundaries differently. v0.2 will define a normative region taxonomy. Until then, implementations SHOULD document their region resolution rules explicitly.
  - `max_retention_hours` (integer >= 1, optional)
  - `redaction_required` (array[string], optional) — Field names that must be redacted before the data may leave this boundary. **v0.1 limitation:** Field names are raw strings with no schema reference — enforcement requires the enforcement point to know the structure of the payload. A future version will support schema-referenced field paths (e.g., JSON Pointer or JSONPath).
  - `egress_allowed` (boolean, required) — Whether the data may cross an organizational boundary at all.
- `audit_required` (boolean, required)

---

## Validation Rules

1. `data_classes` MUST contain unique values.
2. `permitted_operations` MUST contain unique values.
3. If transaction `operation` is not present in `permitted_operations`, the result MUST be deny (`ERR_DBA_OPERATION_NOT_ALLOWED`).
4. If `boundary_constraints.allowed_regions` exists and transaction `region` is not in that set, the result MUST be deny (`ERR_DBA_REGION_NOT_ALLOWED`).
5. If `boundary_constraints.max_retention_hours` exists and transaction `requested_retention_hours` exceeds it, the result MUST be deny (`ERR_DBA_RETENTION_EXCEEDED`).
6. If `boundary_constraints.egress_allowed=false` and transaction `cross_org_transfer=true`, the result MUST be deny (`ERR_DBA_EGRESS_BLOCKED`).
7. If `boundary_constraints.redaction_required` contains field names and any of those names are still present in transaction `visible_fields`, the result MUST be deny (`ERR_DBA_REDACTION_REQUIRED`).

---

## Enforcement Semantics

For each data-bearing transaction:
1. Validate DBA schema.
2. Determine the `subject_type` and the attempted `operation`.
3. Evaluate region restrictions.
4. Evaluate retention request against the maximum allowed duration.
5. Evaluate egress permission across trust boundaries.
6. Evaluate required redaction against currently visible fields.
7. Emit decision (`allow` or `deny`) with a normalized reason code.
8. Emit audit evidence if `audit_required=true`.

---

## Reason Codes (v0.2)

- `ERR_DBA_MISSING`
- `ERR_DBA_OPERATION_NOT_ALLOWED`
- `ERR_DBA_REGION_NOT_ALLOWED`
- `ERR_DBA_RETENTION_EXCEEDED`
- `ERR_DBA_EGRESS_BLOCKED`
- `ERR_DBA_REDACTION_REQUIRED`
- `OK_DBA_ALLOWED`

---

## Evidence Expectations

A compliant implementation SHOULD be able to emit evidence containing:
- `transaction_id`
- `assertion_id`
- `subject_id`
- `decision`
- `reason_code`
- `timestamp`
- `evaluated_region`
- `evaluated_operation`

---

## Relationship To DAE

DAE answers "who may do what."
DBA answers "what may happen to the data involved."

Both may be required for the same transaction:
- DAE can allow a delegated action.
- DBA can still deny the same transaction if the resulting data movement violates boundary policy.

---

## Example Evaluation

Given:
- `permitted_operations=["infer","audit_export"]`
- `allowed_regions=["EU"]`
- `max_retention_hours=24`
- `redaction_required=["customer_email"]`
- `egress_allowed=false`

And a transaction:
- `operation="audit_export"`
- `region="US"`
- `requested_retention_hours=72`
- `cross_org_transfer=true`
- `visible_fields=["customer_email","order_id"]`

The decision MUST be deny. Multiple violations exist, but implementations SHOULD return the highest-priority deterministic reason code. Recommended priority order:
1. `ERR_DBA_EGRESS_BLOCKED`
2. `ERR_DBA_REGION_NOT_ALLOWED`
3. `ERR_DBA_REDACTION_REQUIRED`
4. `ERR_DBA_RETENTION_EXCEEDED`
5. `ERR_DBA_OPERATION_NOT_ALLOWED`

---

## Conformance Hooks

A system claiming DBA support MUST pass at least:
- Cross-org egress denial with evidence
- Region restriction denial with evidence
- Retention limit denial with evidence
- Redaction-required denial with evidence
- Fully compliant transfer allow with evidence

---

## Version History

| Version | Changes |
|---|---|
| 0.2.0 | Added Standards Alignment section. Explicit comparison with AuthZEN (portable contract vs request/response API), OPA/Rego (document vs runtime engine), and data residency regulations. No field changes — alignment is additive documentation. |
| 0.1.0 | Initial draft. |
