# AGF Evaluation: Does AGF Add Value for the AP2 Hotel Booking Scenario?

**Test Version:** 1.0.0
**Date:** 2026-03-12
**AGF Sources:** `spec/governance-primitives/`

---

## Summary Answer

**Yes, AGF adds real value here — but in a specific, targeted way.**

AGF does not duplicate what AP2 does. The two operate at different layers. AP2 is a commerce protocol (how agents negotiate purchases and generate audit evidence). AGF's DAE is a delegation enforcement layer (what the agent is actually authorized to do at runtime).

For the hotel booking scenario, the specific gap AGF addresses is the one AP2 leaves open: **machine-readable spending limit enforcement.**

---

## Where AGF Adds Value

### DAE — Delegated Authority Envelope (`spec/governance-primitives/delegated-authority-envelope.md`)

The DAE directly solves Gap 1 identified in `findings.md`.

AP2's IntentMandate has no `max_value` field. The user's €900 budget lives in natural language only. A DAE for the same scenario would be:

```json
{
  "delegation_id": "dae_hotel_booking_2026_001",
  "principal": "user@example.com",
  "delegate": "shopping-agent-v2",
  "allowed_actions": ["book_hotel"],
  "constraints": {
    "max_value": 900.00,
    "currency": "EUR",
    "jurisdiction": "EU"
  },
  "expiry": "2026-04-14T00:00:00Z",
  "revocable": true,
  "revoked": false,
  "audit_required": true
}
```

DAE Validation Rule 6 (from the spec): "If `constraints.max_value` exists and transaction amount exceeds it, authorization result MUST be deny."

If a DAE were checked before the agent created a PaymentMandate for €930, the result would be `ERR_DAE_MAX_VALUE_EXCEEDED` with reason code and audit evidence — **before the payment was processed**.

This is enforcement, not evidence. This is exactly what AP2 lacks.

### TCR — Transaction Commitment Record (`spec/governance-primitives/transaction-commitment-record.md`)

The TCR addresses Gap 3 — no AP2 mechanism for tracking whether transaction obligations were fulfilled.

An AP2 CartMandate records what was agreed. A TCR records whether what was agreed was actually delivered. In this scenario:

```json
{
  "commitment_id": "tcr_hotel_booking_001",
  "transaction_id": "order_abc123",
  "issuer": "shopping-agent-v2",
  "counterparty": "berlin-grand-hotel",
  "commitments": [
    {
      "type": "delivery",
      "target": "3-night hotel stay April 10-13",
      "due_by": "2026-04-10T14:00:00Z",
      "fulfilled": false,
      "required": true
    }
  ],
  "evidence_refs": [
    {"kind": "receipt", "ref": "pm_mandate_hash_abc"},
    {"kind": "attestation", "ref": "user_device_sig_xyz"}
  ],
  "status": "pending",
  "dispute_window_end": "2026-05-13T00:00:00Z",
  "audit_required": true
}
```

TCR Rule 3: If any `required=true` commitment has `due_by` in the past and `fulfilled=false`, the record MUST be treated as breached.

The AP2 PaymentMandate is strong on "what was paid for." It's silent on "was it delivered." TCR fills that gap explicitly, with structured status tracking rather than relying on dispute adjudicators to infer delivery state from payment receipts.

### DBA — Data Boundary Assertion

Less directly relevant for this specific scenario. The hotel booking scenario doesn't involve cross-org data egress or PII jurisdiction questions beyond what AP2's existing privacy design (§2.2) covers.

DBA would become relevant if the hotel's fraud prevention vendor needed to receive payment data across an organizational boundary — a scenario TACP handles with JWE encryption but without explicit data-retention or operation constraints.

---

## What AGF Does NOT Add Here

AGF does not improve:
- The cryptographic evidence chain (AP2's VDCs are strong here)
- The merchant-price-lock mechanism (CartMandate TTL is solid)
- The flow architecture (AP2's 32-step sequence is well-specified)
- The dispute table framework (AP2's Table 6.1 is useful)

---

## The Honest Assessment

AGF and AP2 are not competing. They're addressing different parts of the problem:

| Concern | AP2 | AGF (DAE) |
|---|---|---|
| Evidence that transaction occurred | ✅ CartMandate, PaymentMandate | — |
| Budget constraint enforcement | ❌ Natural language only | ✅ `max_value` + `ERR_DAE_MAX_VALUE_EXCEEDED` |
| Dispute evidence chain | ✅ Table 6.1 | ✅ TCR (complementary) |
| Runtime authorization check | ❌ Not defined | ✅ DAE enforcement semantics |
| Delivery obligation tracking | ❌ Not addressed | ✅ TCR `commitments` array |
| Data boundary controls | ✅ Partial (PCI/PII separation) | ✅ DBA (additive) |

**For the specific gap in this scenario (budget enforcement), AGF adds real, non-redundant value.**

The question isn't whether to retire AGF. The question is whether AGF should be positioned as a middleware enforcement layer that sits alongside AP2 rather than a competing protocol. Based on this test, that positioning is correct.

---

## Recommendation

AGF's DAE is a legitimate complement to AP2. The two protocols address the same transaction from different angles: AP2 creates the audit trail for dispute resolution, DAE provides the runtime gate that prevents violations in the first place. A well-functioning agentic payment system probably needs both.

If AGF is to be developed further, the priority should be demonstrating how DAE enforcement integrates with AP2's PaymentMandate creation step (before Step 19 in the §7.1 sequence), not replacing AP2.
