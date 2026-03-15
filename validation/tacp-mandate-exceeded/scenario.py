"""
TACP Mandate-Exceeded Scenario
================================
Demonstrates how Forter's Trusted Agentic Commerce Protocol (TACP) handles
(or fails to handle) a situation where a merchant applies a post-checkout
shipping surcharge that pushes the transaction total over the consumer's
mandate ceiling.

Based on:
  - tacp/schema/2025-11-12/schema.json
  - tacp/sdk/python/src/sender.py
  - tacp/sdk/python/src/recipient.py
  - tacp/sdk/python/src/errors.py
  - tacp/README.md
  - tacp/examples/voice_assistant_travel.json

All cryptographic operations are simulated (stubbed) to make the scenario
runnable without actual RSA keys or JWKS endpoints.

Run: python scenario.py
"""

import base64
import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Simulated TACP Protocol Types
# (mirrors tacp/schema/2025-11-12/schema.json)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TACEmailVerification:
    method: str  # e.g., "EMAIL_OTP", "PASSKEYS", "BIOMETRIC"
    at: str      # ISO 8601 timestamp


@dataclass
class TACEmail:
    address: str
    verifications: List[TACEmailVerification] = field(default_factory=list)


@dataclass
class TACPaymentMethod:
    type: str    # "CARD", "WALLET", etc.
    card: Optional[Dict] = None


@dataclass
class TACUser:
    """Per schema.json User definition — no spending_limit or mandate field."""
    id: str
    email: Optional[TACEmail] = None
    paymentMethods: List[TACPaymentMethod] = field(default_factory=list)
    created: Optional[str] = None
    status: str = "ACTIVE"
    type: str = "INDIVIDUAL"


@dataclass
class TACOrder:
    """Per schema.json Order definition."""
    orderId: str
    totalAmount: float
    currency: str
    # NOTE: No consumer_mandate, no spending_limit, no max_authorized_amount field
    # This is the entire order definition per schema v2025-11-12


@dataclass
class TACSession:
    """Per schema.json Session definition."""
    id: str
    intent: str
    consent: str
    channel: str = "WEB"
    source: str = "ai-agent"
    ipAddress: Optional[str] = None
    userAgent: Optional[str] = None


@dataclass
class TACMessage:
    """The complete TACP message payload per schema.json (root object)."""
    schemaVersion: str
    user: Optional[TACUser] = None
    order: Optional[TACOrder] = None
    session: Optional[TACSession] = None
    # Note: items, callbacks, custom also exist in schema but omitted for brevity


# ─────────────────────────────────────────────────────────────────────────────
# Simulated TACP Crypto (stubs — real impl in tacp/sdk/python/src/)
# ─────────────────────────────────────────────────────────────────────────────

class SimulatedJWT:
    """
    Simulates JWS+JWE flow from tacp/sdk/python/src/sender.py
    Real flow: sign JWT with private key (JWS) → encrypt for recipient (JWE)
    """

    @staticmethod
    def sign(payload: dict, issuer_domain: str, recipient_domain: str) -> str:
        """Simulates TACSender.generate_tac_message() JWS step"""
        jti = str(uuid.uuid4())
        now = int(time.time())
        header = {"alg": "RS256", "typ": "JWT", "kid": f"key-{issuer_domain[:8]}"}
        full_payload = {
            "iss": issuer_domain,
            "aud": recipient_domain,
            "iat": now,
            "exp": now + 3600,
            "jti": jti,
            "data": payload,
        }
        # Simulate signed JWT (not real cryptography)
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        payload_b64 = base64.urlsafe_b64encode(json.dumps(full_payload).encode()).decode().rstrip("=")
        sig = hashlib.sha256(f"{header_b64}.{payload_b64}.{issuer_domain}".encode()).hexdigest()[:32]
        return f"{header_b64}.{payload_b64}.{sig}", jti

    @staticmethod
    def encrypt(signed_jwt: str, recipient_domain: str) -> str:
        """Simulates TACSender.generate_tac_message() JWE step"""
        # Simulate JWE by base64-encoding (real impl uses RSA-OAEP-256 + A256GCM)
        container = {
            "alg": "RSA-OAEP-256",
            "enc": "A256GCM",
            "kid": recipient_domain,
            "ciphertext": base64.b64encode(signed_jwt.encode()).decode(),
            "_note": "SIMULATED — real impl uses jose.jwe.encrypt in sender.py"
        }
        return base64.b64encode(json.dumps(container).encode()).decode()

    @staticmethod
    def decrypt(jwe_token: str, recipient_domain: str) -> dict:
        """Simulates TACRecipient.process_tac_message() decryption step"""
        container = json.loads(base64.b64decode(jwe_token).decode())
        signed_jwt = base64.b64decode(container["ciphertext"]).decode()
        parts = signed_jwt.split(".")
        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "==").decode())
        return payload


