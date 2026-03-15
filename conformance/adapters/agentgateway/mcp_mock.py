import argparse
import json
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def log(message):
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"[mcp-mock {timestamp}] {message}", flush=True)


class FixtureHandler(BaseHTTPRequestHandler):
    server_version = "AGKMcpMock/0.1"

    def do_POST(self):
        if self.path != "/mcp":
            self._send_json(404, {"error": "not_found"})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8")
        try:
            request = json.loads(raw)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "invalid_json"})
            return

        method = request.get("method")
        req_id = request.get("id")
        session_id = self.headers.get("Mcp-Session-Id")
        log(
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
                            "name": "agk-local-mcp-mock",
                            "version": "0.1",
                        },
                    },
                },
                extra_headers={"Mcp-Session-Id": response_session},
            )
            log("response method=initialize status=200")
            return

        if not session_id:
            self._send_json(
                400,
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32000,
                        "message": "session header is required for non-initialize requests",
                    },
                },
            )
            log(f"response method={method} status=400 missing-session")
            return

        if method == "tools/list":
            self._send_json(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {"name": "echo", "description": "Echo a string"},
                            {"name": "add", "description": "Add two numbers"},
                            {"name": "printEnv", "description": "Return fixture environment"},
                        ]
                    },
                },
            )
            log("response method=tools/list status=200")
            return

        if method == "tools/call":
            tool_name = request.get("params", {}).get("name")
            if tool_name == "printEnv":
                self._send_json(
                    200,
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [
                                {
                                    "type": "text",
                                    "text": "fixture-printenv",
                                }
                            ]
                        },
                    },
                )
                log("response method=tools/call name=printEnv status=200")
                return

            self._send_json(
                200,
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"fixture-tool:{tool_name}",
                            }
                        ]
                    },
                },
            )
            log(f"response method=tools/call name={tool_name} status=200")
            return

        self._send_json(
            404,
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"unsupported method: {method}"},
            },
        )
        log(f"response method={method} status=404 unsupported")

    def log_message(self, format, *args):
        return

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
    parser = argparse.ArgumentParser(description="AGK local MCP mock")
    parser.add_argument("--port", type=int, default=3001)
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), FixtureHandler)
    log(f"starting server port={args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        log("stopping server")
        server.server_close()


if __name__ == "__main__":
    main()
