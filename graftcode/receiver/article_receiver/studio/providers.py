"""Provider clients for Pipeline Studio: LLMs, TinyFish, DataForSEO and GitHub.

Keys are passed in by the caller (resolved from the workspace's key slots) and are only
ever sent to the provider's own host.
"""
from __future__ import annotations

import base64
import re
import urllib.parse

from . import demo
from .net import NetError, call_api, provider_base, raise_for_status
from .store import StudioError

# ── catalogue (shown in the UI) ───────────────────────────────────────────────

LLM_PROVIDERS = {
    "demo": {"label": "Demo (offline template, no AI)", "style": "demo", "base": "", "default_model": "demo-template",
             "needs_key": False, "models": ["demo-template"]},
    "openai": {"label": "OpenAI", "style": "openai", "base": "https://api.openai.com/v1", "default_model": "gpt-5.5",
               "needs_key": True, "models": ["gpt-5.5", "gpt-5", "gpt-4.1"]},
    "anthropic": {"label": "Anthropic", "style": "anthropic", "base": "https://api.anthropic.com/v1",
                  "default_model": "claude-sonnet-5-5", "needs_key": True,
                  "models": ["claude-sonnet-5-5", "claude-opus-5-5", "claude-haiku-5-5"]},
    "groq": {"label": "Groq", "style": "openai", "base": "https://api.groq.com/openai/v1",
             "default_model": "llama-3.3-70b-versatile", "needs_key": True,
             "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]},
    "moonshot": {"label": "Moonshot (Kimi)", "style": "openai", "base": "https://api.moonshot.ai/v1",
                 "default_model": "kimi-k2.7-code-highspeed", "needs_key": True, "models": ["kimi-k2.7-code-highspeed"]},
    "openrouter": {"label": "OpenRouter", "style": "openai", "base": "https://openrouter.ai/api/v1",
                   "default_model": "openrouter/auto", "needs_key": True, "models": ["openrouter/auto"]},
}

KEYWORD_PROVIDERS = {
    "manual": {"label": "Manual list (no API)", "needs_key": False},
    "sample": {"label": "Sample data (offline, not real volumes)", "needs_key": False},
    "dataforseo": {"label": "DataForSEO (same data OpenSEO uses)", "needs_key": True},
    "tinyfish": {"label": "TinyFish Search (what ranks today)", "needs_key": True},
}

SCRAPE_PROVIDERS = {
    "direct": {"label": "Direct fetch (free, simple pages)", "needs_key": False},
    "sample": {"label": "Sample data (offline)", "needs_key": False},
    "tinyfish": {"label": "TinyFish Fetch (clean markdown, JS pages)", "needs_key": True},
}

KEY_PROVIDERS = sorted({*(p for p, v in LLM_PROVIDERS.items() if v["needs_key"]), "tinyfish", "dataforseo", "github"})


def catalog() -> dict:
    return {
        "llm": [{"id": k, **{x: v[x] for x in ("label", "default_model", "needs_key", "models")}} for k, v in LLM_PROVIDERS.items()],
        "keywords": [{"id": k, **v} for k, v in KEYWORD_PROVIDERS.items()],
        "scrape": [{"id": k, **v} for k, v in SCRAPE_PROVIDERS.items()],
        "key_providers": KEY_PROVIDERS,
    }


# ── LLM chat ──────────────────────────────────────────────────────────────────

def chat(provider: str, key: str, model: str, system: str, user: str, task: str = "text", max_tokens: int = 4096) -> str:
    spec = LLM_PROVIDERS.get(provider)
    if not spec:
        raise StudioError(f"Unknown AI provider: {provider!r}")
    if spec["style"] == "demo":
        return demo.generate(task, system, user)
    if not key:
        raise StudioError(f"No API key for {provider}.")
    model = model or spec["default_model"]
    base = provider_base(provider, spec["base"]).rstrip("/")
    if spec["style"] == "anthropic":
        resp = call_api("POST", f"{base}/messages", headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                        json_body={"model": model, "max_tokens": max_tokens, "system": system,
                                   "messages": [{"role": "user", "content": user}]})
        raise_for_status(resp, "Anthropic")
        parts = resp.json().get("content") or []
        text = "".join(p.get("text", "") for p in parts if isinstance(p, dict))
    else:
        body = {"model": model, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if provider != "openai":          # OpenAI's newer models reject max_tokens; others accept it
            body["max_tokens"] = max_tokens
        resp = call_api("POST", f"{base}/chat/completions", headers={"Authorization": f"Bearer {key}"}, json_body=body)
        raise_for_status(resp, spec["label"])
        choices = resp.json().get("choices") or []
        text = ((choices[0].get("message") or {}).get("content") or "") if choices else ""
    if not text.strip():
        raise NetError(f"{spec['label']} returned an empty answer.")
    return text.strip()


# ── TinyFish ──────────────────────────────────────────────────────────────────

def tinyfish_search(key: str, query: str, location: str = "US", language: str = "en", page: int = 0) -> list[dict]:
    base = provider_base("tinyfish_search", "https://api.search.tinyfish.ai")
    qs = urllib.parse.urlencode({"query": query[:400], "location": location, "language": language, "page": page})
    resp = call_api("GET", f"{base}?{qs}", headers={"X-API-Key": key}, timeout=60)
    raise_for_status(resp, "TinyFish Search")
    return list(resp.json().get("results") or [])


def tinyfish_fetch(key: str, urls: list[str], fmt: str = "markdown") -> tuple[list[dict], list[dict]]:
    """Returns (results, errors). TinyFish reports per-URL failures with HTTP 200, in `errors`."""
    base = provider_base("tinyfish_fetch", "https://api.fetch.tinyfish.ai")
    resp = call_api("POST", base, headers={"X-API-Key": key}, json_body={"urls": urls[:10], "format": fmt}, timeout=150)
    raise_for_status(resp, "TinyFish Fetch")
    data = resp.json()
    return list(data.get("results") or []), list(data.get("errors") or [])


# ── DataForSEO (the data behind OpenSEO) ──────────────────────────────────────

def _basic_auth(key: str) -> str:
    """Accept the Base64 credential OpenSEO uses (DATAFORSEO_API_KEY) or a raw login:password."""
    key = key.strip()
    if ":" in key:
        key = base64.b64encode(key.encode()).decode()
    return f"Basic {key}"


def dataforseo_suggestions(key: str, keyword: str, location_code: int = 2840, language_code: str = "en",
                           limit: int = 50) -> list[dict]:
    base = provider_base("dataforseo", "https://api.dataforseo.com")
    resp = call_api("POST", f"{base}/v3/dataforseo_labs/google/keyword_suggestions/live",
                    headers={"Authorization": _basic_auth(key)}, timeout=90,
                    json_body=[{"keyword": keyword[:200], "location_code": int(location_code),
                                "language_code": language_code, "limit": max(1, min(int(limit), 200))}])
    raise_for_status(resp, "DataForSEO")
    data = resp.json()
    if data.get("status_code") not in (None, 20000):
        raise NetError(f"DataForSEO error: {str(data.get('status_message'))[:160]}")
    out = []
    for task in data.get("tasks") or []:
        if task.get("status_code") not in (None, 20000):
            raise NetError(f"DataForSEO error: {str(task.get('status_message'))[:160]}")
        for result in task.get("result") or []:
            for item in result.get("items") or []:
                info = item.get("keyword_info") or {}
                props = item.get("keyword_properties") or {}
                intent = (item.get("search_intent_info") or {}).get("main_intent", "")
                out.append({"keyword": item.get("keyword", ""), "volume": info.get("search_volume") or 0,
                            "competition": info.get("competition"), "cpc": info.get("cpc"),
                            "difficulty": props.get("keyword_difficulty"), "intent": intent})
    return [k for k in out if k["keyword"]]


# ── GitHub (publishing as a pull request) ─────────────────────────────────────

_REPO_RE = re.compile(r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$")
_BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,100}$")


def _gh(token: str, method: str, path: str, body=None):
    base = provider_base("github", "https://api.github.com")
    resp = call_api(method, f"{base}{path}", json_body=body, timeout=60, headers={
        "Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"})
    raise_for_status(resp, "GitHub")
    return resp.json()


def github_open_pr(token: str, repo: str, base_branch: str, branch: str, path: str, content: str,
                   title: str, body: str) -> dict:
    """Create a branch, commit one file and open a pull request. Never merges."""
    if not _REPO_RE.match(repo):
        raise StudioError("GitHub repo must look like owner/name.")
    if not _BRANCH_RE.match(base_branch) or not _BRANCH_RE.match(branch) or ".." in branch:
        raise StudioError("Invalid branch name.")
    if path.startswith("/") or ".." in path.split("/") or not path.strip():
        raise StudioError("Invalid file path for the repository.")
    ref = _gh(token, "GET", f"/repos/{repo}/git/ref/heads/{urllib.parse.quote(base_branch, safe='')}")
    sha = (ref.get("object") or {}).get("sha")
    if not sha:
        raise NetError("Could not read the base branch.")
    _gh(token, "POST", f"/repos/{repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": sha})
    _gh(token, "PUT", f"/repos/{repo}/contents/{urllib.parse.quote(path)}",
        {"message": title[:200], "content": base64.b64encode(content.encode()).decode(), "branch": branch})
    pr = _gh(token, "POST", f"/repos/{repo}/pulls", {"title": title[:200], "head": branch, "base": base_branch, "body": body[:4000]})
    return {"url": pr.get("html_url", ""), "number": pr.get("number"), "branch": branch}


def github_whoami(token: str) -> str:
    """The login the token belongs to (used to check a token works)."""
    return str(_gh(token, "GET", "/user").get("login", ""))
