# AGF Architecture

Version: v0.2
Date: 2026-03-15

This document describes where the Agent Governance Framework sits in the agent transaction flow and how its two phases relate to the enforcement infrastructure.

---

## Two-Phase Model

AGF governs agent transactions across two phases:

**Phase 1 — Governance Contract (pre-action):** Defines what should happen before the agent acts. Three portable primitives specify the terms of the transaction.

**Phase 2 — Governance Evidence (post-action):** Defines what did happen after the agent acted. Structured, signed records for audit, dispute, and regulatory compliance.

Between the two phases sits the **Policy Enforcement Engine** — any gateway, proxy, or runtime that evaluates the governance contract and permits or denies the action. AGF does not specify the enforcement engine. AGF defines what the engine enforces.

---

## System Flow Diagram

```mermaid
flowchart TD
    subgraph PRINCIPAL["Principal / Delegating System"]
        P1["Human user or system<br/>assigning the agent task"]
    end

    subgraph CONTRACT["Phase 1: Governance Contract"]
        direction TB
        DAE["DAE — Delegated Authority Envelope<br/>Who may act · Allowed actions<br/>Max value constraint · Expiry · Revocation · Audit"]
        DBA["DBA — Data Boundary Assertion<br/>Data classes · Permitted operations<br/>Allowed regions · Egress / retention / redaction"]
        TCR["TCR — Transaction Commitment Record<br/>Required commitments · Deadlines (due_by)<br/>Evidence references · Dispute window"]
    end

    subgraph ENGINE["Policy Enforcement Engine"]
        direction TB
        ENG["Any gateway, proxy, or runtime<br/>agentgateway · Envoy · Kong · custom<br/>Evaluates Phase 1 contracts<br/>Emits allow / deny · Produces Phase 2 evidence"]
    end

    subgraph TRANSPORT["Transport Protocol"]
        direction TB
        T1["A2A · MCP · HTTP<br/>(protocol moves the request)<br/>(AGF governs the request)"]
    end

    subgraph AGENT["Delegate Agent"]
        A1["Acting agent<br/>carries governance token<br/>from enforcement point"]
    end

    subgraph EVIDENCE["Phase 2: Governance Evidence"]
        direction TB
        GDR["GDR — Governance Decision Record<br/>Decision: allow / deny / conditional<br/>Primitives evaluated · Authority chain<br/>Policy reference · Signed + portable"]
        OBL["Obligation Lifecycle<br/>Commitment fulfillment tracking<br/>Breach detection · Notification triggers"]
        EB["Evidence Bundle<br/>Phase 1 contracts + GDR<br/>Obligation status · Content hash<br/>EU AI Act Art.12 mapping"]
        GRC["GRC Integration Profile<br/>OSCAL assessment result · OCSF event (SIEM)<br/>ServiceNow / Vanta / OneTrust · OpenTelemetry"]
    end

    P1 -->|"Creates governance contract (DAE + DBA + TCR)"| CONTRACT
    CONTRACT -->|"Governance contract attached to request"| ENGINE
    ENGINE -->|"Evaluated: allow + token or deny + reason code"| TRANSPORT
    TRANSPORT --> AGENT
    AGENT -->|"Transaction executes (if allowed)"| ENGINE
    ENGINE -->|"Records what happened"| EVIDENCE

    style CONTRACT fill:#1e3a5f,color:#ffffff,stroke:#4a90d9
    style ENGINE fill:#2d4a1e,color:#ffffff,stroke:#6abf40
    style EVIDENCE fill:#4a1e1e,color:#ffffff,stroke:#d96060
    style TRANSPORT fill:#2d2d2d,color:#ffffff,stroke:#888888
    style PRINCIPAL fill:#1e1e3a,color:#ffffff,stroke:#6060d9
    style AGENT fill:#1e1e3a,color:#ffffff,stroke:#6060d9
```

---

## Key Design Principles

**AGF does not specify the enforcement engine.** Any gateway, proxy, or runtime that can evaluate the three Phase 1 primitives and emit Phase 2 evidence records is a valid AGF enforcement point. The framework defines what is enforced, not which software enforces it.

**Transport protocols are unchanged.** A2A, MCP, and HTTP move the request. AGF governs the request. These concerns are layered, not competing.

**Portability is load-bearing.** All three Phase 1 primitives are portable pre-signed documents that travel with the transaction. They can be evaluated at any enforcement point, across organizational boundaries, without requiring connectivity to the issuing system.

**Phase 1 and Phase 2 are linked by a shared `context_id`.** Every primitive — DAE, DBA, TCR, and GDR — carries the same `context_id` for a given agent transaction. This is the authoritative join key for the evidence chain. An auditor or enforcement point correlates all governance artifacts for a transaction by `context_id`, then resolves each primitive by its type-specific identifier (`delegation_id`, `assertion_id`, `commitment_id`, `record_id`).

