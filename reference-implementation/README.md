# AGF Reference Implementation (POC)

This directory contains the executable proof-of-concept for AGF Phase 1.

It demonstrates one narrow procurement flow:

- AGF preflight authorization (DAE constraint evaluation)
- Signed governance token carried across trust boundary
- Real Agentgateway runtime enforcement via `extAuthz`
- A clearly mocked supplier MCP backend
- Outcome events recorded as governance evidence

## What Is Real vs Mocked

Real:
- Agentgateway process
- Live HTTP calls between components
- `extAuthz` verification path

Mocked:
- `agk_service_mock.py` — AGF governance service (mock)
- `supplier_mcp_mock.py` — Supplier MCP backend (mock)

Reusable boundary:
- `agk_sdk.py` — SDK wrapping the governance service API

## Primary Files

```
reference-implementation/
  agk_service_mock.py     AGF governance service mock
  agk_sdk.py              SDK for governance service interaction
  supplier_mcp_mock.py    Supplier MCP backend mock
  main.py                 Scenario runner
```

## Scenario Commands

Run from the repo root:

```bash
python3 reference-implementation/main.py procurement-preflight-deny
python3 reference-implementation/main.py procurement-happy
python3 reference-implementation/main.py procurement-tamper-detect
python3 reference-implementation/main.py procurement-invalid-token
```

By default, the scenario runner prints component logs first:
- `agk_service_mock`
- `supplier_mcp_mock` (when started)
- `agentgateway` (when started)

Then prints the final JSON result.

Diagnostic mode (print outcome even if scenario does not match fixture expectation):

```bash
python3 reference-implementation/main.py procurement-happy --no-assert
```

JSON-only mode:

```bash
python3 reference-implementation/main.py procurement-happy --json-only
```

The `preflight-deny` scenario starts only the AGF mock service.
The other scenarios start:
- `agk_service_mock.py`
- `supplier_mcp_mock.py`
- A real Agentgateway process using the local upstream checkout

## Runtime Requirements

- The local upstream Agentgateway checkout must exist at `upstream/agentgateway/`
- `cargo` must be available locally to build Agentgateway
- Ports used by the POC:
  - `3100` for Agentgateway
  - `3101` for `supplier_mcp_mock.py`
  - `3102` for `agk_service_mock.py`
- In restricted environments, localhost port binding may require running outside the normal sandbox.

## Current Status

This is a Phase 1 bootstrap POC. It is not a production-ready implementation.

The scenarios were validated locally during development using a real Agentgateway process. They demonstrate the structural correctness of the AGF Phase 1 governance contract flow — not production-grade performance, security hardening, or full error handling.

See [ROADMAP.md](../ROADMAP.md) for planned reference implementation milestones (Phase 1 finalization + Phase 2 GDR emitter).
