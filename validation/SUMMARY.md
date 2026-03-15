# Protocol Test Summary: AP2 vs TACP

**Tested by:** George Vagenas
**Date:** 2026-03-12
**Methodology:** Read actual specs, trace scenarios through real code, report what was found.

---

## What Was Tested

Two concrete scenarios were run against two real protocol implementations:

1. **AP2 (Google Agent Payments Protocol v0.1)** — Hotel booking where the price changes between quote and checkout, slightly exceeding the user's stated budget. The agent proceeds using a self-defined 10% tolerance.

2. **TACP (Forter Trusted Agentic Commerce Protocol v2025-11-12)** — Electronics purchase where a post-checkout shipping surcharge pushes the total above the consumer's $500 spending mandate.

---

## Side-by-Side Coverage Comparison

| Concern | AP2 | TACP | Notes |
|---|---|---|---|
| **Agent identity authentication** | Partially (via A2A protocol) | ✅ Strong (JWS+JWE, JWKS) | AP2 defers to A2A/MCP for identity; TACP owns this directly |
| **User authorization evidence** | ✅ CartMandate + PaymentMandate (signed VDCs) | ⚠️ `session.consent` (free text) | AP2's VDCs are cryptographically stronger for dispute evidence |
| **Message integrity** | ✅ JWT signatures on VDCs | ✅ JWE encryption + JWS | Both strong |
| **Replay attack prevention** | ✅ JTI on mandates | ✅ JTI on JWTs | Both specified |
| **Machine-readable spending limit** | ❌ Budget in NL string only | ❌ No mandate concept | Neither protocol covers this |
| **Post-checkout price change handling** | ❌ Not defined | ❌ Not defined | Both silent |
| **Mandate enforcement (runtime)** | ❌ Evidence only, no enforcement | ❌ Out of scope | Neither enforces |
| **Dispute resolution protocol** | ✅ Table 6.1 (structured scenarios) | ❌ Callback only | AP2 has a structured dispute framework; TACP does not |
| **Fraud signal delivery** | ⚠️ Risk field "intentionally open-ended" (§7.4) | ✅ Per-recipient encrypted JWEs | TACP significantly better here |
| **Multi-recipient data isolation** | ⚠️ Partial (role-based architecture) | ✅ Per-JWE data isolation | TACP's multi-recipient encryption is superior |
| **Delivery obligation tracking** | ❌ Not defined | ❌ Not defined | Neither covers fulfillment state |
| **Inter-protocol interoperability** | A2A / MCP extension | Standalone HTTP protocol | Different architectural approaches |

---

## Specific Gaps Found (With Evidence)

### Gap 1: No Machine-Readable Spending Limits in Either Protocol

**AP2 evidence:** `ap2/src/ap2/types/mandate.py` — `IntentMandate` class has `natural_language_description` but no `max_value` or equivalent numeric field.

**TACP evidence:** `tacp/schema/2025-11-12/schema.json` — full schema review shows no `mandate`, `spending_limit`, or `max_authorized_amount` field at any schema level.

**Impact:** Consumer spending mandates are either in free text (AP2) or not transmitted at all (TACP). This is the primary consumer protection mechanism in autonomous purchasing, and neither protocol has it machine-readable in v0.1.

### Gap 2: Post-Checkout Price Change Handling Is Undefined in Both

**AP2 evidence:** §7.1 32-step transaction flow has no "re-check mandate after CartMandate expiry" step. Spec §7.1 Step 5 says price must be final before CartMandate creation, but doesn't define what happens when the CartMandate expires and a new price is available.

**TACP evidence:** `tacp/sdk/python/src/sender.py` and `recipient.py` — authentication is a point-in-time event. No re-auth flow exists in the SDK. No callback type triggers re-authorization.

**Impact:** In both scenarios, a price change after initial authorization proceeds without re-confirmation, creating the conditions for the disputes tested.

### Gap 3: Dispute Resolution Evidence Is Incomplete in Different Ways

**AP2:** Provides Table 6.1 with named dispute scenarios. But budget violations are ambiguous because the budget is in natural language, requiring human interpretation.

