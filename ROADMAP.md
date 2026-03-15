# AGF Roadmap

Current version: **v0.1** (Phase 1 primitives — governance contract)

---

## What Is in v0.1

The current release defines AGF Phase 1: the governance contract layer. Three primitives specify what SHOULD happen before an agent acts:

- [DAE](spec/governance-primitives/delegated-authority-envelope.md) — Delegated Authority Envelope (who may act, under whose authority, within what constraints)
- [DBA](spec/governance-primitives/data-boundary-assertion.md) — Data Boundary Assertion (what data may cross which boundaries)
- [TCR](spec/governance-primitives/transaction-commitment-record.md) — Transaction Commitment Record (what obligations must be fulfilled, by when, with what evidence)

JSON schemas for all three primitives are in [`spec/`](spec/).

Reference implementation and conformance suite are in [`reference-implementation/`](reference-implementation/) and [`conformance/`](conformance/).

Protocol gap evidence (AP2 and TACP) is in [`validation/`](validation/).

---

## Next: v0.2 — Standards Alignment Profiles

Before Phase 2, AGF Phase 1 primitives will be explicitly profiled against the standards they extend:

- **DAE-GNAP-Profile-v0.1.md** — Formal GNAP (RFC 9635) profile. Which fields are GNAP vocabulary, which are AGF extensions (principal, max_value, audit_required, inline revocation state), and why each extension cannot be replaced by GNAP as-is.
- **TCR-PROV-Profile-v0.1.md** — W3C PROV profile. How TCR adopts PROV vocabulary (Activity/Agent/Entity) and where it extends PROV with the commitment lifecycle layer that PROV deliberately omits.
- **DAE Constraints v0.2** — Expand the flat `constraints` object into a typed constraint array: `spending` (max_value + currency + conversion_policy), `quantity`, `temporal`, `rate`, `duration`. Currency conversion policies: deny / fixed_rate / service.
- **DBA data classification alignment** — Reference NIST SP 800-188 / NIST Privacy Framework for the `data_classes` vocabulary rather than leaving it as an undefined free-form array. Also define a normative region taxonomy to replace free-form named regions (`EU`, `US-EAST`) with standardized identifiers.

- **DAE revocation distribution model** — The v0.1 inline `revoked=true` model requires the issuing party to deliver updated documents to all enforcement points that hold a copy of the DAE. For true offline revocation across organizational boundaries, a CRL-style revocation list or revocation event distribution protocol is needed. This milestone will define the v0.2 revocation distribution approach, explicitly addressing the hard problem: how does Company B learn about a revocation without a live call to Company A?

- **TCR clock synchronization semantics** — The v0.1 pull model requires enforcement points to agree on the current time relative to `due_by` timestamps. This milestone will define explicit clock tolerance bounds, recommended synchronization practices (NTP UTC), and the semantics for resolving disagreements caused by clock drift between cross-org enforcement points.

This does not change the core AGF primitives. It resolves known v0.1 open questions by providing explicit answers.

**Milestone output:** `DAE-GNAP-Profile-v0.1.md`, `TCR-PROV-Profile-v0.1.md`, `dae-schema-v0.2.json` (typed constraints), updated DBA spec referencing NIST vocabulary, `DAE-Revocation-v0.2.md`, `TCR-ClockSemantics-v0.2.md`.

---

## Next: v0.3 — Phase 2: Governance Evidence Layer

AGF Phase 2 defines what DID happen after an agent acts — the evidence layer that mirrors the contract layer defined in Phase 1.

Phase 1 answers: *What was the agent authorized to do?*
Phase 2 answers: *What did the agent actually do, and can it be verified?*

### Governance Decision Record (GDR)

The GDR is the AGF Phase 2 canonical evidence format. It records the governance outcome of a transaction: the decision made, the contracts evaluated, the enforcement point that evaluated them, and a cryptographically verifiable audit chain.

The GDR is designed to:

- Reference Phase 1 contracts (DAE, DBA, TCR) as the governance terms that were evaluated
- Record the delegation path from principal to delegate as it was resolved at runtime
- Carry a complete audit trail suitable for regulatory submission, dispute resolution, or cross-org verification
- Be portable and offline-verifiable — the same design principle as Phase 1 contracts

### v0.3 Milestones

- **GDR spec v0.1** — Core semantic model: decision record format, authority chain representation, contract reference schema, evidence envelope
- **GDR JSON schema v0.1** — Machine-readable schema with `$comment` annotations linking each field to its rationale
- **Obligation Lifecycle Integration** — How TCR commitment lifecycle (pending/fulfilled/breached/revoked) connects to GDR evidence records. A fulfilled commitment produces a GDR evidence record. A breached TCR produces a GDR challenge record.
- **EU AI Act Article 12 field mapping** — Explicit mapping from GDR fields to EU AI Act Article 12 logging requirements
- **Audit Package format** — A complete governance package for audit, dispute, or regulatory submission: AGF Phase 1 contracts (DAE + DBA + TCR) + GDR evidence records + EU AI Act Article 12 mapping

---

## v1.0 — Complete Specification

Full Phase 1 + Phase 2 specification:

- All Phase 1 schemas finalized and conformance-tested
- Standards profiles published (DAE-GNAP, TCR-PROV, DBA-NIST)
- GDR spec finalized and conformance-tested
- Audit Package schema and documentation
- OTel governance semantic convention proposal (proposal to OpenTelemetry community for governance-specific spans/metrics)
- Conformance suite covering Phase 1 and Phase 2 scenarios
- Reference implementation covering full Phase 1 + Phase 2 stack

---

## Standards This Roadmap Touches

| Standard | Version | Where AGF Aligns |
|---|---|---|
| GNAP | RFC 9635 | DAE profiles GNAP grant semantics |
| W3C PROV | W3C Recommendation | TCR extends PROV Activity/Agent/Entity |
| NIST SP 800-188 | Current | DBA `data_classes` vocabulary |
| EU AI Act Article 12 | In force | GDR evidence field mapping |
| AuthZEN | OpenID Foundation | DBA enforcement pattern documentation |
| OPA / Rego | CNCF | Reference DBA evaluator (design target) |

---

## Contributing

Phase 2 GDR design is open for community input. If you are building governance infrastructure for AI agents and have feedback on the evidence layer design, open an issue or discussion.

Spec challenge issues — "this primitive overlaps with existing standard X" — are especially welcome and will be formally evaluated. See [docs/standards-alignment.md](docs/standards-alignment.md) for the current evaluation of all known overlaps.

See [CONTRIBUTING.md](CONTRIBUTING.md).
