# AGF vs Policy Cards

**TL;DR:** Policy Cards define governance terms at the class level — for an AI model or system as a whole. AGF defines governance contracts at the instance level — for a specific transaction, with a specific principal, to a specific counterparty, with specific numeric constraints. They address different points in the governance stack.

---

## What Policy Cards Are

Policy Cards (Bernardi et al., 2023+) are a structured documentation format for AI systems. A Policy Card describes what an AI model or system is permitted to do, what data it may use, who is responsible for it, and under what conditions it may be deployed.

Policy Cards provide:
- Class-level governance: "this model may be used for X purposes by Y actors"
- Structured documentation: operator, permitted uses, prohibited uses, data sources, known limitations
- Human-readable compliance record for regulators, deployers, and operators
- Designed to complement Model Cards (Mitchell et al.) with governance intent

Policy Cards are documentation artifacts. They are written before deployment. They do not change at transaction time and do not carry transaction-specific governance terms.

---

## What AGF Defines

AGF defines instance-level governance contracts — documents created for specific transactions at runtime.

AGF provides:
- DAE: "This specific agent (Agent A) is authorized by this specific principal (CFO John Smith) to spend up to $5,000 USD in this specific transaction scope, until this expiry, revocable by this authority"
- DBA: "This specific transaction may send these specific data classes to this specific region, with these redaction requirements"
- TCR: "This specific transaction has these specific commitments (approval by Dec 31, audit export by Jan 15) and this evidence package"

AGF contracts are created at transaction time, specific to one transaction, and expire. They carry cryptographic identity and are verifiable by any party that holds the public key.

---

## The Structural Difference

| Property | Policy Cards | AGF |
|---|---|---|
| Granularity | Class-level (model / system) | Instance-level (transaction) |
| Timing | Written at deployment time | Created at transaction time |
| Principal-specific | No | Yes (`principal` field in DAE) |
| Numeric constraints | No | Yes (`max_value` + `currency`) |
| Machine-enforceable | No | Yes |
| Expires | No | Yes (per transaction `expiry`) |
| Cryptographically signed | No | Yes |
| Offline-verifiable | No | Yes |

---

## Why Both Are Needed

Policy Cards answer: "Is this AI system allowed to be used for this type of task at all?"

AGF answers: "Is this specific agent, acting right now, under this specific delegation, authorized to take this specific action within these specific constraints?"

A complete governance picture requires both:
- The Policy Card establishes the class-level governance policy for the AI system (its permitted use domain, operator responsibilities, prohibited uses)
- The AGF contract governs the specific transaction that occurs when the AI system operates within that policy domain

Policy Cards are static governance documentation. AGF contracts are dynamic runtime governance artifacts. They operate at different layers and are complementary.

---

## Relationship to AGF

AGF does not replace Policy Cards. A Policy Card for an AI agent system could reference the AGF primitives it uses for transaction-level governance — and an AGF DAE could reference the Policy Card that defines the class-level authorization under which the agent operates.

Policy Cards are outside AGF's scope. AGF defines instance-level transaction governance. Class-level governance documentation is a separate layer that AGF is designed to coexist with.

→ [DAE Specification](../../spec/governance-primitives/delegated-authority-envelope.md)
→ [AGF Architecture](../architecture.md)
→ [Policy Cards (Bernardi et al.)](https://arxiv.org/abs/2302.02257)
→ [Policy Cards GitHub](https://github.com/AI4TRUST-project/policy-cards)
