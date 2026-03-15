# AGF vs PEAC

**TL;DR:** AGF Phase 1 defines pre-action governance contracts (what the agent is authorized to do). PEAC defines post-action governance evidence (what the agent actually did). They are complementary layers in a complete governance stack.

---

## What PEAC Is

PEAC Protocol (Portable Evidence for Agent Coordination, peacprotocol.org) is an open protocol (Apache 2.0, ~1,400 commits as of early 2026) for recording evidence of agent coordination decisions.

PEAC provides:
- Signed portable receipts (Ed25519 JWS)
- A `ControlBlock` structure carrying authority chain, allow/deny decision, and per-step policy reference
- EU AI Act Article 12 compliance mapping
- Official A2A integration profile
- Official MCP integration profile
- Dispute bundles (ZIP archive with receipt + policy + verification report)

PEAC is an evidence format. It records what happened after the agent acted.

---

## What AGF Defines

AGF Phase 1 defines pre-action governance contracts:
- DAE: Who authorized the agent, with what constraints, until when
- DBA: What data may cross which boundaries
- TCR: What obligations must be fulfilled and what evidence must be retained

AGF Phase 2 (GDR — in development) defines the AGF-native governance evidence format for post-action audit trails, with explicit OCSF mapping for SIEM integration.

---

## The Structural Difference

PEAC covers the evidence layer. AGF Phase 1 covers the contract layer. These are different phases of the same governance lifecycle:

```
Phase 1: Contract  →  Enforcement  →  Phase 2: Evidence
[DAE / DBA / TCR]     [gateway]       [GDR / PEAC receipt]
What was authorized    Decision        What actually happened
```

PEAC receipts reference a policy field — what they reference is undefined by PEAC itself. AGF Phase 1 contracts are the natural `policy` reference for PEAC receipts on AGF-governed transactions.

---

## Does PEAC Cover Phase 1?

PEAC does not cover the pre-action contract layer. PEAC is an evidence format; it records the outcome of a governance decision. It does not define:
- A machine-readable principal→delegate delegation chain
- A numeric spending limit with a currency denomination
- A subject matter scope for the delegation
- Portable offline-verifiable pre-action authorization

This is confirmed by PEAC's documentation: "PEAC is not a payment rail or policy engine. It is the evidence layer." PEAC receipt `kind: "challenge"` provides a pre-action query mechanism, but it requires PEAC infrastructure to be present at the enforcement point — it is not a portable self-contained document.

AGF Phase 1 fills the pre-action contract gap that PEAC explicitly does not address.

---

## The Complementary Design

A complete AGF + PEAC governance stack for a transaction:

**Pre-action (AGF Phase 1):**
1. DAE is issued: principal authorizes agent, $5,000 USD max, expires in 4 hours
2. DBA is issued: transaction may send PII to EU region only, with redaction
3. TCR is issued: delivery commitment due by EOD, dispute window 30 days

**At enforcement (gateway evaluates):**
4. Enforcement point evaluates DAE, DBA offline
5. AuthZEN call for live policy decision
6. Decision: allow, with token

**Post-action (PEAC evidence):**
7. PEAC receipt created; `policy` field references DAE, DBA, TCR by ID
8. `ControlBlock` carries the authority chain from the DAE
9. PEAC receipt signed and archived with the TCR evidence package

**Result:** A complete audit chain from authorization contract to execution evidence, portable across organizational boundaries, suitable for EU AI Act Article 12 submission.

---

## Summary

| Property | PEAC | AGF Phase 1 |
|---|---|---|
| Phase | Post-action evidence | Pre-action contract |
| Principal→delegate chain | Not defined | DAE `principal` + `delegate` |
| Numeric spending limits | Not defined | DAE `max_value` + `currency` |
| Data boundary constraints | Not defined | DBA |
| Obligation lifecycle | Not defined | TCR |
| Evidence format | Signed portable receipt | (Phase 2 GDR defines AGF evidence) |
| OCSF mapping | Not defined | GDR target (Phase 2) |
| Relationship | Evidence layer | Contract layer |

AGF Phase 1 fills the pre-action governance gap. PEAC fills the post-action evidence gap. They govern the same transaction at different points in its lifecycle.

→ [DAE Specification](../../spec/governance-primitives/delegated-authority-envelope.md)
→ [TCR Specification](../../spec/governance-primitives/transaction-commitment-record.md)
→ [AGF ROADMAP — Phase 2 GDR](../../ROADMAP.md)
→ [PEAC Protocol](https://www.peacprotocol.org/)
→ [PEAC GitHub](https://github.com/peacprotocol/peac)
