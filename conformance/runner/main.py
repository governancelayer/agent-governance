import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
TESTS_DIR = BASE_DIR / "catalog" / "tests"
REPORT_JSON = BASE_DIR / "reports" / "latest" / "report.json"
REPORT_MD = BASE_DIR / "reports" / "latest" / "report.md"
sys.path.insert(0, str(BASE_DIR))

from adapters.agentgateway.client import AgentgatewayClient
from adapters.mock.adapter import MockAdapter


LOG_LEVELS = {"QUIET": 0, "INFO": 1, "DEBUG": 2}


def current_log_level():
    raw = os.environ.get("AGK_LOG_LEVEL", "INFO").upper()
    return LOG_LEVELS.get(raw, LOG_LEVELS["INFO"])


def log(message, level="INFO", component="runner"):
    if LOG_LEVELS.get(level, LOG_LEVELS["INFO"]) > current_log_level():
        return
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"[{component} {level} {timestamp}] {message}")


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_tests():
    for p in sorted(TESTS_DIR.glob("*.json")):
        test = load_json(p)
        print(f"{test['id']}: {test['title']}")


def emit_target_logs(client, test_id, phase):
    if not hasattr(client, "get_debug_snapshot"):
        return

    snapshot = client.get_debug_snapshot()
    for name, path in snapshot.get("log_files", {}).items():
        log(f"{test_id}: {phase} {name} log -> {path}", component="trace")

    for name, tail in snapshot.get("log_tails", {}).items():
        if tail:
            log(
                f"{test_id}: recent {name} log lines: {tail}",
                component="trace",
            )

    if current_log_level() < LOG_LEVELS["DEBUG"]:
        return

    for line in snapshot.get("recent_logs", []):
        log(f"{test_id}: {line}", level="DEBUG", component="trace")


def evaluate_test(client, test):
    log(f"starting test {test['id']}")
    try:
        client_config = test.get("adapter_config")
        if client_config is not None:
            if not hasattr(client, "init"):
                raise ValueError("target client does not support adapter_config")
            log(f"{test['id']}: applying scenario override {client_config}")
            client.init(client_config)

        log(f"{test['id']}: resetting target state")
        client.reset_environment()
        log(f"{test['id']}: submitting transaction")
        result = client.submit_transaction(test["input"], test.get("primitive"))
        log(f"{test['id']}: collecting evidence for {result['transaction_id']}")
        evidence = client.collect_evidence(result["transaction_id"])
    except Exception as exc:
        emit_target_logs(client, test["id"], "on-failure")
        debug_snapshot = {}
        if hasattr(client, "get_debug_snapshot"):
            debug_snapshot = client.get_debug_snapshot()
        failures = [f"execution error: {exc}"]
        for name, path in debug_snapshot.get("log_files", {}).items():
            failures.append(f"{name} log: {path}")
        for name, tail in debug_snapshot.get("log_tails", {}).items():
            if tail:
                failures.append(f"{name} tail: {tail}")
        return {
            "id": test["id"],
            "title": test["title"],
            "pass": False,
            "result": {"decision": "error", "reason": str(exc)},
            "evidence_count": 0,
            "failures": failures,
        }

    expected = test["expected"]
    ok = True
    failures = []

    for key, expected_value in expected.items():
        if key in ("required_evidence_fields", "evidence_equals_result_fields"):
            continue
        actual_value = result.get(key)
        if actual_value != expected_value:
            ok = False
            failures.append(
                f"{key} mismatch: expected={expected_value} actual={actual_value}"
            )

    required_fields = expected.get("required_evidence_fields", [])
    first = evidence[0] if evidence else None
    if required_fields:
        if not evidence:
            ok = False
            failures.append("missing evidence: expected at least one audit entry")
        else:
            missing = [f for f in required_fields if f not in first]
            if missing:
                ok = False
                failures.append(f"evidence missing fields: {', '.join(missing)}")

    linked_fields = expected.get("evidence_equals_result_fields", [])
    if linked_fields:
        if not first:
            ok = False
            failures.append("missing evidence: cannot verify cross-link fields")
        else:
            for field in linked_fields:
                if field not in first:
                    ok = False
                    failures.append(f"evidence missing cross-link field: {field}")
                    continue
                if field not in result:
                    ok = False
                    failures.append(f"result missing cross-link field: {field}")
                    continue
                if first[field] != result[field]:
                    ok = False
                    failures.append(
                        f"evidence/result mismatch for {field}: "
                        f"evidence={first[field]} result={result[field]}"
                    )

    emit_target_logs(client, test["id"], "after-test")
    log(
        f"{test['id']}: decision={result.get('decision')} "
        f"reason_code={result.get('reason_code')} reason={result.get('reason')!r}",
        component="trace",
    )
    log(f"{test['id']}: completed with pass={ok}")
    return {
        "id": test["id"],
        "title": test["title"],
        "pass": ok,
        "result": result,
        "evidence_count": len(evidence),
        "failures": failures,
    }


