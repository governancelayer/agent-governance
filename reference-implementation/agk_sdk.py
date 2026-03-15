import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from agk_service_mock import DEFAULT_ALLOWED_ACTION  # noqa: E402


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def build_procurement_request(amount, supplier_id="supplier-x"):
    return {
        "principal": {
            "id": "alice@company-a",
            "type": "human_user",
        },
        "agent": {
            "id": "procurement-assistant",
            "instance_id": "poc-agent-1",
        },
        "counterparty": {
            "org_id": supplier_id,
            "endpoint_id": "supplier-mcp-poc",
        },
        "action": {
            "type": "tool_call",
            "name": DEFAULT_ALLOWED_ACTION,
        },
        "business_context": {
            "currency": "EUR",
            "amount": amount,
            "supplier_id": supplier_id,
        },
        "data_context": {
            "fields_present": ["shipping_address", "order_lines"],
            "data_classes": ["commercial"],
        },
    }


class AGKSDK:
    def __init__(
        self,
        service_base_url="http://127.0.0.1:3102",
        gateway_base_url="http://127.0.0.1:3100",
        caller_auth="Bearer agk-poc-buyer",
    ):
        self.service_base_url = service_base_url.rstrip("/")
        self.gateway_base_url = gateway_base_url.rstrip("/")
        self.caller_auth = caller_auth

    def execute_governed_action(
        self,
        request,
        call_overrides=None,
        corrupt_token=False,
    ):
        preflight = self.authorize(request)
        transaction_id = preflight["transaction_id"]
        if preflight["decision"] == "deny":
            self.emit_event(
                {
                    "transaction_id": transaction_id,
                    "event_type": "preflight_denied",
                    "timestamp": utc_now_iso(),
                    "source": "agk-sdk-poc",
                    "payload": {"reason_code": preflight["reason_code"]},
                }
            )
            return {
                "phase": "preflight_denied",
                "decision": "deny",
                "transaction_id": transaction_id,
                "preflight": preflight,
            }

        token = preflight["governance_token"]
        if corrupt_token:
            token = token[:-1] + ("A" if token[-1] != "A" else "B")

        tool_arguments = {
            "amount": request["business_context"]["amount"],
            "currency": request["business_context"]["currency"],
            "supplier_id": request["business_context"]["supplier_id"],
            "order_lines": [
                {"sku": "MON-27", "qty": 20},
            ],
            "shipping_address": "warehouse-1",
        }
        if call_overrides:
            tool_arguments.update(call_overrides)

        try:
            session_id = self.initialize_session(token)
            self.emit_event(
                {
                    "transaction_id": transaction_id,
                    "event_type": "request_sent",
                    "timestamp": utc_now_iso(),
                    "source": "agk-sdk-poc",
                    "payload": {
                        "tool_name": DEFAULT_ALLOWED_ACTION,
                        "amount": tool_arguments["amount"],
                        "supplier_id": tool_arguments["supplier_id"],
                    },
                }
            )
            call_response = self.call_tool(
                session_id=session_id,
                token=token,
                tool_name=DEFAULT_ALLOWED_ACTION,
                arguments=tool_arguments,
            )
        except urllib.error.HTTPError as exc:
            status = exc.code
            error_body = self._decode_http_error_body(exc)
            exc.close()
            event_type = "gateway_rejected" if status in (401, 403) else "transport_error"
            self.emit_event(
                {
                    "transaction_id": transaction_id,
                    "event_type": event_type,
                    "timestamp": utc_now_iso(),
                    "source": "agk-sdk-poc",
                    "payload": {
                        "status": status,
                        "error": error_body,
                    },
                }
            )
            return {
                "phase": event_type,
                "decision": "deny",
                "transaction_id": transaction_id,
                "preflight": preflight,
                "http_status": status,
                "error": error_body,
            }
        except urllib.error.URLError as exc:
            self.emit_event(
                {
                    "transaction_id": transaction_id,
                    "event_type": "transport_error",
                    "timestamp": utc_now_iso(),
                    "source": "agk-sdk-poc",
                    "payload": {"error": str(exc.reason)},
                }
            )
            return {
                "phase": "transport_error",
                "decision": "deny",
                "transaction_id": transaction_id,
                "preflight": preflight,
                "error": str(exc.reason),
            }

        result_payload = self._extract_call_payload(call_response["body"])
        self.emit_event(
            {
                "transaction_id": transaction_id,
                "event_type": "supplier_completed",
                "timestamp": utc_now_iso(),
                "source": "agk-sdk-poc",
                "payload": result_payload,
            }
        )
        return {
            "phase": "fulfilled",
            "decision": "allow",
            "transaction_id": transaction_id,
            "preflight": preflight,
            "call": call_response,
            "result": result_payload,
        }

    def authorize(self, request):
        return self._post_json(
            f"{self.service_base_url}/v1/governed-actions/authorize",
            request,
            allow_http_error=True,
        )["body"]

    def emit_event(self, event):
        return self._post_json(
            f"{self.service_base_url}/v1/governed-actions/events",
            event,
            allow_http_error=False,
        )["body"]

    def get_state(self):
        request = urllib.request.Request(
            f"{self.service_base_url}/v1/governed-actions/state",
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=5.0) as response:
            return json.loads(response.read().decode("utf-8"))

    def initialize_session(self, token):
        response = self._send_mcp_request(
            payload={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {
                        "name": "agk-poc-sdk",
                        "version": "0.1",
                    },
                },
            },
            token=token,
        )
        headers = response["headers"]
        session_id = headers.get("Mcp-Session-Id") or headers.get("mcp-session-id")
        if not session_id:
            raise RuntimeError("initialize_missing_session_id")
        return session_id

    def call_tool(self, session_id, token, tool_name, arguments):
        return self._send_mcp_request(
            payload={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments,
                },
            },
            token=token,
            session_id=session_id,
        )

    def _send_mcp_request(self, payload, token, session_id=None):
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": self.caller_auth,
            "X-AGK-Governance-Token": token,
        }
        if session_id:
            headers["Mcp-Session-Id"] = session_id

        request = urllib.request.Request(
            f"{self.gateway_base_url}/mcp",
            data=body,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10.0) as response:
            raw_body = response.read().decode("utf-8")
            return {
                "status": response.status,
                "headers": dict(response.headers.items()),
                "body": self._decode_mcp_body(raw_body),
            }

    def _post_json(self, url, payload, allow_http_error):
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5.0) as response:
                return {
                    "status": response.status,
                    "headers": dict(response.headers.items()),
                    "body": json.loads(response.read().decode("utf-8")),
                }
        except urllib.error.HTTPError as exc:
            if not allow_http_error:
                raise
            try:
                error_body = exc.read().decode("utf-8")
                return {
                    "status": exc.code,
                    "headers": dict(exc.headers.items()),
                    "body": json.loads(error_body),
                }
            finally:
                exc.close()

    def _decode_http_error_body(self, exc):
        try:
            raw = exc.read().decode("utf-8")
        except Exception:
            return {"error": "unreadable_error_body"}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}

    def _extract_call_payload(self, response_body):
        result = response_body.get("result", {})
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured

        content = result.get("content", [])
        if content and isinstance(content[0], dict):
            text = content[0].get("text")
            if isinstance(text, str):
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"text": text}
        return {"raw_result": result}

    def _decode_mcp_body(self, raw_body):
        if not raw_body.strip():
            return {}
        try:
            return json.loads(raw_body)
        except json.JSONDecodeError:
            data_lines = []
            for line in raw_body.splitlines():
                if line.startswith("data:"):
                    data_lines.append(line.split(":", 1)[1].strip())
            if data_lines:
                joined = "\n".join(data_lines)
                return json.loads(joined)
            raise
