"""
Tiny local HTTP server that renders a draft as an actual HTML page with
images — so it can be reviewed at a real localhost URL instead of reading
raw markdown in chat. Starts once per MCP server process and stays up;
each request re-reads the file fresh from disk, so edits show up on refresh.
"""

import threading
import markdown as md
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

PORT = 8420
DRAFTS_DIR = Path(__file__).parent.parent / "drafts"

_server_thread = None

PAGE_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, Georgia, serif; max-width: 760px; margin: 40px auto; padding: 0 20px; line-height: 1.6; color: #222; }}
  img {{ max-width: 100%; border-radius: 8px; }}
  h1, h2, h3 {{ line-height: 1.3; }}
  em {{ color: #666; font-size: 0.9em; }}
  a {{ color: #0a5; }}
</style>
</head>
<body>
{content}
</body>
</html>
"""


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # keep this quiet — don't print to stdout/stderr on every request

    def do_GET(self):
        path = unquote(self.path).lstrip("/")

        if not path:
            self._serve_index()
            return

        matches = list(DRAFTS_DIR.glob(f"*{path}*"))
        if not matches:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Draft not found")
            return

        filepath = sorted(matches, reverse=True)[0]
        raw = filepath.read_text()
        html_body = md.markdown(raw, extensions=["extra"])
        page = PAGE_TEMPLATE.format(title=filepath.stem, content=html_body)

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))

    def _serve_index(self):
        drafts = sorted(DRAFTS_DIR.glob("*.md"), reverse=True)
        links = "\n".join(f'<li><a href="/{d.stem}">{d.stem}</a></li>' for d in drafts)
        page = PAGE_TEMPLATE.format(title="Drafts", content=f"<h1>Drafts</h1><ul>{links}</ul>")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(page.encode("utf-8"))


def ensure_server_running() -> int:
    """Start the preview server once per process. Returns the port."""
    global _server_thread
    if _server_thread is not None:
        return PORT

    server = ThreadingHTTPServer(("127.0.0.1", PORT), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _server_thread = thread
    return PORT


def preview_url(filename_hint: str = "") -> str:
    ensure_server_running()
    if filename_hint:
        return f"http://localhost:{PORT}/{filename_hint}"
    return f"http://localhost:{PORT}/"
