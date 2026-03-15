import argparse
import json
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from agk_sdk import AGKSDK  # noqa: E402


REPO_ROOT = CURRENT_DIR.parents[1]
UPSTREAM_ROOT = REPO_ROOT / "upstream" / "agentgateway"
AGK_SERVICE_SCRIPT = CURRENT_DIR / "agk_service_mock.py"
SUPPLIER_MCP_SCRIPT = CURRENT_DIR / "supplier_mcp_mock.py"
GATEWAY_CONFIG = CURRENT_DIR / "agentgateway" / "procurement-config.yaml"
FIXTURE_DIR = CURRENT_DIR / "agentgateway" / "fixtures"
DEFAULT_PORTS = {
    "gateway": 3100,
    "supplier": 3101,
    "agk": 3102,
}
SCENARIO_FIXTURES = {
    "procurement-happy": FIXTURE_DIR / "procurement_happy.json",
    "procurement-preflight-deny": FIXTURE_DIR / "procurement_over_limit.json",
    "procurement-tamper-detect": FIXTURE_DIR / "procurement_tamper.json",
    "procurement-invalid-token": FIXTURE_DIR / "procurement_invalid_token.json",
}


class ProcessGroup:
    def __init__(self):
        self.processes = []
        self.log_handles = []
        self.log_dir = Path(tempfile.mkdtemp(prefix="agk-poc-"))

    def start_process(self, name, cmd, wait_port):
        log_path = self.log_dir / f"{name}.log"
        handle = open(log_path, "w", encoding="utf-8")
        process = subprocess.Popen(
            cmd,
            stdout=handle,
            stderr=subprocess.STDOUT,
            cwd=UPSTREAM_ROOT if name == "agentgateway" else None,
        )
        self.processes.append((name, process, log_path))
        self.log_handles.append(handle)
        wait_for_port(wait_port, name, process)
        return process

    def stop(self):
        for _, process, _ in reversed(self.processes):
            if process.poll() is not None:
                continue
            process.terminate()
            try:
                process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5.0)
        for handle in self.log_handles:
            handle.close()

    def log_snapshot(self):
        for handle in self.log_handles:
            handle.flush()
        snapshot = {}
        for name, _, log_path in self.processes:
            if log_path.exists():
                snapshot[name] = log_path.read_text(encoding="utf-8")
        return snapshot


def wait_for_port(port, name, process, timeout=60.0):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"{name}_exited_before_ready")
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.1)
    raise RuntimeError(f"{name}_port_timeout")


def load_fixture(name):
    path = SCENARIO_FIXTURES.get(name)
    if path is None:
        raise ValueError(f"unknown_scenario:{name}")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def run_named_scenario(name, assert_expected=True):
    fixture = load_fixture(name)
    if shutil.which("cargo") is None and fixture.get("requires_gateway"):
        raise RuntimeError("cargo_not_available")

    group = ProcessGroup()
    try:
        group.start_process(
            "agk_service_mock",
            [sys.executable, str(AGK_SERVICE_SCRIPT), "--port", str(DEFAULT_PORTS["agk"])],
            DEFAULT_PORTS["agk"],
        )

        if fixture.get("requires_gateway"):
            group.start_process(
                "supplier_mcp_mock",
                [sys.executable, str(SUPPLIER_MCP_SCRIPT), "--port", str(DEFAULT_PORTS["supplier"])],
                DEFAULT_PORTS["supplier"],
            )
            cargo_bin = shutil.which("cargo")
            group.start_process(
                "agentgateway",
                [cargo_bin, "run", "--", "-f", str(GATEWAY_CONFIG)],
                DEFAULT_PORTS["gateway"],
            )

        sdk = AGKSDK(
            service_base_url=f"http://127.0.0.1:{DEFAULT_PORTS['agk']}",
            gateway_base_url=f"http://127.0.0.1:{DEFAULT_PORTS['gateway']}",
        )
        result = sdk.execute_governed_action(
            request=fixture["request"],
            call_overrides=fixture.get("call_overrides"),
            corrupt_token=bool(fixture.get("corrupt_token")),
        )
        state = sdk.get_state()
        logs = group.log_snapshot()
        expected_phase = fixture["expected_phase"]
        if assert_expected and result["phase"] != expected_phase:
            raise AssertionError(
                f"unexpected_phase expected={expected_phase} actual={result['phase']}"
            )
        return {
            "scenario": name,
            "expected_phase": expected_phase,
            "result": result,
            "state": state,
            "logs": logs,
            "log_dir": str(group.log_dir),
        }
    finally:
        group.stop()


def print_component_logs(logs):
    for name in sorted(logs):
        print(f"=== {name} logs ===", flush=True)
        content = logs[name].rstrip()
        if content:
            print(content, flush=True)
        else:
            print("(no logs captured)", flush=True)
        print("", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Run AGK POC scenarios")
    parser.add_argument("scenario", choices=sorted(SCENARIO_FIXTURES.keys()))
    parser.add_argument(
        "--no-assert",
        action="store_true",
        help="return the outcome even if the observed phase does not match the fixture",
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="suppress component log sections and print only the JSON result",
    )
    args = parser.parse_args()

    outcome = run_named_scenario(args.scenario, assert_expected=not args.no_assert)
    logs = outcome.pop("logs", {})
    if not args.json_only:
        print_component_logs(logs)
    print(json.dumps(outcome, indent=2), flush=True)


if __name__ == "__main__":
    main()
