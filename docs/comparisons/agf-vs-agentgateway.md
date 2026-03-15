# AGF vs agentgateway

**TL;DR:** agentgateway is a Policy Enforcement Point (PEP). AGF defines the governance contracts that agentgateway enforces. They operate at different layers of the stack and are designed to work together.

---

## What agentgateway Is

agentgateway (agentgateway/agentgateway, Apache 2.0) is an agent-aware API gateway. It proxies A2A and MCP traffic, applies policy via an AuthZEN-compatible PDP, and logs transactions.

agentgateway provides:
- A2A and MCP protocol support (routes, translates, proxies agent traffic)
- AuthZEN integration: PEP→PDP call for real-time access decisions
- Tool-level authorization (CEL rules evaluate which tools an agent may call)
- Telemetry and logging via OTel

agentgateway is enforcement infrastructure. It enforces policy at the transport layer. It calls a PDP to make the enforcement decision.

---

## What AGF Defines

AGF defines the governance contract layer — the pre-signed documents that specify the governance terms of a transaction before it executes.

AGF provides:
- DAE: Who authorized the agent, with what constraints (including spending limits)
- DBA: What data may cross which boundaries, to which regions, with what redaction
- TCR: What obligations must be fulfilled and what evidence must be retained
- GDR: What governance decision was made, with a signed audit trail

AGF does not route traffic. AGF does not call a PDP. AGF defines the contracts that PDPs evaluate.

---

## The Structural Difference

agentgateway sits at the transport layer and enforces policy at runtime. Its policy source is a live PDP (OPA, AuthZEN-compatible endpoint).

AGF sits at the governance contract layer. Its contracts travel with the transaction as portable signed documents. They specify governance terms that any enforcement point — including agentgateway — evaluates.

---

## How They Work Together

A complete governance enforcement flow with agentgateway and AGF:

1. The AI agent constructs a request to Company B's resources, attaching AGF Phase 1 contracts (DAE + DBA + TCR)
2. The request arrives at agentgateway (Company B's enforcement point)
3. agentgateway performs offline DAE evaluation: checks expiry, revocation, allowed_actions, max_value constraint
4. agentgateway performs offline DBA evaluation: checks egress_allowed, allowed_regions, redaction requirements
5. agentgateway calls its AuthZEN-connected PDP for live policy evaluation (Company B's internal policies)
6. All checks pass: agentgateway forwards the request with a governance token
7. The response returns through agentgateway
8. agentgateway creates a TCR evidence record and a GDR decision record
9. Evidence is retained for the TCR dispute window

agentgateway provides the enforcement infrastructure. AGF provides the governance contracts and defines what the evaluation must produce.

---

## What agentgateway Does Not Provide (and AGF Does)

agentgateway's tool-level authorization (CEL rules, JWT claims) answers: "Is this agent allowed to call this tool?" It is a per-request online check.

This does not cover:
- **Cross-org portability**: CEL rules are enforced at Company B's gateway. If Company A's agent needs Company B to verify governance terms from Company A's authorization system, CEL rules don't help. DAE fills this gap.
- **Numeric spending constraints**: agentgateway's authorization model is binary (allow/deny per tool). DAE's `max_value` + `currency` provides a machine-enforceable budget constraint that survives across calls and organizations.
- **Post-action obligation lifecycle**: A transaction may commit to delivery, redaction, or audit obligations that must be tracked over time. agentgateway logs the call; TCR tracks whether the obligations were fulfilled.
- **Portable audit trail**: agentgateway OTel spans are local telemetry. GDR is a portable, signed, cross-org verifiable audit record.

---

## Summary

| Property | agentgateway | AGF |
|---|---|---|
| Type | API gateway / PEP | Governance contract specification |
| Layer | Transport / enforcement | Governance contract |
| Policy source | Live PDP (AuthZEN) | Portable pre-signed contract |
| Cross-org portability | Local to Company B's deployment | Carried by agent across boundaries |
| Spending limits | Not in scope | DAE `max_value` + `currency` |
| Post-action obligation lifecycle | Not in scope | TCR |
| Portable signed audit trail | Not in scope | GDR |
| Relationship | Enforcement infrastructure | Governance contract layer |

agentgateway is a valid AGF enforcement point. AGF defines the contracts agentgateway evaluates and the evidence agentgateway should produce.

→ [AGF Architecture](../architecture.md)
→ [DAE Specification](../../spec/governance-primitives/delegated-authority-envelope.md)
→ [agentgateway (GitHub)](https://github.com/agentgateway/agentgateway)
