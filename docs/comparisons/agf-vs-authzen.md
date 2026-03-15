# AGF vs AuthZEN

**TL;DR:** AuthZEN is a live API for real-time policy decisions at an enforcement point within a single organization. AGF DBA is a portable pre-signed contract that travels with the transaction across organizational boundaries. They are designed to coexist in the same enforcement stack.

---

## What AuthZEN Is

AuthZEN (OpenID Foundation) defines a standardized API between a Policy Enforcement Point (PEP) and a Policy Decision Point (PDP). The PEP calls the PDP, the PDP evaluates the request against policy, and returns allow/deny.

AuthZEN provides:
- A standard PEP→PDP request/response format
- JSON body: subject, resource, action, context
- Clean decoupling of enforcement from policy evaluation
- Works with any PDP (OPA, Cedar, custom engines)

AuthZEN requires a live PDP. The PEP calls the PDP at enforcement time. The PDP must be reachable.

---

## What AGF DBA Is

DBA (Data Boundary Assertion) is an AGF governance primitive — a portable pre-signed data governance contract. It specifies what data may cross which boundaries, to which regions, under what constraints.

DBA provides:
- A portable signed document that travels with the transaction
- Offline-verifiable data permissions: no PDP connectivity required at evaluation time
- Cross-org verifiability: Company B verifies data permissions without calling Company A's systems
- Machine-enforceable fields: `egress_allowed`, `allowed_regions[]`, `max_retention_hours`, `redaction_required[]`
- Dispute-ready: the contract is signed and timestamped; it is evidence in itself

---

## The Structural Difference

AuthZEN is a protocol between two components within a trust boundary. Both the PEP and PDP are within the organization or are explicitly trusted by it. The PDP call is synchronous and requires network connectivity.

DBA is a contract that crosses trust boundaries. When an agent from Company A arrives at Company B's systems, Company B has no AuthZEN PDP belonging to Company A it can call. Company B needs a self-contained verifiable document that proves the data permissions. DBA is that document.

---

## How They Work Together in a Deployment

The two complement each other in a typical enforcement stack:

1. The agent arrives at Company B's enforcement point (e.g., agentgateway) with a DBA attached
2. The enforcement point performs offline DBA evaluation: checks `egress_allowed`, `allowed_regions[]`, `data_classes[]` against the requested operation
3. The enforcement point then calls its own PDP via AuthZEN for live policy evaluation against Company B's internal policies
4. Both checks must pass for the action to proceed
5. The TCR records what was decided and commits the evidence

DBA handles the portable cross-org pre-check. AuthZEN handles the live policy decision at the enforcement point. Neither replaces the other.

---

## Summary

| Property | AuthZEN | AGF DBA |
|---|---|---|
| Type | PEP→PDP protocol | Portable governance document |
| Connectivity at enforcement | Required (live PDP call) | Not required |
| Cross-org verifiability | Requires shared PDP access | Offline, signature-based |
| Data permissions | Defined in PDP policy | Carried in signed document |
| Dispute evidence | No (decision is ephemeral) | Yes (signed document is evidence) |
| Relationship | Enforcement decision layer | Pre-flight governance contract layer |

AGF DBA and AuthZEN are complementary. DBA verifies the governance terms carried by the transaction. AuthZEN verifies live policy at the enforcement point.

→ [DBA Specification](../../spec/governance-primitives/data-boundary-assertion.md)
→ [DBA Schema v0.2](../../spec/dba-schema-v0.2.json)
→ [AuthZEN Specification](https://openid.net/wg/authzen/)
