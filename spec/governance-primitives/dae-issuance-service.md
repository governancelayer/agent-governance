# DAE Issuance Service v0.1

Status: Draft
Version: 0.1.0
Date: 2026-03-15

## Purpose

The DAE Issuance Service is the mechanism by which signed Delegated Authority Envelopes (DAEs) are created and issued to agents. It accepts structured delegation requests from principals (humans or systems), validates the requested scope, optionally triggers a human approval workflow, signs the resulting DAE with the organization's Ed25519 private key, and returns the signed artifact.

The Issuance Service is not a negotiation protocol. It is a REST API. It handles one delegation request at a time and returns one signed DAE.

---

## Design Principles

**No protocol requirement.** The Issuance Service does not require GNAP, OAuth, or any specific authorization protocol. It works with whatever authentication and authorization mechanisms the deploying organization already has.

**GNAP and OAuth 2.0 are integration profiles.** Organizations with existing GNAP Authorization Servers or OAuth 2.0 AS can configure the Issuance Service to route authorization decisions through their AS.

**`issuance_mode` makes assurance level explicit.** A DAE issued after explicit human approval carries materially stronger assurance than one issued automatically by a policy engine. To make this difference machine-readable and auditable, every issued DAE carries an `issuance_mode` field:

| `issuance_mode` value | Meaning |
|---|---|
| `human_approved` | A human explicitly reviewed and approved this delegation |
| `policy_automated` | Issued automatically because the request satisfied a pre-configured policy rule; no human was in the loop |
| `system_direct` | Issued directly by an authenticated principal with no additional approval step |

Enforcement points and auditors SHOULD use `issuance_mode` to apply appropriate trust levels. A relying party that requires human approval for high-value delegations SHOULD reject DAEs where `issuance_mode != "human_approved"` for those action types.

**Human approval is optional and configurable.** The Issuance Service can require human approval for all delegations, for delegations above a value threshold, for delegations involving specific action types, or for none. The approval mechanism (email, portal, Slack, etc.) is not specified — it is a deployment configuration.

---

## Issuance Paths

### Path A: Direct Issuance

The principal (or an orchestrator acting on behalf of the principal) sends a delegation request directly to the Issuance Service API. The service authenticates the caller, validates the scope, and issues the DAE.

```
Principal → [AGF Issuance Service API] → Signed DAE
```

Suitable for: any organization, any technology stack, any authorization model.

### Path B: GNAP Integration Profile

For organizations with an existing GNAP (RFC 9635) or OAuth 2.0 Authorization Server, the Issuance Service acts as a client of that AS. It constructs the grant request, submits it to the AS (which may trigger a human approval workflow), receives the grant, converts it to a DAE with AGF extensions, and returns the signed DAE.

```
Principal → [AGF Issuance Service] → [GNAP / OAuth AS] → [DAE created from grant] → Signed DAE
```

The AGF extensions added beyond the GNAP grant:
- `principal` — explicit delegation chain identity (not derivable from GNAP grant alone)
- `constraints.max_value` — machine-enforceable numeric budget
- `constraints.currency` — ISO 4217 currency denomination
- `audit_required` — compliance audit flag

---

## API

### POST /delegations

Create a new delegation and receive a signed DAE.

**Request body:**

```json
{
  "principal": "did:key:z6Mk...CFO-Alice",
  "delegate": "did:key:z6Mk...procurement-agent-7f",
  "allowed_actions": ["purchase_order:create", "quote:request"],
  "constraints": {
    "max_value": 900.00,
    "currency": "EUR",
    "jurisdiction": "EU"
  },
  "expiry": "2026-04-15T00:00:00Z",
  "revocable": true,
  "audit_required": true,
  "approval_context": {
    "reason": "Q2 office supplies procurement — standard budget",
    "urgency": "normal"
  }
}
```

**Response (200 OK — synchronous approval or no approval required):**

```json
{
  "status": "issued",
  "dae": {
    "delegation_id": "dae-2026-0042",
    "principal": "did:key:z6Mk...CFO-Alice",
    "delegate": "did:key:z6Mk...procurement-agent-7f",
    "allowed_actions": ["purchase_order:create", "quote:request"],
    "constraints": {
      "max_value": 900.00,
      "currency": "EUR",
      "jurisdiction": "EU"
    },
    "expiry": "2026-04-15T00:00:00Z",
    "revocable": true,
    "revoked": false,
    "audit_required": true,
    "issuance_mode": "human_approved"
  },
  "signature": "eyJhbGciOiJFZERTQSJ9...",
  "issued_at": "2026-03-15T09:00:00Z",
  "issued_by": "did:key:z6Mk...company-a-issuance-service"
}
```

