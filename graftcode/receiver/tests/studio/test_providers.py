import base64
import json

import pytest

from article_receiver.studio import providers
from article_receiver.studio.net import NetError
from article_receiver.studio.store import StudioError

OPENAI_OK = {"choices": [{"message": {"content": "  Hello from the model  "}}]}


@pytest.fixture()
def base(mock, monkeypatch):
    for name in ("openai", "anthropic", "groq", "moonshot", "openrouter", "tinyfish_search", "tinyfish_fetch", "dataforseo", "github"):
        monkeypatch.setenv(f"STUDIO_BASE_{name.upper()}", mock.url + ("/v1" if name in ("openai", "anthropic", "groq", "moonshot", "openrouter") else ""))
    return mock


# ── LLMs ──────────────────────────────────────────────────────────────────────

def test_openai_request_shape(base):
    base.on("POST", "/v1/chat/completions", OPENAI_OK)
    out = providers.chat("openai", "sk-test", "", "SYSTEM", "USER", "write")
    assert out == "Hello from the model"
    req = base.requests[-1]
    body = base.body_of()
    assert req["headers"]["authorization"] == "Bearer sk-test"
    assert body["model"] == "gpt-5.5" and body["messages"][0] == {"role": "system", "content": "SYSTEM"} and "max_tokens" not in body


@pytest.mark.parametrize("provider", ["groq", "moonshot", "openrouter"])
def test_openai_compatible_providers(base, provider):
    base.on("POST", "/v1/chat/completions", OPENAI_OK)
    assert providers.chat(provider, "k", "my-model", "s", "u", "text", 777) == "Hello from the model"
    assert base.body_of()["model"] == "my-model" and base.body_of()["max_tokens"] == 777


def test_anthropic_request_shape(base):
    base.on("POST", "/v1/messages", {"content": [{"type": "text", "text": "Hi "}, {"type": "text", "text": "there"}]})
    assert providers.chat("anthropic", "ak-test", "claude-x", "SYS", "USR", "text", 100) == "Hi there"
    req, body = base.requests[-1], base.body_of()
    assert req["headers"]["x-api-key"] == "ak-test" and req["headers"]["anthropic-version"] == "2023-06-01"
    assert body["system"] == "SYS" and body["messages"] == [{"role": "user", "content": "USR"}] and body["max_tokens"] == 100


def test_llm_errors_never_contain_the_key(base):
    base.on("POST", "/v1/chat/completions", {"error": {"message": "Incorrect API key provided: sk-LEAKYKEY"}}, status=401)
    with pytest.raises(NetError) as err:
        providers.chat("openai", "sk-LEAKYKEY", "", "s", "u")
    assert "API key was rejected" in str(err.value)
    assert "LEAKYKEY" not in str(err.value) and "sk-" not in str(err.value)


def test_secrets_are_redacted_from_non_auth_error_messages(base):
    base.on("POST", "/v1/chat/completions", {"error": {"message": "model rejected request from key sk-LEAKYKEY"}}, status=400)
    with pytest.raises(NetError) as err:
        providers.chat("openai", "sk-LEAKYKEY", "", "s", "u")
    assert "[redacted]" in str(err.value) and "LEAKYKEY" not in str(err.value)


def test_basic_auth_passwords_are_redacted_too(base):
    base.on("POST", "/v3/", {"status_message": "bad request for me@x.com:hunter2hunter2"}, status=400)
    with pytest.raises(NetError) as err:
        providers.dataforseo_suggestions("me@x.com:hunter2hunter2", "x")
    assert "hunter2hunter2" not in str(err.value)


def test_empty_answers_are_errors(base):
    base.on("POST", "/v1/chat/completions", {"choices": []})
    with pytest.raises(NetError, match="empty"):
        providers.chat("openai", "k", "", "s", "u")


def test_unknown_provider_and_missing_key():
    with pytest.raises(StudioError):
        providers.chat("nope", "k", "", "s", "u")
    with pytest.raises(StudioError):
        providers.chat("openai", "", "", "s", "u")


def test_demo_provider_needs_no_key_or_network():
    assert "Demo template" in providers.chat("demo", "", "", "s", "TOPIC: x\nPRIMARY KEYWORD: y", "write")


# ── TinyFish ──────────────────────────────────────────────────────────────────

def test_tinyfish_search(base):
    base.on("GET", "/", {"query": "q", "results": [{"position": 1, "title": "T", "url": "https://a.com", "snippet": "S"}]})
    results = providers.tinyfish_search("tf-key", "best crm software", "GB", "en")
    req = base.requests[-1]
    assert req["headers"]["x-api-key"] == "tf-key" and "query=best+crm+software" in req["path"] and "location=GB" in req["path"]
    assert results[0]["url"] == "https://a.com"


