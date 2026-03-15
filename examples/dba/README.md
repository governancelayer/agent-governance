# DBA Examples: Data Boundary Assertion

These examples demonstrate the Data Boundary Assertion (DBA) primitive for governing what may happen to data involved in an agent transaction.

**Schema:** [`spec/dba-schema-v0.1.json`](../../spec/dba-schema-v0.1.json)
**Primitive description:** [`spec/governance-primitives/data-boundary-assertion.md`](../../spec/governance-primitives/data-boundary-assertion.md)

## Scenario

A governance service (`OrgA.GovernanceService`) issues data boundary assertions for transactions involving customer data classified as PII, customer content, or confidential. Both assertions restrict data to the EU and prohibit egress.

## Examples

### transfer-allowed.json

A request (`req-1001`) containing customer content and confidential data. The assertion permits inference and audit export operations within EU boundaries. Customer email must be redacted before any export, and data may be retained for up to 24 hours.

An enforcement point should **allow** the transfer, provided the consuming system honors the boundary constraints.

### egress-blocked.json

A response (`resp-2002`) containing PII and customer content. The assertion permits only storage. Egress is denied, retention is limited to 12 hours, and both customer email and account number must be redacted.

An enforcement point should **block** any attempt to export, forward, or move this data outside the declared boundary.

## What This Shows

DBA answers one question: **even if the caller is authorized, is this use of the data allowed?**

A valid delegation (DAE) does not override a data boundary violation. The DBA governs:

- Which operations are permitted on classified data
- Where data may reside (region constraints)
- How long data may be retained
- Which fields must be redacted before transfer or logging
- Whether the data may leave the organizational boundary at all