def generate_tac_message(
    sender_domain: str,
    recipients_data: Dict[str, dict]
) -> str:
    """
    Simulates TACSender.generate_tac_message() from sender.py lines 199–284.

    Real flow:
    1. For each recipient domain, sign JWT with sender private key (JWS)
    2. Encrypt the signed JWT with recipient's public key (JWE)
    3. Bundle all JWEs into multi-recipient container
    4. Base64-encode the container

    Per sender.py line 281:
    multi_recipient_message = {"version": SCHEMA_VERSION, "recipients": recipient_jwes}
    """
    recipient_jwes = []
    jtis = {}

    for domain, data in recipients_data.items():
        signed_jwt, jti = SimulatedJWT.sign(data, sender_domain, domain)
        encrypted = SimulatedJWT.encrypt(signed_jwt, domain)
        recipient_jwes.append({"kid": domain, "jwe": encrypted})
        jtis[domain] = jti
        print(f"  [TACSender] Signed JWT for {domain} (jti={jti[:8]}...)")
        print(f"  [TACSender] Encrypted JWE for {domain} (RSA-OAEP-256+A256GCM)")

    container = {"version": "2025-11-12", "recipients": recipient_jwes}
    encoded = base64.b64encode(json.dumps(container).encode()).decode()
    return encoded, jtis


