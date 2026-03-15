"""
AP2 Hotel Booking Price Change Scenario
========================================
Demonstrates how Google Agent Payments Protocol (AP2) handles a hotel
booking where the price changes between search and checkout, and the
agent proceeds within a self-defined threshold that slightly exceeds the
user's stated budget.

Based on AP2 spec: ap2/docs/specification.md
Types from: ap2/src/ap2/types/mandate.py, ap2/src/ap2/types/payment_request.py

This is a simulation — no actual AP2 agents are running. All cryptographic
operations are stubbed with descriptive labels to show the protocol flow.

Run: python scenario.py
"""

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional


# ─────────────────────────────────────────────────────────────────────────────
# Simulated AP2 Type Definitions
# (mirrors ap2/src/ap2/types/mandate.py and payment_request.py)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PaymentCurrencyAmount:
    currency: str
    value: float


@dataclass
class PaymentItem:
    label: str
    amount: PaymentCurrencyAmount
    pending: Optional[bool] = False
    refund_period: int = 30


@dataclass
class PaymentDetailsInit:
    id: str
    display_items: list
    total: PaymentItem
    shipping_options: Optional[list] = None
    modifiers: Optional[list] = None


@dataclass
class PaymentMethodData:
    supported_methods: str
    data: dict = field(default_factory=dict)


@dataclass
class PaymentRequest:
    method_data: list
    details: PaymentDetailsInit
    options: Optional[dict] = None
    shipping_address: Optional[dict] = None


@dataclass
class CartContents:
    """Per ap2/src/ap2/types/mandate.py CartContents"""
    id: str
    user_cart_confirmation_required: bool
    payment_request: PaymentRequest
    cart_expiry: str
    merchant_name: str


@dataclass
class CartMandate:
    """Per ap2/src/ap2/types/mandate.py CartMandate"""
    contents: CartContents
    merchant_authorization: Optional[str] = None  # JWT stub

    def compute_hash(self) -> str:
        """Simulates the cart_hash computation described in spec §4.1.1"""
        content_str = json.dumps({
            "id": self.contents.id,
            "merchant": self.contents.merchant_name,
            "total": self.contents.payment_request.details.total.amount.value,
            "currency": self.contents.payment_request.details.total.amount.currency,
        }, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]


@dataclass
class IntentMandate:
    """
    Per ap2/src/ap2/types/mandate.py IntentMandate
    NOTE: No machine-readable budget field — budget is in natural_language_description only.
    """
    user_cart_confirmation_required: bool
    natural_language_description: str
    intent_expiry: str
    merchants: Optional[list] = None
    skus: Optional[list] = None
    requires_refundability: Optional[bool] = False


@dataclass
class PaymentMandateContents:
    """Per ap2/src/ap2/types/mandate.py PaymentMandateContents"""
    payment_mandate_id: str
    payment_details_id: str
    payment_details_total: PaymentItem
    payment_response: dict
    merchant_agent: str
    timestamp: str


@dataclass
class PaymentMandate:
    """Per ap2/src/ap2/types/mandate.py PaymentMandate"""
    payment_mandate_contents: PaymentMandateContents
    user_authorization: Optional[str] = None  # VP/SD-JWT stub


# ─────────────────────────────────────────────────────────────────────────────
# Simulated Protocol Actors
# ─────────────────────────────────────────────────────────────────────────────

class DisputeOutcome(Enum):
    USER_LIABILITY = "user_liability"
    AGENT_LIABILITY = "agent_liability"
    MERCHANT_LIABILITY = "merchant_liability"
    AMBIGUOUS = "ambiguous_requires_nlp_interpretation"


