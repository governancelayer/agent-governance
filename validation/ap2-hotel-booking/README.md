# Test 1: AP2 — Hotel Booking Price Change Scenario

**Protocol:** Google Agent Payments Protocol (AP2) v0.1
**Spec Source:** `ap2/docs/specification.md`
**Types Source:** `ap2/src/ap2/types/`
**Test Version:** 1.0.0
**Date:** 2026-03-12

---

## Scenario Description

A consumer's AI agent (Shopping Agent) is tasked with booking a hotel room. The user creates a Human-Not-Present IntentMandate: "Book me a 3-night stay at any 4-star hotel in Berlin for April 10–13. Budget is €300/night, max €900 total." The agent finds a room at €280/night (€840 total). Between the time the agent gets the quoted price and submits the payment, the hotel's dynamic pricing engine changes the rate to €310/night (€930 total). The agent proceeds because €930 is within a self-defined 10% tolerance over the €900 mandate ceiling. The consumer later disputes the charge, claiming the agent should have re-confirmed before exceeding the stated €900 budget.

---

## Step-by-Step Walkthrough (AP2 Spec)

### Step 1 — Mandate Creation (Spec §4.1.2, §5.2)

The user creates an **IntentMandate** via the Shopping Agent. Per `ap2/src/ap2/types/mandate.py`:

```python
class IntentMandate(BaseModel):
    user_cart_confirmation_required: bool  # False = agent can proceed without re-confirming
    natural_language_description: str      # "Book hotel... budget €900"
    merchants: Optional[list[str]]         # None = any merchant
    requires_refundability: Optional[bool] # False
    intent_expiry: str                     # ISO 8601
```

**Observation:** The `IntentMandate` schema has a `natural_language_description` field and a boolean `user_cart_confirmation_required`. There is **no machine-readable numeric budget field** in v0.1. The budget is embedded in the natural language string. There is no `max_value`, `price_tolerance_pct`, or `threshold` field anywhere in the AP2 type definitions.

The user sets `user_cart_confirmation_required=False`, meaning the agent is authorized to book without re-asking the user.

### Step 2 — Agent Discovers Merchant and Gets Quoted Price (Spec §5.2)

The Shopping Agent discovers a compliant hotel Merchant Agent via the A2A registry. It sends the IntentMandate to the Merchant Agent (Spec §7.1, Step 8). The merchant quotes €280/night = €840 total for three nights.

### Step 3 — Merchant Signs CartMandate (Spec §4.1.1, §7.1 Steps 9–12)

The Merchant Agent creates a **CartMandate**. Per `ap2/src/ap2/types/mandate.py`:

```python
class CartContents(BaseModel):
    id: str
    user_cart_confirmation_required: bool
    payment_request: PaymentRequest   # Contains final price
    cart_expiry: str
    merchant_name: str
```

The merchant signs the CartMandate with a short-lived JWT (spec §4.1.1 merchant_authorization field), cryptographically locking the price at **€840** for 5–15 minutes (spec §4.1.1 states: "short-lived expiration (e.g., 5-15 minutes)").

**Key fact from spec §7.1 Step 10:** "The cart mandate is first signed by the merchant entity (not an Agent) to guarantee they will fulfill the order based on the SKU, price and shipping information."

### Step 4 — Dynamic Price Change Before Payment Submission

Between the merchant signing the CartMandate and the agent actually submitting the PaymentMandate, the hotel's dynamic pricing updates. When the agent requests the final payment credentials from the Credentials Provider (Step 17), the cart has expired. The agent fetches a new CartMandate and the price is now **€930** (€310/night × 3).

**AP2 does not define what the Shopping Agent should do here.** The spec says in §7.1 Step 5: "All selections that may alter a cart price must be completed prior to the CartMandate being able to be created." But it gives no guidance on what happens when a price changes between mandate creation and payment execution, or when the new price exceeds the user's stated budget.

### Step 5 — Agent Applies Self-Defined Threshold (Undefined in AP2)

The Shopping Agent has been programmed with a 10% tolerance rule. €930 is 3.3% over the €900 mandate budget. The agent creates a new PaymentMandate at €930 and proceeds.

**AP2 status:** This threshold logic is **not defined anywhere in the spec**. There is no `tolerance_pct` field, no `mandate_check()` enforcement, no mechanism that would block this or log it as a mandate deviation.

### Step 6 — PaymentMandate Creation (Spec §4.1.3, §7.1 Steps 19–24)

The Shopping Agent creates a **PaymentMandate**:

```python
class PaymentMandateContents(BaseModel):
    payment_mandate_id: str
    payment_details_id: str
    payment_details_total: PaymentItem   # €930 — the new, higher price
    payment_response: PaymentResponse    # tokenized card
    merchant_agent: str
    timestamp: str
```

