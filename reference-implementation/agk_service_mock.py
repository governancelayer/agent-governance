import argparse
import base64
import hashlib
import hmac
import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


DEFAULT_SHARED_SECRET = "agk-poc-shared-secret"
DEFAULT_MAX_AMOUNT = 8000
DEFAULT_ALLOWED_SUPPLIER_ID = "supplier-x"
DEFAULT_ALLOWED_ACTION = "createPurchaseOrder"


def utc_now():
    return datetime.now(timezone.utc)


def _log(message):
    print(f"[agk-service-mock {utc_now().isoformat()}] {message}", flush=True)


def _b64url_encode(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64url_decode(value):
    padding = "=" * ((4 - (len(value) % 4)) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def sign_governance_token(payload, secret):
    payload_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    payload_part = _b64url_encode(payload_bytes)
    signature = hmac.new(
        secret.encode("utf-8"), payload_part.encode("ascii"), hashlib.sha256
    ).digest()
    signature_part = _b64url_encode(signature)
    return f"{payload_part}.{signature_part}"


def verify_governance_token(token, secret):
    try:
        payload_part, signature_part = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("invalid_token_format") from exc

    expected_sig = hmac.new(
        secret.encode("utf-8"), payload_part.encode("ascii"), hashlib.sha256
    ).digest()
    actual_sig = _b64url_decode(signature_part)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("invalid_signature")

    payload = json.loads(_b64url_decode(payload_part).decode("utf-8"))
    expires_at = datetime.fromisoformat(payload["expires_at"])
    if utc_now() > expires_at:
        raise ValueError("token_expired")

    return payload


def extract_mcp_contract(mcp_request):
    method = mcp_request.get("method")
    params = mcp_request.get("params", {})
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    return {
        "method": method,
        "tool_name": tool_name,
        "arguments": arguments,
    }


class AGKServiceMock:
    def __init__(
        self,
        secret=DEFAULT_SHARED_SECRET,
        max_amount=DEFAULT_MAX_AMOUNT,
        allowed_supplier_id=DEFAULT_ALLOWED_SUPPLIER_ID,
        allowed_action=DEFAULT_ALLOWED_ACTION,
        issuer="agk-poc",
    ):
        self.secret = secret
        self.max_amount = max_amount
        self.allowed_supplier_id = allowed_supplier_id
        self.allowed_action = allowed_action
        self.issuer = issuer
        self.transactions = {}
        self.events = []

    def authorize(self, request):
        tx_id = request.get("request_id") or f"tx-poc-{uuid.uuid4().hex[:8]}"
        amount = int(request.get("business_context", {}).get("amount", 0))
        supplier_id = request.get("business_context", {}).get("supplier_id")
        action_name = request.get("action", {}).get("name")
        principal_id = request.get("principal", {}).get("id")
        agent_id = request.get("agent", {}).get("id")

        record = {
            "transaction_id": tx_id,
            "request": request,
            "created_at": utc_now().isoformat(),
            "state": "created",
            "last_reason_code": None,
            "events": [],
        }

        if action_name != self.allowed_action:
            response = {
                "transaction_id": tx_id,
                "decision": "deny",
                "reason_code": "ERR_ACTION_NOT_ALLOWED",
            }
            record["state"] = "denied"
            record["last_reason_code"] = response["reason_code"]
            self.transactions[tx_id] = record
            return response

        if supplier_id != self.allowed_supplier_id:
            response = {
                "transaction_id": tx_id,
                "decision": "deny",
                "reason_code": "ERR_SUPPLIER_NOT_ALLOWED",
            }
            record["state"] = "denied"
            record["last_reason_code"] = response["reason_code"]
            self.transactions[tx_id] = record
            return response

        if amount > self.max_amount:
            response = {
                "transaction_id": tx_id,
                "decision": "deny",
                "reason_code": "ERR_APPROVAL_LIMIT_EXCEEDED",
            }
            record["state"] = "denied"
            record["last_reason_code"] = response["reason_code"]
            self.transactions[tx_id] = record
            return response

        token_payload = {
            "transaction_id": tx_id,
            "issuer": self.issuer,
            "principal_id": principal_id,
            "agent_id": agent_id,
            "allowed_action": self.allowed_action,
            "allowed_supplier_id": self.allowed_supplier_id,
            "max_amount": self.max_amount,
            "expires_at": (utc_now() + timedelta(hours=8)).isoformat(),
        }
        token = sign_governance_token(token_payload, self.secret)
        response = {
            "transaction_id": tx_id,
            "decision": "allow",
            "reason_code": "OK_GOVERNED_ACTION_ALLOWED",
            "governance_token": token,
            "runtime_constraints": {
                "allowed_action": self.allowed_action,
                "max_amount": self.max_amount,
                "allowed_supplier_id": self.allowed_supplier_id,
                "expires_at": token_payload["expires_at"],
            },
        }

        record["state"] = "authorized"
        record["last_reason_code"] = response["reason_code"]
        record["token_payload"] = token_payload
        self.transactions[tx_id] = record
        return response

    def record_event(self, event):
        tx_id = event.get("transaction_id")
        if not tx_id:
            raise ValueError("transaction_id_required")

        record = self.transactions.get(tx_id)
        if record is None:
            raise ValueError("unknown_transaction")

        event_type = event.get("event_type")
        state_map = {
            "preflight_denied": "denied",
            "request_sent": "request_sent",
            "gateway_rejected": "gateway_rejected",
            "supplier_rejected": "supplier_rejected",
            "supplier_completed": "fulfilled",
            "transport_error": "transport_error",
        }
        record["state"] = state_map.get(event_type, record["state"])
        record["events"].append(event)
        record["last_event_type"] = event_type
        record["updated_at"] = utc_now().isoformat()
        self.events.append(event)
        return {
            "transaction_id": tx_id,
            "state": record["state"],
            "last_event_type": event_type,
        }

    def verify_runtime_contract(self, token, mcp_request):
        payload = verify_governance_token(token, self.secret)
        contract = extract_mcp_contract(mcp_request)
        method = contract["method"]
        tx_id = payload["transaction_id"]
        if tx_id not in self.transactions:
            raise ValueError("unknown_transaction")

        if method == "initialize":
            return {
                "decision": "allow",
                "transaction_id": tx_id,
                "reason_code": "OK_INITIALIZE_ALLOWED",
            }

        if method == "tools/list":
            return {
                "decision": "allow",
                "transaction_id": tx_id,
                "reason_code": "OK_TOOLS_LIST_ALLOWED",
            }

        if method != "tools/call":
            raise ValueError("unsupported_mcp_method")

        if contract["tool_name"] != payload["allowed_action"]:
            raise ValueError("tool_name_mismatch")

        arguments = contract["arguments"]
        amount = int(arguments.get("amount", 0))
        supplier_id = arguments.get("supplier_id")

        if supplier_id != payload["allowed_supplier_id"]:
            raise ValueError("supplier_mismatch")
        if amount > int(payload["max_amount"]):
            raise ValueError("amount_exceeds_max")

        return {
            "decision": "allow",
            "transaction_id": tx_id,
            "reason_code": "OK_RUNTIME_CONTRACT_VALID",
        }

    def get_transaction(self, transaction_id):
        return self.transactions.get(transaction_id)

    def get_state_snapshot(self):
        return {
            "transactions": self.transactions,
            "events": self.events,
        }


class AGKMockHandler(BaseHTTPRequestHandler):
    server_version = "AGKServiceMock/0.1"

    @property
    def agk(self):
        return self.server.agk_service

    def do_GET(self):
        if self.path == "/healthz":
            self._send_json(200, {"ok": True})
            return

        if self.path == "/v1/governed-actions/state":
            self._send_json(200, self.agk.get_state_snapshot())
            return

        self._send_json(404, {"error": "not_found"})

    def do_POST(self):
        raw = self._read_body()
        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return

        if self.path == "/v1/governed-actions/authorize":
            response = self.agk.authorize(payload)
            status = 200 if response["decision"] == "allow" else 403
            _log(
                f"authorize transaction_id={response['transaction_id']} "
                f"decision={response['decision']}"
            )
            self._send_json(status, response)
            return

        if self.path == "/v1/governed-actions/events":
            try:
                response = self.agk.record_event(payload)
            except ValueError as exc:
                self._send_json(400, {"error": str(exc)})
                return
            _log(
                f"event transaction_id={response['transaction_id']} "
                f"state={response['state']}"
            )
            self._send_json(200, response)
            return

        if self.path == "/v1/governed-actions/verify":
            token = self.headers.get("X-AGK-Governance-Token")
            if not token:
                _log("verify decision=deny reason=missing_token")
                self._send_json(403, {"decision": "deny", "reason_code": "ERR_MISSING_TOKEN"})
                return
            try:
                response = self.agk.verify_runtime_contract(token, payload)
            except ValueError as exc:
                _log(f"verify decision=deny reason={exc}")
                self._send_json(
                    403,
                    {"decision": "deny", "reason_code": str(exc)},
                )
                return
            _log(
                f"verify transaction_id={response['transaction_id']} "
                f"decision={response['decision']}"
            )
            self._send_json(200, response)
            return

        self._send_json(404, {"error": "not_found"})

    def log_message(self, format, *args):
        return

    def _read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return ""
        return self.rfile.read(length).decode("utf-8")

    def _send_json(self, status, payload):
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main():
    parser = argparse.ArgumentParser(description="AGK mock control-plane service")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3102)
    parser.add_argument(
        "--secret",
        default=os.environ.get("AGK_POC_SHARED_SECRET", DEFAULT_SHARED_SECRET),
    )
    args = parser.parse_args()

    agk = AGKServiceMock(secret=args.secret)
    server = ThreadingHTTPServer((args.host, args.port), AGKMockHandler)
    server.agk_service = agk
    _log(f"starting server host={args.host} port={args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        _log("stopping server")
        server.server_close()


if __name__ == "__main__":
    main()