**Response (202 Accepted — pending human approval):**

```json
{
  "status": "pending_approval",
  "delegation_id": "dae-2026-0043",
  "approval_url": "https://governance.company-a.com/approvals/dae-2026-0043",
  "poll_url": "/delegations/dae-2026-0043/status",
  "estimated_approval_sla": "PT4H"
}
```

**Response (400 Bad Request — scope exceeds policy):**

```json
{
  "status": "rejected",
  "reason": "ERR_SCOPE_EXCEEDS_POLICY",
  "detail": "max_value 900 EUR exceeds principal spend limit of 500 EUR for purchase_order:create"
}
```

---

### GET /delegations/{delegation_id}

Retrieve an issued DAE by ID, including current revocation state.

**Response:**

```json
{
  "delegation_id": "dae-2026-0042",
  "status": "active",
  "dae": { ... },
  "signature": "eyJhbGciOiJFZERTQSJ9...",
  "issued_at": "2026-03-15T09:00:00Z"
}
```

---

### DELETE /delegations/{delegation_id}

Revoke a delegation before its expiry.

**Response (200 OK):**

```json
{
  "delegation_id": "dae-2026-0042",
  "status": "revoked",
  "revoked_at": "2026-03-15T14:30:00Z",
  "revoked_by": "did:key:z6Mk...CFO-Alice"
}
```

After revocation, any enforcement point evaluating a cached copy of this DAE will still see `revoked: false` until it re-fetches or the revocation propagates. This is a known trade-off of the offline model. For high-stakes delegations, `revocable: true` signals that enforcement points SHOULD poll for revocation status on sensitive actions.

---

### GET /delegations/{delegation_id}/status

Poll for approval status (used when initial POST returned 202).

**Response (still pending):**

```json
{
  "delegation_id": "dae-2026-0043",
  "status": "pending_approval",
  "submitted_at": "2026-03-15T09:00:00Z"
}
```

**Response (approved):**

```json
{
  "delegation_id": "dae-2026-0043",
  "status": "issued",
  "dae": { ... },
  "signature": "eyJhbGciOiJFZERTQSJ9..."
}
```

**Response (rejected by approver):**

```json
{
  "delegation_id": "dae-2026-0043",
  "status": "rejected",
  "reason": "ERR_APPROVAL_DENIED",
  "detail": "Approver: outside Q2 procurement window"
}
```

---

## Validation Rules (Issuance Time)

1. `principal` MUST be authenticated by the caller's identity before the request is accepted.
2. `delegate` MUST be a known agent identity within the organization's identity registry, OR the issuance service MUST be configured to accept external delegate identities.
3. `allowed_actions` MUST be a subset of the actions the principal is permitted to delegate under organizational policy.
4. If `constraints.max_value` is present, `constraints.currency` MUST also be present (ISO 4217).
5. `expiry` MUST be in the future at issuance time.
6. If `max_value` exceeds the configured per-principal spend authorization threshold, the request MUST route to human approval.

---

## Relationship to GNAP (RFC 9635)

GNAP is not required and is not the default. The Issuance Service API above is simpler than GNAP because the DAE use case is simpler:

| GNAP feature | DAE Issuance Service | Reason |
|---|---|---|
| Grant request negotiation (multi-step continuation) | Not needed | Delegation is a single decision: approve or reject |
| AS discovery via metadata | Not needed | Issuance Service URL is configured, not discovered |
| Token management API | Not needed | DAE carries inline revocation state; `DELETE /delegations/{id}` is sufficient |
| Multiple token formats | Not needed | DAE is the only output format |

When a GNAP integration profile is configured, the Issuance Service implements the GNAP client role and the AS handles the authorization decision. The service converts the GNAP grant into a DAE by:
1. Mapping GNAP `access` rights → DAE `allowed_actions`
2. Mapping GNAP grant subject → DAE `delegate`
3. Mapping GNAP grant expiry → DAE `expiry`
4. Adding AGF extensions: `principal`, `constraints.max_value`, `constraints.currency`, `audit_required`

---

## Conformance Hooks

An implementation claiming DAE Issuance Service conformance MUST:
- Issue a valid DAE for a well-formed delegation request from an authenticated principal
- Return 400 (scope exceeds policy) for requests that violate configured policy
- Support revocation via DELETE
- Return a DAE with `revoked: true` after revocation is applied
- Validate `currency` is present when `max_value` is present

---

## Version History

| Version | Changes |
|---|---|
| 0.1.0 | Initial draft. Direct issuance path + GNAP integration profile. Core CRUD API. Approval flow (sync and async). Validation rules. |
