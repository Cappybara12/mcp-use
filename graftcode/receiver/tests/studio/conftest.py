"""Fixtures for Pipeline Studio tests: an isolated data folder and a mock provider server."""
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def studio_env(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_DATA_DIR", str(tmp_path / "studio-data"))
    monkeypatch.setenv("STUDIO_ALLOW_PRIVATE_URLS", "1")   # tests talk to a 127.0.0.1 mock server
    for var in ("STUDIO_KEY_OPENAI", "STUDIO_KEY_TINYFISH", "STUDIO_KEY_DATAFORSEO", "STUDIO_KEY_GITHUB"):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


class Mock:
    """A tiny HTTP server that records requests and answers from a route table."""

    def __init__(self):
        self.requests = []
        self.routes = {}        # (METHOD, path-prefix) -> (status, body, headers)
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _serve(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                outer.requests.append({"method": self.command, "path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()},
                                       "body": body})
                for (method, prefix), (status, payload, headers) in outer.routes.items():
                    if method == self.command and self.path.startswith(prefix):
                        data = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
                        self.send_response(status)
                        if "Content-Type" not in (headers or {}):
                            self.send_header("Content-Type", "application/json")
                        for k, v in (headers or {}).items():
                            self.send_header(k, v)
                        self.send_header("Content-Length", str(len(data)))
                        self.end_headers()
                        self.wfile.write(data)
                        return
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.end_headers()

            do_GET = do_POST = do_PUT = _serve

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=0.01), daemon=True)
        self.thread.start()

    def on(self, method, prefix, body, status=200, headers=None):
        self.routes[(method, prefix)] = (status, body, headers)

    def body_of(self, index=-1):
        return json.loads(self.requests[index]["body"].decode())

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture()
def mock():
    m = Mock()
    yield m
    m.stop()


@pytest.fixture()
def api():
    from article_receiver.studio import api as studio_api
    return studio_api


@pytest.fixture()
def ws(api):
    return api.create_workspace("Acme Analytics", "", "SaaS analytics", "demo")["id"]
