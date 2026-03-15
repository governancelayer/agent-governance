import argparse
import json
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def _log(message):
    print(f"[supplier-mcp-mock {utc_now()}] {message}", flush=True)


class SupplierMCPHandler(BaseHTTPRequestHandler):
    server_version = "AGKSupplierMCPMock/0.1"

    def do_POST(self):
        if self.path != "/mcp":
            self._send_json(404, {"error": "not_found"})
            return

        raw = self._read_body()
        try:
            request = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return

        method = request.get("method")
        req_id = request.get("id")
        session_id = self.headers.get("Mcp-Session-Id")
        _log(
            f"request method={method} id={req_id} "
            f"session_id={'present' if session_id else 'absent'}"
        )

        if method == "initialize":
            response_session = str(uuid.uuid4())
            self._send_json(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": request.get("params", {}).get(
                            "protocolVersion", "2025-06-18"
                        ),
                        "capabilities": {"tools": {}},
                        "serverInfo": {
                            "name": "agk-supplier-mcp-mock",
                            "version": "0.1",
                        },
                    },
                },
                extra_headers={"Mcp-Session-Id": response_session},
            )
            return

        if not session_id:
            self._send_json(
                400,
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32000,
                        "message": "session header is required",
                    },
                },
            )
            return

        if method == "tools/list":
            self._send_json(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {
                                "name": "createPurchaseOrder",
                                "description": "Create a procurement purchase order",
                            }
                        ]
                    },
                },
            )
            return

        if method == "tools/call":
            tool_name = request.get("params", {}).get("name")
            if tool_name != "createPurchaseOrder":
                self._send_json(
                    404,
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {
                            "code": -32601,
                            "message": f"unknown tool: {tool_name}",
                        },
                    },
                )
                return

            arguments = request.get("params", {}).get("arguments", {})
            result = {
                "purchase_order_id": f"PO-POC-{uuid.uuid4().hex[:6].upper()}",
                "status": "accepted",
                "supplier_id": arguments.get("supplier_id"),
                "amount": arguments.get("amount"),
                "currency": arguments.get("currency"),
            }
            self._send_json(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(result),
                            }
                        ],
                        "structuredContent": result,
                    },
                },
            )
            return

        self._send_json(
            404,
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"unsupported method: {method}"},
            },
        )

    def log_message(self, format, *args):
        return

    def _read_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return ""
        return self.rfile.read(length).decode("utf-8")

    def _send_json(self, status, payload, extra_headers=None):
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        if extra_headers:
            for key, value in extra_headers.items():
                self.send_header(key, value)
        self.end_headers()
        self.wfile.write(encoded)


def main():
    parser = argparse.ArgumentParser(description="Supplier MCP mock for AGK POC")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=3101)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), SupplierMCPHandler)
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
