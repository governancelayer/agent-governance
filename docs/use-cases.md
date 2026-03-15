# Agent Governance Real Use Cases

## Plain-Language Scenarios For Technical And Executive Readers

**Version:** v1.1\
**Published:** 2026-03-05 UTC\
**Status:** Public reference document

> **Terminology note:** This document uses `AGK` to refer to a reference AGF runtime — a service implementing the AGF (Agent Governance Framework) specification. `AGF` is the open specification defined in this repository (DAE, DBA, TCR, GDR primitives). `AGK` is one implementation of that specification and is used in these scenarios to make the examples concrete. Any enforcement gateway or proxy can implement AGF primitives — `AGK` is the reference runtime, not a required product.

------------------------------------------------------------------------

# 1. Purpose

This document illustrates AGF governance through concrete, real-world scenarios using a reference AGF runtime (`AGK`).

It is intentionally practical.

Its job is to answer:

- what happens in a real transaction
- which runtime actors are involved
- what an AGF-compliant governance service does
- what the gateway does
- what the receiving side still decides for itself

This is not a speculative architecture document.
It is a plain-language use-case reference.

------------------------------------------------------------------------

# 2. One Sentence Summary

An AGF-compliant governance service is the authorization and transaction record layer for agent
actions that cross meaningful trust, organizational, or accountability
boundaries.

It evaluates what is allowed when a request reaches a runtime enforcement
point, carries that decision into the runtime path as a signed governance
token, and records what happened after the request.

Agents do not need to integrate with the governance service directly. It integrates
with gateways and enforcement points, keeping governance transparent to
the agent.

------------------------------------------------------------------------

# 3. Canonical Real Use Case: Cross-Organization Procurement

## Executive version

A finance employee at Company A asks an internal procurement assistant
to buy 20 monitors from Supplier X for up to 8,000 EUR.

That sounds simple, but the company needs to answer four questions
before allowing an autonomous tool or agent call:

1. Is the procurement assistant allowed to act for this employee?
2. What data is allowed to leave Company A?
3. What is the maximum spend and approved supplier scope?
4. What evidence must exist after the purchase request is made?

`AGK` is the system that answers those questions and records the
transaction.

The gateway is the system that calls `AGK` and enforces the approved
decision at request time. The agent does not need to know about `AGK`.

The supplier still decides whether to accept and execute the request.

## Runtime actors

1. Human user
   - the finance employee at Company A
2. Buyer app / agent host
   - the system running the procurement assistant
3. Buyer-side gateway (integrated with `AGK`)
   - outbound runtime enforcement point
4. Buyer-side `AGK`
   - governance decision service and transaction record
5. Supplier-side gateway
   - inbound validation and anti-abuse layer
6. Supplier app / supplier agent host
   - the system that can create the purchase order

## What each actor does

### Human user

Provides the business instruction:

> Buy 20 monitors from Supplier X for up to 8,000 EUR.

### Buyer app / agent host

Interprets the request and sends it through the buyer-side gateway.
The agent does not call `AGK` directly.

### Buyer-side gateway

Intercepts the outbound request and calls `AGK` for a governance
decision (via external authorization integration such as extAuthz).

### Buyer-side `AGK`

Evaluates the governance decision.

It decides:

- whether the agent may act for this user
- whether the amount is allowed
- whether the supplier is in scope
- what data may leave
- what post-action obligations must be tracked

It returns:

- allow or deny
- a transaction ID
- one signed governance token

### Buyer-side gateway (continued)

If `AGK` allows, the gateway attaches the signed governance token and
forwards the request. If denied, the gateway blocks the request.

Validates the governance token locally and blocks malformed or
out-of-policy outbound requests.

### Supplier-side gateway

Performs inbound checks such as:

- sender identification
- governance token presence/basic validity
- rate limits
- replay or malformed request rejection

### Supplier app / supplier agent host

Makes the supplier-side business decision:

- accept
- reject
- queue
- require manual review

If accepted, it creates the purchase order.

## Technical flow

### Step 1: Agent sends request through the gateway

The buyer app sends the outbound request through the buyer-side
gateway. The agent does not interact with `AGK`.

### Step 2: Gateway calls the AGF governance service for a decision

> **Note:** The steps below show the AGK reference implementation pattern. Any AGF-compliant governance service may use a different control-plane architecture, endpoint design, or integration model — what matters is that it evaluates DAE, DBA, and TCR and returns a signed governance artifact. AGK is one way to implement this; it is not the only way.

The gateway calls the governance service (here: `AGK`) via its external authorization integration:

- `POST /v1/governed-actions/authorize`

The request asks:

- may this agent perform this action
- for this principal
- against this supplier
- under this business and data context

`AGK` evaluates authority, data boundaries, and required commitments.

