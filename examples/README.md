# Examples

This directory contains example payloads for each governance primitive. Each example is a valid JSON document that conforms to the corresponding schema in [`spec/`](../spec/).

## DAE: Delegated Authority Envelope

These examples show a procurement delegation where `OrgA.AgentA` (the principal) delegates authority to `OrgA.AgentB` (the delegate) to create purchase orders up to 10,000 in the EU.

| File | Outcome | Why |
|------|---------|-----|
| [`a2a/delegation-allowed.json`](a2a/delegation-allowed.json) | Allowed | Delegation is valid, not expired, and not revoked |
| [`a2a/delegation-expired.json`](a2a/delegation-expired.json) | Denied | Delegation expired on 2024-01-01 |
| [`a2a/delegation-revoked.json`](a2a/delegation-revoked.json) | Denied | Delegation was explicitly revoked |

All three share the same structure. The differences are in `expiry` and `revoked`, which illustrate how a single delegation can transition from valid to denied through time or explicit revocation.

## DBA: Data Boundary Assertion

These examples show data governance decisions issued by `OrgA.GovernanceService`. Both assert that data must stay within the EU, require field redaction, and prohibit egress.

| File | Outcome | Why |
|------|---------|-----|
| [`dba/transfer-allowed.json`](dba/transfer-allowed.json) | Allowed | Data may be used for inference and audit export within boundary constraints |
| [`dba/egress-blocked.json`](dba/egress-blocked.json) | Blocked | Data may only be stored; egress is denied; additional fields must be redacted |

Key fields to compare:

- `permitted_operations`: `["infer", "audit_export"]` vs. `["store"]` -- the blocked case restricts what can be done with the data
- `redaction_required`: both require `customer_email` redaction; the blocked case additionally requires `account_number` redaction
- `max_retention_hours`: 24 hours vs. 12 hours -- the blocked case has a tighter retention window

## TCR: Transaction Commitment Record

These examples show transaction-level accountability for actions between `OrgA.AgentA` and `OrgB.ServiceB`.

| File | Outcome | Why |
|------|---------|-----|
| [`tcr/fulfilled.json`](tcr/fulfilled.json) | Fulfilled | Both required commitments (approval + audit export) are fulfilled |
| [`tcr/breached.json`](tcr/breached.json) | Breached | Approval was fulfilled, but the required audit export was not completed before `due_by` |

Key fields to compare:

- `commitments[].fulfilled`: both commitments are `true` in the fulfilled case; in the breached case, the audit export remains `false`
- `status`: `"fulfilled"` vs. `"breached"`
- `breach_reason`: only present in the breached case, explaining why the transaction is in breach
- `evidence_refs`: the fulfilled case has both a trace and a receipt; the breached case has only a trace (the missing receipt corresponds to the unfulfilled commitment)

## How These Relate

In a real governed transaction, all three primitives work together:

1. **DAE** determines whether the agent is authorized to act
2. **DBA** determines whether the data handling is within bounds
3. **TCR** tracks whether the required obligations were fulfilled after the action

A transaction can be denied at any layer. A valid delegation (DAE) does not override a data boundary violation (DBA). A successful action does not close the transaction if required commitments (TCR) remain unfulfilled.
