# The Governance Layer

## Why Governance --- Not Infrastructure --- Determines Value Capture in Agent Ecosystems

**Author:** George Vagenas\
**Version:** v1.2\
**Last reviewed:** 2026-03-02 UTC\
**Status:** Perspective Paper

> **Note:** This is a perspective and thought-leadership piece, not a technical specification. It presents a structural argument about where governance fits in agent ecosystems. It uses analogy, strategic framing, and forward-looking claims. It should be read as a thesis to debate, not as evidence or normative guidance. The AGF technical specification is in [`spec/`](../spec/).

------------------------------------------------------------------------

# 1. Purpose of This Document

This document establishes a formal intellectual position:

> Governance --- not infrastructure --- determines value capture in
> agent ecosystems.

It consolidates the thesis developed across public writings into a
coherent, citation-ready framework suitable for:

-   Industry publication reference
-   Conference abstracts
-   Consulting discussions
-   Strategic enterprise conversations
-   Future product development

This is not a blog post. It is a structural argument.

------------------------------------------------------------------------

# 2. Background: The Structural Shift

AI agents are transitioning from tools assisting humans to autonomous
systems transacting across organizational boundaries.

The industry narrative currently emphasizes:

-   Model capability
-   Infrastructure scale
-   Protocol interoperability
-   Identity systems

However, infrastructure maturity does not determine economic control.

In every networked market historically --- telecom, internet routing,
financial clearing systems --- value concentrated at the layer defining
interaction terms, not connectivity.

Agent ecosystems are entering the same structural phase.

------------------------------------------------------------------------

# 3. The Core Thesis

Agent ecosystems are structurally complete at the infrastructure layer.

What remains undefined is the governance layer:

-   Authorization scope
-   Data boundary policy
-   Liability allocation
-   Escalation mechanisms
-   Cross-organizational accountability

The organizations that define these governance terms will shape default
interaction rules.

Default interaction rules determine value capture.

------------------------------------------------------------------------

# 4. The Governance Gap

Current agent protocols focus on:

-   Discovery
-   Capability negotiation
-   Session routing
-   Identity verification
-   Access enforcement

They do not define:

-   What an agent is authorized to commit to without human intervention
-   What contextual data may cross boundaries and under what retention
    constraints
-   Who bears responsibility when commitments exceed authorization
-   How risk is allocated across machine-mediated transactions

This gap is structural, not technical.

------------------------------------------------------------------------

# 5. The Agent Governance Framework

This paper proposes a three-pillar governance model for
inter-organizational agent ecosystems:

## Pillar 1: Authorization Scope Architecture

Defines the limits of machine authority. Establishes thresholds
requiring human approval. Implements scope attenuation in
cross-principal transactions.

## Pillar 2: Data Boundary Governance

Defines permissible data exchange. Specifies retention and downstream
use conditions. Controls contextual memory propagation across systems.

## Pillar 3: Liability & Accountability Design

Allocates responsibility for overcommitment. Defines escalation paths.
Clarifies contractual risk transfer between principals.

These pillars operate above infrastructure and enforcement layers.

Infrastructure enforces. Governance defines.

------------------------------------------------------------------------

# 6. Economic Consequence: Value Capture

Infrastructure commoditizes. Governance centralizes power.

In telecom: Switching hardware commoditized. Interconnect agreements
defined economics.

In internet routing: Fiber deployed everywhere. Peering agreements
determined leverage.

In agent ecosystems: Model quality will converge. Protocol
interoperability will standardize. Infrastructure will commoditize.

Governance architecture will determine:

-   Who sets default transaction terms
-   Who absorbs liability
-   Who controls data flows
-   Who captures economic margin

------------------------------------------------------------------------

# 7. Strategic Implications for Enterprises

Enterprises deploying agents must define governance architecture before
defaults are imposed externally.

Three foundational questions:

1.  What may your agent commit to autonomously?
2.  What data may it exchange across organizational boundaries?
3.  Where does liability reside when authorization is exceeded?

Organizations that fail to define these internally will inherit
governance structures designed around external incentives.

------------------------------------------------------------------------

# 7A. A Concrete Enterprise Example

Consider a cross-organizational procurement request:

- a finance employee at Company A asks an internal procurement
  assistant to buy 20 monitors from Supplier X for up to 8,000 EUR

That transaction requires more than a generic allow or deny check.

A serious enterprise still needs to decide:

- what authority the procurement assistant has for this employee
- what supplier and spending boundaries apply
- what data may leave Company A
- what evidence or confirmations must exist after the request is sent

In practical runtime terms:

- the buyer-side gateway calls `AGK` for the governance decision
- `AGK` issues one signed governance token for the runtime path
- gateways validate and enforce that token
- the supplier still decides whether to accept and execute
- `AGK` keeps the transaction record after the request

This is the difference between infrastructure and governance:

- infrastructure moves and enforces the request
- governance defines the transaction terms and records whether they were
  upheld

This same pattern is recognizable in mature systems:

- payments: authorization, settlement, dispute handling
- procurement: approval limits, PO issuance, vendor confirmation
- data export control: access may be granted while data movement is
  still prohibited

------------------------------------------------------------------------

# 8. Why This Matters Now

The surrounding stack is no longer hypothetical. It is beginning to
standardize and harden in public:

-   MCP now has a current protocol version dated 2025-11-25
-   GNAP is now an IETF Standards Track RFC (RFC 9635, published October
    2024)
-   OpenID's AuthZEN effort is advancing fine-grained authorization
    interoperability
-   NIST has launched an AI Agent Standards Initiative
-   gateway and policy vendors now openly market agent-focused
    authorization, observability, and governance-adjacent controls

This does not eliminate the governance gap. It sharpens it.

The market is actively building:

-   transport
-   connectivity
-   tool access control
-   policy decision points
-   audit surfaces

What remains unsettled is the layer that defines portable transaction
terms across organizational boundaries.

History suggests that governance terms solidify early and persist for
decades.

Enterprises that participate in defining governance architecture shape
long-term market structure.

Enterprises that wait adapt to frameworks built by others.

------------------------------------------------------------------------

# 9. Intended Use of This Document

This document may serve as:

-   A reference artifact for industry discussion
-   A conceptual foundation for enterprise governance design
-   A basis for consulting engagements
-   A precursor to formal governance playbooks or tooling
-   A citation anchor for policy and standards participation

It is intentionally a thesis document, not a vendor comparison or
feature matrix.

------------------------------------------------------------------------

# 10. Author Positioning

George Vagenas analyzes governance architecture in agent ecosystems,
focusing on how authorization design, data boundaries, and liability
allocation determine long-term value capture.

This work examines governance as a market-structuring force rather than
a compliance afterthought.

------------------------------------------------------------------------

# End of Document
