"""Storage for Pipeline Studio: workspaces, API keys, pipelines, plans, runs and drafts.

Everything lives under one data folder that is *outside the repository* by default
(``~/.graft-studio``), because it holds API keys. All identifiers that become part of a
path are validated and the final path is checked to stay inside the data folder.
"""
from __future__ import annotations

import copy
import json
import os
import re
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
SLOT_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,39}$")

PLAN_STATUSES = ("idea", "planned", "drafting", "review", "approved", "published", "rejected")

MAX_PIPELINE_NODES = 60
MAX_TEXT = 20000          # longest free-text config value (prompts, rules)
MAX_PLAN_ITEMS = 2000


class StudioError(ValueError):
    """A user-facing error: bad input or a missing resource."""


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ── paths ─────────────────────────────────────────────────────────────────────

def data_root() -> Path:
    root = Path(os.environ.get("STUDIO_DATA_DIR") or (Path.home() / ".graft-studio")).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    return root.resolve()


def _inside(root: Path, path: Path) -> Path:
    resolved = path.resolve()
    if resolved != root and not resolved.is_relative_to(root):
        raise StudioError("Path resolves outside the Studio data folder.")
    return resolved


def check_slug(value, what: str = "id") -> str:
    if not isinstance(value, str) or not SLUG_RE.match(value):
        raise StudioError(f"Invalid {what}: use 1-40 lowercase letters, digits or dashes (got {value!r}).")
    return value


def check_id(value, what: str = "id") -> str:
    if not isinstance(value, str) or not ID_RE.match(value):
        raise StudioError(f"Invalid {what}: use letters, digits, '-' or '_' (got {value!r}).")
    return value


def workspaces_dir() -> Path:
    path = data_root() / "workspaces"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ws_dir(ws: str, must_exist: bool = True) -> Path:
    check_slug(ws, "workspace")
    path = _inside(data_root(), workspaces_dir() / ws)
    if must_exist and not (path / "config.json").is_file():
        raise StudioError(f"Workspace '{ws}' does not exist.")
    return path


def sub_path(ws: str, *parts: str) -> Path:
    base = ws_dir(ws)
    return _inside(base, base.joinpath(*parts))


# ── JSON io ───────────────────────────────────────────────────────────────────

def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return copy.deepcopy(default)
    except json.JSONDecodeError as exc:
        raise StudioError(f"{path.name} is not valid JSON: {exc}") from exc


