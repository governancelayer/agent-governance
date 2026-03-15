# AGF Evaluation: Does AGF Add Value for the TACP Mandate-Exceeded Scenario?

**Test Version:** 1.0.0
**Date:** 2026-03-12
**AGF Sources:** `spec/governance-primitives/`

---

## Summary Answer

**Yes, and the value is clearer here than in the AP2 scenario.**

TACP is a pure authentication layer. It never claimed to handle mandate enforcement. AGF's DAE fills exactly the gap TACP leaves open: machine-readable, enforceable spending constraints with deterministic authorization decisions.

The question isn't whether AGF duplicates TACP. They operate on different concerns and are complementary by design.

---

## Where AGF Adds Value

### DAE — Direct Mandate Enforcement (`spec/governance-primitives/delegated-authority-envelope.md`)

The mandate-exceeded scenario is the canonical use case for the DAE.

A DAE for this transaction:

```json
{
  "delegation_id": "dae_electronics_2026_001",
  "principal": "consumer@example.com",
  "delegate": "shopping-agent.example.com",
  "allowed_actions": ["purchase"],
  "constraints": {
    "max_value": 500.00
  },
  "expiry": "2026-03-13T00:00:00Z",
  "revocable": true,
  "revoked": false,
  "audit_required": true
}
```

When the merchant adds the $30 surcharge and the total becomes $510:

Per DAE Validation Rule 6: "If `constraints.max_value` exists and transaction amount exceeds it, authorization result MUST be deny."

Expected output: `ERR_DAE_MAX_VALUE_EXCEEDED` with audit evidence.

This check would occur before the payment is processed. The surcharge triggers a re-validation against the DAE, and the result is a hard deny at $510. The agent would then need to either:
a) Notify the user and request an updated mandate
b) Reject the surcharge

**This is exactly what the consumer expected the agent to do. DAE makes it enforced behavior, not a hopeful convention.**

### DAE + TACP Integration

The natural architecture is:
1. TACP authenticates the agent's identity (who is making this request?)
2. DAE enforces the agent's authorization constraints (what are they allowed to do?)

TACP answers: "This is the authenticated shopping agent from shopping-agent.example.com, representing consumer@example.com."
DAE answers: "This agent is authorized to purchase up to $500."

Neither duplicates the other. Both are needed for secure, governed agent commerce.

An integration point: the agent should check the DAE before creating the TACP PaymentMandate (or before finalizing any order modification). If the DAE check returns deny, no TACP message is sent for the modified amount.

### TCR — Post-Checkout Modification Tracking (`spec/governance-primitives/transaction-commitment-record.md`)

The TCR is directly applicable to the post-checkout surcharge scenario.

```json
{
  "commitment_id": "tcr_order_abc123",
  "transaction_id": "ord_abc123",
  "issuer": "shopping-agent.example.com",
  "counterparty": "electronics-retailer.example.com",
  "commitments": [
    {
      "type": "approval",
      "target": "order_total_max_usd_500",
      "due_by": "2026-03-12T18:00:00Z",
      "fulfilled": true,
      "required": true
    },
    {
      "type": "delivery",
      "target": "electronics_bundle",
      "due_by": "2026-03-15T18:00:00Z",
      "fulfilled": false,
      "required": true
    }
  ],
  "evidence_refs": [
    {"kind": "attestation", "ref": "tac_message_jti_abc123..."},
    {"kind": "receipt", "ref": "merchant_order_confirmation"}
  ],
  "status": "pending",
  "dispute_window_end": "2026-04-12T00:00:00Z",
  "audit_required": true
}
```

When the surcharge is applied and the total changes to $510, the TCR's `approval` commitment (`order_total_max_usd_500`) would transition to `breached` — providing structured dispute evidence that explicitly records the breach.

Per TCR Rule 5: "If a transaction close/finalize action is attempted while the record is `breached` or `revoked`, the result MUST be deny."

This goes beyond what TACP provides. TACP proves the initial authentication. TCR proves whether the transaction obligations were actually honored.

### DBA — Data Boundary Assertion

Relevant for the fraud signal isolation in TACP. When the agent sends device data and forterToken to Forter (encrypted in a separate JWE), DBA can formalize:

- `permitted_operations: ["infer"]` — Forter can infer fraud risk but not store indefinitely
- `max_retention_hours: 168` — fraud signals have a 7-day retention limit
- `egress_allowed: false` — Forter cannot forward this data to other parties

This operationalizes data governance that TACP's encryption mechanism enables but doesn't formally constrain. Not critical for the mandate scenario specifically, but relevant to the broader TACP deployment context.

---

## What AGF Does NOT Add Here

AGF does not improve:
- Agent authentication (TACP's JWS+JWE is superior for this)
- Fraud signal delivery (TACP's multi-recipient JWE isolation is purpose-built)
- Replay attack prevention (TACP's JTI tracking is already well-specified)
- User identity verification (TACP's JWKS-based key distribution is standard)

---

## The Honest Assessment

For TACP specifically, AGF is complementary in a cleaner way than for AP2:

| Concern | TACP | AGF (DAE) |
|---|---|---|
| Agent identity | ✅ JWS signatures | — |
| Message integrity | ✅ JWE encryption | — |
| Spending mandate enforcement | ❌ Not in scope | ✅ `max_value` constraint |
| Post-checkout modification control | ❌ Not defined | ✅ Re-validate against DAE |
| Dispute evidence | ⚠️ Partial (authentication only) | ✅ TCR (breach record + evidence refs) |
| Data retention governance | ⚠️ Encryption only, no retention rules | ✅ DBA `max_retention_hours` |

TACP and AGF together produce a more complete governance stack than either alone. TACP solves authentication. AGF solves authorization constraints, commitment tracking, and data boundaries.

---

## Recommendation

For TACP deployments handling consumer mandates, AGF's DAE is not optional — it's the mechanism that makes consumer mandates enforceable rather than aspirational. Mandate enforcement is the primary consumer protection in autonomous purchasing, and TACP explicitly out-of-scopes it.

AGF should be developed with specific attention to TACP integration: define how the DAE is checked before a TACP PaymentMandate is created, and how TCR records are associated with TACP JTI identifiers to link authentication evidence to commitment evidence.

This is a concrete, bounded development goal — not a broad governance framework. Scoping AGF to this integration layer is more viable than positioning it as a standalone protocol.
