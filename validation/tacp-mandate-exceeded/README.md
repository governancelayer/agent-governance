# Test 2: TACP — Mandate Exceeded by Post-Checkout Shipping Surcharge

**Protocol:** Forter Trusted Agentic Commerce Protocol (TACP) v2025-11-12
**Schema Source:** `tacp/schema/2025-11-12/schema.json`
**SDK Source:** `tacp/sdk/python/src/` (sender.py, recipient.py, errors.py)
**README Source:** `tacp/README.md`, `tacp/AGENTS.md`
**Test Version:** 1.0.0
**Date:** 2026-03-12

---

## Scenario Description

A consumer's AI agent is KYA-verified with a valid consumer mandate capping spending at $500. The agent searches an online retailer and finds a bundle deal for electronics at $480 — within the $500 mandate. It proceeds to checkout using TACP for authenticated agent identity. During the checkout flow the merchant applies a $30 "express shipping" surcharge post-checkout (after the initial order submission), bringing the total to $510. This exceeds the $500 consumer mandate by $10. The consumer disputes the $510 charge, claiming their agent should have caught the mandate violation.

---

## Step-by-Step Walkthrough (TACP Protocol)

### Step 1 — Agent Authentication Setup (README.md §Key Generation)

The agent operator generates RSA keys and publishes a JWKS endpoint:

```
https://shopping-agent.example.com/.well-known/jwks.json
```

Per `tacp/README.md`: "Signs JWTs to prove identity" and "Encrypts sensitive user data for specific recipients."

The merchant and Forter publish their own JWKS encryption endpoints. This establishes the trust fabric for the transaction.

**TACP covers:** Agent identity authentication, key distribution via JWKS standard.

### Step 2 — KYA Verification (README.md §Key Benefits)

The TACP README describes KYA (Know Your Agent) verification as part of the agent trust model:

> "Your agent is recognized and trusted by merchant sites, leading to near-100% success rates for login and checkout."

The KYA verification status is conveyed in the TACP message via the `session.consent` field in the schema (`schema/2025-11-12/schema.json`). Per the voice assistant example (`examples/voice_assistant_travel.json`):

```json
"session": {
    "id": "assistant-session-12345",
    "channel": "VOICE",
    "source": "assistant-name",
    "intent": "Purchase electronics bundle",
    "consent": "User confirmed purchase via authenticated session"
}
```

**TACP covers:** Session context, agent identity, user consent signal.

**TACP does NOT cover:** The consumer mandate amount ($500 limit). There is no `mandate_id`, `spending_limit`, or `max_authorized_amount` field anywhere in the TACP schema. Confirmed by review of `tacp/schema/2025-11-12/schema.json`.

### Step 3 — Agent Constructs TACP Message for Checkout (sender.py §generate_tac_message)

The agent uses `TACSender.generate_tac_message()` (from `tacp/sdk/python/src/sender.py`).

The protocol flow:
1. Agent signs a JWT with its RSA private key (JWS)
2. For each recipient (merchant, Forter fraud platform), creates a separate JWE
3. Each JWE contains only the data intended for that recipient
4. All JWEs are bundled into a multi-recipient container and base64-encoded

The data payload for the merchant includes:

```json
{
    "schemaVersion": "2025-11-12",
    "user": {
        "id": "user-123",
        "email": {"address": "consumer@example.com"},
        "paymentMethods": [{"type": "CARD", "card": {"last4": "4242"}}]
    },
    "order": {
        "totalAmount": 480.00,
        "currency": "USD",
        "items": [{"name": "Electronics Bundle", "price": 480.00}]
    },
    "session": {
        "intent": "Purchase electronics bundle for $480",
        "consent": "User authorized purchase via KYA-verified agent"
    }
}
```

**TACP covers:** Agent-to-merchant secure data transmission, user identity, order details.

**TACP does NOT cover:** The $500 spending limit is not transmitted. There is no `consumer_mandate.max_value` field in the TACP schema. The merchant receives the order total ($480) but has no visibility into the consumer's mandate ceiling.

### Step 4 — Merchant Processes Initial Order

The merchant receives and decrypts the TACP message using `TACRecipient.process_tac_message()` (from `tacp/sdk/python/src/recipient.py`).

The merchant:
1. Decrypts their JWE using their private key
2. Verifies the agent's JWT signature against the agent's JWKS endpoint
3. Validates `aud` matches merchant domain, checks `exp` and `iat`
4. Extracts the order data: $480 total

The merchant approves the order. TACP has successfully authenticated the agent and verified the user data was not tampered with.

**TACP covers:** Full cryptographic verification of agent identity and message integrity.

### Step 5 — Merchant Applies Post-Checkout Shipping Surcharge