**TACP:** Provides partial evidence (authentication proof for the initial amount). Has no structured dispute protocol. Callback notifications are not dispute evidence.

### Gap 4: AP2 Risk Field Is Explicitly Underdefined

**Evidence:** AP2 spec §7.4: "The v0.1 implementation includes a Risk field in the JSON exchange between the various entities but it is intentionally left open-ended for now."

This is an honest acknowledgment in the spec itself. The risk/fraud signal layer is deferred to ecosystem participants to define.

---

## What Both Protocols Do Well

**AP2:**
- The three-mandate VDC architecture (IntentMandate → CartMandate → PaymentMandate) is a coherent, well-structured audit chain.
- CartMandate TTL with merchant signature is a real safety mechanism.
- The dispute table in §6 is useful and names specific scenarios.
- The `user_cart_confirmation_required` boolean gives users a formal delegation mechanism.

**TACP:**
- JWS+JWE cryptography is well-implemented and well-specified.
- Multi-recipient data isolation (per-JWE encryption) is a genuine improvement over current checkout APIs.
- The fraud signal layer (forterToken, device data) in a separately encrypted JWE is architecturally sound.
- Replay attack prevention is clearly specified and required.

---

## AGF Relevance Assessment

Based on the tests, AGF's three primitives (DAE, TCR, DBA) are complementary to both protocols, not competitive.

**DAE (Delegated Authority Envelope):**
Directly addresses the machine-readable spending limit gap that neither AP2 nor TACP covers. `max_value` constraint with `ERR_DAE_MAX_VALUE_EXCEEDED` is the enforcement mechanism both scenarios needed but neither protocol provided. This is genuine, non-redundant value.

**TCR (Transaction Commitment Record):**
Addresses the delivery obligation tracking gap. Neither AP2 nor TACP has a first-class mechanism for tracking whether transaction commitments (delivery, fulfillment) were honored. TCR fills this gap and provides structured dispute evidence that goes beyond authentication-only proof.

**DBA (Data Boundary Assertion):**
Relevant for TACP deployments where fraud signal data is shared across organizational boundaries. TACP's JWE provides confidentiality; DBA adds retention limits and egress controls. Less critical for AP2 which addresses PCI/PII separation through role architecture.

---

## Recommendation

### Do not retire AGF.

The gaps found are real and consistent across both protocols. Machine-readable spending limits, post-checkout modification governance, and delivery commitment tracking are not covered by either AP2 or TACP v0.1. AGF's primitives address these gaps with concrete, implementable specifications.

### Pivot AGF from a standalone protocol to a middleware enforcement layer.

The most viable path is not AGF as a separate competing protocol, but AGF as the governance glue between AP2 and TACP:

```
Consumer Mandate → DAE (enforcement)
       ↓
TACP (authentication: who is the agent?)
       ↓
AP2 (commerce: what was agreed to?)
       ↓
TCR (accountability: were the commitments met?)
```

**Specific development priorities for AGF:**

1. Define how DAE is evaluated before AP2 PaymentMandate creation (before Step 19 in AP2 §7.1).
2. Define how TCR evidence references AP2 mandate hashes and TACP JTI identifiers.
3. Define how DAE `max_value` triggers TACP re-authentication when a post-checkout modification exceeds the constraint.

### Don't over-scope AGF.

AGF adds real value at the mandate enforcement and commitment tracking layer. It does not need to replicate authentication (TACP does this well) or audit trail creation (AP2 does this reasonably well). Keep scope tight.

---

## Summary Table

| Assessment | AP2 | TACP | AGF |
|---|---|---|---|
| Core value | Audit trail for commerce | Agent authentication | Mandate enforcement |
| V0.1 completeness | 70% (budget gaps, NL only) | 80% (authentication scope) | 60% (draft specs, no implementation) |
| Dispute handling | ✅ Structured framework | ❌ Notification only | ✅ TCR (complementary) |
| Mandate enforcement | ❌ Not enforced | ❌ Out of scope | ✅ DAE max_value |
| Retire? | No | No | No — pivot scope |
| Priority gaps | Machine-readable budget fields (v1.x roadmap) | Mandate layer integration | DAE-AP2-TACP integration spec |
