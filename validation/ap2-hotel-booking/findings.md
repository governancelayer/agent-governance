# AP2 Findings: Hotel Booking Price Change

**Test Version:** 1.0.0
**Date:** 2026-03-12
**Spec Reviewed:** `ap2/docs/specification.md` (full), `ap2/src/ap2/types/mandate.py`, `ap2/src/ap2/types/payment_request.py`

---

## What AP2 Gets Right

**1. The VDC architecture is coherent and dispute-friendly.**
The three-mandate system (IntentMandate → CartMandate → PaymentMandate) creates a verifiable chain of evidence. The adjudicator scenario in §6 Table 6.1 directly names "Mispick, Unapproved by User" as a recognized dispute category. If the budget constraint is later parsed from the IntentMandate's natural language field, the card network has something concrete to work with.

**2. The CartMandate TTL is a genuine safety mechanism.**
Spec §4.1.1 specifies a 5–15 minute expiry on CartMandate JWTs, forcing the agent to re-fetch the cart at current prices before submitting payment. This is a real, implementable guard against stale-price execution. This is good engineering.

**3. `user_cart_confirmation_required` is a meaningful control.**
The boolean field in IntentMandate (§5.2) gives users a formal way to grant or withhold autonomous purchase authority. Setting this to `false` creates a clear paper trail of delegated authority, even if the budget question is unresolved.

**4. PaymentMandate enables network/issuer visibility.**
Per §4.1.3, the PaymentMandate can be appended to existing transaction authorization packets. This is an additive approach that doesn't require legacy systems to be rebuilt. It's pragmatic.

---

## What AP2 Leaves Undefined (Honest Assessment)

### Gap 1 — No Machine-Readable Budget Field
**Evidence:** `ap2/src/ap2/types/mandate.py`, `IntentMandate` class (lines 32–76).

The IntentMandate has: `natural_language_description`, `user_cart_confirmation_required`, `merchants`, `skus`, `requires_refundability`, `intent_expiry`. There is no `max_value`, `max_total_amount`, `spending_limit`, or equivalent numeric field.

Budget constraints live entirely in the natural language description. This makes machine validation impossible and dispute adjudication dependent on NLP interpretation of free text.

The spec acknowledges the human-not-present scenario with "don't spend more than $1000" (§5.2), but this remains in the narrative, not in the schema.

**Impact:** Dispute adjudicators cannot programmatically determine whether the agent violated a budget mandate. They must read the natural language field and make a judgment call.

### Gap 2 — No Price Change Re-Confirmation Protocol
**Evidence:** §7.1 transaction flow (32-step sequence). There is no step for "re-check mandate after CartMandate expiry."

The spec says (§7.1 Step 5): "All selections that may alter a cart price must be completed prior to the CartMandate being able to be created." This implies price should be final before mandate creation, but it doesn't define what happens when a CartMandate expires and the re-fetched price differs from the original quote.

If the new CartMandate price exceeds the original IntentMandate budget, the protocol flow has no defined re-confirmation step. The agent simply creates a new PaymentMandate at the new price.

**Impact:** In the hotel booking scenario, the agent can legally (under AP2) proceed at €930 when the user said €900, because no part of the protocol enforces the natural language budget at this transition point.

### Gap 3 — No Mandate Enforcement Layer
**Evidence:** Spec §4 (VDC architecture). VDCs are evidence objects, not enforcement objects.

AP2 creates excellent audit artifacts but has no runtime enforcement mechanism. No part of the protocol prevents an agent from creating a PaymentMandate that exceeds the values in the IntentMandate. The CartMandate merchant signature doesn't compare against IntentMandate constraints. The Credential Provider doesn't receive the IntentMandate to verify. The Merchant Payment Processor doesn't check it either.

The protocol creates the evidence for adjudication *after* something goes wrong. It doesn't prevent it from going wrong.

**Impact:** The mandate framework is court-friendly but not runtime-safe.

### Gap 4 — Liability Table Has Natural Language Ambiguity
**Evidence:** §6 Table 6.1, "Mispick, Unapproved by User" row.

Key evidence listed: "The Intent Mandate vs. the cart transaction details should show the discrepancy."

This works when the discrepancy is clear (wrong item, wrong SKU). It's ambiguous when the discrepancy is "price slightly over NL-stated budget." The adjudicator must decide: Was €930 a "violation" of "budget €900" given that `user_cart_confirmation_required=False`? AP2 doesn't answer this.

### Gap 5 — `user_cart_confirmation_required=False` Creates Ambiguity About Budget Scope
The user set `user_cart_confirmation_required=False` to allow autonomous booking. Does this authorization extend to price changes? To price changes that exceed the stated budget? The spec doesn't define the scope of this flag in relation to budget constraints.

This is a genuine design question without a clear answer in the current spec.

---

## What Breaks in Production

| Issue | Severity | Evidence |
|---|---|---|
| Budget enforcement requires NLP on dispute artifacts | High | `mandate.py` — no `max_value` field |
| Agent's tolerance rule is invisible to all parties | High | No tolerance field in any mandate type |
| CartMandate expiry + price change has no defined handling | Medium | §7.1 flow has no "re-check mandate" step |
| `user_cart_confirmation_required=False` + budget overage = ambiguous liability | High | §5.2 + §6 combined |
| Risk field in JSON "intentionally left open-ended" (spec §7.4) | Medium | Spec §7.4 explicitly says this |

---

## Verdict

AP2 v0.1 is a well-structured protocol for establishing audit trails in agentic commerce. The VDC framework and dispute table are genuinely useful. However, for the specific price-change scenario tested here, AP2 provides strong evidence collection but no enforcement.

The budget constraint gap is not a minor oversight. Budget enforcement is the primary consumer protection mechanism in autonomous purchasing. Leaving it in natural language means it cannot be machine-validated, and disputes involving it will require human judgment — which defeats the purpose of having structured VDCs.

AP2's authors appear to be aware of some of these gaps (see §9 "A Call for Ecosystem Collaboration"), and the v1.x roadmap mentions "human-not-present scenarios" as a priority. This is early-stage, not broken-by-design.