def test_tinyfish_fetch_reports_per_url_errors(base):
    base.on("POST", "/", {"results": [{"url": "https://a.com", "text": "# Hi", "title": "A"}], "errors": [{"url": "https://b.com", "error": "bot_blocked"}]})
    results, errors = providers.tinyfish_fetch("tf-key", ["https://a.com", "https://b.com"])
    assert base.requests[-1]["headers"]["x-api-key"] == "tf-key"
    assert base.body_of() == {"urls": ["https://a.com", "https://b.com"], "format": "markdown"}
    assert results[0]["text"] == "# Hi" and errors[0]["error"] == "bot_blocked"


def test_tinyfish_fetch_never_sends_more_than_ten_urls(base):
    base.on("POST", "/", {"results": [], "errors": []})
    providers.tinyfish_fetch("k", [f"https://x.com/{i}" for i in range(25)])
    assert len(base.body_of()["urls"]) == 10


def test_tinyfish_credit_errors_are_friendly(base):
    base.on("GET", "/", {}, status=402)
    with pytest.raises(NetError, match="no credits"):
        providers.tinyfish_search("k", "q")


# ── DataForSEO ────────────────────────────────────────────────────────────────

DFS_OK = {"status_code": 20000, "tasks": [{"status_code": 20000, "result": [{"items": [
    {"keyword": "retention table", "keyword_info": {"search_volume": 320, "competition": 0.2, "cpc": 1.5},
     "keyword_properties": {"keyword_difficulty": 28}, "search_intent_info": {"main_intent": "informational"}},
    {"keyword": "", "keyword_info": {}}]}]}]}


def test_dataforseo_accepts_login_password_or_base64(base):
    base.on("POST", "/v3/dataforseo_labs/google/keyword_suggestions/live", DFS_OK)
    providers.dataforseo_suggestions("me@x.com:secretpw", "retention", 2840, "en", 20)
    expected = "Basic " + base64.b64encode(b"me@x.com:secretpw").decode()
    assert base.requests[-1]["headers"]["authorization"] == expected
    providers.dataforseo_suggestions(base64.b64encode(b"me@x.com:secretpw").decode(), "retention")
    assert base.requests[-1]["headers"]["authorization"] == expected


def test_dataforseo_request_and_parsing(base):
    base.on("POST", "/v3/dataforseo_labs/google/keyword_suggestions/live", DFS_OK)
    items = providers.dataforseo_suggestions("a:b", "retention", 2826, "en", 5000)
    assert base.body_of() == [{"keyword": "retention", "location_code": 2826, "language_code": "en", "limit": 200}]
    assert items == [{"keyword": "retention table", "volume": 320, "competition": 0.2, "cpc": 1.5, "difficulty": 28, "intent": "informational"}]


def test_dataforseo_api_level_errors_surface(base):
    base.on("POST", "/v3/", {"status_code": 40100, "status_message": "Authentication failed", "tasks": []})
    with pytest.raises(NetError, match="Authentication failed"):
        providers.dataforseo_suggestions("a:b", "x")


# ── GitHub ────────────────────────────────────────────────────────────────────

def test_github_pull_request_flow(base):
    base.on("GET", "/repos/me/site/git/ref/heads/main", {"object": {"sha": "abc123"}})
    base.on("POST", "/repos/me/site/git/refs", {"ref": "refs/heads/b"}, status=201)
    base.on("PUT", "/repos/me/site/contents/", {"content": {}}, status=201)
    base.on("POST", "/repos/me/site/pulls", {"html_url": "https://github.com/me/site/pull/7", "number": 7}, status=201)
    pr = providers.github_open_pr("ghp_x", "me/site", "main", "graft-studio/post-1", "content/blog/post.md", "# Hi\n", "Add post", "body")
    assert pr == {"url": "https://github.com/me/site/pull/7", "number": 7, "branch": "graft-studio/post-1"}
    methods = [(r["method"], r["path"].split("?")[0]) for r in base.requests]
    assert methods == [("GET", "/repos/me/site/git/ref/heads/main"), ("POST", "/repos/me/site/git/refs"),
                       ("PUT", "/repos/me/site/contents/content/blog/post.md"), ("POST", "/repos/me/site/pulls")]
    assert base.requests[0]["headers"]["authorization"] == "Bearer ghp_x"
    put = json.loads(base.requests[2]["body"])
    assert base64.b64decode(put["content"]).decode() == "# Hi\n" and put["branch"] == "graft-studio/post-1"
    assert base.body_of(1)["sha"] == "abc123"


@pytest.mark.parametrize("repo,base_branch,branch,path", [
    ("not a repo", "main", "b", "a.md"), ("me/site", "main", "../b", "a.md"), ("me/site", "ma in", "b", "a.md"),
    ("me/site", "main", "b", "../../etc/x"), ("me/site", "main", "b", "/abs.md"), ("me/site", "main", "b", " "),
])
def test_github_rejects_bad_targets_before_any_request(base, repo, base_branch, branch, path):
    with pytest.raises(StudioError):
        providers.github_open_pr("t", repo, base_branch, branch, path, "x", "t", "b")
    assert base.requests == []
