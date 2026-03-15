# AGF Standards Alignment

Version: v0.1
Date: 2026-03-14

This document maps each AGF primitive to existing standards. It defines what AGF adopts from each standard, what it extends, and what is genuinely novel. It also explains where AGF deliberately diverges and why.

AGF's guiding principle: **do not reinvent what is already standardized**. Where a standard provides coverage, AGF profiles or extends it. Where no standard provides coverage, AGF defines a new primitive. Where overlap exists, this document makes the relationship explicit.

---

## Phase 1 — Governance Contract Primitives

### DAE — Delegated Authority Envelope

**AGF position:** Borrows vocabulary from GNAP (RFC 9635) and adds agent-governance extensions. DAE is architecturally distinct from GNAP: GNAP is a negotiation protocol requiring server connectivity; DAE is a portable pre-signed contract evaluated offline. DAE is not a GNAP profile.

#### Standard: GNAP — Grant Negotiation and Authorization Protocol (RFC 9635, IETF)

GNAP is a published IETF RFC defining grant negotiation between clients, authorization servers, and resource servers. It provides the closest published standard to what DAE requires.

| DAE Field | GNAP Coverage | AGF Extension |
|---|---|---|
| `delegation_id` | GNAP access token identifier | DAE makes it portable and pre-signed, not server-issued |
| `delegate` | GNAP client identity | Direct mapping |
| `allowed_actions` | GNAP `access` rights array | Direct mapping |
| `expiry` | GNAP `expires_in` / `expires_at` | DAE uses absolute RFC3339 timestamp for offline portability |
| `revocable` / `revoked` | GNAP server-side revocation API | DAE carries revocation state inline — no server round-trip required |
| `principal` | Not in GNAP | AGF extension: explicit delegation chain identity |
| `constraints.max_value` | Not in GNAP | AGF extension: machine-enforceable numeric budget for autonomous commerce |
| `audit_required` | Not in GNAP | AGF extension: compliance flag for audit trail emission |

**What GNAP provides:** Token lifecycle semantics, client/resource server model, access rights vocabulary.

**Why DAE is not replaced by GNAP directly:** GNAP is a negotiation protocol — it requires connectivity to an authorization server at enforcement time. DAE is a portable pre-signed contract evaluated at any enforcement point, offline or across organizational boundaries. The portability semantics are AGF's structural addition.

**Planned milestone:** `DAE-GNAP-Profile-v0.1.md` — explicit GNAP profile document with formal vocabulary mappings and extension registry.

---

### DBA — Data Boundary Assertion

**AGF position:** Architecturally distinct from AuthZEN and OPA. DBA is a portable pre-signed contract; AuthZEN and OPA are runtime APIs/engines.

#### Standard: AuthZEN (OpenID Foundation)

AuthZEN defines a standardized PEP-to-PDP API. The PEP sends a context object (`subject`, `resource`, `action`, environmental context) to the PDP and receives a decision.

| DBA Field | AuthZEN Coverage | Notes |
|---|---|---|
| `subject_id` / `subject_type` | AuthZEN `resource` object | Partial mapping |
| `permitted_operations` | AuthZEN `action` type | Partial mapping |
| `boundary_constraints.allowed_regions` | AuthZEN environmental context | Regions can be passed as context; not a first-class field in AuthZEN |
| `egress_allowed`, `redaction_required`, `max_retention_hours` | Not in AuthZEN | AGF defines these as first-class fields for data governance |

**Structural difference:** AuthZEN requires a live PDP call at enforcement time. DBA travels with the transaction as a document and is evaluated locally. These are complementary patterns: a system running AuthZEN can use DBA as the portable artifact that travels to non-AuthZEN enforcement points.

**Planned milestone:** `DBA-AuthZEN-Profile-v0.1.md` — explicit comparison document and interop guidance.

#### Standard: OPA / Rego (CNCF Open Policy Agent)

OPA can evaluate every DBA constraint as Rego policy. The architectural difference is the same as AuthZEN: OPA is a runtime engine; DBA is a portable document.

AGF's reference DBA evaluator can be implemented as a Rego policy bundle. This is a design target for the reference implementation.

---

### TCR — Transaction Commitment Record

**AGF position:** Extends W3C PROV Activity model with a commitment lifecycle. The temporal lifecycle and dispute-ready evidence container are genuinely novel.

#### Standard: W3C PROV (W3C Recommendation)

W3C PROV defines a vocabulary for provenance — how entities, activities, and agents relate to each other.

| TCR Field | W3C PROV Equivalent | Notes |
|---|---|---|
| `transaction_id` | PROV `Activity` identifier | Direct mapping |
| `issuer` | PROV `Agent` (`wasAssociatedWith`) | Direct mapping |
| `counterparty` | PROV `Agent` (`actedOnBehalfOf`) | Direct mapping |
| `evidence_refs` | PROV `Entity` references | Artifacts produced or consumed by the activity |
| `commitments[].type` | Not in PROV | PROV records what happened; it does not record what was promised |
| `commitments[].due_by` | Not in PROV | PROV has no commitment deadlines |
| `status` lifecycle | Not in PROV | PROV has no pending/breached/revoked lifecycle states |
| `dispute_window_end` | Not in PROV | PROV has no dispute window concept |

**What PROV provides:** Activity/entity/agent vocabulary, provenance tracing, evidence reference semantics.

**What PROV does not provide:** Commitment lifecycle, breach detection, dispute window, denial semantics on breach.

