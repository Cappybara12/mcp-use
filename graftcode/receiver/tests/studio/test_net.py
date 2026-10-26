import socket

import pytest

from article_receiver.studio import net
from article_receiver.studio.net import NetError


@pytest.fixture()
def strict(monkeypatch):
    monkeypatch.delenv("STUDIO_ALLOW_PRIVATE_URLS", raising=False)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1/", "http://localhost/", "http://10.0.0.5/", "http://192.168.1.1/x", "http://172.16.5.5/",
    "http://169.254.169.254/latest/meta-data/", "http://[::1]/", "http://0.0.0.0/", "http://100.64.0.1/",
    "http://[::ffff:127.0.0.1]/",
])
def test_private_and_local_addresses_are_blocked(strict, url):
    with pytest.raises(NetError, match="not public|resolve"):
        net.fetch_public(url)


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/", "gopher://example.com/", "javascript:alert(1)",
                                 "http:///path", "http://user:pass@example.com/", "//example.com/"])
def test_dangerous_schemes_and_credentials_are_rejected(strict, url):
    with pytest.raises(NetError):
        net.fetch_public(url)


def _resolver(monkeypatch, table):
    real = socket.getaddrinfo

    def fake(host, port, *a, **k):
        if host not in table:                      # IP literals (the pinned connection) resolve normally
            return real(host, port, *a, **k)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, port)) for ip in table[host]]
    monkeypatch.setattr(net.socket, "getaddrinfo", fake)


def test_a_name_that_resolves_to_a_private_address_is_blocked(strict, monkeypatch):
    _resolver(monkeypatch, {"evil.example": ["127.0.0.1"]})
    with pytest.raises(NetError, match="not public"):
        net.resolve_public("http://evil.example/")


def test_mixed_public_and_private_answers_are_blocked(strict, monkeypatch):
    _resolver(monkeypatch, {"rebind.example": ["93.184.216.34", "10.0.0.7"]})
    with pytest.raises(NetError, match="not public"):
        net.resolve_public("https://rebind.example/")


def test_public_name_is_accepted_and_pinned(strict, monkeypatch):
    _resolver(monkeypatch, {"good.example": ["93.184.216.34"]})
    parsed, ip, port = net.resolve_public("https://good.example/page")
    assert (ip, port) == ("93.184.216.34", 443)


def test_connection_is_pinned_to_the_checked_address(mock, monkeypatch):
    """The request goes to the IP that was validated, with the original Host header (no second DNS lookup)."""
    mock.on("GET", "/page", b"<html>ok</html>")
    _resolver(monkeypatch, {"pinned.test": ["127.0.0.1"]})
    port = mock.server.server_port
    resp = net.fetch_public(f"http://pinned.test:{port}/page")
    assert resp.status == 200 and "ok" in resp.text()
    assert mock.requests[-1]["headers"]["host"] == f"pinned.test:{port}"


def test_redirect_to_a_private_address_is_blocked(mock, monkeypatch):
    mock.on("GET", "/start", b"", status=302, headers={"Location": "http://169.254.169.254/latest/meta-data/"})
    calls = {"n": 0}

    def allow_first_hop_only():
        calls["n"] += 1
        return calls["n"] == 1

    monkeypatch.setattr(net, "_allow_private", allow_first_hop_only)
    with pytest.raises(NetError, match="not public"):
        net.fetch_public(f"{mock.url}/start")


def test_redirect_loops_stop(mock):
    mock.on("GET", "/loop", b"", status=302, headers={"Location": "/loop"})
    with pytest.raises(NetError, match="Too many redirects"):
        net.fetch_public(f"{mock.url}/loop")


def test_oversized_responses_are_cut_off(mock):
    mock.on("GET", "/big", b"x" * 50_000)
    with pytest.raises(NetError, match="larger than"):
        net.fetch_public(f"{mock.url}/big", max_bytes=1000)


def test_unreachable_hosts_give_a_clean_error():
    with pytest.raises(NetError, match="Could not"):
        net.fetch_public("http://127.0.0.1:9/")


# ── keyed API calls ───────────────────────────────────────────────────────────

def test_call_api_sends_json_and_headers(mock):
    mock.on("POST", "/x", {"ok": True})
    resp = net.call_api("POST", f"{mock.url}/x", headers={"X-Test": "1"}, json_body={"a": 1})
    assert resp.json() == {"ok": True}
    req = mock.requests[-1]
    assert req["headers"]["x-test"] == "1" and req["headers"]["content-type"] == "application/json" and mock.body_of() == {"a": 1}


@pytest.mark.parametrize("status,needle", [(401, "API key was rejected"), (402, "no credits"), (403, "refused"), (429, "rate limit"),
                                           (422, "invalid values"), (500, "request failed")])
def test_http_errors_become_friendly_messages_without_secrets(mock, status, needle):
    mock.on("GET", "/e", {"error": {"message": "bad thing"}}, status=status)
    resp = net.call_api("GET", f"{mock.url}/e", headers={"Authorization": "Bearer sk-TOPSECRET"})
    with pytest.raises(NetError) as err:
        net.raise_for_status(resp, "Service")
    assert needle in str(err.value) and "sk-TOPSECRET" not in str(err.value)


def test_non_json_bodies_are_reported(mock):
    mock.on("GET", "/h", b"<html>nope</html>")
    with pytest.raises(NetError, match="valid JSON"):
        net.call_api("GET", f"{mock.url}/h").json()
