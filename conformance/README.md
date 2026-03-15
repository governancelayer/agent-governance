# Governance Conformance Suite (Bootstrap)

This is a minimal deterministic local runner for governance tests.

## Quick Start

```bash
python3 conformance/runner/main.py list
python3 conformance/runner/main.py run --target mock
```

First real-target validation path:

```bash
python3 conformance/runner/main.py run --target agentgateway
```

Outputs:
- `conformance/reports/latest/report.json`
- `conformance/reports/latest/report.md`

## Scope (v0.1)
- Mock target adapter
- First narrow Agentgateway adapter for one live authorization
  allow/deny pair
- Implemented runtime coverage: DAE, DBA, and TCR mock evaluations
- Drafted primitive specs available locally: DAE, DBA, TCR
- Evidence presence checks
- Evidence/result cross-link checks for selected fields

## Current Boundary

The runner is still primarily a deterministic local harness.
It now executes:
- DAE authorization scenarios
- DBA data-boundary scenarios
- TCR commitment/accountability scenarios
- Combined stack scenarios where DAE -> DBA -> TCR are evaluated in one transaction path
- Configurable combined-mode precedence overrides
- Aggregate multi-failure reporting in one combined result
- One real Agentgateway authorization allow/deny pair against a live
  local target

The real-target boundary is still intentionally narrow. It does not yet
provide broader gateway/runtime coverage or richer orchestration such
as:
- adapter parity with a real gateway/runtime target
- a formalized combined-mode semantics spec shared across non-mock targets
- multi-scenario real-target coverage

## Directory Structure

```
conformance/
  runner/           Test runner (main.py)
  adapters/
    mock/           Mock adapter for local testing
    agentgateway/   Real agentgateway adapter (narrow)
  catalog/          Test scenario definitions
  reports/          Output directory for run reports
```

## Runtime Notes

- The `agentgateway` target requires a local `cargo` toolchain and the
  local upstream checkout at `upstream/agentgateway/`.
- Live local validation binds localhost ports and may require an
  unrestricted local run outside the normal sandbox.
- Per-test real-target scenario changes are now handled through
  `adapter_config` in the test catalog.
- Default logs are visible during test execution.
- Set `AGK_LOG_LEVEL=DEBUG` for extra trace detail and recent target log
  tails after each test.