---

## Enforcement Flow: agentgateway + AuthZEN + OPA

This section describes the full AGF enforcement flow using agentgateway as the Policy Enforcement Point (PEP) and OPA as the Policy Decision Point (PDP). **The PEP and PDP always belong to the same organization** — here, Company A's outbound enforcement stack checks the agent's governance before it acts. Company B receives the signed DAE and verifies it offline.

```mermaid
sequenceDiagram
    participant Agent as AI Agent (Company A)
    participant GW as agentgateway<br/>(PEP, Company A)
    participant OPA as OPA<br/>(PDP, Company A)
    participant Store as GDR / TCR Store
    participant B as Company B<br/>Enforcement Point

    Agent->>GW: Action request + DAE + DBA

    rect rgb(232, 244, 232)
        note over GW: AGF Phase 1 — offline check (no server call)
        GW->>GW: 1. Verify DAE signature (Ed25519)
        GW->>GW: 2. Check DAE: not expired, not revoked,<br/>action in allowed_actions, amount ≤ max_value
        GW->>GW: 3. Check DBA: egress_allowed,<br/>allowed_regions, data_class permitted
    end

    GW->>OPA: AuthZEN POST /access/v1/evaluation<br/>{subject, resource, action, context}

    rect rgb(232, 240, 254)
        note over OPA: Live policy check — Company A internal
        OPA->>OPA: Evaluate Rego policies:<br/>rate limits · spend limits · fraud score<br/>procurement policy · agent allowlist
    end

    OPA-->>GW: {decision: true}

    GW->>Store: Create TCR (commitment record)
    GW->>Store: Create GDR (signed evidence, OCSF mapped)
    GW-->>Agent: Request cleared

    Agent->>B: Request + signed DAE
    B->>B: Verify DAE signature offline<br/>(no call to Company A required)
    B-->>Agent: Allow / Deny + reason code
```

**PEP = agentgateway (Company A). PDP = OPA (Company A). AuthZEN = the API spec between them.**

Two complementary checks run in series:

| Question | Mechanism | Requires server? |
|---|---|---|
| Was this agent authorized by a human principal? | AGF Phase 1 — DAE (offline) | ❌ No |
| Is this data access within the authorized scope? | AGF Phase 1 — DBA (offline) | ❌ No |
| Does this action comply with Company A's live policies? | AuthZEN → OPA (online) | ✅ Yes |

AGF Phase 1 proves authorization — cryptographically, offline, cross-org. AuthZEN/OPA enforces live platform policies. Both must pass.

---

## DAE Issuance: Direct and GNAP Integration Paths

DAE issuance does not require GNAP. The **AGF DAE Issuance Service** is the primary issuance mechanism — a simple REST API that accepts delegation requests, optionally triggers a human approval workflow, and returns signed DAE documents. GNAP is an optional integration profile for organizations that already operate GNAP or OAuth AS infrastructure.

```mermaid
flowchart TD
    PRINCIPAL["Principal<br/>(human or system)"]

    subgraph DIRECT["Path A: Direct Issuance (no GNAP)"]
        direction TB
        ISS["AGF Issuance Service<br/>POST /delegations<br/>Authenticate principal · Validate scope<br/>Optional: human approval · Sign DAE (Ed25519)"]
    end

    subgraph GNAP_PATH["Path B: GNAP Integration Profile (optional)"]
        direction TB
        GNAP_CLIENT["AGF Issuance Service (GNAP client)<br/>Construct GNAP grant request<br/>Submit to AS"]
        AS["GNAP Authorization Server<br/>(Okta · Azure AD · custom)<br/>Human approval workflow<br/>Enterprise policy evaluation · Grant issuance"]
        CONVERT["AGF Issuance Service<br/>Convert GNAP grant to DAE<br/>Add AGF extensions:<br/>principal, max_value, currency, audit_required"]
    end

    DAE_STORE[("Signed DAE (Ed25519)<br/>returned to agent")]

    PRINCIPAL -->|"Delegation request"| DIRECT
    PRINCIPAL -->|"Delegation request (enterprise with GNAP AS)"| GNAP_PATH

    GNAP_CLIENT --> AS
    AS -->|"Grant issued"| CONVERT

    DIRECT --> DAE_STORE
    CONVERT --> DAE_STORE

    style DIRECT fill:#1e3a5f,color:#ffffff,stroke:#4a90d9
    style GNAP_PATH fill:#2d2d4a,color:#ffffff,stroke:#7070d9
    style DAE_STORE fill:#2d4a1e,color:#ffffff,stroke:#6abf40
```

**Path A (direct):** The issuance service handles authorization directly. Suitable for any organization regardless of their existing identity infrastructure. No GNAP AS required.