### Step 3: Signed governance token is issued

If allowed, `AGK` returns:

- `transaction_id`
- allow decision
- one signed governance token

That token carries the runtime-enforceable contract:

- who the principal is
- which agent is acting
- what action is allowed
- which counterparty is allowed
- when the permission expires
- what runtime constraints must hold

### Step 4: Gateway forwards the governed request

The gateway attaches the token and sends the outbound request.

Canonical path:

`Buyer App -> Buyer Gateway -> Supplier Gateway -> Supplier App`

The request carries:

- the business payload
- caller auth
- the signed governance token

### Step 5: Supplier-side gateway validates

The supplier-side gateway performs the first inbound defensive layer.

It may reject for:

- invalid sender
- invalid token
- replay
- anti-abuse / spam rules

### Step 6: Supplier app decides whether to execute

Even if the buyer-side request was valid, the supplier still decides
whether to accept it.

The supplier may reject because:

- the buyer is not in an approved trading relationship
- the amount exceeds supplier-side auto-approval limits
- the request looks suspicious

### Step 7: Outcome is recorded

The gateway captures the result and reports it to `AGK`:

- `POST /v1/governed-actions/events`

This updates the transaction record.

Examples:

- request rejected by buyer gateway
- supplier rejected
- supplier accepted
- purchase order created
- later confirmation received

## What `AGK` adds beyond the gateway

The gateway alone can block or allow a request at runtime.

`AGK` adds:

1. a governance decision evaluated at the enforcement point
2. one transaction ID and one governance record for the whole action
3. a signed governance token that carries the runtime contract
4. post-action state tracking after the request completes
5. the ability to mark a transaction as pending, fulfilled, denied, or
   breached over time

Without `AGK`, the gateway can say:

- this request was allowed

With `AGK`, the system can also say:

- who authorized it
- under what limits
- what data was allowed to leave
- what obligations were created
- whether those obligations were later fulfilled

------------------------------------------------------------------------

# 4. Real Use Case: Customer Refund With Internal Separation Of Duties

## Scenario

A customer support agent wants to issue a refund during a support case.

The company does not want support agents issuing refunds freely.

## What `AGK` does

- confirms the support agent is acting within approved refund authority
- enforces refund amount and case-context limits
- applies data constraints around customer billing information
- records that a supervisor approval receipt and audit record are
  required for the refund to be fully accountable

The agent sends the refund request through an internal gateway. The
gateway calls `AGK` for the governance decision. The agent does not
interact with `AGK` directly.

## Why this matters

This is not just access control.

It is a separation-of-duties problem with:

- delegated authority
- data handling constraints
- required post-action evidence

------------------------------------------------------------------------

# 5. Real Use Case: Governed MCP Billing Access

## Scenario

A support assistant uses MCP to call a billing tool and retrieve a
customer's billing history during a live support case.

## What `AGK` does

- verifies the assistant may invoke the billing tool for this case
- constrains what billing data may be returned or exported
- records that the access must create an audit event tied to the case

The MCP gateway calls `AGK` for governance evaluation before forwarding
the tool call. The agent host does not integrate with `AGK` directly.

## Why this matters

This is not only "can the tool be called?"

It is also:

- under what authority
- with what data restrictions
- with what accountability obligation

------------------------------------------------------------------------

# 6. Familiar Governance Parallels

Executives and platform teams should not think of this as a strange new
control problem.

The closest mental models already exist in mature systems.

## Payments

The closest payments analogy is:

- authorization: may the transaction proceed?
- settlement: what happened after approval?
- dispute or chargeback: was the transaction truly final?

Parallel:

- `AGK` governance decision is analogous to authorization
- the transaction record is analogous to settlement state
- breach, dispute, or missing obligations are analogous to post-approval
  liability handling

## Procurement / ERP

The closest procurement analogy is:

- approval limit
- approved vendor scope
- purchase order creation
- vendor confirmation
- audit trail

Parallel:

- the governance token is the runtime approval contract
- the supplier still chooses whether to accept
- the transaction remains incomplete until confirmations and records
  exist

## Data Export Controls

The closest data-governance analogy is:

- a user may be authorized
- but the data still may not cross a boundary

Parallel:

- the action may be allowed in principle
- the transaction may still be denied because the data movement is not
  allowed

------------------------------------------------------------------------

# 7. Bottom Line

The point of `AGK` is not to replace the gateway or the receiving
system.

The point is to give agent transactions:

- a governance decision at the enforcement point
- a portable runtime contract
- a durable transaction record

Agents do not need to integrate with `AGK` directly. The gateway is
the integration point. That eliminates an entire SDK integration
surface and keeps governance transparent to the agent.

That is what turns a tool call or agent call into a governable business
transaction.

------------------------------------------------------------------------