class ShoppingAgent:
    """
    Simulates the Shopping Agent (SA) role.
    The SA operates in Human-Not-Present mode.
    It applies a self-defined 10% tolerance for price fluctuations.
    This tolerance is NOT defined in the AP2 spec.
    """

    def __init__(self, agent_id: str, price_tolerance_pct: float = 0.10):
        self.agent_id = agent_id
        self.price_tolerance_pct = price_tolerance_pct
        print(f"[ShoppingAgent] Initialized. ID={agent_id}, "
              f"tolerance={price_tolerance_pct*100:.0f}% (NOTE: not defined in AP2 spec)")

    def create_intent_mandate(
        self,
        description: str,
        budget_eur: float,
        expiry_hours: int = 24,
    ) -> IntentMandate:
        """
        Creates IntentMandate per AP2 spec §4.1.2.
        OBSERVATION: budget_eur is included in the description string,
        but there is no max_value or machine-readable budget field in AP2 v0.1.
        """
        expiry = (datetime.now(timezone.utc) + timedelta(hours=expiry_hours)).isoformat()
        mandate = IntentMandate(
            user_cart_confirmation_required=False,  # Human-not-present: agent may proceed autonomously
            natural_language_description=description,
            intent_expiry=expiry,
        )
        print(f"\n[ShoppingAgent] Created IntentMandate")
        print(f"  user_cart_confirmation_required: {mandate.user_cart_confirmation_required}")
        print(f"  natural_language_description: '{mandate.natural_language_description}'")
        print(f"  NOTE: Budget '{budget_eur}' is only in natural language — no machine-readable max_value field exists in AP2 v0.1")
        return mandate

    def check_price_against_mandate(
        self, mandate: IntentMandate, quoted_price: float, budget: float
    ) -> bool:
        """
        This logic is OUTSIDE the AP2 spec.
        The agent is implementing its own budget tolerance check.
        AP2 does not define this behavior.
        """
        max_allowed = budget * (1 + self.price_tolerance_pct)
        within_tolerance = quoted_price <= max_allowed
        print(f"\n[ShoppingAgent] Mandate budget check (NOT defined by AP2 spec):")
        print(f"  Stated budget: €{budget:.2f}")
        print(f"  Quoted price: €{quoted_price:.2f}")
        print(f"  Self-defined tolerance ({self.price_tolerance_pct*100:.0f}%): up to €{max_allowed:.2f}")
        print(f"  Decision: {'PROCEED' if within_tolerance else 'ABORT'} (agent-internal rule, not AP2)")
        return within_tolerance

    def create_payment_mandate(
        self, cart_mandate: CartMandate, payment_token: str
    ) -> PaymentMandate:
        """Creates PaymentMandate per AP2 spec §4.1.3"""
        total = cart_mandate.contents.payment_request.details.total
        contents = PaymentMandateContents(
            payment_mandate_id=f"pm_{uuid.uuid4().hex[:8]}",
            payment_details_id=cart_mandate.contents.payment_request.details.id,
            payment_details_total=total,
            payment_response={
                "request_id": cart_mandate.contents.payment_request.details.id,
                "method_name": "CARD",
                "details": {"token": payment_token},
            },
            merchant_agent="BerlinHotelAgent",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        pm = PaymentMandate(
            payment_mandate_contents=contents,
            user_authorization=None,  # human-not-present: no real-time user signing
        )
        print(f"\n[ShoppingAgent] Created PaymentMandate")
        print(f"  payment_mandate_id: {contents.payment_mandate_id}")
        print(f"  total: €{total.amount.value:.2f} {total.amount.currency}")
        print(f"  user_authorization: None (human-not-present, user_cart_confirmation_required=False)")
        return pm


class MerchantAgent:
    """Simulates the Merchant Agent (ME) role."""

    def __init__(self, name: str, base_price_per_night: float):
        self.name = name
        self.base_price_per_night = base_price_per_night
        self._price_changed = False

    def get_quoted_price(self) -> float:
        return self.base_price_per_night

    def apply_dynamic_pricing(self, new_price: float):
        """Simulates hotel dynamic pricing update"""
        old = self.base_price_per_night
        self.base_price_per_night = new_price
        self._price_changed = True
        print(f"\n[MerchantAgent] DYNAMIC PRICING UPDATE: €{old:.2f} → €{new_price:.2f}/night")

    def create_cart_mandate(
        self,
        cart_id: str,
        nights: int,
        payment_methods: list,
    ) -> CartMandate:
        """
        Creates and merchant-signs the CartMandate.
        Per AP2 spec §4.1.1, §7.1 Steps 9-11.
        The merchant signs at the CURRENT price.
        """
        price_per_night = self.base_price_per_night
        total = price_per_night * nights

        payment_request = PaymentRequest(
            method_data=[PaymentMethodData(
                supported_methods="CARD",
                data={"payment_processor_url": "https://hotel-payments.example.com/pay"}
            )],
            details=PaymentDetailsInit(
                id=f"order_{cart_id}",
                display_items=[
                    PaymentItem(
                        label=f"Hotel room x{nights} nights @ €{price_per_night:.2f}",
                        amount=PaymentCurrencyAmount(currency="EUR", value=total)
                    )
                ],
                total=PaymentItem(
                    label="Total",
                    amount=PaymentCurrencyAmount(currency="EUR", value=total)
                ),
            ),
        )

        cart_expiry = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        contents = CartContents(
            id=cart_id,
            user_cart_confirmation_required=False,
            payment_request=payment_request,
            cart_expiry=cart_expiry,
            merchant_name=self.name,
        )

        mandate = CartMandate(contents=contents)
        cart_hash = mandate.compute_hash()

        # Stub merchant JWT signature per spec §4.1.1
        mandate.merchant_authorization = (
            f"[STUB_MERCHANT_JWT iss={self.name} cart_hash={cart_hash} "
            f"total_eur={total:.2f} exp=10min alg=RS256]"
        )

        print(f"\n[MerchantAgent] Created and signed CartMandate")
        print(f"  cart_id: {cart_id}")
        print(f"  price: €{price_per_night:.2f}/night × {nights} nights = €{total:.2f}")
        print(f"  cart_expiry: {cart_expiry}")
        print(f"  merchant_authorization: {mandate.merchant_authorization}")
        return mandate


class CredentialProvider:
    """Simulates the Credentials Provider (CP) role."""

    def get_payment_token(self, cart_mandate: CartMandate) -> str:
        token = f"tok_{uuid.uuid4().hex[:12]}"
        print(f"\n[CredentialProvider] Issued payment token: {token}")
        return token


class DisputeAdjudicator:
    """
    Simulates the card network adjudicator reviewing the dispute.
    Demonstrates what AP2 evidence is available and what gaps exist.
    """

    def adjudicate(
        self,
        intent_mandate: IntentMandate,
        payment_mandate: PaymentMandate,
        stated_budget: float,
    ) -> DisputeOutcome:
        """
        AP2 Table 6.1: "Mispick, Unapproved by User" scenario.
        The adjudicator compares Intent Mandate vs. final transaction amount.
        """
        actual_total = payment_mandate.payment_mandate_contents.payment_details_total.amount.value
        currency = payment_mandate.payment_mandate_contents.payment_details_total.amount.currency

        print(f"\n[DisputeAdjudicator] Reviewing dispute evidence (AP2 §6, Table 6.1)")
        print(f"  IntentMandate.natural_language_description: '{intent_mandate.natural_language_description}'")
        print(f"  IntentMandate.user_cart_confirmation_required: {intent_mandate.user_cart_confirmation_required}")
        print(f"  PaymentMandate.total: {currency} {actual_total:.2f}")
        print(f"  Stated budget (from NL parsing): {currency} {stated_budget:.2f}")
        print(f"  Overage: {currency} {actual_total - stated_budget:.2f} ({((actual_total/stated_budget)-1)*100:.1f}%)")
        print(f"\n  AP2 GAP: The budget '{stated_budget}' must be extracted from natural language.")
        print(f"  AP2 GAP: No machine-readable max_value field in IntentMandate v0.1.")
        print(f"  AP2 GAP: Agent's 10% tolerance rule was not recorded in any AP2 artifact.")
        print(f"  AP2 COVERAGE: Table 6.1 'Mispick, Unapproved by User' provides framework for this.")

        if intent_mandate.user_cart_confirmation_required is False:
            print(f"\n  COMPLICATING FACTOR: user_cart_confirmation_required=False means the user")
            print(f"  explicitly authorized autonomous purchase. Does this extend to price changes?")
            print(f"  AP2 is silent on this specific question.")
            return DisputeOutcome.AMBIGUOUS
        else:
            return DisputeOutcome.USER_LIABILITY


# ─────────────────────────────────────────────────────────────────────────────
# Main Scenario
# ─────────────────────────────────────────────────────────────────────────────

def run_scenario():
    print("=" * 70)
    print("AP2 HOTEL BOOKING PRICE CHANGE SCENARIO")
    print("Version 1.0.0 | Based on AP2 spec ap2/docs/specification.md")
    print("=" * 70)

    # Configuration
    NIGHTS = 3
    INITIAL_PRICE_PER_NIGHT = 280.0   # €280/night = €840 total
    CHANGED_PRICE_PER_NIGHT = 310.0   # Price changes to €310/night = €930 total
    STATED_BUDGET = 900.0             # User said "max €900 total"

    # ── Phase 1: Mandate Creation ─────────────────────────────────────────
    print("\n" + "─" * 50)
    print("PHASE 1: USER CREATES INTENT MANDATE")
    print("─" * 50)

    agent = ShoppingAgent(agent_id="shopping-agent-v2", price_tolerance_pct=0.10)
    intent_mandate = agent.create_intent_mandate(
        description=(
            "Book a 3-night stay at a 4-star hotel in Berlin, April 10–13 2026. "
            "Budget is €300/night, maximum total €900. No specific hotel required."
        ),
        budget_eur=STATED_BUDGET,
    )

    # ── Phase 2: Agent Discovers Merchant, Gets Quoted Price ──────────────
    print("\n" + "─" * 50)
    print("PHASE 2: AGENT GETS INITIAL QUOTE (€840)")
    print("─" * 50)

    merchant = MerchantAgent("Berlin Grand Hotel", base_price_per_night=INITIAL_PRICE_PER_NIGHT)
    initial_total = merchant.get_quoted_price() * NIGHTS
    print(f"\n[ShoppingAgent] Received quote: €{merchant.get_quoted_price():.2f}/night = €{initial_total:.2f} total")
    print(f"[ShoppingAgent] Quote is within budget (€{initial_total:.2f} < €{STATED_BUDGET:.2f}). Proceeding.")

    initial_cart_id = f"cart_{uuid.uuid4().hex[:8]}"
    initial_cart = merchant.create_cart_mandate(initial_cart_id, NIGHTS, ["CARD"])

    # ── Phase 3: Dynamic Price Change (between quote and payment) ─────────
    print("\n" + "─" * 50)
    print("PHASE 3: DYNAMIC PRICE CHANGE OCCURS (€280 → €310)")
    print("─" * 50)

    merchant.apply_dynamic_pricing(CHANGED_PRICE_PER_NIGHT)
    print(f"[MerchantAgent] Previous CartMandate (€840) has expired (10-min TTL).")
    print(f"[MerchantAgent] Agent requests new CartMandate at updated price.")

    # The agent must request a new CartMandate at the new price
    new_cart_id = f"cart_{uuid.uuid4().hex[:8]}"
    new_cart = merchant.create_cart_mandate(new_cart_id, NIGHTS, ["CARD"])
    new_total = CHANGED_PRICE_PER_NIGHT * NIGHTS

    # ── Phase 4: Agent's Self-Defined Tolerance Check ─────────────────────
    print("\n" + "─" * 50)
    print("PHASE 4: AGENT APPLIES SELF-DEFINED TOLERANCE (NOT AP2-SPECIFIED)")
    print("─" * 50)

    should_proceed = agent.check_price_against_mandate(
        intent_mandate, new_total, STATED_BUDGET
    )

    if not should_proceed:
        print("[ShoppingAgent] Price exceeds tolerance — would abort and notify user.")
        return

    # ── Phase 5: Payment Execution ────────────────────────────────────────
    print("\n" + "─" * 50)
    print("PHASE 5: PAYMENT EXECUTION AT NEW PRICE (€930)")
    print("─" * 50)

    cp = CredentialProvider()
    payment_token = cp.get_payment_token(new_cart)
    payment_mandate = agent.create_payment_mandate(new_cart, payment_token)

    print(f"\n[MerchantAgent] Processing payment of €{new_total:.2f}")
    print(f"[Network/Issuer] Transaction approved. Receipt issued.")
    print(f"[ShoppingAgent] Purchase completed: €{new_total:.2f} for {NIGHTS}-night stay.")

    # ── Phase 6: Consumer Dispute ─────────────────────────────────────────
    print("\n" + "─" * 50)
    print("PHASE 6: CONSUMER DISPUTE FILED")
    print("─" * 50)
    print(f"\n[User] 'I instructed the agent to spend max €{STATED_BUDGET:.2f}. It spent €{new_total:.2f}.'")
    print(f"[User] 'The agent should have asked me before exceeding my budget.'")

    # ── Phase 7: Dispute Adjudication ─────────────────────────────────────
    print("\n" + "─" * 50)
    print("PHASE 7: AP2 DISPUTE ADJUDICATION (Spec §6, Table 6.1)")
    print("─" * 50)

    adjudicator = DisputeAdjudicator()
    outcome = adjudicator.adjudicate(intent_mandate, payment_mandate, STATED_BUDGET)

    # ── Phase 8: Summary ──────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("SCENARIO SUMMARY")
    print("=" * 70)

    summary = {
        "scenario": "AP2 Hotel Booking — Price Change",
        "initial_quote_eur": initial_total,
        "final_charge_eur": new_total,
        "stated_budget_eur": STATED_BUDGET,
        "overage_eur": round(new_total - STATED_BUDGET, 2),
        "overage_pct": round(((new_total / STATED_BUDGET) - 1) * 100, 1),
        "user_cart_confirmation_required": intent_mandate.user_cart_confirmation_required,
        "dispute_outcome": outcome.value,
        "ap2_coverage": {
            "intent_mandate_created": True,
            "cart_mandate_merchant_signed": True,
            "payment_mandate_created": True,
            "dispute_evidence_chain_exists": True,
            "budget_field_machine_readable": False,   # GAP
            "price_change_protocol_defined": False,   # GAP
            "tolerance_threshold_defined": False,     # GAP
            "mandate_enforcement_runtime": False,     # GAP
        },
    }

    print(json.dumps(summary, indent=2))
    print("\n✓ Scenario complete. See findings.md for full analysis.")


if __name__ == "__main__":
    run_scenario()
