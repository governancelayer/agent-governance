import datetime as dt
import json
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path


ADAPTER_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[4]
UPSTREAM_ROOT = REPO_ROOT / "upstream" / "agentgateway"
JWT_DIR = UPSTREAM_ROOT / "manifests" / "jwt"
MCP_MOCK_SCRIPT = ADAPTER_DIR / "mcp_mock.py"
DEFAULT_SCENARIO_FIXTURE = (
    ADAPTER_DIR / "fixtures" / "authorization_printenv_deny.json"
)
LOG_DIR = REPO_ROOT / "tools" / "conformance-suite" / "reports" / "latest" / "logs"


class AgentgatewayClient:
    def __init__(self, config=None):
        self.config = {}
        self.audit_log = []
        self.scenario = None
        self.last_transaction_id = None
        self.gateway_process = None
        self.backend_process = None
        self.gateway_log_path = LOG_DIR / "agentgateway.log"
        self.mcp_log_path = LOG_DIR / "mcp_mock.log"
        self.gateway_log_handle = None
        self.mcp_log_handle = None
        self.debug_events = []
        self.logger = None
        if config is not None:
            self.init(config)

    def set_logger(self, logger):
        self.logger = logger

    def init(self, config):
        self.config = dict(config or {})
        fixture_path = self.config.get("scenario_fixture")
        if fixture_path:
            fixture_path = self._resolve_path(Path(fixture_path))
        else:
            fixture_path = DEFAULT_SCENARIO_FIXTURE

        self.scenario = self._load_fixture(fixture_path)
        self._validate_scenario(self.scenario)
        self._log(
            "selected scenario "
            f"id={self.scenario['id']} fixture={fixture_path}"
        )
        return {
            "target": "agentgateway",
            "scenario_id": self.scenario["id"],
            "scenario_fixture": str(fixture_path),
        }

    def reset_environment(self):
        self._log("resetting managed local processes")
        self._stop_processes()
        self.audit_log = []
        self.last_transaction_id = None
        return {
            "reset": True,
            "mode": "managed_local_bootstrap",
            "scenario_id": self._scenario_id(),
        }

    def apply_identities(self, identities):
        return {
            "applied": False,
            "mode": "fixture_owned",
            "reason": "Identity handling is owned by the selected scenario fixture.",
            "scenario_id": self._scenario_id(),
        }

    def apply_policies(self, policies):
        return {
            "applied": False,
            "mode": "fixture_owned",
            "reason": "Policy handling is owned by the selected upstream example config.",
            "scenario_id": self._scenario_id(),
        }

    def submit_transaction(self, transaction, primitive=None):
        if self.scenario is None:
            self.init({})

        tx = dict(transaction or {})
        tx_id = tx.get("transaction_id") or f"agw-{uuid.uuid4().hex[:8]}"
        self.last_transaction_id = tx_id
        started = time.time()
        self._log(
            f"starting transaction tx_id={tx_id} primitive={primitive or 'n/a'} "
            f"tool={tx.get('tool_name') or self.scenario['tool_name']}"
        )

        self._ensure_environment()
        identity_fixture = tx.get("identity_fixture") or self.scenario["identity_fixture"]
        token = self._load_identity_token(identity_fixture)
        self._log(f"loaded identity fixture={identity_fixture}")

        initialize_response = self._send_mcp_request(
            token=token,
            payload={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": self.scenario.get(
                        "protocol_version", "2025-06-18"
                    ),
                    "capabilities": {},
                    "clientInfo": {
                        "name": "agk-conformance",
                        "version": "0.1",
                    },
                },
            },
        )

        session_id = (
            initialize_response["headers"].get("Mcp-Session-Id")
            or initialize_response["headers"].get("mcp-session-id")
        )
        if not session_id:
            raise RuntimeError("initialize response missing Mcp-Session-Id")
        self._log("received session_id from initialize")

        tool_name = tx.get("tool_name") or self.scenario["tool_name"]
        list_response = self._send_mcp_request(
            token=token,
            session_id=session_id,
            payload={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {},
            },
        )
        visible_tools = self._extract_tool_names(list_response)
        tool_visible = tool_name in visible_tools
        self._log(
            "observed tools/list "
            f"status={list_response['status']} tools={visible_tools or []}"
        )

        call_response = self._send_mcp_request(
            token=token,
            session_id=session_id,
            payload={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": tx.get("arguments", {}),
                },
            },
        )

        decision, reason_code, reason = self._classify_tool_call(
            call_response,
            tool_name=tool_name,
        )
        total_ms = int((time.time() - started) * 1000)
        self._log(
            "normalized live result "
            f"decision={decision} reason_code={reason_code} reason={reason!r}"
        )

        result = {
            "transaction_id": tx_id,
            "decision": decision,
            "reason": reason,
            "reason_code": reason_code,
            "scenario_id": self.scenario["id"],
            "outputs": {
                "scenario_id": self.scenario["id"],
                "tool_name": tool_name,
                "initialize_status": initialize_response["status"],
                "list_status": list_response["status"],
                "call_status": call_response["status"],
                "session_id_present": bool(session_id),
                "tool_visible": tool_visible,
                "identity_fixture": identity_fixture,
            },
            "timings_ms": {"total": total_ms},
        }

        self.audit_log.append(
            {
                "transaction_id": tx_id,
                "scenario_id": self.scenario["id"],
                "decision": decision,
                "reason_code": reason_code,
                "timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
                "source": "agentgateway-client",
                "initialize_status": initialize_response["status"],
                "list_status": list_response["status"],
                "call_status": call_response["status"],
                "tool_visible": tool_visible,
                "identity_fixture": identity_fixture,
            }
        )

        return result

    def collect_evidence(self, transaction_id):
        return [e for e in self.audit_log if e.get("transaction_id") == transaction_id]

    def shutdown(self):
        self._log("shutting down managed local processes")
        self._stop_processes()
        self.audit_log = []
        self.last_transaction_id = None
        return {"shutdown": True, "target": "agentgateway"}

    def get_debug_snapshot(self):
        return {
            "scenario_id": self._scenario_id(),
            "log_files": {
                "mcp_mock": str(self.mcp_log_path),
                "agentgateway": str(self.gateway_log_path),
            },
            "recent_logs": self.debug_events[-20:],
            "log_tails": {
                "mcp_mock": self._tail_process_log("mcp_mock", lines=12),
                "agentgateway": self._tail_process_log("agentgateway", lines=12),
            },
        }

    def _load_fixture(self, path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _validate_scenario(self, scenario):
        required = [
            "id",
            "upstream_example_path",
            "config_path",
            "identity_fixture",
            "tool_name",
            "expected_decision",
        ]
        missing = [key for key in required if key not in scenario]
        if missing:
            raise ValueError(
                "Agentgateway scenario fixture missing required fields: "
                + ", ".join(missing)
            )

    def _scenario_id(self):
        if not self.scenario:
            return None
        return self.scenario.get("id")

    def _ensure_environment(self):
        mcp_port = int(self.scenario.get("backend_port", 3001))
        gateway_port = int(self.scenario.get("gateway_port", 3000))

        if not self._port_open(mcp_port):
            self._start_mcp_mock(mcp_port)
        else:
            self._log(f"reusing existing mcp_mock on port={mcp_port}")
        if not self._port_open(gateway_port):
            self._start_gateway(gateway_port)
        else:
            self._log(f"reusing existing agentgateway on port={gateway_port}")

    def _start_mcp_mock(self, port):
        self._prepare_log_dir()
        self._close_log_handle("mcp")
        self.mcp_log_handle = open(self.mcp_log_path, "w", encoding="utf-8")
        self._log(f"starting mcp_mock port={port} log={self.mcp_log_path}")
        self.backend_process = subprocess.Popen(
            [sys.executable, str(MCP_MOCK_SCRIPT), "--port", str(port)],
            stdout=self.mcp_log_handle,
            stderr=subprocess.STDOUT,
        )
        self._wait_for_port(port, "mcp_mock", self.backend_process)

    def _start_gateway(self, port):
        config_path = self._resolve_path(Path(self.scenario["config_path"]))
        try:
            config_arg = str(config_path.relative_to(UPSTREAM_ROOT))
        except ValueError:
            config_arg = str(config_path)
        cargo_bin = self._resolve_cargo_bin()

        self._prepare_log_dir()
        self._close_log_handle("gateway")
        self.gateway_log_handle = open(self.gateway_log_path, "w", encoding="utf-8")
        self._log(
            f"starting agentgateway port={port} config={config_arg} "
            f"log={self.gateway_log_path}"
        )
        self.gateway_process = subprocess.Popen(
            [cargo_bin, "run", "--", "-f", config_arg],
            cwd=UPSTREAM_ROOT,
            stdout=self.gateway_log_handle,
            stderr=subprocess.STDOUT,
        )
        self._wait_for_port(port, "agentgateway", self.gateway_process, timeout=300.0)

    def _wait_for_port(self, port, name, process, timeout=10.0):
        self._log(f"waiting for {name} port={port} timeout={timeout}s")
        deadline = time.time() + timeout
        while time.time() < deadline:
            if process is not None and process.poll() is not None:
                tail = self._tail_process_log(name)
                raise RuntimeError(
                    f"{name} exited before becoming ready (exit={process.returncode})"
                    + (f"; last log lines: {tail}" if tail else "")
                )
            if self._port_open(port):
                self._log(f"{name} is ready on port={port}")
                return
            time.sleep(0.2)
        raise RuntimeError(f"{name} did not become ready on port {port}")

    def _port_open(self, port):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            return False

    def _load_identity_token(self, token_name):
        token_path = JWT_DIR / token_name
        with open(token_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    def _resolve_cargo_bin(self):
        cargo_bin = shutil.which("cargo")
        if cargo_bin:
            return cargo_bin

        fallback = Path.home() / ".cargo" / "bin" / "cargo"
        if fallback.exists():
            return str(fallback)

        raise RuntimeError(
            "cargo was not found on PATH and ~/.cargo/bin/cargo does not exist"
        )

    def _send_mcp_request(self, token, payload, session_id=None):
        gateway_port = int(self.scenario.get("gateway_port", 3000))
        mcp_path = self.scenario.get("mcp_path", "/mcp")
        url = f"http://127.0.0.1:{gateway_port}{mcp_path}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json,text/event-stream",
            "Authorization": f"Bearer {token}",
        }
        if session_id:
            headers["Mcp-Session-Id"] = session_id

        method = payload.get("method")
        self._log(
            f"request method={method} url={url} "
            f"session_id={'present' if session_id else 'absent'}"
        )
        request = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                body = response.read().decode("utf-8")
                normalized = self._normalize_http_result(
                    response.getcode(), response.headers, body
                )
                self._log(
                    f"response method={method} status={normalized['status']}"
                )
                return normalized
        except urllib.error.HTTPError as err:
            body = err.read().decode("utf-8")
            normalized = self._normalize_http_result(err.code, err.headers, body)
            self._log(f"response method={method} status={normalized['status']}")
            return normalized

    def _normalize_http_result(self, status, headers, body):
        return {
            "status": status,
            "headers": {k: v for k, v in headers.items()},
            "body_text": body,
            "body_json": self._parse_response_json(body),
        }

    def _extract_tool_names(self, response):
        body_json = response["body_json"]
        if not isinstance(body_json, dict):
            return []

        result = body_json.get("result")
        if not isinstance(result, dict):
            return []

        tools = result.get("tools")
        if not isinstance(tools, list):
            return []

        names = []
        for tool in tools:
            if isinstance(tool, dict):
                name = tool.get("name")
                if isinstance(name, str):
                    names.append(name)
        return names

    def _classify_tool_call(self, response, tool_name=None):
        status = response["status"]
        body_json = response["body_json"]
        body_text = response["body_text"]
        error_text = self._extract_error_text(response)
        unknown_tool = "unknown tool" in error_text.lower()
        tool_name_matches = bool(tool_name) and tool_name.lower() in error_text.lower()

        if status in (401, 403):
            return ("deny", "ERR_AGW_TOOL_CALL_DENIED", error_text)

        if unknown_tool and (tool_name_matches or not tool_name):
            return ("deny", "ERR_AGW_TOOL_CALL_DENIED", error_text)

        if status >= 400:
            return ("deny", "ERR_AGW_REQUEST_FAILED", error_text)

        if isinstance(body_json, dict) and "error" in body_json:
            return ("deny", "ERR_AGW_TOOL_CALL_DENIED", error_text)

        success_text = self._extract_success_text(response)
        return (
            "allow",
            "OK_AGW_ALLOWED",
            success_text or body_text or "Gateway allowed tool call",
        )

    def _extract_error_text(self, response):
        body_json = response["body_json"]
        if isinstance(body_json, dict):
            error = body_json.get("error")
            if isinstance(error, dict):
                return error.get("message") or json.dumps(error, sort_keys=True)
            if error is not None:
                return str(error)
        return response["body_text"] or "request failed"

    def _extract_success_text(self, response):
        body_json = response["body_json"]
        if not isinstance(body_json, dict):
            return None

        result = body_json.get("result")
        if not isinstance(result, dict):
            return None

        content = result.get("content")
        if not isinstance(content, list):
            return None

        text_chunks = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str) and text:
                text_chunks.append(text)

        if not text_chunks:
            return None
        return "\n".join(text_chunks)

    def _parse_response_json(self, body):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            pass

        sse_payload = None
        for line in body.splitlines():
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if not payload:
                continue
            try:
                sse_payload = json.loads(payload)
            except json.JSONDecodeError:
                continue

        return sse_payload

    def _log(self, message, level="INFO"):
        entry = f"[agentgateway-client {level}] {message}"
        self.debug_events.append(entry)
        if self.logger is not None:
            self.logger(level, message)

    def _stop_processes(self):
        for proc in (self.gateway_process, self.backend_process):
            if proc is None:
                continue
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
        self.gateway_process = None
        self.backend_process = None
        self._close_log_handle("gateway")
        self._close_log_handle("mcp")

    def _resolve_path(self, path):
        if path.is_absolute():
            return path
        return REPO_ROOT / path

    def _prepare_log_dir(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    def _close_log_handle(self, name):
        attr = f"{name}_log_handle"
        handle = getattr(self, attr)
        if handle is not None and not handle.closed:
            handle.flush()
            handle.close()
        setattr(self, attr, None)

    def _tail_process_log(self, name, lines=20):
        log_path = self.mcp_log_path if name == "mcp_mock" else self.gateway_log_path
        if not log_path.exists():
            return ""
        try:
            content = log_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return ""
        if not content:
            return ""
        return " | ".join(content[-lines:])
