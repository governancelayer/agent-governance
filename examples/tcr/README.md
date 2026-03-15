# TCR Examples: Transaction Commitment Record

These examples demonstrate the Transaction Commitment Record (TCR) primitive for tracking obligations and accountability state across a governed transaction.

**Schema:** [`spec/tcr-schema-v0.1.json`](../../spec/tcr-schema-v0.1.json)
**Primitive description:** [`spec/governance-primitives/transaction-commitment-record.md`](../../spec/governance-primitives/transaction-commitment-record.md)

## Scenario

An agent (`OrgA.AgentA`) transacts with an external service (`OrgB.ServiceB`). Each transaction requires two commitments to be fulfilled before it can close:

1. An **approval** artifact for the action
2. An **audit export** of the decision record

## Examples

### fulfilled.json

Transaction `tx-2001` (purchase order creation). Both required commitments are marked as fulfilled. Evidence includes a trace reference and a receipt for the decision record. The transaction status is `"fulfilled"` and a dispute window remains open until `2030-01-08`.

### breached.json

Transaction `tx-2002` (refund issuance). The approval commitment was fulfilled, but the audit export was **not** completed before its `due_by` deadline. The transaction status is `"breached"` with a clear reason: `"required audit export was not completed before due_by"`. Only a trace reference exists (the receipt for the missing audit export is absent).

## What This Shows

TCR answers one question: **is this transaction actually complete and accountable?**

A transaction can succeed operationally (the refund was issued, the order was placed) but still be in breach if required commitments were not fulfilled. TCR tracks:

- What commitments were required
- Whether each commitment was fulfilled
- When commitments were due
- What evidence exists to support the commitments
- Whether the transaction is pending, fulfilled, breached, or revoked