def write_json(path: Path, data, private: bool = False) -> None:
    """Atomic write. ``private`` makes the file readable by the owner only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
        if private:
            os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


# ── workspaces ────────────────────────────────────────────────────────────────

DEFAULT_REDDIT_PLAYBOOK = (
    "Goal: bring people to the blog by being useful first.\n"
    "- Lead with a specific, honest insight from the article, not a link.\n"
    "- One post per article per community; wait for replies before posting elsewhere.\n"
    "- Read each subreddit's self-promotion rules first and follow them.\n"
    "- Put the link in a comment or the last line, and disclose that it is your own blog.\n"
    "- Never ask for upvotes."
)

DEFAULT_CONFIG = {
    "name": "",
    "site_url": "",
    "niche": "",
    "voice_prompt": "",
    "default_provider": "demo",
    "default_model": "",
    "default_key_slot": "",
    "categories": ["Guides", "Comparisons", "How-to"],
    "reddit_playbook": DEFAULT_REDDIT_PLAYBOOK,
    "github": {"repo": "", "base_branch": "main", "path_template": "content/blog/{slug}.md"},
    "schedule": {"cron": "0 9 * * 1-5"},
    "created_at": "",
}

_CONFIG_KEYS = set(DEFAULT_CONFIG) - {"created_at"}


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40].strip("-")
    return slug or "workspace"


def list_workspaces() -> list[dict]:
    out = []
    for path in sorted(workspaces_dir().iterdir()):
        cfg = read_json(path / "config.json", None) if path.is_dir() else None
        if cfg:
            out.append({"id": path.name, "name": cfg.get("name") or path.name, "site_url": cfg.get("site_url", ""),
                        "niche": cfg.get("niche", ""), "created_at": cfg.get("created_at", "")})
    return out


def create_workspace(name: str, site_url: str = "", niche: str = "") -> dict:
    if not isinstance(name, str) or not name.strip():
        raise StudioError("Workspace name is required.")
    name = name.strip()[:80]
    base = _slugify(name)
    slug, n = base, 2
    while (workspaces_dir() / slug).exists():
        slug = f"{base[:36]}-{n}"
        n += 1
    ws = check_slug(slug, "workspace")
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg.update(name=name, site_url=_check_url_text(site_url), niche=str(niche or "")[:200], created_at=now_iso())
    root = _inside(data_root(), workspaces_dir() / ws)
    root.mkdir(parents=True)
    write_json(root / "config.json", cfg)
    write_json(root / "plan.json", [])
    write_json(root / "rulebook.json", {"rules": [], "stats": {}, "sources": [], "updated_at": ""})
    return {"id": ws, **cfg}


def delete_workspace(ws: str) -> None:
    import shutil

    path = ws_dir(ws)
    shutil.rmtree(path)


def _check_url_text(value) -> str:
    value = (value or "").strip() if isinstance(value, str) else ""
    if value and not re.match(r"^https?://[^\s]+$", value):
        raise StudioError("Site URL must start with http:// or https://.")
    return value[:300]


def get_config(ws: str) -> dict:
    cfg = read_json(sub_path(ws, "config.json"), {})
    merged = copy.deepcopy(DEFAULT_CONFIG)
    for key, value in cfg.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key].update(value)
        else:
            merged[key] = value
    return merged


def save_config(ws: str, patch: dict) -> dict:
    if not isinstance(patch, dict):
        raise StudioError("Config must be an object.")
    cfg = get_config(ws)
    for key, value in patch.items():
        if key not in _CONFIG_KEYS:
            raise StudioError(f"Unknown config key: {key}")
        if key == "site_url":
            value = _check_url_text(value)
        elif key == "categories":
            if not isinstance(value, list) or not all(isinstance(v, str) and v.strip() for v in value) or len(value) > 30:
                raise StudioError("categories must be a list of up to 30 non-empty strings.")
            value = [v.strip()[:60] for v in value]
        elif key in ("github", "schedule"):
            if not isinstance(value, dict) or not all(isinstance(v, str) for v in value.values()):
                raise StudioError(f"{key} must be an object of strings.")
            value = {**cfg[key], **{k: v[:300] for k, v in value.items()}}
        elif key == "default_key_slot":
            value = str(value or "")
            if value:
                value = check_slot(value)
        else:
            if not isinstance(value, str):
                raise StudioError(f"{key} must be text.")
            value = value[:MAX_TEXT]
        cfg[key] = value
    write_json(sub_path(ws, "config.json"), cfg)
    return cfg


# ── API keys (write-only from the outside) ────────────────────────────────────

def check_slot(value) -> str:
    if not isinstance(value, str) or not SLOT_RE.match(value):
        raise StudioError("Key name must be 1-40 lowercase letters, digits, '-' or '_'.")
    return value


def _secrets_path(ws: str) -> Path:
    return sub_path(ws, "secrets.json")


def set_secret(ws: str, slot: str, provider: str, key: str) -> None:
    check_slot(slot)
    if not isinstance(provider, str) or not re.match(r"^[a-z0-9_]{2,30}$", provider):
        raise StudioError("Invalid provider.")
    if not isinstance(key, str) or not key.strip() or len(key) > 4000 or any(c.isspace() for c in key.strip()):
        raise StudioError("API key must be a single non-empty token.")
    secrets = read_json(_secrets_path(ws), {})
    secrets[slot] = {"provider": provider, "key": key.strip(), "updated_at": now_iso()}
    write_json(_secrets_path(ws), secrets, private=True)


def delete_secret(ws: str, slot: str) -> None:
    check_slot(slot)
    secrets = read_json(_secrets_path(ws), {})
    secrets.pop(slot, None)
    write_json(_secrets_path(ws), secrets, private=True)


def mask(key: str) -> str:
    return "••••" + key[-4:] if len(key) > 8 else "••••"


def list_secrets(ws: str) -> list[dict]:
    """Never returns key material: only the slot, provider and a masked tail."""
    secrets = read_json(_secrets_path(ws), {})
    return [
        {"slot": slot, "provider": item.get("provider", ""), "masked": mask(item.get("key", "")),
         "updated_at": item.get("updated_at", "")}
        for slot, item in sorted(secrets.items())
    ]


def resolve_key(ws: str, provider: str, slot: str = "") -> str:
    """Key lookup order: the named slot, the workspace default slot, any slot for this provider,
    then the environment variable STUDIO_KEY_<PROVIDER> (for CI runs). Raises with a helpful message."""
    secrets = read_json(_secrets_path(ws), {})
    if slot:
        item = secrets.get(slot)
        if item:
            return item["key"]
        env_slot = os.environ.get(f"STUDIO_KEY_SLOT_{slot.upper().replace('-', '_')}")
        if env_slot:
            return env_slot
        raise StudioError(f"Key '{slot}' is not set for this workspace. Add it in Keys.")
    default_slot = get_config(ws).get("default_key_slot", "")
    for candidate in (default_slot,):
        item = secrets.get(candidate) if candidate else None
        if item and item.get("provider") == provider:
            return item["key"]
    for item in secrets.values():
        if item.get("provider") == provider:
            return item["key"]
    env = os.environ.get(f"STUDIO_KEY_{provider.upper()}")
    if env:
        return env
    raise StudioError(f"No API key for {provider}. Add one in Keys (or set STUDIO_KEY_{provider.upper()}).")


# ── pipelines ─────────────────────────────────────────────────────────────────

def list_pipelines(ws: str) -> list[dict]:
    folder = sub_path(ws, "pipelines")
    out = []
    if folder.is_dir():
        for path in sorted(folder.glob("*.json")):
            data = read_json(path, {})
            out.append({"id": path.stem, "name": data.get("name", path.stem), "nodes": len(data.get("nodes", []))})
    return out


def get_pipeline(ws: str, pipeline_id: str) -> dict:
    check_id(pipeline_id, "pipeline id")
    data = read_json(sub_path(ws, "pipelines", f"{pipeline_id}.json"), None)
    if data is None:
        raise StudioError(f"Pipeline '{pipeline_id}' does not exist.")
    return data


def save_pipeline(ws: str, pipeline: dict, node_types: dict) -> dict:
    """Validate and store a pipeline: known node types, valid edges, no cycles, bounded size."""
    if not isinstance(pipeline, dict):
        raise StudioError("Pipeline must be an object.")
    pid = check_id(pipeline.get("id", ""), "pipeline id")
    name = str(pipeline.get("name") or pid)[:80]
    nodes, edges = pipeline.get("nodes"), pipeline.get("edges", [])
    if not isinstance(nodes, list) or not isinstance(edges, list):
        raise StudioError("Pipeline needs 'nodes' and 'edges' lists.")
    if len(nodes) > MAX_PIPELINE_NODES:
        raise StudioError(f"A pipeline can have at most {MAX_PIPELINE_NODES} nodes.")
    clean_nodes, seen = [], set()
    for node in nodes:
        if not isinstance(node, dict):
            raise StudioError("Every node must be an object.")
        nid = check_id(node.get("id", ""), "node id")
        if nid in seen:
            raise StudioError(f"Duplicate node id: {nid}")
        seen.add(nid)
        ntype = node.get("type")
        if ntype not in node_types:
            raise StudioError(f"Unknown node type: {ntype!r}")
        config = node.get("config", {})
        if not isinstance(config, dict):
            raise StudioError(f"Node {nid}: config must be an object.")
        if len(json.dumps(config)) > 200_000:
            raise StudioError(f"Node {nid}: config is too large.")
        pos = node.get("position") or {}
        clean_nodes.append({
            "id": nid, "type": ntype, "config": config,
            "position": {"x": float(pos.get("x", 0)), "y": float(pos.get("y", 0))},
        })
    clean_edges = []
    for edge in edges:
        src, dst = edge.get("source"), edge.get("target")
        if src not in seen or dst not in seen or src == dst:
            raise StudioError("Every edge must connect two different existing nodes.")
        clean_edges.append({"id": str(edge.get("id") or f"{src}->{dst}")[:140], "source": src, "target": dst})
    if _has_cycle(seen, clean_edges):
        raise StudioError("The pipeline contains a loop. Connect nodes in one direction only.")
    data = {"id": pid, "name": name, "nodes": clean_nodes, "edges": clean_edges, "updated_at": now_iso()}
    write_json(sub_path(ws, "pipelines", f"{pid}.json"), data)
    return data


def delete_pipeline(ws: str, pipeline_id: str) -> None:
    check_id(pipeline_id, "pipeline id")
    path = sub_path(ws, "pipelines", f"{pipeline_id}.json")
    if path.is_file():
        path.unlink()


def _has_cycle(node_ids, edges) -> bool:
    indeg = {n: 0 for n in node_ids}
    out: dict[str, list[str]] = {n: [] for n in node_ids}
    for e in edges:
        indeg[e["target"]] += 1
        out[e["source"]].append(e["target"])
    queue = [n for n, d in indeg.items() if d == 0]
    visited = 0
    while queue:
        n = queue.pop()
        visited += 1
        for m in out[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                queue.append(m)
    return visited != len(indeg)


# ── content plan ──────────────────────────────────────────────────────────────

def _parse_when(value) -> str:
    if value in (None, ""):
        return ""
    if not isinstance(value, str):
        raise StudioError("scheduled_for must be an ISO date/time string.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise StudioError(f"scheduled_for is not a valid date/time: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat()


def list_plan(ws: str) -> list[dict]:
    return read_json(sub_path(ws, "plan.json"), [])


def save_plan_item(ws: str, item: dict) -> dict:
    if not isinstance(item, dict):
        raise StudioError("Plan item must be an object.")
    title = str(item.get("title", "")).strip()
    if not title:
        raise StudioError("A plan item needs a title.")
    status = item.get("status") or ("planned" if item.get("scheduled_for") else "idea")
    if status not in PLAN_STATUSES:
        raise StudioError(f"Invalid status: {status!r}")
    plan = list_plan(ws)
    item_id = item.get("id") or uuid.uuid4().hex[:12]
    check_id(item_id, "plan item id")
    existing = next((p for p in plan if p["id"] == item_id), None)
    entry = {
        **(existing or {}),
        "id": item_id,
        "title": title[:200],
        "category": str(item.get("category", (existing or {}).get("category", "")))[:60],
        "keyword": str(item.get("keyword", (existing or {}).get("keyword", "")))[:120],
        "notes": str(item.get("notes", (existing or {}).get("notes", "")))[:2000],
        "source": str(item.get("source", (existing or {}).get("source", "manual")))[:30],
        "scheduled_for": _parse_when(item.get("scheduled_for", (existing or {}).get("scheduled_for", ""))),
        "pipeline_id": str(item.get("pipeline_id", (existing or {}).get("pipeline_id", "")))[:64],
        "status": status,
        "run_id": (existing or {}).get("run_id", ""),
        "updated_at": now_iso(),
    }
    if entry["pipeline_id"]:
        check_id(entry["pipeline_id"], "pipeline id")
    if existing:
        plan = [entry if p["id"] == item_id else p for p in plan]
    else:
        if len(plan) >= MAX_PLAN_ITEMS:
            raise StudioError("The plan is full.")
        plan.append(entry)
    write_json(sub_path(ws, "plan.json"), plan)
    return entry


def set_plan_fields(ws: str, item_id: str, **fields) -> None:
    plan = list_plan(ws)
    for p in plan:
        if p["id"] == item_id:
            p.update(fields, updated_at=now_iso())
    write_json(sub_path(ws, "plan.json"), plan)


def delete_plan_item(ws: str, item_id: str) -> None:
    check_id(item_id, "plan item id")
    write_json(sub_path(ws, "plan.json"), [p for p in list_plan(ws) if p["id"] != item_id])


# ── ideas (what the source nodes found) ───────────────────────────────────────

def get_ideas(ws: str) -> list[dict]:
    return read_json(sub_path(ws, "ideas.json"), [])


def add_ideas(ws: str, ideas: list[dict], source: str) -> None:
    """Merge new ideas (from RSS, keyword research, ...) into the workspace idea list, de-duplicated by title."""
    current = get_ideas(ws)
    known = {i["title"].strip().lower() for i in current}
    for idea in ideas:
        title = str(idea.get("title", "")).strip()[:200]
        if not title or title.lower() in known:
            continue
        known.add(title.lower())
        current.append({
            "id": uuid.uuid4().hex[:12], "title": title, "source": source,
            "keyword": str(idea.get("keyword", ""))[:120], "category": str(idea.get("category", ""))[:60],
            "note": str(idea.get("note", ""))[:300], "added_at": now_iso(),
        })
    write_json(sub_path(ws, "ideas.json"), current[-1000:])


def delete_idea(ws: str, idea_id: str) -> None:
    check_id(idea_id, "idea id")
    write_json(sub_path(ws, "ideas.json"), [i for i in get_ideas(ws) if i["id"] != idea_id])


# ── runs & drafts ─────────────────────────────────────────────────────────────

def new_run_id() -> str:
    return uuid.uuid4().hex[:16]


def run_path(ws: str, run_id: str) -> Path:
    check_id(run_id, "run id")
    return sub_path(ws, "runs", f"{run_id}.json")


def load_run(ws: str, run_id: str) -> dict:
    run = read_json(run_path(ws, run_id), None)
    if run is None:
        raise StudioError(f"Run '{run_id}' does not exist.")
    return run


def save_run(ws: str, run: dict) -> None:
    run["updated_at"] = now_iso()
    write_json(run_path(ws, run["id"]), run)


def list_runs(ws: str, limit: int = 30) -> list[dict]:
    folder = sub_path(ws, "runs")
    out = []
    if folder.is_dir():
        for path in sorted(folder.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]:
            run = read_json(path, {})
            out.append({k: run.get(k) for k in ("id", "pipeline_id", "status", "title", "created_at", "updated_at")})
    return out


def draft_path(ws: str, run_id: str) -> Path:
    check_id(run_id, "run id")
    return sub_path(ws, "drafts", f"{run_id}.md")


def save_draft(ws: str, run_id: str, markdown: str) -> Path:
    path = draft_path(ws, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(markdown, encoding="utf-8")
    return path


def load_draft(ws: str, run_id: str) -> str:
    path = draft_path(ws, run_id)
    if not path.is_file():
        raise StudioError("No draft for this run yet.")
    return path.read_text(encoding="utf-8")


# ── rulebook ──────────────────────────────────────────────────────────────────

RULE_KINDS = ("length", "em_dash", "opener", "hook", "faq", "structure", "title", "sentences", "lists", "links", "cta",
              "note", "banned_phrases")
MAX_RULES = 60


def get_rulebook(ws: str) -> dict:
    return read_json(sub_path(ws, "rulebook.json"), {"rules": [], "stats": {}, "sources": [], "updated_at": ""})


def _clean_params(params) -> dict:
    if not isinstance(params, dict) or len(params) > 12:
        raise StudioError("Rule params must be a small object.")
    out = {}
    for key, value in params.items():
        if not isinstance(key, str) or len(key) > 40:
            raise StudioError("Invalid rule param name.")
        if isinstance(value, bool) or isinstance(value, (int, float)):
            out[key] = value
        elif isinstance(value, str):
            out[key] = value[:300]
        elif isinstance(value, list) and len(value) <= 40 and all(isinstance(v, str) and len(v) <= 100 for v in value):
            out[key] = value
        else:
            raise StudioError(f"Rule param '{key}' has an unsupported value.")
    return out


def save_rulebook(ws: str, rb: dict) -> dict:
    """Validate and store a rulebook (used for edits from the dashboard and for freshly learned rules)."""
    if not isinstance(rb, dict) or not isinstance(rb.get("rules"), list):
        raise StudioError("Rulebook needs a 'rules' list.")
    if len(rb["rules"]) > MAX_RULES:
        raise StudioError(f"A rulebook can have at most {MAX_RULES} rules.")
    clean, seen = [], set()
    for rule in rb["rules"]:
        if not isinstance(rule, dict):
            raise StudioError("Every rule must be an object.")
        rid = check_id(rule.get("id", ""), "rule id")
        if rid in seen:
            raise StudioError(f"Duplicate rule id: {rid}")
        seen.add(rid)
        kind = rule.get("kind", "note")
        if kind not in RULE_KINDS:
            raise StudioError(f"Unknown rule kind: {kind!r}")
        text = str(rule.get("text", "")).strip()
        if not text:
            raise StudioError("A rule needs some text.")
        clean.append({
            "id": rid, "kind": kind, "text": text[:600], "evidence": str(rule.get("evidence", ""))[:300],
            "params": _clean_params(rule.get("params", {})), "enabled": bool(rule.get("enabled", True)),
            "source": "custom" if rule.get("source") == "custom" else "learned", "edited": bool(rule.get("edited", False)),
        })
    data = {"rules": clean, "stats": rb.get("stats", {}) if isinstance(rb.get("stats"), dict) else {},
            "sources": rb.get("sources", [])[:50] if isinstance(rb.get("sources"), list) else [], "updated_at": now_iso()}
    write_json(sub_path(ws, "rulebook.json"), data)
    return data
