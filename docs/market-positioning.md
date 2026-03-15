# Agent Governance Market Positioning Brief

## A Public Brief On What The Market Has - And What It Still Lacks

**Version:** v1.1\
**Published:** 2026-03-02 UTC\
**Status:** Public Positioning Brief

> **Terminology note:** This document uses "AGF" to refer to the Agent Governance Framework specification (what this repository defines) and "AGK" where it refers to a reference runtime implementing that specification. AGF is the open spec. AGK is one possible implementation of it. This distinction matters: any enforcement gateway, proxy, or platform can implement AGF primitives — AGK is not the only path.

------------------------------------------------------------------------

# 1. Purpose

This document explains where the agent-governance market stands today
and what remains structurally unaddressed, from my perspective.

It is intended to clarify the positioning of AGF (Agent Governance Framework)
without relying on a private competitor matrix.

------------------------------------------------------------------------

# 2. What The Market Already Has

The surrounding ecosystem is moving quickly.

The market already has:

-   protocol standards for agent and tool connectivity
-   delegated-authorization standards
-   externalized authorization systems
-   gateways that enforce identity-aware and tool-aware controls
-   data-security systems that block or redact sensitive data
-   durable workflow systems that track execution state
-   machine-verifiable credential formats for proof-bearing claims

In other words: the market is no longer missing control points.

It is building them aggressively.

------------------------------------------------------------------------

# 3. What The Market Still Lacks

What remains weakly defined is the layer above those systems.

Most current tools answer one of these questions well:

-   Where should traffic be routed?
-   Which tool may be called?
-   Should this request be allowed?
-   Should this data be blocked or redacted?
-   Did this workflow complete?

But enterprises increasingly need a different kind of answer:

-   What authority was delegated for this transaction?
-   What data boundary conditions applied to this exact transaction?
-   What obligations, approvals, or evidence were required before the
    transaction could be considered complete?
-   Can those conditions be tested consistently across systems?

This is the missing layer.

------------------------------------------------------------------------

# 4. The Missing Layer

The missing layer is not infrastructure.

It is not another gateway, another policy engine, or another DLP tool.

It is a portable transaction-governance layer that can define:

1.  authority terms
2.  data-boundary terms
3.  accountability terms
4.  the evidence required to prove those terms were upheld

And just as importantly:

5.  the conformance criteria for testing whether systems actually uphold
    them

------------------------------------------------------------------------

# 5. Why This Matters Strategically

As more vendors own runtime control points, the strategic question
shifts.

The question is no longer:

"Will agent systems have enforcement points?"

They already do.

The real question is:

"Who defines the portable terms those enforcement points should honor?"

The organization that helps define those terms influences:

-   default trust boundaries
-   default delegation norms
-   default audit expectations
-   default accountability allocation

That is why governance remains the strategic layer.

------------------------------------------------------------------------

# 6. What Agent Governance Kit Is

Agent Governance Kit is best understood as:

**a portable, testable transaction-governance layer for agent systems**

It is designed to specify what must be true across:

-   authorization scope
-   data boundaries
-   accountability and evidence

It is intended to work with existing gateways, policy engines, and
security systems rather than replace them.

The AGK reference implementation uses this operational pattern:

-   an `AGK` control-plane service that evaluates governance decisions
    and maintains the transaction record
-   gateways and enforcement points that call `AGK` for governance
    decisions, attach the signed governance token to outbound requests,
    and report outcome events
-   agents that send requests through gateways without needing to
    integrate with `AGK` directly

In other words: in the AGK reference architecture, `AGK` is the governance control plane and transaction record; the gateway is both the runtime enforcement point and the `AGK` integration point; agents are governance-unaware.

**This is a reference architecture, not a requirement.** Any system that evaluates AGF primitives (DAE, DBA, TCR) and emits AGF-compliant evidence (GDR) is a valid AGF implementation — regardless of whether it uses a centralized control-plane service, a sidecar model, an embedded library, or any other architecture. AGK is one example. The spec does not mandate any particular runtime shape.

Concrete enterprise example:

-   a buyer-side procurement assistant wants to create a purchase order
    with an external supplier
-   `AGK` decides whether the agent may act, issues one signed
    governance token, and records the transaction
-   gateways validate and enforce that runtime contract
-   the supplier still decides whether to accept and execute
-   `AGK` records what happened after the request

This makes the position easier to understand:

-   `AGK` is not another gateway
-   it is the governance control plane around the transaction

Familiar parallels:

-   payments: authorization, settlement, dispute state
-   procurement: approval limits, PO creation, vendor confirmation
-   data export controls: a request may be authorized while the data
    movement is still prohibited

------------------------------------------------------------------------

# 7. What Agent Governance Kit Is Not

To keep the category clear:

-   It is not an agent gateway.
-   It is not a replacement for externalized authorization.
-   It is not a DLP platform.
-   It is not a workflow engine.
-   It is not just a gateway plugin.
-   It is not a broad "AI governance" umbrella for ethics, model risk,
    or enterprise compliance paperwork.

It is a transaction-governance and conformance layer.

------------------------------------------------------------------------

# 8. Why Conformance Is The First Wedge

The strongest early wedge is conformance.

Why:

-   many systems can enforce policy
-   fewer systems define neutral, portable requirements
-   almost none define cross-system tests for transaction-level
    governance

A conformance-first approach does two things:

1.  It clarifies what meaningful governance support actually is.
2.  It creates a neutral standard that multiple systems can be measured
    against.

This is how a governance layer becomes legible to the market.

------------------------------------------------------------------------

# 9. Bottom Line

The market has many fast-improving control surfaces.

What it still lacks is a portable, testable way to define and verify
transaction-level authority, data-boundary, and accountability terms
across systems.

That is the space Agent Governance Kit should continue to own.

------------------------------------------------------------------------
