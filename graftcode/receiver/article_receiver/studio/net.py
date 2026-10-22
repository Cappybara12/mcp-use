"""HTTP helpers for Pipeline Studio.

Two kinds of requests:

* ``fetch_public`` - for URLs a *user* supplies (RSS feeds, blog pages). These are protected
  against SSRF: http(s) only, the host is resolved once, every resolved address must be public,
  and the connection is pinned to the address that was checked (so DNS rebinding cannot swap it).
* ``call_api`` - for keyed calls to fixed provider hosts (TinyFish, DataForSEO, GitHub, LLMs).
  API keys are only ever sent to those hosts, and are never included in error messages.

Test hooks (never set in production): STUDIO_ALLOW_PRIVATE_URLS=1 lets ``fetch_public`` reach
127.0.0.1 mock servers; STUDIO_BASE_<PROVIDER> overrides a provider's base URL.
"""
from __future__ import annotations

import base64
import http.client
import ipaddress
import json
import os
import socket
import ssl
import urllib.parse
from dataclasses import dataclass

from .store import StudioError

USER_AGENT = "graft-studio/1.0 (+https://github.com/Cappybara12/mcp-use)"
MAX_REDIRECTS = 5
DEFAULT_MAX_BYTES = 3_000_000


class NetError(StudioError):
    """A network problem with a message that is safe to show (no secrets)."""