The PaymentMandate at this point contains `€930` as the total. The original IntentMandate said "budget €900" in natural language.

**Per spec §4.1.3:** "While the Cart and Intent mandates are required by the merchant to fulfill the order, separately the protocol provides additional visibility into the agentic transaction to the payments ecosystem."

The PaymentMandate is sent to the user for device-level signing (Step 20), or per `user_cart_confirmation_required=False`, this step is bypassed. **This is the critical bifurcation in the spec.**

### Step 7 — User Signing Decision (Spec §5.2 Point 1)

**In Human-Not-Present mode with `user_cart_confirmation_required=False`:**
The user is NOT shown the €930 price change. No re-confirmation is required by protocol. The agent proceeds to payment execution.

**In Human-Present mode:**
The user would see the new CartMandate with €930 and could reject it.

### Step 8 — Payment Execution (Spec §7.1 Steps 25–32)

The Merchant Payment Processor receives the PaymentMandate, requests credentials from the CP, processes €930 payment, and returns a receipt. The issuer approves.

### Step 9 — Dispute Filed

The consumer receives the €930 charge and disputes it, claiming the agent exceeded its €900 budget mandate.

**AP2 Dispute Handling (Spec §6, Table 6.1):**

The dispute most closely matches:

| Scenario | Description | Key Evidence |
|---|---|---|
| **Mispick, Unapproved by User** | "The Shopping Agent autonomously purchases an item that violates the user's signed Intent Mandate (e.g., exceeds budget or is the wrong item)." | "The Intent Mandate vs. the cart transaction details should show the discrepancy." |

The adjudicator (card network) would receive:
- The IntentMandate (natural language: "budget €900")
- The CartMandate/PaymentMandate (total: €930)
- The user's device attestation (if signed)

**Problem:** The adjudicator must interpret natural language ("budget €900") from the IntentMandate and compare it to the €930 in the PaymentMandate. There is no machine-readable budget field. The adjudicator has to do linguistic parsing to identify the discrepancy.

---

## What AP2 Handles

**Per the actual spec (with section references):**

1. **Mandate structure**: Cart and Intent mandates are well-defined cryptographic objects (§4.1). The IntentMandate captures intent before purchase.
2. **Merchant price lock**: CartMandate is merchant-signed for a short TTL, preventing price changes within the mandate window (§4.1.1, §7.1 Step 10).
3. **Dispute evidence chain**: The spec provides a Table 6.1 with "Mispick, Unapproved by User" that directly covers budget violation disputes (§6).
4. **Human-not-present flag**: `user_cart_confirmation_required` gives agents explicit authorization to proceed without re-confirmation (§5.2, `mandate.py`).
5. **PaymentMandate visibility**: AI agent presence and modality signals are shared with issuers/networks (§4.1.3).
6. **Challenge mechanism**: Any party can force a step-up challenge (§5.5), which could theoretically intercept a budget-exceeding transaction.

## What AP2 Leaves Undefined

1. **No machine-readable budget field in IntentMandate**: The budget lives in `natural_language_description` only. There is no `max_value` or `max_total_amount` field. Confirmed by inspection of `ap2/src/ap2/types/mandate.py`.
2. **No price-change handling protocol**: When a CartMandate expires and a new price is available, the spec is silent on what the agent should do. No "re-check mandate" step exists in the 32-step sequence.
3. **No tolerance/threshold mechanism**: The spec does not define how or whether agents may apply tolerance windows around mandate budgets. This is entirely agent-implementation-specific.
4. **Dispute adjudication requires NLP**: Because the budget is in natural language, comparing IntentMandate to PaymentMandate for budget violations is ambiguous and requires human interpretation.
5. **Mandate enforcement is advisory, not enforced**: AP2 provides the evidence but has no runtime enforcement layer. Nothing in the protocol *prevents* the agent from exceeding the budget.
6. **Cart expiry behavior undefined**: What happens when a CartMandate expires during the payment flow? The spec says the cart has a TTL (§4.1.1) but does not define the agent's re-confirmation obligation when a price changes on renewal.

## What Breaks

1. The consumer's dispute is **technically valid** under Table 6.1, but winning it depends on the card network adjudicator interpreting natural language in the IntentMandate. This is operationally fragile.
2. The agent's 10% tolerance rule is **invisible to all other parties** in the protocol. No other actor knows the threshold was applied.
3. If `user_cart_confirmation_required=False` was set, the spec's design intent may actually **support the agent's decision**, but this conflicts with the consumer's reasonable expectation that the "budget €900" was a hard limit.

---

## Running the Code

```bash
pip install pydantic
python scenario.py
```
