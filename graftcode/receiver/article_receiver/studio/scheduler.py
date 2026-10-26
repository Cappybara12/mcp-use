"""Scheduling: find plan items that are due, run them, and export a GitHub Action that does it on a timer."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from . import engine, nodes, providers, seo, store
from .store import StudioError

_CRON_RE = re.compile(r"^[0-9*/,\-]+( [0-9*/,\-]+){4}$")
RUNNER_PIP = 'git+https://github.com/Cappybara12/mcp-use@main#subdirectory=graftcode/receiver'


def _now() -> datetime:
    return datetime.now(timezone.utc)


def due_items(ws: str, now: datetime | None = None) -> list[dict]:
    now = now or _now()
    out = []
    for item in store.list_plan(ws):
        if item.get("status") != "planned" or not item.get("scheduled_for"):
            continue
        if datetime.fromisoformat(item["scheduled_for"]) <= now:
            out.append(item)
    return sorted(out, key=lambda i: i["scheduled_for"])


def _first_pipeline(ws: str) -> str:
    pipelines = store.list_pipelines(ws)
    if not pipelines:
        raise StudioError("This workspace has no pipeline.")
    return pipelines[0]["id"]


def run_due(ws: str, now: datetime | None = None, out_dir: str = "", max_items: int = 5) -> list[dict]:
    """Create drafts for every due item. The run stops at the review step: a person approves before anything is published."""
    results = []
    for item in due_items(ws, now)[: max(1, max_items)]:
        try:
            run = engine.start_run(ws, item.get("pipeline_id") or _first_pipeline(ws), item)
            run = engine.run_until_blocked(ws, run["id"])
        except StudioError as exc:
            store.set_plan_fields(ws, item["id"], status="idea")
            results.append({"item": item["title"], "ok": False, "error": str(exc)})
            continue
        entry = {"item": item["title"], "run_id": run["id"], "status": run["status"], "ok": run["status"] == "awaiting_review"}
        failed = next((s["error"] for s in run["nodes"].values() if s["status"] == "error"), "")
        if failed:
            entry.update(ok=False, error=failed)
            store.set_plan_fields(ws, item["id"], status="planned")
        elif out_dir and run["status"] == "awaiting_review":
            folder = Path(out_dir)
            folder.mkdir(parents=True, exist_ok=True)
            seo_report = next((s["output"].get("seo") for s in run["nodes"].values() if s.get("output") and s["output"].get("seo")), {})
            slug = (seo_report or {}).get("slug") or seo.slugify(item["title"])
            (folder / f"{slug}.md").write_text(store.load_draft(ws, run["id"]), encoding="utf-8")
            reddit = next((s["output"].get("reddit") for s in run["nodes"].values() if s.get("output") and s["output"].get("reddit")), "")
            if reddit:
                (folder / f"{slug}.reddit.md").write_text(reddit, encoding="utf-8")
            entry["file"] = str(folder / f"{slug}.md")
        results.append(entry)
    return results


# ── export ────────────────────────────────────────────────────────────────────

def _providers_used(ws: str) -> list[str]:
    used: set[str] = set()
    cfg = store.get_config(ws)
    for meta in store.list_pipelines(ws):
        for node in store.get_pipeline(ws, meta["id"])["nodes"]:
            c = node.get("config", {})
            if node["type"] in ("outline", "write", "reddit"):
                prov = c.get("provider") or cfg.get("default_provider") or "demo"
                if prov != "demo":
                    used.add(prov)
            elif node["type"] in ("keywords", "scrape", "corpus") and c.get("provider") in ("dataforseo", "tinyfish"):
                used.add(c["provider"])
    return sorted(used)


def export_workflow(ws: str, cron: str = "") -> dict:
    cron = (cron or store.get_config(ws).get("schedule", {}).get("cron") or "0 9 * * 1-5").strip()
    if not _CRON_RE.match(cron):
        raise StudioError("Schedule must be a cron expression such as '0 9 * * 1-5' (minute hour day month weekday).")
    used = _providers_used(ws)
    env = "\n".join(f"          STUDIO_KEY_{p.upper()}: ${{{{ secrets.{p.upper()}_API_KEY }}}}" for p in used)
    yaml = f"""name: Graft Studio drafts
# Creates drafts for plan items that are due and opens a pull request for you to review.
# Nothing is published until you merge that pull request.
on:
  schedule:
    - cron: "{cron}"   # UTC
  workflow_dispatch: {{}}

permissions:
  contents: write
  pull-requests: write

jobs:
  draft:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install the Graft Studio runner
        run: pip install "{RUNNER_PIP}"
      - name: Create drafts for items that are due
        env:
          STUDIO_DATA_DIR: .graft-studio
{env}
        run: graft-studio run-due --workspace {ws} --out content/drafts
      - name: Open a pull request with the drafts
        uses: peter-evans/create-pull-request@v6
        with:
          branch: graft-studio/drafts
          title: "Graft Studio: new drafts for review"
          commit-message: "Add drafts created by Graft Studio"
          body: "Drafts created on schedule. Review, edit and merge, or close this pull request."
          add-paths: |
            content/drafts
            .graft-studio
"""
    secrets = [{"name": f"{p.upper()}_API_KEY", "for": p} for p in used]
    return {"path": ".github/workflows/graft-studio.yml", "yaml": yaml, "secrets_needed": secrets, "cron": cron,
            "steps": ["Commit the workspace files from the export (they contain no API keys) to your site repository.",
                      "Add the listed secrets in the repository's Settings > Secrets and variables > Actions.",
                      "Commit the workflow file. It runs on the schedule and from the Actions tab."]}


def export_bundle(ws: str) -> dict:
    """The workspace's settings, plan, rulebook and pipelines (never API keys) as files for the site repo."""
    base = f".graft-studio/workspaces/{ws}"
    files = [{"path": f"{base}/config.json", "content": json.dumps(store.get_config(ws), indent=2)},
             {"path": f"{base}/plan.json", "content": json.dumps(store.list_plan(ws), indent=2)},
             {"path": f"{base}/rulebook.json", "content": json.dumps(store.get_rulebook(ws), indent=2)}]
    for meta in store.list_pipelines(ws):
        files.append({"path": f"{base}/pipelines/{meta['id']}.json", "content": json.dumps(store.get_pipeline(ws, meta["id"]), indent=2)})
    return {"files": files}
