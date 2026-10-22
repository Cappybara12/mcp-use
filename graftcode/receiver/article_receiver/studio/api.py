"""The Pipeline Studio API: plain functions the receiver exposes (through Graftcode) to the dashboard.

Every function takes simple values and returns plain data; errors are StudioError (a ValueError)
with a message that is safe to show.
"""
from __future__ import annotations

import json

from . import engine, nodes, providers, rulebook, scheduler, seo, store
from .store import StudioError

MAX_JSON = 1_000_000


def _loads(text: str, what: str):
    if not isinstance(text, str) or len(text) > MAX_JSON:
        raise StudioError(f"{what} is missing or too large.")
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise StudioError(f"{what} is not valid JSON.") from exc


# ── catalogue & workspaces ────────────────────────────────────────────────────

def catalog() -> dict:
    return {"nodes": nodes.describe_types(), **providers.catalog(), "plan_statuses": list(store.PLAN_STATUSES)}


def list_workspaces() -> list:
    return store.list_workspaces()


def create_workspace(name: str, site_url: str, niche: str, template: str) -> dict:
    ws = store.create_workspace(name, site_url, niche)
    store.save_pipeline(ws["id"], nodes.default_pipeline(live=(template == "live")), nodes.NODE_TYPES)
    if template != "live":
        store.save_config(ws["id"], {"site_url": ws.get("site_url") or "", "niche": ws.get("niche") or "demo blog"})
    return workspace(ws["id"])


def workspace(ws: str) -> dict:
    cfg = store.get_config(ws)
    return {"id": ws, "config": cfg, "secrets": store.list_secrets(ws), "pipelines": store.list_pipelines(ws),
            "rule_count": len(store.get_rulebook(ws).get("rules", [])), "plan_count": len(store.list_plan(ws))}


def delete_workspace(ws: str) -> dict:
    store.delete_workspace(ws)
    return {"deleted": ws}


def save_config(ws: str, patch_json: str) -> dict:
    return store.save_config(ws, _loads(patch_json, "Settings"))


# ── keys ──────────────────────────────────────────────────────────────────────

def set_secret(ws: str, slot: str, provider: str, key: str) -> list:
    store.set_secret(ws, slot, provider, key)
    return store.list_secrets(ws)


def delete_secret(ws: str, slot: str) -> list:
    store.delete_secret(ws, slot)
    return store.list_secrets(ws)


# ── pipelines ─────────────────────────────────────────────────────────────────

def get_pipeline(ws: str, pipeline_id: str) -> dict:
    return store.get_pipeline(ws, pipeline_id)


def save_pipeline(ws: str, pipeline_json: str) -> dict:
    return store.save_pipeline(ws, _loads(pipeline_json, "Pipeline"), nodes.NODE_TYPES)


def delete_pipeline(ws: str, pipeline_id: str) -> list:
    if len(store.list_pipelines(ws)) <= 1:
        raise StudioError("A workspace needs at least one pipeline.")
    store.delete_pipeline(ws, pipeline_id)
    return store.list_pipelines(ws)


def new_pipeline(ws: str, name: str, live: bool) -> dict:
    base = nodes.default_pipeline(live=live)
    slug = "".join(c if c.isalnum() else "-" for c in (name or "pipeline").lower()).strip("-")[:30] or "pipeline"
    existing = {p["id"] for p in store.list_pipelines(ws)}
    pid, n = slug, 2
    while pid in existing:
        pid, n = f"{slug}-{n}", n + 1
    base.update(id=pid, name=(name or pid)[:80])
    return store.save_pipeline(ws, base, nodes.NODE_TYPES)


def preview_prompt(ws: str, pipeline_id: str, node_id: str, run_id: str) -> dict:
    return engine.preview_prompt(ws, pipeline_id, node_id, run_id)


# ── ideas, plan, rulebook ─────────────────────────────────────────────────────

def list_ideas(ws: str) -> list:
    return store.get_ideas(ws)


