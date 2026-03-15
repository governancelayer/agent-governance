# TACP Findings: Mandate Exceeded by Post-Checkout Surcharge

**Test Version:** 1.0.0
**Date:** 2026-03-12
**Spec Reviewed:** `tacp/schema/2025-11-12/schema.json` (full), `tacp/sdk/python/src/sender.py`, `tacp/sdk/python/src/recipient.py`, `tacp/README.md`, `tacp/AGENTS.md`, `tacp/examples/voice_assistant_travel.json`

---

## What TACP Gets Right

**1. The authentication model is technically strong.**
JWS + JWE is a well-established cryptographic pattern. Agent identity is verifiably tied to a domain via JWKS. The message can't be tampered with in transit. Replay attacks are prevented by JTI tracking. This is solid, standard cryptographic engineering.

Per `tacp/README.md §Replay Attack Prevention`: "Recipients MUST implement replay attack prevention by tracking JWT IDs (`jti` claims)." This is clearly specified, not vague.

**2. Multi-recipient data isolation is a genuine innovation.**
Each recipient (merchant, fraud platform) receives only the data intended for them, encrypted separately. The merchant's JWE doesn't contain fraud signals. The fraud platform's JWE doesn't contain the merchant's order data. Per `sender.py` lines 240–278, this is implemented at the JWT payload level, not just the transport level. This is more privacy-preserving than most checkout APIs.

**3. The `session.consent` and `session.intent` fields are useful for user intent capture.**
Per `examples/voice_assistant_travel.json`, the `session.intent` field ("Book round-trip flight and hotel for family vacation to Orlando") and `session.consent` field ("User confirmed booking via voice command") provide a lightweight mechanism for recording what the user authorized. This is not as strong as a signed VDC, but it's something.

**4. The fraud signal layer is well-conceived.**
The Forter-specific data (device fingerprint, forterToken, IP address) in the fraud platform's encrypted JWE mirrors the actual data Forter uses for fraud decisions. The protocol enables this without exposing sensitive fraud signals to the merchant. This is a meaningful operational improvement over current checkout flows where fraud signals are either absent or visible to all parties.

---

## What TACP Leaves Undefined (Honest Assessment)

### Gap 1 — No Consumer Mandate / Spending Limit Concept
**Evidence:** Full review of `tacp/schema/2025-11-12/schema.json`.

The schema root properties are: `schemaVersion`, `user`, `order`, `session`, `items`, `callbacks`, `custom`.

The `Order` object contains: `orderId`, `totalAmount`, `currency`, and order-level metadata. There is no `mandate`, `spending_limit`, `authorized_max_amount`, `consumer_policy`, or equivalent field at any schema level.

The `User` object contains: `id`, `merchantId`, `email`, `phone`, `preferences`, `loyalties`, `paymentMethods`, `addresses`, `created`, `lastLogin`, `status`, `type`. No mandate-related field.

The `Session` object contains: `id`, `channel`, `source`, `intent`, `consent`, and device/IP signals. The `consent` field is a free-text string, not a structured authorization object.

**Impact:** A consumer's $500 spending limit cannot be expressed in TACP. It doesn't flow from agent to merchant. The merchant has no way to know it was exceeded. The fraud platform has no way to flag it.

This is not a design flaw in TACP — TACP was not designed to carry spending mandate data. But it means TACP alone cannot solve mandate enforcement.

### Gap 2 — No Post-Checkout Amount Change Protocol
**Evidence:** `tacp/sdk/python/src/sender.py` and `recipient.py`.

TACP authenticates a specific message at a specific point in time. Once the message is sent and verified, there is no mechanism to:
- Detect that the merchant modified the total
- Re-authenticate the new amount
- Notify the agent that the order total changed
- Require the agent to re-sign an updated order

The `callbacks` array in the schema (`schema.json §callbacks`) provides webhook/email/SMS notification channels for events including `ORDER_STATUS` and `DISPUTE`. But callbacks are notification channels, not re-authorization flows. They don't create new TACP-authenticated messages.

**Impact:** The merchant's $30 shipping surcharge is applied entirely outside the TACP authentication boundary. The TACP message still references $480. The $510 total was never signed by the agent or transmitted via TACP.

### Gap 3 — No Dispute Resolution Protocol
**Evidence:** `tacp/README.md`, `tacp/schema/2025-11-12/schema.json`.

The README does not define a dispute resolution mechanism. The schema has a `DISPUTE` callback event type (`voice_assistant_travel.json`), but receiving a webhook notification about a dispute is not the same as providing structured evidence for dispute resolution.

TACP can prove:
- The agent was authenticated
- The user consented to a specific intent
- The order amount at the time of authentication was $480

TACP cannot prove:
- Whether the consumer's mandate was $500
- Whether the $510 charge was authorized
- Whether the surcharge was legitimate

The dispute adjudicator is left with incomplete evidence.

### Gap 4 — `session.consent` Is a Free-Text String
**Evidence:** `schema.json §Session`, `voice_assistant_travel.json`.

The consent field is `"User confirmed booking via voice command"` — a human-readable string with no structured machine-parseable format. It cannot be used to verify what specific amount or conditions the user authorized.

This contrasts with AP2's CartMandate, which uses a cryptographically signed, hash-verified, structured object to record user authorization.

---

## What Breaks in Production

| Issue | Severity | Evidence |
|---|---|---|
| Consumer mandate not transmitted | Critical (for mandate use case) | No mandate field in schema.json |
| Post-checkout modifications not re-authenticated | High | No re-auth flow in sender.py/recipient.py |
| Dispute evidence incomplete | High | No dispute protocol in README or schema |
| `session.consent` is opaque free text | Medium | schema.json Session definition |
| Fraud platform has no mandate visibility | Medium | Fraud data isolated in separate JWE |

---

## Scope Clarification: TACP's Actual Purpose

To be fair to TACP: it was designed for agent authentication and fraud prevention, not commerce governance. The README states:

> "A secure authentication and data encryption protocol that allows AI agents, merchants and merchant vendors to authenticate each other, maintain rich customer data, improve user experience, and prevent fraud."

The mandate enforcement gap is not because TACP failed to implement its goals. It's because mandate enforcement is outside its stated scope. The scenario tests whether TACP is sufficient for end-to-end agent commerce governance — and the answer is no, for the specific reason that it addresses authentication, not authorization constraints.

---

## Verdict

TACP is a well-implemented authentication protocol for agentic commerce. Its core value proposition — trusted agent identity, encrypted fraud signals, multi-recipient isolation — is genuine and useful. It solves real problems that merchants and fraud platforms face today.

For the mandate-exceeded scenario tested here, TACP provides partial but insufficient coverage:
- It proves the agent was authenticated for a $480 order.
- It does not prove, transmit, or enforce the $500 mandate.
- It has no mechanism to detect or flag the $30 post-checkout modification.

The gaps in this scenario are structural, not implementation bugs. They reflect a deliberate scope choice by TACP's designers to focus on authentication rather than authorization policy.
