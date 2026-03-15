# AGF vs OPA

**TL;DR:** OPA evaluates policy against data. AGF defines the governance contracts that carry the data OPA evaluates. A Rego policy evaluating AGF primitives is a design target — OPA is the intended reference evaluator for DBA.

---

## What OPA Is

OPA (Open Policy Agent, CNCF) is a general-purpose policy engine. You write policy as Rego, provide data (as JSON), and OPA returns a decision. OPA decouples policy from the enforcement point and from the application.

OPA provides:
- A rich, expressive policy language (Rego)
- Ability to evaluate any JSON structure against any policy
- SIDECAR deployment pattern: OPA runs alongside the enforcement point and receives queries
- High performance evaluation for real-time enforcement

OPA requires a running OPA instance at enforcement time. Policy updates require deploying updated Rego to the OPA instance. OPA itself does not define the structure of governance contracts — it evaluates whatever JSON you provide.

---

## What AGF Defines

AGF defines the structure of governance contracts (DAE, DBA, TCR) — the JSON documents that carry governance terms. AGF specifies:
- The fields these documents must contain
- The semantics of each field
- The validation rules that must be evaluated at enforcement time
- The reason codes to emit for each violation

AGF does not specify the enforcement engine. Any system that can evaluate the AGF field semantics and emit the correct reason codes is a valid AGF enforcement point. OPA/Rego is the recommended reference evaluator for DBA constraints.

---

## The Relationship

OPA evaluates. AGF defines what gets evaluated.

A complete enforcement stack:
1. The agent carries an AGF DBA document to the enforcement point
2. The enforcement point passes the DBA JSON to OPA along with the requested operation
3. A Rego policy evaluates the DBA fields: `egress_allowed`, `allowed_regions[]`, `data_classes[]`, `max_retention_hours`, `redaction_required[]`
4. OPA returns allow/deny with the applicable reason code
5. The enforcement point acts on the decision and records the outcome in a TCR

This is the target integration pattern. A reference Rego policy for DBA evaluation is a design target in the AGF conformance suite.

---

## What OPA Does Not Provide

OPA as a standalone policy engine does not define:
- **The governance contract format**: OPA will evaluate any JSON. AGF specifies what JSON governance contracts must look like.
- **Portability semantics**: OPA requires a live instance. AGF contracts are designed to be evaluatable by any conformant implementation, including offline evaluators and cross-org enforcement points.
- **The delegation chain**: OPA has no concept of a principal→delegate chain, spending limits, or inline revocation state. These are AGF fields that a Rego policy evaluates.
- **Post-action evidence format**: OPA returns a decision. AGF TCR and GDR define how that decision is recorded and preserved for audit.

---

## Summary

| Property | OPA | AGF |
|---|---|---|
| Type | Policy engine | Governance contract specification |
| Input | Any JSON you provide | Defined governance contract format |
| Output | Policy decision | Defined reason codes + evidence |
| Connectivity | Live OPA instance required | Contract portable; evaluator can be offline |
| Defines contract structure | No | Yes |
| Defines post-action evidence | No | Yes (TCR, GDR) |
| Relationship | Evaluation engine | Contract specification layer |

AGF and OPA are designed to work together. OPA is the recommended reference implementation for DBA evaluation. AGF defines what OPA evaluates.

→ [DBA Specification](../../spec/governance-primitives/data-boundary-assertion.md)
→ [AGF Conformance Suite](../../conformance/)
→ [OPA Documentation](https://www.openpolicyagent.org/docs/latest/)