**Planned milestone:** `TCR-PROV-Profile-v0.1.md` — explicit PROV vocabulary mappings and commitment lifecycle extension specification.

#### Standard: XACML 3.0 Obligations (OASIS)

XACML 3.0 defines an Obligations mechanism: a policy decision may include obligations the PEP must fulfill for the decision to stand. The conceptual overlap with TCR commitments is direct.

| Property | XACML Obligations | TCR |
|---|---|---|
| Timing | Synchronous — same request/response cycle | Asynchronous — `due_by` deadline, monitored over time |
| Persistence | Not persisted as a document | Persistent portable document with lifecycle state |
| Breach detection | PEP must deny if cannot fulfill obligation immediately | Auto-detects breach when `due_by` passes |
| Dispute support | None | `dispute_window_end` + `evidence_refs` |
| Portability | In-process, within XACML enforcement context | Travels with the transaction as evidence |

**TCR's novel contribution:** The combination of async commitment lifecycle, temporal breach detection, portable dispute-ready evidence container, and denial semantic on breach is not covered by any existing standard.

---

## Phase 2 — Governance Evidence Components

Phase 2 is in design. Standards alignment will be formalized as each component is specified.

### GDR — Governance Decision Record

**Design target:** The GDR is a portable, signed record of a governance decision. The audit artifact that compliance officers, regulators, and dispute adjudicators receive.

#### Standard: EU AI Act Article 12

EU AI Act Article 12 mandates logging for high-risk AI systems. GDR is designed to address these requirements; the mapping below is a design target, not a finalized compliance checklist. Legal review is required before treating any GDR implementation as compliant.

| Article 12 Requirement | GDR Field (design target) |
|---|---|
| Identification of the system | `enforcement_point` |
| Date and time of operation | `timestamps.decision_time` |
| Reference database used | `policy_reference` |
| Input data and output description | Covered via Phase 1 contract reference |
| Identification of responsible persons | `authority_chain` |
| Logging of high-risk decisions | `decision` + `primitives_evaluated` |

#### Standard: OSCAL (NIST)

NIST OSCAL Assessment Results model provides a structured format for recording security assessment findings. GDR maps to OSCAL Assessment Results where possible for FedRAMP/federal alignment.

#### Standard: OCSF (Open Cybersecurity Schema Framework)

OCSF defines a standardized event schema for security tooling and SIEM integration. OCSF's Authorization Event class (class_uid 3002) partially covers GDR. AGF will define a GDR-to-OCSF mapping for SIEM/SOC integration.

**Planned milestone:** `gdr-schema-v0.1.json`, GDR specification, EU AI Act Article 12 mapping table, OSCAL profile, OCSF mapping.

---

### Evidence Bundle

A packaged, signed artifact for audit, dispute, or regulatory submission:
- Phase 1 governance contracts (DAE + DBA + TCR)
- Phase 2 Governance Decision Record (GDR)
- Obligation lifecycle status
- Hash of relevant request/response content
- Explicit EU AI Act Article 12 compliance mapping

**Planned milestone:** Evidence bundle schema and specification.

---

### GRC Integration Profile

Defined mappings from AGF evidence output to enterprise GRC platforms:
- OSCAL-compatible assessment result (FedRAMP/federal)
- OCSF-compatible event format (SIEM/SOC)
- REST API ingestion schema for ServiceNow, Vanta, OneTrust, Drata
- OpenTelemetry governance semantic convention proposal

**Planned milestone:** GRC integration profile document + mapping tables.

---

## Summary Matrix

| Standard | AGF Component | Relationship | AGF Action |
|---|---|---|---|
| GNAP (RFC 9635) | DAE | 70-80% vocabulary overlap; AGF adds portability + agent extensions; architecturally distinct | Borrow vocabulary; document extensions and structural difference; publish formal profile |
| AuthZEN (OpenID) | DBA | Partial structural overlap; fundamentally different architecture | Coexist; document distinction; provide interop guidance |
| OPA / Rego | DBA | Can evaluate all DBA constraints; different architecture | Coexist; provide Rego reference evaluator |
| W3C PROV | TCR | Partial vocabulary overlap; PROV lacks lifecycle | Extend PROV; add commitment lifecycle layer |
| XACML 3.0 Obligations | TCR | Conceptual overlap; XACML is synchronous only | Coexist; document why async lifecycle requires TCR |
| OSCAL (NIST) | Phase 2 GDR | Medium overlap for assessment evidence | Profile OSCAL Assessment Results for GDR |
| OCSF | Phase 2 GDR | Medium overlap for authorization event | Coexist; provide OCSF mapping for SIEM integration |
| EU AI Act Art. 12 | Phase 2 GDR | Identifies the gap GDR is designed to address; Article 12 logging requirements motivate GDR field design (design target — legal review required) | Map GDR fields to Article 12 logging requirements; publish compliance checklist |
| A2A (Google/LF) | AGF overall | Governance explicitly deferred in A2A spec | AGF sits above A2A; fills the deferred governance layer |
| MCP (Anthropic) | AGF overall | Governance acknowledged as gap in 2026 roadmap | AGF sits above MCP; fills the governance gap |
| Policy Cards (arxiv) | Both phases | Direct competitor — academic preprint, unknown adoption | Monitor; AGF must differentiate on implementability |
| OpenTelemetry | Phase 2 GRC | No overlap yet | Propose governance semantic convention to OTel community |

---

## Contributing

Spec challenge issues — "this primitive overlaps with existing standard X" — are especially welcome and will be formally evaluated.

See [CONTRIBUTING.md](../CONTRIBUTING.md).