def process_tac_message(
    tac_message: str,
    recipient_domain: str
) -> dict:
    """
    Simulates TACRecipient.process_tac_message() from recipient.py lines 156–309.

    Real flow:
    1. Decode base64 container
    2. Find the JWE for this recipient
    3. Decrypt JWE with recipient's private key
    4. Verify JWT signature against sender's JWKS
    5. Validate aud, iss, exp, iat, jti
    6. Return payload data
    """
    container = json.loads(base64.b64decode(tac_message).decode())
    recipients_list = [r["kid"] for r in container["recipients"]]

    our_jwe = None
    for recipient in container["recipients"]:
        if recipient["kid"] == recipient_domain:
            our_jwe = recipient["jwe"]
            break

    if not our_jwe:
        return {"valid": False, "errors": [f"Not a recipient: {recipient_domain}"]}

    payload = SimulatedJWT.decrypt(our_jwe, recipient_domain)

    print(f"  [TACRecipient] Decrypted JWE for {recipient_domain}")
    print(f"  [TACRecipient] Verified JWT signature from {payload.get('iss')}")
    print(f"  [TACRecipient] Validated: aud={recipient_domain}, exp=valid, jti={payload.get('jti','')[:8]}...")

    return {
        "valid": True,
        "issuer": payload.get("iss"),
        "data": payload.get("data"),
        "jti": payload.get("jti"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Protocol Actors
# ─────────────────────────────────────────────────────────────────────────────

class AIShoppingAgent:
    """
    Consumer's AI agent with KYA verification.
    Has an internal consumer mandate of $500 — but this is NOT transmitted via TACP.
    """

    def __init__(self, agent_domain: str, consumer_mandate_usd: float):
        self.domain = agent_domain
        self.consumer_mandate = consumer_mandate_usd
        print(f"[AIShoppingAgent] Init: domain={agent_domain}, mandate=${consumer_mandate_usd}")
        print(f"  NOTE: Consumer mandate of ${consumer_mandate_usd} is agent-internal — not part of TACP schema")

    def checkout(
        self,
        merchant_domain: str,
        fraud_platform_domain: str,
        order: TACOrder,
        user: TACUser,
        session: TACSession,
    ) -> tuple:
        """
        Sends TACP checkout message to merchant and fraud platform.
        Per tacp/sdk/python/src/sender.py TACSender.generate_tac_message()
        """
        print(f"\n[AIShoppingAgent] Generating TACP message for checkout")
        print(f"  Order total: ${order.totalAmount:.2f} (within mandate ${self.consumer_mandate:.2f})")

        merchant_data = {
            "schemaVersion": "2025-11-12",
            "user": {
                "id": user.id,
                "email": {"address": user.email.address if user.email else None},
                "paymentMethods": [{"type": "CARD", "card": {"last4": "4242"}}],
                "status": user.status,
            },
            "order": {
                "orderId": order.orderId,
                "totalAmount": order.totalAmount,
                "currency": order.currency,
                # NOTE: consumer_mandate not included — no such field in TACP schema
            },
            "session": {
                "id": session.id,
                "intent": session.intent,
                "consent": session.consent,
                "channel": session.channel,
            },
        }

        fraud_platform_data = {
            "schemaVersion": "2025-11-12",
            "session": {
                "id": session.id,
                "intent": session.intent,
                "ipAddress": "203.0.113.45",
                "userAgent": "AIAgent/2.1 (Chrome; macOS 14)",
                "deviceId": "device-abc123",
                "forterToken": "ftr_" + uuid.uuid4().hex[:12],
            },
            "user": {
                "id": user.id,
                "email": {
                    "address": user.email.address if user.email else None,
                    "verifications": [{"method": "EMAIL_OTP", "at": "2025-01-15T10:30:00Z"}],
                },
                "created": user.created,
            },
            "paymentMethods": [{"type": "CARD", "card": {"last4": "4242"}, "created": user.created}],
        }

        tac_message, jtis = generate_tac_message(
            sender_domain=self.domain,
            recipients_data={
                merchant_domain: merchant_data,
                fraud_platform_domain: fraud_platform_data,
            }
        )

        print(f"  [AIShoppingAgent] TACP message generated. Size: {len(tac_message)} bytes")
        print(f"  [AIShoppingAgent] Recipients: {merchant_domain}, {fraud_platform_domain}")
        return tac_message, jtis


class OnlineMerchant:
    """Simulates the merchant receiving TACP messages and processing orders."""

    def __init__(self, domain: str):
        self.domain = domain
        self.orders = {}

    def receive_checkout(self, tac_message: str, agent_domain: str) -> dict:
        """
        Decrypts and verifies TACP message.
        Per tacp/sdk/python/src/recipient.py TACRecipient.process_tac_message()
        """
        print(f"\n[OnlineMerchant] Processing TACP message from {agent_domain}")
        result = process_tac_message(tac_message, self.domain)

        if not result["valid"]:
            return {"approved": False, "reason": result.get("errors", ["Unknown error"])}

        order_data = result["data"].get("order", {})
        order_id = order_data.get("orderId")
        total = order_data.get("totalAmount")

        print(f"  [OnlineMerchant] Agent verified: issuer={result['issuer']}")
        print(f"  [OnlineMerchant] Order {order_id} approved at ${total:.2f}")

        self.orders[order_id] = {
            "initial_total": total,
            "current_total": total,
            "status": "approved",
            "agent_domain": agent_domain,
            "jti": result["jti"],
        }

        return {"approved": True, "order_id": order_id, "total": total}

    def apply_shipping_surcharge(self, order_id: str, surcharge: float) -> dict:
        """
        Applies a post-checkout shipping surcharge.
        This is OUTSIDE the TACP authentication flow — no re-authentication occurs.
        """
        if order_id not in self.orders:
            return {"error": "Order not found"}

        order = self.orders[order_id]
        old_total = order["current_total"]
        new_total = old_total + surcharge
        order["current_total"] = new_total

        print(f"\n[OnlineMerchant] Applying shipping surcharge to {order_id}")
        print(f"  Old total: ${old_total:.2f}")
        print(f"  Surcharge: +${surcharge:.2f}")
        print(f"  New total: ${new_total:.2f}")
        print(f"  NOTE: No new TACP message generated. Surcharge applied outside protocol.")
        print(f"  NOTE: Agent's TACP message still references ${old_total:.2f}. No re-auth triggered.")

        return {
            "order_id": order_id,
            "old_total": old_total,
            "new_total": new_total,
            "surcharge": surcharge,
            "tacp_authenticated_amount": old_total,
            "gap": "post-checkout modification outside TACP authentication boundary",
        }

    def charge_customer(self, order_id: str) -> dict:
        """Processes final payment at current (modified) total."""
        order = self.orders[order_id]
        total = order["current_total"]
        print(f"\n[OnlineMerchant] Processing payment for ${total:.2f}")
        print(f"  (Original TACP-authenticated amount was ${order['initial_total']:.2f})")
        return {"charged": total, "order_id": order_id}


class FraudPlatform:
    """Simulates Forter receiving encrypted fraud signals via TACP."""

    def __init__(self, domain: str):
        self.domain = domain

    def receive_signals(self, tac_message: str) -> dict:
        """Processes Forter-specific encrypted signals."""
        print(f"\n[FraudPlatform] Processing TACP fraud signals")
        result = process_tac_message(tac_message, self.domain)

        if result["valid"]:
            session = result["data"].get("session", {})
            print(f"  [FraudPlatform] Signals received from: {result['issuer']}")
            print(f"  [FraudPlatform] Device: {session.get('deviceId', 'N/A')}")
            print(f"  [FraudPlatform] ForterToken: {session.get('forterToken', 'N/A')[:16]}...")
            print(f"  NOTE: Fraud platform has no visibility into consumer mandate ($500)")
            print(f"  NOTE: Fraud platform will evaluate based on behavioral signals, not mandate")
            return {"fraud_score": 0.05, "decision": "ALLOW", "reason": "Low-risk KYA-verified agent"}
        return {"fraud_score": 1.0, "decision": "DENY", "reason": "Auth failed"}


# ─────────────────────────────────────────────────────────────────────────────
# Main Scenario
# ─────────────────────────────────────────────────────────────────────────────

def run_scenario():
    print("=" * 70)
    print("TACP MANDATE EXCEEDED SCENARIO")
    print("Version 1.0.0 | Based on tacp/schema/2025-11-12/schema.json")
    print("=" * 70)

    AGENT_DOMAIN = "shopping-agent.example.com"
    MERCHANT_DOMAIN = "electronics-retailer.example.com"
    FORTER_DOMAIN = "forter.com"
    CONSUMER_MANDATE = 500.00   # The agent's spending limit — NOT in TACP schema
    BUNDLE_PRICE = 480.00       # Initial order price
    SHIPPING_SURCHARGE = 30.00  # Post-checkout addition by merchant
    FINAL_TOTAL = BUNDLE_PRICE + SHIPPING_SURCHARGE  # $510

    # ── Phase 1: Setup ────────────────────────────────────────────────────
    print("\n" + "─" * 50)
    print("PHASE 1: AGENT SETUP — KYA VERIFIED, MANDATE $500")
    print("─" * 50)

    agent = AIShoppingAgent(AGENT_DOMAIN, CONSUMER_MANDATE)
    merchant = OnlineMerchant(MERCHANT_DOMAIN)
    fraud_platform = FraudPlatform(FORTER_DOMAIN)

    user = TACUser(
        id="user-consumer-123",
        email=TACEmail(
            address="consumer@example.com",
            verifications=[TACEmailVerification(method="EMAIL_OTP", at="2025-01-15T10:30:00Z")]
        ),
        created="2024-03-01T00:00:00Z",
        status="ACTIVE",
        type="INDIVIDUAL",
    )

    # ── Phase 2: Agent Finds Bundle Deal ($480, within mandate) ───────────
    print("\n" + "─" * 50)
    print("PHASE 2: AGENT FINDS BUNDLE DEAL AT $480 (WITHIN MANDATE)")
    print("─" * 50)

    order = TACOrder(
        orderId=f"ord_{uuid.uuid4().hex[:8]}",
        totalAmount=BUNDLE_PRICE,
        currency="USD",
    )

    session = TACSession(
        id=f"sess_{uuid.uuid4().hex[:8]}",
        intent=f"Purchase electronics bundle for ${BUNDLE_PRICE:.2f}",
        consent="User authorized purchase via KYA-verified agent session",
        channel="WEB",
        source=AGENT_DOMAIN,
        ipAddress="203.0.113.45",
    )

    print(f"\n[AIShoppingAgent] Bundle found: ${BUNDLE_PRICE:.2f} (mandate: ${CONSUMER_MANDATE:.2f})")
    print(f"[AIShoppingAgent] Within mandate — proceeding to checkout")

    # ── Phase 3: TACP Authentication — Agent Signs + Encrypts ────────────
    print("\n" + "─" * 50)
    print("PHASE 3: TACP AUTHENTICATION (JWS + JWE per sender.py)")
    print("─" * 50)

    tac_message, jtis = agent.checkout(
        merchant_domain=MERCHANT_DOMAIN,
        fraud_platform_domain=FORTER_DOMAIN,
        order=order,
        user=user,
        session=session,
    )

    # ── Phase 4: Merchant + Fraud Platform Verify ─────────────────────────
    print("\n" + "─" * 50)
    print("PHASE 4: MERCHANT AND FRAUD PLATFORM VERIFY TACP MESSAGE")
    print("─" * 50)

    checkout_result = merchant.receive_checkout(tac_message, AGENT_DOMAIN)
    fraud_result = fraud_platform.receive_signals(tac_message)

    print(f"\n  Merchant decision: {'APPROVED' if checkout_result['approved'] else 'DENIED'}")
    print(f"  Fraud decision: {fraud_result['decision']} (score={fraud_result['fraud_score']})")

    # ── Phase 5: Merchant Applies Post-Checkout Surcharge ────────────────
    print("\n" + "─" * 50)
    print("PHASE 5: MERCHANT ADDS $30 SHIPPING SURCHARGE POST-CHECKOUT")
    print("─" * 50)

    surcharge_result = merchant.apply_shipping_surcharge(
        order.orderId, SHIPPING_SURCHARGE
    )

    # ── Phase 6: Payment Processed at $510 ───────────────────────────────
    print("\n" + "─" * 50)
    print("PHASE 6: PAYMENT PROCESSED AT $510 (EXCEEDS $500 MANDATE)")
    print("─" * 50)

    charge = merchant.charge_customer(order.orderId)
    print(f"\n  Mandate: ${CONSUMER_MANDATE:.2f}")
    print(f"  Charged: ${charge['charged']:.2f}")
    print(f"  Overage: ${charge['charged'] - CONSUMER_MANDATE:.2f}")

    mandate_exceeded = charge["charged"] > CONSUMER_MANDATE
    print(f"\n  MANDATE EXCEEDED: {mandate_exceeded}")
    print(f"  TACP detected this: NO (no mandate concept in TACP schema)")

    # ── Phase 7: Consumer Dispute ─────────────────────────────────────────
    print("\n" + "─" * 50)
    print("PHASE 7: CONSUMER DISPUTE — WHAT EVIDENCE EXISTS?")
    print("─" * 50)

    tacp_authenticated_amount = surcharge_result["tacp_authenticated_amount"]
    print(f"\n[Consumer] 'I was charged ${FINAL_TOTAL:.2f} but my mandate is ${CONSUMER_MANDATE:.2f}.'")
    print(f"[Consumer] 'The agent should not have authorized a ${FINAL_TOTAL:.2f} charge.'")
    print(f"\n[DisputeAdjudicator] Available TACP evidence:")
    print(f"  ✓ TACP message: agent was authenticated and authorized ${tacp_authenticated_amount:.2f}")
    print(f"  ✓ JWT issuer verified: {AGENT_DOMAIN}")
    print(f"  ✓ Session intent: 'Purchase electronics bundle for ${tacp_authenticated_amount:.2f}'")
    print(f"  ✗ Consumer mandate ($500): NOT in TACP message (no such schema field)")
    print(f"  ✗ Surcharge authorization: NOT authenticated via TACP")
    print(f"  ✗ $510 total: Never signed by agent in any TACP artifact")

    # ── Phase 8: Summary ──────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SCENARIO SUMMARY")
    print("=" * 70)

    summary = {
        "scenario": "TACP Mandate Exceeded by Post-Checkout Shipping Surcharge",
        "consumer_mandate_usd": CONSUMER_MANDATE,
        "initial_order_usd": BUNDLE_PRICE,
        "shipping_surcharge_usd": SHIPPING_SURCHARGE,
        "final_charge_usd": FINAL_TOTAL,
        "mandate_exceeded_by_usd": round(FINAL_TOTAL - CONSUMER_MANDATE, 2),
        "tacp_authenticated_amount_usd": tacp_authenticated_amount,
        "tacp_coverage": {
            "agent_identity_authentication": True,
            "message_integrity": True,
            "user_session_context": True,
            "multi_recipient_data_isolation": True,
            "replay_attack_prevention": True,
            "fraud_signal_delivery": True,
            "consumer_mandate_enforcement": False,          # GAP
            "post_checkout_modification_detection": False,  # GAP
            "mandate_transmission": False,                  # GAP
            "dispute_resolution_protocol": False,           # GAP
        },
        "gap_analysis": {
            "mandate_in_schema": "No — tacp/schema/2025-11-12/schema.json has no mandate/spending_limit field",
            "surcharge_handling": "Undefined — merchant can modify total outside TACP boundary",
            "dispute_evidence": "Partial — TACP proves $480 was authorized, not $510",
            "consumer_protection": "Not TACP's scope — TACP is authentication, not commerce governance",
        }
    }

    print(json.dumps(summary, indent=2))
    print("\n✓ Scenario complete. See findings.md for full analysis.")


if __name__ == "__main__":
    run_scenario()