def add_idea(ws: str, title: str, keyword: str, category: str) -> list:
    store.add_ideas(ws, [{"title": title, "keyword": keyword, "category": category}], "manual")
    return store.get_ideas(ws)


def delete_idea(ws: str, idea_id: str) -> list:
    store.delete_idea(ws, idea_id)
    return store.get_ideas(ws)


def list_plan(ws: str) -> list:
    return store.list_plan(ws)


def save_plan_item(ws: str, item_json: str) -> dict:
    return store.save_plan_item(ws, _loads(item_json, "Plan item"))


def delete_plan_item(ws: str, item_id: str) -> list:
    store.delete_plan_item(ws, item_id)
    return store.list_plan(ws)


def get_rulebook(ws: str) -> dict:
    return store.get_rulebook(ws)


def save_rulebook(ws: str, rulebook_json: str) -> dict:
    return store.save_rulebook(ws, _loads(rulebook_json, "Rulebook"))


def add_custom_rule(ws: str, text: str, kind: str, phrases: str) -> dict:
    params = {"phrases": [p.strip() for p in phrases.split(",") if p.strip()][:40]} if kind == "banned_phrases" else {}
    rb = store.get_rulebook(ws)
    rb["rules"].append(rulebook.new_custom_rule(text, kind or "note", params))
    return store.save_rulebook(ws, rb)


# ── runs ──────────────────────────────────────────────────────────────────────

def start_run(ws: str, pipeline_id: str, item_json: str) -> dict:
    item = _loads(item_json, "Item") if item_json.strip() else {}
    return engine.start_run(ws, pipeline_id, item)


def start_run_for_plan_item(ws: str, pipeline_id: str, item_id: str) -> dict:
    item = next((p for p in store.list_plan(ws) if p["id"] == item_id), None)
    if not item:
        raise StudioError("That plan item does not exist.")
    return engine.start_run(ws, pipeline_id or item.get("pipeline_id") or store.list_pipelines(ws)[0]["id"], item)


def run_node(ws: str, run_id: str, node_id: str) -> dict:
    return engine.run_node(ws, run_id, node_id)


def run_all(ws: str, run_id: str) -> dict:
    return engine.run_until_blocked(ws, run_id)


def get_run(ws: str, run_id: str) -> dict:
    return engine.get_run(ws, run_id)


def list_runs(ws: str) -> list:
    return store.list_runs(ws)


def reset_from(ws: str, run_id: str, node_id: str) -> dict:
    return engine.reset_from(ws, run_id, node_id)


def review(ws: str, run_id: str, node_id: str, decision: str, notes: str, markdown: str) -> dict:
    return engine.review(ws, run_id, node_id, decision, notes, markdown)


def get_draft(ws: str, run_id: str) -> dict:
    markdown = store.load_draft(ws, run_id)
    state = store.load_run(ws, run_id)
    keyword = ""
    for s in state["nodes"].values():
        if s.get("output") and s["output"].get("primary"):
            keyword = s["output"]["primary"]
    report = seo.check(markdown, keyword or (state.get("item") or {}).get("keyword", ""), store.get_rulebook(ws), store.get_config(ws).get("site_url", ""))
    return {"markdown": markdown, "seo": report}


def save_draft(ws: str, run_id: str, markdown: str) -> dict:
    """Save a person's edits to a run's draft and return it with a fresh SEO report."""
    if not isinstance(markdown, str) or not markdown.strip():
        raise StudioError("The draft cannot be empty.")
    if len(markdown) > 400_000:
        raise StudioError("The draft is too large.")
    store.load_run(ws, run_id)                      # the run must exist
    store.save_draft(ws, run_id, markdown.rstrip() + "\n")
    return get_draft(ws, run_id)


# ── scheduling ────────────────────────────────────────────────────────────────

def run_due(ws: str) -> list:
    return scheduler.run_due(ws)


def export_workflow(ws: str, cron: str) -> dict:
    return scheduler.export_workflow(ws, cron)


def export_bundle(ws: str) -> dict:
    return scheduler.export_bundle(ws)
