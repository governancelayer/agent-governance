# AGF Protocol Validation

This directory contains evidence-based validation tests run against real production agent protocols. The goal is to verify two things: that the governance gaps AGF addresses are genuine (not theoretical), and that AGF's primitives address them without duplicating what the protocols already do well.

These are not unit tests for AGF. They are protocol gap tests: runnable scenarios that exercise the edges of existing agent protocols, with findings cited to specific spec sections and source code.

---

## Why This Matters

A new specification must answer a hard question: *does this actually fill a gap, or does something else already handle it?* I tested AGF's core claim — that machine-readable spending limits, portable authorization contracts, and cross-org verifiable governance are missing from current agent protocols — against the most relevant production specs I could find.

The two scenarios below demonstrate that the identified gaps exist in these protocols. They do not constitute proof that AGF is the only or best way to address them; alternative architectural approaches may exist, and I welcome challenges. These tests build an evidence base for the gap — they are not a proof of category-level necessity.

---

## What We Tested

### AP2 — Google Agent Payments Protocol (Hotel Booking)

**Protocol:** Google Agent Payments Protocol v0.1
**Source:** [github.com/google/agent-payments-protocol](https://github.com/google/agent-payments-protocol)

**Scenario:** A consumer AI agent books a hotel at €280/night (€840 total, within the stated €900 budget). Between quote and payment, the hotel's dynamic pricing updates to €310/night (€930 total). The agent proceeds because it has been programmed with a 10% tolerance. The user disputes the charge.

**What AP2 gets right:**
- Three-mandate cryptographic evidence chain (IntentMandate → CartMandate → PaymentMandate)
- Short-lived CartMandate TTL forcing price re-fetch before payment
- `user_cart_confirmation_required` control giving agents explicit autonomous authority
- Liability table (§6 Table 6.1) covering "Mispick, Unapproved by User" disputes

**The gap AGF addresses:**
AP2's `IntentMandate` has no machine-readable budget field. The €900 constraint lives in `natural_language_description` only. Nothing in the AP2 protocol *prevents* the agent from creating a €930 PaymentMandate. Dispute adjudication requires an NLP interpretation of free text to determine whether the budget was violated.

AGF's answer: DAE `constraints.max_value: 900, currency: "EUR"` — evaluated at the enforcement point before any payment mandate is created. `ERR_DAE_MAX_VALUE_EXCEEDED` fires with a reason code. Machine-enforceable. Audit-ready.

→ [Full scenario walkthrough](ap2-hotel-booking/README.md) · [Findings](ap2-hotel-booking/findings.md) · [AGF evaluation](ap2-hotel-booking/agf-evaluation.md) · [Code](ap2-hotel-booking/scenario.py)

---

### TACP — Forter Trusted Agentic Commerce Protocol (Mandate Exceeded)

**Protocol:** Forter Trusted Agentic Commerce Protocol v2025-11-12
**Source:** [github.com/forter/tacp](https://github.com/forter/tacp)

**Scenario:** A procurement AI agent is authorized up to $500. It places an electronics order for $480. The merchant adds a $30 post-checkout shipping surcharge, bringing the total to $510. The charge processes. The agent never had a mechanism to detect or block the overage.

**What TACP gets right:**
- Strong agent authentication with JWE-encrypted credentials
- Rich fraud signal sharing between merchant and issuer
- Agent context metadata visible to the fraud risk engine
- Well-structured schema for agentic transaction lifecycle

**The gap AGF addresses:**
TACP is an agent authentication protocol. There is no `mandate`, `spending_limit`, `max_authorized_amount`, or equivalent field at any level of the schema. TACP verifies *who* the agent is. It does not verify *what the agent was authorized to do* or *within what limits*. The $510 charge is processed by an authenticated agent — TACP has no basis to flag the overage because it was never given the mandate.

AGF's answer: same DAE. TACP authenticates the agent identity; DAE enforces the authorization terms. They are complementary layers, not competing protocols.

→ [Full scenario walkthrough](tacp-mandate-exceeded/README.md) · [Findings](tacp-mandate-exceeded/findings.md) · [AGF evaluation](tacp-mandate-exceeded/agf-evaluation.md) · [Code](tacp-mandate-exceeded/scenario.py)

---

## Summary

| Concern | AP2 | TACP | AGF (DAE) |
|---|---|---|---|
| Machine-readable spending limits | ❌ Natural language only | ❌ Not in scope | ✅ `max_value` + `currency` |
| Runtime enforcement of limits | ❌ Not defined | ❌ Not in scope | ✅ `ERR_DAE_MAX_VALUE_EXCEEDED` |
| Cross-org portable authorization | ❌ Requires AS call | ❌ Not addressed | ✅ Offline-verifiable signature |
| Delegation chain (principal → delegate) | ❌ Not defined | ❌ Not defined | ✅ `principal` + `delegate` fields |
| Post-action obligation tracking | ❌ Not addressed | ❌ Not addressed | ✅ TCR |
| Agent authentication | ✅ VDC chain | ✅ JWE credentials | Not in scope (separate layer) |
| Payment audit evidence | ✅ Strong | ✅ Good | Complementary (GDR) |

The full cross-protocol comparison: [`SUMMARY.md`](SUMMARY.md)

---

## Methodology

1. Read the full protocol spec and source code (not summaries or blog posts)
2. Select a concrete edge-case scenario that exercises the authorization boundary
3. Trace which spec sections, schema fields, and code classes are relevant
4. Run the scenario in code and record the exact outcome
5. Document what the protocol handles well, and where the gap is
6. Evaluate whether AGF adds non-redundant value for that specific gap
7. Cite every claim to a spec section or source file

Findings that show AGF is redundant are recorded honestly. Findings that show the existing protocol is strong are recorded honestly. The tests exist to build an evidence base, not to confirm a predetermined conclusion.

---

## How to Run

```bash
# AP2 hotel booking test
python3 validation/ap2-hotel-booking/scenario.py

# TACP mandate exceeded test
python3 validation/tacp-mandate-exceeded/scenario.py
```

Python 3.8+ required. No external dependencies beyond `pydantic`.
