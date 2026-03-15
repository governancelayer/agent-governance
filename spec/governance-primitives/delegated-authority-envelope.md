# Delegated Authority Envelope (DAE) v0.3

Status: Draft
Version: 0.3.0
Date: 2026-03-14
Supersedes: 0.2.0

## Purpose

DAE defines a machine-readable delegation object that constrains what a delegate agent may do on behalf of a principal.

DAE is a **portable pre-signed delegation contract** that borrows vocabulary from GNAP (Grant Negotiation and Authorization Protocol, RFC 9635) where GNAP provides coverage and defines AGF-specific extensions where GNAP's scope ends. DAE is architecturally distinct from GNAP: GNAP is a negotiation protocol requiring server connectivity at enforcement time; DAE is an offline-verifiable document that travels across trust boundaries without contacting an authorization server.

## Standards Alignment

### Relationship to GNAP (RFC 9635)

GNAP (RFC 9635) defines a protocol for grant negotiation between clients, authorization servers, and resource servers. GNAP's grant request and access token model provides field-level vocabulary alignment for 70-80% of what DAE requires.

**Fields derived from GNAP vocabulary:**

| DAE Field | GNAP Equivalent | Notes |
|---|---|---|
| `delegation_id` | GNAP access token identifier | GNAP issues token IDs server-side; DAE makes the identifier portable and pre-signed |
| `delegate` | GNAP `client.key` or client instance | The agent acting under delegation |
| `allowed_actions` | GNAP `access` array (access rights) | GNAP `access` can contain type/actions strings; DAE makes this explicit and machine-enforceable |
| `expiry` | GNAP access token `expires_in` / `expires_at` | GNAP uses TTL from server; DAE uses an absolute RFC3339 timestamp for portable offline evaluation |
| `revocable` / `revoked` | GNAP token management API (revocation via POST) | GNAP defines revocation as a server API call; DAE carries revocation state inline for enforcement without a server round-trip |

**AGF extensions — not present in GNAP:**

| DAE Field | Reason Not in GNAP | AGF Rationale |
|---|---|---|
| `principal` | GNAP identifies the resource owner implicitly via the grant request flow; no explicit delegation chain field | Agent governance requires an explicit traceable delegation chain from human principal to acting agent |
| `constraints.max_value` | Out of GNAP scope; GNAP does not constrain transaction amounts | Machine-readable numeric budget constraint is required for autonomous purchasing agents; free-text instructions cannot be programmatically enforced |
| `audit_required` | Not in GNAP | Compliance requirement to flag which delegations require audit trail emission |

### Why DAE is not replaced by GNAP directly

GNAP is a **negotiation protocol**: a client requests a grant from a server, the server issues a token, and the token grants access. The protocol assumes connectivity to an authorization server at enforcement time.

DAE is a **portable pre-signed contract**: it is created once, travels with the agent through trust boundaries, and is evaluated deterministically at any enforcement point — including offline. The enforcement point evaluates the DAE document directly; no server round-trip is required.

This is the structural difference. DAE borrows GNAP's vocabulary for field semantics but is not a GNAP profile and does not require a GNAP authorization server at enforcement time.

**AGF's position:** Where GNAP vocabulary covers a concept, DAE uses it. Where GNAP's model ends (delegation chain identity, numeric constraints, portable inline revocation state), DAE extends. DAE is to GNAP what a W3C Verifiable Credential is to OpenID Connect: same vocabulary and trust anchors, architecturally distinct artifact model.

---

## GNAP + DAE Issuance Pattern

GNAP and DAE are designed to work together in enterprise environments that already have GNAP or OAuth authorization infrastructure. GNAP serves as the negotiation protocol that obtains human or enterprise authorization; DAE is the portable artifact created from that authorization.

**Sequence:**

