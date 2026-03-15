# AGF vs GNAP

**TL;DR:** GNAP is the authorization negotiation protocol. DAE is the portable governance artifact created from that authorization. They are designed to work together, not compete.

---

## What GNAP Is

GNAP (Grant Negotiation and Authorization Protocol, RFC 9635) is an IETF standard for delegated authorization. A client requests a grant from an authorization server (AS), the AS issues a token, and the token grants the client access to resources.

GNAP provides:
- A protocol for structured grant requests (typed access rights, not freeform scopes)
- Multi-step authorization flows including human-in-the-loop approval
- A defined key model for client and subject identities
- A token management API including revocation via server call

GNAP is a server-connected protocol. Enforcement requires a live authorization server or requires the resource server to call the AS to verify the token.

---

## What DAE Is

DAE (Delegated Authority Envelope) is an AGF governance primitive — a portable pre-signed delegation contract. It borrows vocabulary from GNAP where GNAP provides coverage, and adds AGF-specific extensions where GNAP's scope ends.

DAE provides:
- A portable signed document that travels with the agent across trust boundaries
- Offline-verifiable delegation state: no AS connectivity required at enforcement time
- Explicit delegation chain: `principal` → `delegate` (not derivable from GNAP alone)
- Machine-enforceable numeric constraints: `max_value` + `currency` (not in GNAP)
- Inline revocation state: `revoked=true` is verifiable without calling the AS
- Cross-org verifiability: Company B can verify Company A's delegation without access to Company A's systems

---

## Where They Overlap

DAE borrows GNAP vocabulary for the following fields:

| DAE Field | GNAP Equivalent | What DAE Adds |
|---|---|---|
| `delegation_id` | Access token identifier | Portable pre-signed identifier, not server-issued |
| `delegate` | `client.key` / client instance | Same concept |
| `allowed_actions[]` | GNAP `access` rights array | Made explicit and machine-enforceable |
| `expiry` | Token `expires_in` / `expires_at` | Absolute RFC3339 timestamp (not TTL) for offline evaluation |
| `revocable` / `revoked` | GNAP token management API (server-side) | Carried inline for enforcement without server round-trip |

---

## The Structural Difference

GNAP requires server connectivity. DAE does not.

When an agent carries a GNAP token to Company B, Company B must either trust the token opaquely or call Company A's AS to verify it. Neither works across untrusted boundaries.

When an agent carries a DAE, Company B verifies the Ed25519 signature against Company A's public key — no call to Company A required. The delegation chain, constraints, and revocation state are all in the document.

This is the same architectural distinction as OAuth opaque tokens vs JWTs: same authorization decision, different portability model. DAE extends this further by adding governance-specific fields (delegation chain, numeric constraints, audit flags) that neither GNAP tokens nor JWTs carry.

---

## The Issuance Pattern: GNAP + DAE Working Together

In enterprise deployments, GNAP and DAE are not alternatives — they are complementary:

1. An AI agent requests delegation from an AGF issuance layer
2. The issuance layer constructs a GNAP grant request for the required actions
3. The GNAP AS (e.g., enterprise OAuth portal, CFO approval system) evaluates the grant request — this may involve human approval
4. On grant issuance, the AGF layer creates a DAE from the GNAP grant, adding: `principal`, `constraints.max_value`, `constraints.currency`, `audit_required`
5. The DAE is signed and returned to the agent
6. The agent carries the signed DAE across trust boundaries
7. External enforcement points verify the DAE offline — no call to the originating AS

**GNAP handles:** Grant negotiation, human approval, enterprise authorization infrastructure.
**DAE provides:** Portable signed artifact usable across organizational boundaries without server connectivity.

Organizations can reuse existing GNAP/OAuth authorization servers and gain cross-boundary portability through DAE.

---

## Summary

| Property | GNAP | DAE |
|---|---|---|
| Type | Negotiation protocol | Portable governance document |
| Server at enforcement time | Required | Not required |
| Cross-org verifiability | Requires trust or AS call | Offline, signature-based |
| Delegation chain | Implicit in grant flow | Explicit `principal` → `delegate` field |
| Numeric budget constraints | Not in scope | `max_value` + `currency` |
| Inline revocation | Server-side API | `revoked=true` carried in document |
| Relationship | Authorization negotiation layer | Governance contract layer |

AGF DAE does not replace GNAP. It provides the portable governance artifact that GNAP-based enterprise authorization produces.

→ [DAE Specification](../../spec/governance-primitives/delegated-authority-envelope.md)
→ [DAE Schema v0.3](../../spec/dae-schema-v0.3.json)
→ [GNAP RFC 9635](https://www.rfc-editor.org/rfc/rfc9635)