After initial order approval, the merchant adds a $30 "express shipping" surcharge, updating the total to $510.

**Critical question:** Does TACP have any mechanism to prevent, flag, or require re-confirmation when an order total changes post-checkout?

**Answer:** No. TACP is a message-authentication protocol. It authenticates the agent's identity when the message is sent. It does not:
- Monitor subsequent order modifications
- Have a "re-authorize on amount change" flow
- Transmit the consumer's spending mandate to the merchant
- Define a callback or notification protocol when an order amount increases

The `callbacks` array in the TACP schema (`schema.json` line 29) can carry webhook/email/SMS callbacks for events like `ORDER_STATUS` and `DISPUTE` (as seen in `examples/voice_assistant_travel.json`), but these are notification channels, not re-authorization flows.

### Step 6 — Consumer Dispute Filed

The consumer receives a $510 charge. Their expectation was $480 (the authenticated order amount) or at most $500 (their stated mandate limit). They dispute:

1. The agent should not have authorized $510 (mandate exceeded)
2. The $30 surcharge was applied after authentication (no re-auth)

**What TACP evidence exists for this dispute:**

- The TACP message authenticates the agent's identity and the user's session at the time of the original checkout.
- The signed JWT contains `"intent": "Purchase electronics bundle for $480"` — the $480 amount the agent authorized.
- However, the TACP message does NOT contain the consumer's $500 mandate.
- The $510 total was never signed by the agent via TACP — it was a post-checkout merchant modification.

**TACP covers:** Evidence that the agent was authenticated and the user consented to the original $480 order.

**TACP does NOT cover:**
- The $500 mandate constraint
- The $30 post-checkout modification
- Any mechanism to detect or dispute amount changes after initial authentication

### Step 7 — Dispute Evidence Review

TACP provides:
- Signed JWT showing agent identity and original order intent ($480)
- Session context showing user consent
- Forter fraud signal data (in the separately encrypted Forter-recipient JWE)

TACP does NOT provide:
- Evidence that the $510 total was authorized by the agent or user
- Evidence that the mandate was exceeded
- Any mechanism linking the $500 mandate to the transaction

The dispute adjudicator has a partial picture: they can prove the agent was authenticated for a $480 purchase, but they cannot prove whether the consumer's mandate was $500, $1000, or unlimited.

---

## What TACP Handles

**Per the actual spec (with source references):**

1. **Agent identity authentication**: JWS signatures prove the agent's identity (`sender.py`, `README.md §Key Benefits`).
2. **Message integrity**: JWE encryption prevents tampering in transit (`sender.py` lines 262–278).
3. **Replay attack prevention**: JTI claim tracking (`README.md §Replay Attack Prevention`).
4. **Multi-recipient data isolation**: Each recipient receives only their encrypted data slice (`sender.py §add_recipient_data`).
5. **User session context**: `session.consent` and `session.intent` convey user authorization signals (`schema.json §Session`).
6. **Fraud signal delivery**: Sensitive fraud data (IP, device fingerprint, forterToken) encrypted for the fraud platform only (`examples/voice_assistant_travel.json`).
7. **User KYC data delivery**: Email verification status, authentication method, account age — all encrypted per-recipient (`schema.json §User.email.verifications`).

## What TACP Leaves Undefined

1. **No consumer mandate / spending limit concept**: The TACP schema has no `mandate`, `spending_limit`, or `max_authorized_amount` field. Confirmed by full review of `tacp/schema/2025-11-12/schema.json`. The consumer's $500 limit is invisible to the protocol.
2. **No post-checkout amount change handling**: TACP authenticates the initial request. If the merchant modifies the total after authentication, TACP has no re-authorization flow.
3. **No dispute resolution mechanism**: TACP has callbacks for `DISPUTE` events (`examples/voice_assistant_travel.json`), but these are notification webhooks, not dispute handling protocols. There is no structured dispute evidence format.
4. **No mandate violation detection**: TACP cannot determine that a $510 charge violated a $500 mandate because the mandate was never part of the protocol.
5. **No order modification signing**: When the merchant changes the total from $480 to $510, no new TACP-authenticated message is created. The modification happens outside the protocol.

## What Breaks

1. The consumer's $500 mandate is enforced nowhere in the TACP flow. If it exists, it lives in the agent's internal logic — invisible to the merchant, the fraud platform, and the dispute adjudicator.
2. The $510 total was never authenticated by TACP. The agent signed a message for $480. The $30 surcharge was applied unilaterally by the merchant.
3. The dispute adjudicator cannot use TACP evidence to resolve the mandate question because the mandate was never transmitted.

---

## Running the Code

```bash
python scenario.py
```

No external dependencies required. The crypto operations are simulated.