**Path B (GNAP integration):** For organizations with an existing GNAP or OAuth 2.0 AS. The issuance service acts as a GNAP client — it requests a grant, converts the result into a DAE with AGF extensions, and returns the signed artifact. The enterprise AS remains the authorization authority; AGF adds portability.

The resulting DAE is identical regardless of issuance path. Enforcement points verify the DAE signature — they have no visibility into which issuance path was used.

→ [DAE Issuance Service Specification](../spec/governance-primitives/dae-issuance-service.md)

---

## Where AGF Sits Relative to Existing Standards

```mermaid
flowchart LR
    subgraph IDENTITY["Identity Layer"]
        GNAP["GNAP RFC 9635<br/>Grant negotiation"]
        OIDC["OIDC / OAuth 2<br/>Authentication"]
    end

    subgraph GOVERNANCE["Governance Layer — AGF"]
        direction TB
        PH1["Phase 1: Contract<br/>DAE (GNAP vocabulary + portability)<br/>DBA (portable contract)<br/>TCR (extends W3C PROV)"]
        PH2["Phase 2: Evidence<br/>GDR (maps OSCAL + OCSF)<br/>Evidence Bundle · GRC Integration"]
    end

    subgraph POLICY["Policy Layer"]
        OPA["OPA / Rego<br/>Policy evaluation"]
        AUTHZEN["AuthZEN<br/>PEP to PDP API"]
    end

    subgraph TRANSPORT["Protocol Layer"]
        A2A["A2A<br/>(governance deferred)"]
        MCP["MCP<br/>(governance gap)"]
        HTTP["HTTP"]
    end

    IDENTITY --> GOVERNANCE
    GOVERNANCE --> TRANSPORT
    POLICY -.->|"can evaluate DAE/DBA constraints"| GOVERNANCE

    style GOVERNANCE fill:#1e3a5f,color:#ffffff,stroke:#4a90d9
    style IDENTITY fill:#1e1e3a,color:#ffffff,stroke:#6060d9
    style POLICY fill:#2d2d4a,color:#ffffff,stroke:#7070d9
    style TRANSPORT fill:#2d2d2d,color:#ffffff,stroke:#888888
```

AGF sits between the identity/authentication layer and the transport/protocol layer. It is not a replacement for GNAP, OPA, or A2A. It is the governance layer that was missing between them.

---

## GNAP + DAE Issuance Pattern (Enterprise Integration Profile)

GNAP is **optional** as a DAE issuance mechanism. For the full picture including direct issuance without GNAP, see the [DAE Issuance section above](#dae-issuance-direct-and-gnap-integration-paths).

For organizations that already operate GNAP or OAuth AS infrastructure, GNAP handles the authorization negotiation and human approval workflow. DAE is the portable governance artifact created from the resulting grant.

```mermaid
sequenceDiagram
    participant Agent as AI Agent
    participant AGF as AGF Issuance Layer
    participant AS as GNAP Authorization Server
    participant Store as DAE Store (signed)
    participant B as Company B Enforcement Point

    Agent->>AGF: Request delegation
    AGF->>AS: GNAP grant request (scoped actions)
    AS->>AS: Human review / enterprise approval
    AS-->>AGF: GNAP grant issued
    AGF->>AGF: Create DAE from GNAP grant + AGF extensions<br/>(principal, max_value, currency, audit_required)
    AGF->>Store: Sign DAE (Ed25519)
    Store-->>Agent: Signed DAE returned
    Agent->>B: Request + signed DAE
    B->>B: Verify DAE signature offline<br/>(no call to Company A)
    B-->>Agent: Allow / Deny + reason code
```

**What GNAP handles:** Grant negotiation, human approval workflow, access rights scoping, token issuance by an enterprise-trusted AS.

**What DAE adds:** Portable signed artifact with explicit delegation chain (`principal` → `delegate`), machine-enforceable numeric constraints (`max_value` + `currency`), offline-verifiable revocation state, and cross-org transferability without server connectivity.

This pattern enables reuse of existing GNAP/OAuth infrastructure for the authorization decision while providing the cross-boundary portability that GNAP tokens alone do not offer.

---

## Standards Referenced

| AGF Component | Standard | Relationship |
|---|---|---|
| DAE | GNAP (RFC 9635) | Vocabulary borrowing — DAE reuses GNAP field semantics; architecturally distinct (offline portable artifact vs server-connected token) |
| DBA | AuthZEN, OPA/Rego | Coexist — different architecture (portable contract vs API/engine) |
| TCR | W3C PROV, XACML 3.0 | Extends PROV + fills XACML async lifecycle gap |
| GDR | OSCAL (NIST), OCSF | Maps to both for GRC/SIEM integration |
| Evidence Bundle | EU AI Act Article 12 | GDR targets Article 12 logging requirement coverage (design target — full mapping in v0.3) |

For the full mapping, see [docs/standards-alignment.md](standards-alignment.md).
