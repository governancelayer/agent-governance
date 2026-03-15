# DAE Examples: Delegated Authority Envelope

These examples demonstrate the Delegated Authority Envelope (DAE) primitive in an agent-to-agent procurement scenario.

**Schema:** [`spec/dae-schema-v0.1.json`](../../spec/dae-schema-v0.1.json)
**Primitive description:** [`spec/governance-primitives/delegated-authority-envelope.md`](../../spec/governance-primitives/delegated-authority-envelope.md)

## Scenario

A principal agent (`OrgA.AgentA`) delegates authority to another agent (`OrgA.AgentB`) to create purchase orders. The delegation is constrained to:

- Maximum transaction value of 10,000
- Jurisdiction limited to EU
- Subject to revocation

## Examples

### delegation-allowed.json

A valid, active delegation. The expiry is in the future and the delegation has not been revoked. An enforcement point evaluating this DAE should **allow** the requested action.

### delegation-expired.json

The same delegation, but the `expiry` field is set to `2024-01-01T00:00:00Z` (in the past). An enforcement point should **deny** the action because the delegated authority has expired.

### delegation-revoked.json

The same delegation with a future expiry, but `revoked` is set to `true`. An enforcement point should **deny** the action because the principal has explicitly revoked the delegation.

## What This Shows

DAE answers one question: **may this agent act on behalf of this authority?**

The answer depends on:

- Whether a delegation exists for the requested action
- Whether the delegation has expired
- Whether the delegation has been revoked
- Whether the action falls within the declared constraints