@dataclass
class Response:
    status: int
    headers: dict
    body: bytes
    url: str
    secrets: tuple = ()      # secret values that were sent with the request; never allowed into messages

    def text(self) -> str:
        charset = "utf-8"
        ctype = self.headers.get("content-type", "")
        if "charset=" in ctype:
            charset = ctype.split("charset=", 1)[1].split(";")[0].strip() or "utf-8"
        try:
            return self.body.decode(charset, errors="replace")
        except LookupError:
            return self.body.decode("utf-8", errors="replace")

    def json(self):
        try:
            return json.loads(self.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise NetError(f"The service did not return valid JSON (HTTP {self.status}).") from exc


# ── SSRF protection ───────────────────────────────────────────────────────────

def _allow_private() -> bool:
    return os.environ.get("STUDIO_ALLOW_PRIVATE_URLS") == "1"


def _is_public(ip: str) -> bool:
    """Only globally routable unicast addresses count as public (this also excludes 100.64.0.0/10 and similar)."""
    addr = ipaddress.ip_address(ip.split("%")[0])
    mapped = getattr(addr, "ipv4_mapped", None)
    if mapped is not None:          # ::ffff:127.0.0.1 is judged as the IPv4 address it wraps
        addr = mapped
    return addr.is_global and not addr.is_multicast


def resolve_public(url: str) -> tuple[urllib.parse.ParseResult, str, int]:
    """Validate a user URL and return (parsed, pinned_ip, port). Raises NetError if it is not safe."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise NetError("Only http and https URLs are allowed.")
    if not parsed.hostname:
        raise NetError("The URL has no host.")
    if parsed.username or parsed.password:
        raise NetError("URLs with embedded credentials are not allowed.")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise NetError(f"Could not resolve {parsed.hostname}.") from exc
    addresses = [info[4][0] for info in infos]
    if not addresses:
        raise NetError(f"Could not resolve {parsed.hostname}.")
    if not _allow_private():
        for ip in addresses:
            if not _is_public(ip):
                raise NetError("That address is not public, so it is blocked (private, local and reserved ranges are not allowed).")
    return parsed, addresses[0], port


class _PinnedHTTP(http.client.HTTPConnection):
    def __init__(self, host, ip, port, timeout):
        super().__init__(host, port, timeout=timeout)
        self._ip = ip

    def connect(self):
        self.sock = socket.create_connection((self._ip, self.port), self.timeout)


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, ip, port, timeout):
        super().__init__(host, port, timeout=timeout, context=ssl.create_default_context())
        self._ip = ip
        self._sni = host

    def connect(self):
        sock = socket.create_connection((self._ip, self.port), self.timeout)
        self.sock = self._context.wrap_socket(sock, server_hostname=self._sni)


def _request_once(parsed, ip, port, method, headers, body, timeout, max_bytes) -> Response:
    conn_cls = _PinnedHTTPS if parsed.scheme == "https" else _PinnedHTTP
    conn = conn_cls(parsed.hostname, ip, port, timeout)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    try:
        conn.request(method, path, body=body, headers={"Host": parsed.netloc, "User-Agent": USER_AGENT,
                                                      "Accept-Encoding": "identity", **headers})
        resp = conn.getresponse()
        chunks, total = [], 0
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise NetError(f"The response is larger than {max_bytes // 1000} KB, so it was not read.")
            chunks.append(chunk)
        return Response(resp.status, {k.lower(): v for k, v in resp.getheaders()}, b"".join(chunks), parsed.geturl())
    except (OSError, http.client.HTTPException) as exc:
        raise NetError(f"Could not reach {parsed.hostname}: {exc.__class__.__name__}.") from exc
    finally:
        conn.close()


def fetch_public(url: str, *, timeout: float = 20, max_bytes: int = DEFAULT_MAX_BYTES, headers: dict | None = None) -> Response:
    """GET a user-supplied URL safely, following redirects (each hop is re-validated and pinned)."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        parsed, ip, port = resolve_public(current)
        resp = _request_once(parsed, ip, port, "GET", headers or {}, None, timeout, max_bytes)
        if resp.status in (301, 302, 303, 307, 308) and resp.headers.get("location"):
            current = urllib.parse.urljoin(current, resp.headers["location"])
            continue
        return resp
    raise NetError("Too many redirects.")


# ── keyed calls to fixed hosts ────────────────────────────────────────────────

def provider_base(provider: str, default: str) -> str:
    return os.environ.get(f"STUDIO_BASE_{provider.upper()}") or default


def call_api(method: str, url: str, *, headers: dict | None = None, json_body=None, timeout: float = 120,
             max_bytes: int = 8_000_000) -> Response:
    """Call a fixed provider API. ``url`` must be built from a trusted base, never from user input."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise NetError("Invalid API URL.")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    body = None
    hdrs = dict(headers or {})
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    try:
        ip = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)[0][4][0]
    except socket.gaierror as exc:
        raise NetError(f"Could not resolve {parsed.hostname}.") from exc
    resp = _request_once(parsed, ip, port, method, hdrs, body, timeout, max_bytes)
    resp.secrets = _secret_values(hdrs)
    return resp


def _secret_values(headers: dict) -> tuple:
    """Credentials carried in request headers (including a decoded Basic login:password)."""
    found = set()
    for name, value in headers.items():
        if name.lower() in ("authorization", "x-api-key") and isinstance(value, str):
            token = value.split(" ", 1)[-1].strip()
            if len(token) >= 6:
                found.add(token)
                try:
                    decoded = base64.b64decode(token, validate=True).decode()
                    found.update(part for part in decoded.split(":") if len(part) >= 6)
                    found.add(decoded)
                except (ValueError, UnicodeDecodeError):
                    pass
    return tuple(found)


def redact(text: str, secrets) -> str:
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[redacted]")
    return text


def raise_for_status(resp: Response, service: str) -> None:
    """Turn an HTTP error into a short, safe message (never echoes headers or keys)."""
    if resp.status < 400:
        return
    hints = {
        400: "the request was rejected as invalid",
        401: "the API key was rejected (check it in Settings & keys)",
        402: "no credits left or the free allowance is used up",
        403: "access was refused for this key or account",
        404: "not found",
        422: "the request had invalid values",
        429: "rate limit reached; wait a moment and retry",
    }
    detail = ""
    if resp.status not in (401, 403):        # providers often echo (part of) a rejected key, so say nothing about auth failures
        try:
            body = resp.json()
            if isinstance(body, dict):
                err = body.get("error") or body.get("message") or body.get("detail")
                if isinstance(err, dict):
                    err = err.get("message")
                if isinstance(err, str):
                    detail = ": " + redact(err[:200], resp.secrets)
        except NetError:
            pass
    raise NetError(f"{service} returned HTTP {resp.status} - {hints.get(resp.status, 'request failed')}{detail}")