1. An AI agent requests delegation authority from an AGF issuance layer
2. The issuance layer constructs a GNAP grant request covering the required actions
3. The GNAP authorization server (e.g., an enterprise OAuth AS, CFO approval portal) evaluates the request — this may trigger a human approval workflow
4. On grant issuance, the AGF issuance layer creates a DAE document from the GNAP grant, adding AGF extensions: `principal`, `constraints.max_value`, `constraints.currency`, `audit_required`
5. The DAE is signed (Ed25519) and returned to the agent
6. The agent carries the signed DAE across trust boundaries
7. Receiving enforcement points (e.g., Company B's agentgateway) verify the DAE signature offline — no call to Company A's authorization server

**What GNAP handles:** Grant negotiation, human authorization, access rights scoping, token issuance by an already-trusted AS.

**What DAE adds:** Portable signed artifact with explicit delegation chain (`principal` → `delegate`), machine-enforceable numeric constraints (`max_value` + `currency`), offline-verifiable revocation state, and cross-org transferability without server connectivity.

This pattern enables organizations to reuse existing GNAP/OAuth infrastructure for the authorization decision while gaining the cross-boundary portability that GNAP tokens alone do not provide.

---

## Normative Fields

- `context_id` (string, required) — Shared transaction correlation identifier. The same `context_id` MUST appear in the DAE, DBA, TCR, and GDR for a single agent transaction. It is the join key that allows an enforcement point or auditor to correlate all governance artifacts for a given transaction without relying on type-specific identifiers.
- `delegation_id` (string, required) — Unique identifier for this delegation. Maps to GNAP token identifier semantics.
- `principal` (string, required) — Identity of the human or system delegating authority. AGF extension: makes the delegation chain explicit.
- `delegate` (string, required) — Identity of the agent receiving authority. Maps to GNAP client identity.
- `allowed_actions` (non-empty array[string], required) — The actions this delegation permits. Maps to GNAP `access` rights array.
- `constraints` (object, required)
  - `max_value` (number, optional) — Maximum transaction value. AGF extension: machine-enforceable numeric budget. Required for autonomous commerce agents.
  - `currency` (string, optional) — ISO 4217 currency code (e.g., `"USD"`, `"EUR"`, `"GBP"`). REQUIRED when `max_value` is present. Defines the denomination for `max_value` enforcement. Without an explicit currency, cross-currency enforcement is undefined.
  - `jurisdiction` (string, optional) — Jurisdictional constraint on where the delegated action may execute.
- `expiry` (RFC3339 UTC timestamp, required) — Absolute expiry time. Derived from GNAP token expiry semantics; expressed as absolute timestamp for offline portability.
- `revocable` (boolean, required) — Whether this delegation can be revoked before expiry. AGF extension to GNAP inline revocation state.
- `revoked` (boolean, required) — Current revocation state. If `true`, all enforcement points MUST deny immediately without contacting a server.
- `audit_required` (boolean, required) — Whether this delegation requires audit evidence emission. AGF extension.
- `issuance_mode` (string enum, required) — How this DAE was issued. One of: `human_approved`, `policy_automated`, `system_direct`. Makes the assurance level of the delegation machine-readable and auditable. Enforcement points MAY reject DAEs where `issuance_mode` does not meet the relying party's assurance requirements for the requested action.

---

## Validation Rules

1. `allowed_actions` must contain unique action names.
2. `expiry` must be a valid RFC3339 timestamp with UTC offset (`Z` or explicit offset).
3. If `revoked=true`, authorization result MUST be deny (`ERR_DAE_REVOKED`).
4. If current time is greater than `expiry`, authorization result MUST be deny (`ERR_DAE_EXPIRED`).
5. If transaction action is not in `allowed_actions`, authorization result MUST be deny (`ERR_DAE_ACTION_NOT_ALLOWED`).
6. If `constraints.max_value` exists and transaction amount exceeds it, authorization result MUST be deny (`ERR_DAE_MAX_VALUE_EXCEEDED`).
7. If `constraints.max_value` exists, `constraints.currency` MUST also be present. If absent, authorization result MUST be deny (`ERR_DAE_CURRENCY_MISSING`).
8. If `constraints.currency` is not a valid ISO 4217 code, authorization result MUST be deny (`ERR_DAE_CURRENCY_INVALID`).

---

## Enforcement Semantics

For each delegated transaction:
1. Validate DAE schema.
2. Validate delegation state (`revoked`, `expiry`).
3. Validate action authorization.
4. Validate numeric and contextual constraints.
5. Emit decision (`allow` or `deny`) with normalized reason code.
6. Emit audit evidence if `audit_required=true`.

---

## Reason Codes (v0.3)

- `ERR_DAE_REVOKED`
- `ERR_DAE_EXPIRED`
- `ERR_DAE_ACTION_NOT_ALLOWED`
- `ERR_DAE_MAX_VALUE_EXCEEDED`
- `ERR_DAE_CURRENCY_MISSING`
- `ERR_DAE_CURRENCY_INVALID`
- `ERR_DAE_MISSING`
- `OK_DAE_ALLOWED`

---

## Revocation Model

Revocation is carried inline via `revoked=true`. This diverges from GNAP's server-side revocation API.

**Rationale:** GNAP revocation requires a POST to the authorization server's token management endpoint. In agent governance scenarios, enforcement points may operate across trust or network boundaries where server connectivity is not guaranteed. Inline revocation state allows deterministic enforcement at any point in the chain.

**Known limitation — revocation distribution:** The current model requires that the party issuing the revocation (Company A) delivers the updated `revoked=true` document to all enforcement points that may receive the DAE (including Company B). This is a real operational problem: if Company A cannot reach Company B's enforcement point, revocation is not guaranteed. The v0.1 mitigation is short-lived DAEs (aggressive `expiry`) and periodic sync. A more robust solution — CRL-style revocation lists or a revocation event distribution protocol — is planned for a future release. This is an open problem in the specification, not a solved one.

A future version will add a `revocation_timestamp` and `revocation_authority` field to enable cryptographic verification of the revocation event, alongside a revocation distribution model.

---

## Conformance Hooks

A system claiming DAE support MUST pass at least:
- Constraint breach denial + audit evidence (`ERR_DAE_MAX_VALUE_EXCEEDED`)
- Expired delegation denial + audit evidence (`ERR_DAE_EXPIRED`)
- Revoked delegation denial + audit evidence (`ERR_DAE_REVOKED`)
- Action not in allowed set denial (`ERR_DAE_ACTION_NOT_ALLOWED`)

---

## Version History

| Version | Changes |
|---|---|
| 0.3.0 | Added GNAP+DAE Issuance Pattern section. Clarified DAE is architecturally distinct from GNAP (not a GNAP profile). Added `constraints.currency` (ISO 4217, required when `max_value` present). Added `ERR_DAE_CURRENCY_MISSING` and `ERR_DAE_CURRENCY_INVALID` reason codes. Added currency validation rules 7-8. |
| 0.2.0 | Added Standards Alignment section. Explicit GNAP (RFC 9635) field mapping. Documented AGF extensions (principal, max_value, audit_required, inline revocation) and rationale. No field changes — alignment is additive documentation. |
| 0.1.0 | Initial draft. |