def run_tests(target, test_id=None):
    log(f"starting run target={target} test_id={test_id or 'all'}")
    client = create_target_client(target)

    tests = []
    for p in sorted(TESTS_DIR.glob("*.json")):
        test = load_json(p)
        test_targets = test.get("targets") or ["mock"]
        if target not in test_targets:
            continue
        if test_id and test["id"] != test_id:
            continue
        tests.append(test)

    if not tests:
        raise ValueError(f"No tests available for --target {target}")

    log(f"selected tests: {[t['id'] for t in tests]}")
    try:
        outcomes = [evaluate_test(client, t) for t in tests]
    finally:
        log("shutting down target client")
        client.shutdown()
    passed = sum(1 for o in outcomes if o["pass"])
    failed = len(outcomes) - passed

    report = {
        "summary": {"total": len(outcomes), "passed": passed, "failed": failed},
        "outcomes": outcomes,
    }

    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    write_markdown_report(report)
    log(f"wrote reports: {REPORT_JSON} and {REPORT_MD}")

    print(f"total={len(outcomes)} passed={passed} failed={failed}")
    for outcome in outcomes:
        status = "PASS" if outcome["pass"] else "FAIL"
        print(f"[{status}] {outcome['id']} - {outcome['title']}")
        for failure in outcome["failures"]:
            print(f"  - {failure}")


def create_target_client(target):
    if target == "mock":
        log("using MockAdapter", component="trace")
        return MockAdapter()
    if target == "agentgateway":
        log("using AgentgatewayClient", component="trace")
        client = AgentgatewayClient()
        client.set_logger(
            lambda level, message: log(
                message, level=level, component="agentgateway-client"
            )
        )
        client.init({})
        return client
    raise ValueError(f"Unsupported --target {target}")


def write_markdown_report(report):
    lines = [
        "# Conformance Report",
        "",
        f"- Total: {report['summary']['total']}",
        f"- Passed: {report['summary']['passed']}",
        f"- Failed: {report['summary']['failed']}",
        "",
        "## Outcomes",
        "",
    ]

    for outcome in report["outcomes"]:
        status = "PASS" if outcome["pass"] else "FAIL"
        lines.append(f"- {status} `{outcome['id']}`: {outcome['title']}")
        if outcome["failures"]:
            for failure in outcome["failures"]:
                lines.append(f"  failure: {failure}")

    with open(REPORT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description="Governance conformance runner")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List tests")

    run_parser = sub.add_parser("run", help="Run tests")
    run_parser.add_argument("--target", required=True)
    run_parser.add_argument("--test", required=False)

    args = parser.parse_args()

    if args.command == "list":
        list_tests()
    elif args.command == "run":
        run_tests(target=args.target, test_id=args.test)


if __name__ == "__main__":
    main()
