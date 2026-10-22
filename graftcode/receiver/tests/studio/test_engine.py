import json
from datetime import datetime, timedelta, timezone

import pytest

from article_receiver.studio import cli, engine, nodes, scheduler, store
from article_receiver.studio.store import StudioError

ITEM = {"title": "How to read a retention table", "keyword": "retention table", "category": "Guides"}


def start(api, ws, item=ITEM, pipeline="blog-engine"):
    return api.start_run(ws, pipeline, json.dumps(item))


def states(run):
    return {n: s["status"] for n, s in run["nodes"].items()}


# ── a full demo run ───────────────────────────────────────────────────────────

def test_demo_pipeline_runs_to_the_review_step(api, ws):
    run = api.run_all(ws, start(api, ws)["id"])
    assert run["status"] == "awaiting_review"
    s = states(run)
    assert all(s[n] == "done" for n in ("topic", "rss", "corpus", "rulebook", "keywords", "scrape", "outline", "write", "seo"))
    assert s["review"] == "awaiting_review" and s["reddit"] == s["publish"] == "pending"
    assert store.load_draft(ws, run["id"]).startswith("---")
    assert run["order"].index("write") < run["order"].index("seo") < run["order"].index("review")


def test_steps_use_the_output_of_earlier_steps(api, ws):
    run = api.run_all(ws, start(api, ws)["id"])
    assert run["nodes"]["keywords"]["output"]["primary"] == "retention table"
    assert "retention table" in run["nodes"]["write"]["output"]["draft"].lower()
    seo = run["nodes"]["seo"]["output"]["seo"]
    assert seo["keyword"] == "retention table" and len(seo["faq_schema"]["mainEntity"]) >= 3
    assert run["nodes"]["corpus"]["output"]["saved"] and api.get_rulebook(ws)["rules"]


def test_source_steps_feed_the_idea_list(api, ws):
    api.run_all(ws, start(api, ws)["id"])
    sources = {i["source"] for i in api.list_ideas(ws)}
    assert {"rss", "keywords"} <= sources


def test_steps_must_run_in_order(api, ws):
    run = start(api, ws)
    run = api.run_node(ws, run["id"], "write")
    assert run["nodes"]["write"]["status"] == "error" and "step before" in run["nodes"]["write"]["error"]


def test_a_failing_step_stops_the_run_with_a_clear_message(api, ws):
    run = api.run_all(ws, start(api, ws, {"title": ""})["id"])
    assert run["status"] == "error" and "topic" in run["nodes"]["topic"]["error"].lower()
    assert run["nodes"]["outline"]["status"] == "pending"


def test_unexpected_bugs_do_not_crash_or_leak(api, ws, monkeypatch):
    def boom(ctx, config, up):
        raise RuntimeError("secret internal detail sk-12345")
    monkeypatch.setitem(nodes.NODE_TYPES["topic"], "run", boom)
    run = api.run_node(ws, start(api, ws)["id"], "topic")
    assert run["nodes"]["topic"]["status"] == "error"
    assert "sk-12345" not in json.dumps(run) and "RuntimeError" in run["nodes"]["topic"]["error"]


# ── review gate ───────────────────────────────────────────────────────────────

def test_publish_is_blocked_until_a_person_approves(api, ws):
    run = api.run_all(ws, start(api, ws)["id"])
    run = api.run_node(ws, run["id"], "publish")
    assert run["nodes"]["publish"]["status"] == "error" and "approve or reject" in run["nodes"]["publish"]["error"]
    run = api.review(ws, run["id"], "review", "approve", "looks good", "")
    run = api.run_node(ws, run["id"], "publish")
    result = run["nodes"]["publish"]["output"]["result"]
    assert run["nodes"]["publish"]["status"] == "done" and result["mode"] == "dry_run" and result["path"].endswith(".md")


def test_a_person_can_edit_the_draft_while_approving(api, ws):
    run = api.run_all(ws, start(api, ws)["id"])
    api.review(ws, run["id"], "review", "approve", "", "# My edited title\n\nChanged by a person.")
    assert "Changed by a person" in store.load_draft(ws, run["id"])
    run = api.run_node(ws, run["id"], "publish")
    assert run["nodes"]["publish"]["output"]["result"]["chars"] > 20


def test_rejecting_stops_the_flow_and_updates_the_plan(api, ws):
    item = api.save_plan_item(ws, json.dumps({"title": "Plan me", "keyword": "plan me"}))
    run = api.start_run_for_plan_item(ws, "blog-engine", item["id"])
    run = api.run_all(ws, run["id"])
    assert api.list_plan(ws)[0]["status"] == "review"
    run = api.review(ws, run["id"], "review", "reject", "off brand", "")
    assert run["status"] == "error" and "off brand" in run["nodes"]["review"]["error"]
    assert api.list_plan(ws)[0]["status"] == "rejected"


def test_review_only_works_when_waiting(api, ws):
    run = start(api, ws)
    with pytest.raises(StudioError, match="not waiting"):
        api.review(ws, run["id"], "review", "approve", "", "")
    with pytest.raises(StudioError, match="not a review"):
        api.review(ws, run["id"], "topic", "approve", "", "")
    run = api.run_all(ws, run["id"])
    with pytest.raises(StudioError, match="approve"):
        api.review(ws, run["id"], "review", "maybe", "", "")


def test_plan_item_goes_through_every_status(api, ws):
    item = api.save_plan_item(ws, json.dumps({"title": "Status trip", "keyword": "kw"}))
    run = api.start_run_for_plan_item(ws, "blog-engine", item["id"])
    assert api.list_plan(ws)[0]["status"] == "drafting"
    run = api.run_all(ws, run["id"])
    assert api.list_plan(ws)[0]["status"] == "review"
    api.review(ws, run["id"], "review", "approve", "", "")
    assert api.list_plan(ws)[0]["status"] == "approved"
    api.run_node(ws, run["id"], "publish")
    assert api.list_plan(ws)[0]["status"] == "published" and api.list_plan(ws)[0]["run_id"] == run["id"]


# ── editing and re-running ────────────────────────────────────────────────────

def test_editing_a_prompt_and_rerunning_a_step_uses_the_new_text(api, ws):
    run = api.run_all(ws, start(api, ws)["id"])
    before = api.preview_prompt(ws, "blog-engine", "write", run["id"])
    assert "Use short headings everywhere" not in before["system"]
    pipe = api.get_pipeline(ws, "blog-engine")
    next(n for n in pipe["nodes"] if n["id"] == "write")["config"]["prompt"] = "Use short headings everywhere."
    api.save_pipeline(ws, json.dumps(pipe))
    run = api.reset_from(ws, run["id"], "write")
    assert states(run)["write"] == "pending" and states(run)["seo"] == "pending" and states(run)["outline"] == "done"
    assert "Use short headings everywhere" in api.preview_prompt(ws, "blog-engine", "write", run["id"])["system"]
    run = api.run_all(ws, run["id"])
    assert run["status"] == "awaiting_review"


def test_prompt_preview_shows_rules_keywords_and_your_instructions(api, ws):
    run = api.run_all(ws, start(api, ws)["id"])
    p = api.preview_prompt(ws, "blog-engine", "write", run["id"])
    assert "PRIMARY KEYWORD: retention table" in p["user"] and "WRITING RULEBOOK" in p["user"] and "OUTLINE TO FOLLOW" in p["user"]
    assert "ADDITIONAL INSTRUCTIONS FROM THE OWNER" in p["system"]
    assert p["provider"] == "demo"
    with pytest.raises(StudioError, match="AI steps"):
        api.preview_prompt(ws, "blog-engine", "seo", run["id"])


def test_the_workspace_voice_is_added_to_prompts(api, ws):
    api.save_config(ws, json.dumps({"voice_prompt": "Write like a calm senior engineer."}))
    run = api.run_all(ws, start(api, ws)["id"])
    assert "calm senior engineer" in api.preview_prompt(ws, "blog-engine", "write", run["id"])["user"]


def test_rewiring_the_graph_changes_the_order(api, ws):
    pipe = {"id": "mini", "name": "Mini", "nodes": [
        {"id": "t", "type": "topic", "config": {"topic": "Hello world"}}, {"id": "k", "type": "keywords", "config": {"provider": "manual", "manual": "hello world"}},
        {"id": "w", "type": "write", "config": {}}, {"id": "s", "type": "seo", "config": {}}],
        "edges": [{"source": "t", "target": "k"}, {"source": "k", "target": "w"}, {"source": "w", "target": "s"}]}
    api.save_pipeline(ws, json.dumps(pipe))
    run = api.run_all(ws, api.start_run(ws, "mini", "")["id"])
    assert run["status"] == "done" and run["order"] == ["t", "k", "w", "s"]


# ── scheduling and exports ────────────────────────────────────────────────────

def _plan(api, ws, title, when, status=None):
    item = {"title": title, "keyword": title.lower(), "scheduled_for": when.isoformat()}
    if status:
        item["status"] = status
    return api.save_plan_item(ws, json.dumps(item))


def test_only_due_planned_items_are_picked(api, ws):
    now = datetime.now(timezone.utc)
    _plan(api, ws, "Past planned", now - timedelta(hours=1))
    _plan(api, ws, "Future planned", now + timedelta(days=2))
    _plan(api, ws, "Past but drafting", now - timedelta(hours=1), "drafting")
    api.save_plan_item(ws, json.dumps({"title": "No date"}))
    assert [i["title"] for i in scheduler.due_items(ws)] == ["Past planned"]


def test_run_due_creates_a_draft_and_stops_for_review(api, ws, tmp_path):
    _plan(api, ws, "Scheduled idea", datetime.now(timezone.utc) - timedelta(minutes=5))
    result = scheduler.run_due(ws, out_dir=str(tmp_path / "drafts"))
    assert result[0]["ok"] and result[0]["status"] == "awaiting_review"
    assert (tmp_path / "drafts").glob("*.md") and list((tmp_path / "drafts").glob("*.md"))
    assert api.list_plan(ws)[0]["status"] == "review"           # a person still has to approve it
    assert scheduler.run_due(ws) == []                          # and it is not created twice


def test_run_due_reports_failures_and_keeps_the_item_planned(api, ws, monkeypatch):
    _plan(api, ws, "Will fail", datetime.now(timezone.utc) - timedelta(minutes=5))
    pipe = api.get_pipeline(ws, "blog-engine")
    next(n for n in pipe["nodes"] if n["id"] == "write")["config"]["provider"] = "openai"      # no key saved
    api.save_pipeline(ws, json.dumps(pipe))
    result = scheduler.run_due(ws)
    assert result[0]["ok"] is False and "No API key for openai" in result[0]["error"]
    assert api.list_plan(ws)[0]["status"] == "planned"


def test_cli_run_due(api, ws, tmp_path, capsys):
    _plan(api, ws, "From the CLI", datetime.now(timezone.utc) - timedelta(minutes=5))
    assert cli.main(["list-due", "--workspace", ws]) == 0
    assert "From the CLI" in capsys.readouterr().out
    assert cli.main(["run-due", "--workspace", ws, "--out", str(tmp_path / "out")]) == 0
    assert "[ok ]" in capsys.readouterr().out and list((tmp_path / "out").glob("*.md"))
    assert cli.main(["run-due", "--workspace", ws]) == 0 and "Nothing is due" in capsys.readouterr().out
    assert cli.main(["run-due", "--workspace", "does-not-exist"]) == 1


def test_workflow_export(api, ws):
    api.save_config(ws, json.dumps({"default_provider": "openai"}))
    out = api.export_workflow(ws, "30 8 * * 1")
    assert out["path"] == ".github/workflows/graft-studio.yml" and 'cron: "30 8 * * 1"' in out["yaml"]
    assert f"run-due --workspace {ws}" in out["yaml"] and "STUDIO_KEY_OPENAI: ${{ secrets.OPENAI_API_KEY }}" in out["yaml"]
    assert out["secrets_needed"] == [{"name": "OPENAI_API_KEY", "for": "openai"}]
    assert "create-pull-request" in out["yaml"] and "merge" in out["yaml"].lower()


@pytest.mark.parametrize("bad", ["", "daily", "0 9 * *", "0 9 * * * *", "$(rm -rf /) * * * *", "0 9 * * 1; echo hi", "a b c d e"])
def test_workflow_export_validates_the_cron(api, ws, bad):
    if bad == "":
        api.export_workflow(ws, bad)                 # empty falls back to the workspace default
        return
    with pytest.raises(StudioError, match="cron"):
        api.export_workflow(ws, bad)


def test_bundle_contains_no_secrets(api, ws):
    api.set_secret(ws, "main", "openai", "sk-NEVER-EXPORT-ME")
    bundle = api.export_bundle(ws)
    paths = [f["path"] for f in bundle["files"]]
    assert f".graft-studio/workspaces/{ws}/config.json" in paths and any(p.endswith("pipelines/blog-engine.json") for p in paths)
    assert "sk-NEVER-EXPORT-ME" not in json.dumps(bundle) and not any("secrets" in p for p in paths)


# ── keys never leak ───────────────────────────────────────────────────────────

def test_a_saved_key_appears_in_no_api_output(api, ws, mock, monkeypatch):
    secret = "sk-LEAKCHECK-9876543210"
    monkeypatch.setenv("STUDIO_BASE_OPENAI", mock.url + "/v1")
    mock.on("POST", "/v1/chat/completions", {"error": {"message": f"bad key {secret}"}}, status=401)
    api.set_secret(ws, "main", "openai", secret)
    pipe = api.get_pipeline(ws, "blog-engine")
    next(n for n in pipe["nodes"] if n["id"] == "outline")["config"].update(provider="openai", key_slot="main")
    api.save_pipeline(ws, json.dumps(pipe))
    run = api.run_all(ws, start(api, ws)["id"])
    assert run["nodes"]["outline"]["status"] == "error"
    dump = json.dumps([run, api.workspace(ws), api.list_runs(ws), api.export_bundle(ws), api.export_workflow(ws, ""),
                       api.get_pipeline(ws, "blog-engine"), api.preview_prompt(ws, "blog-engine", "write", run["id"])])
    assert secret not in dump


# ── live providers through the pipeline (mock servers) ────────────────────────

def _live_pipeline(api, ws, updates):
    pipe = api.get_pipeline(ws, "blog-engine")
    for node_id, cfg in updates.items():
        next(n for n in pipe["nodes"] if n["id"] == node_id)["config"].update(cfg)
    api.save_pipeline(ws, json.dumps(pipe))


def test_tinyfish_research_and_dataforseo_keywords_and_openai_writing(api, ws, mock, monkeypatch):
    for name, suffix in (("TINYFISH_SEARCH", ""), ("TINYFISH_FETCH", ""), ("DATAFORSEO", ""), ("OPENAI", "/v1")):
        monkeypatch.setenv(f"STUDIO_BASE_{name}", mock.url + suffix)
    mock.on("GET", "/?query", {"results": [{"position": 1, "title": "Result", "url": "https://r.example/a", "snippet": "S"}]})
    mock.on("POST", "/v3/dataforseo_labs", {"status_code": 20000, "tasks": [{"status_code": 20000, "result": [{"items": [
        {"keyword": "retention table guide", "keyword_info": {"search_volume": 900}, "keyword_properties": {"keyword_difficulty": 15},
         "search_intent_info": {"main_intent": "informational"}}]}]}]})
    mock.on("POST", "/v1/chat/completions", {"choices": [{"message": {"content": "# AI outline\n## One\n## FAQ"}}]})
    mock.on("POST", "/", {"results": [{"url": "https://r.example/a", "title": "R", "text": "Fetched page text about retention."}], "errors": []})
    api.set_secret(ws, "tf", "tinyfish", "tf-key-123456")
    api.set_secret(ws, "dfs", "dataforseo", "login:password")
    api.set_secret(ws, "oai", "openai", "oai-key-123456")
    _live_pipeline(api, ws, {"scrape": {"provider": "tinyfish", "key_slot": "tf"},
                             "keywords": {"provider": "dataforseo", "key_slot": "dfs"},
                             "outline": {"provider": "openai", "key_slot": "oai"}})
    run = start(api, ws, {"title": "Retention tables", "keyword": ""})
    for node in ("topic", "rss", "keywords", "scrape", "corpus", "rulebook", "outline"):
        run = api.run_node(ws, run["id"], node)
        assert run["nodes"][node]["status"] == "done", (node, run["nodes"][node]["error"])
    kw = run["nodes"]["keywords"]["output"]
    assert kw["primary"] == "retention table guide" and kw["has_volumes"] and kw["keywords"][0]["volume"] == 900
    assert run["nodes"]["scrape"]["output"]["sources"][0]["text"].startswith("Fetched page")
    assert run["nodes"]["outline"]["output"]["outline"].startswith("# AI outline")
    sent = [r for r in mock.requests if r["path"].startswith("/v1/chat/completions")][0]
    body = json.loads(sent["body"])
    assert "Fetched page text about retention" in body["messages"][1]["content"] and sent["headers"]["authorization"] == "Bearer oai-key-123456"


def test_github_pull_request_publishing_requires_approval_and_a_repo(api, ws, mock, monkeypatch):
    monkeypatch.setenv("STUDIO_BASE_GITHUB", mock.url)
    mock.on("GET", "/repos/me/site/git/ref/heads/main", {"object": {"sha": "abc"}})
    mock.on("POST", "/repos/me/site/git/refs", {}, status=201)
    mock.on("PUT", "/repos/me/site/contents/", {}, status=201)
    mock.on("POST", "/repos/me/site/pulls", {"html_url": "https://github.com/me/site/pull/3", "number": 3}, status=201)
    api.set_secret(ws, "gh", "github", "ghp_token_123456")
    _live_pipeline(api, ws, {"publish": {"mode": "github_pr", "repo": "", "key_slot": "gh"}})
    run = api.run_all(ws, start(api, ws)["id"])
    run = api.run_node(ws, run["id"], "publish")
    assert "approve or reject" in run["nodes"]["publish"]["error"] and not mock.requests
    api.review(ws, run["id"], "review", "approve", "", "")
    run = api.run_node(ws, run["id"], "publish")
    assert "Set the GitHub repo" in run["nodes"]["publish"]["error"] and not mock.requests
    api.save_config(ws, json.dumps({"github": {"repo": "me/site"}}))
    run = api.run_node(ws, run["id"], "publish")
    assert run["nodes"]["publish"]["output"]["result"]["pull_request"] == "https://github.com/me/site/pull/3"
    put = [r for r in mock.requests if r["method"] == "PUT"][0]
    assert "/content/blog/" in put["path"] and "application/ld+json" in __import__("base64").b64decode(json.loads(put["body"])["content"]).decode()
    assert not any(r["path"].endswith("/merge") for r in mock.requests)            # it opens a pull request and never merges


def test_corpus_learning_from_a_live_blog(api, ws, mock):
    for i, slug in enumerate(("one", "two", "three")):
        mock.on("GET", f"/blog/{slug}", headers={"Content-Type": "text/html"}, body=(
            f"<html><body><article><h1>Post {slug} about growth (2026)</h1><p>Have you wondered about growth? " + "Growth takes steady weekly work. " * 24 +
            "</p><h2>FAQ</h2><h3>What is it?</h3><p>A thing.</p><h3>Why?</h3><p>Because.</p></article></body></html>").encode())
    _live_pipeline(api, ws, {"corpus": {"provider": "direct", "site_url": "", "urls": "\n".join(f"{mock.url}/blog/{s}" for s in ("one", "two", "three"))}})
    run = start(api, ws)
    run = api.run_node(ws, run["id"], "corpus")
    assert run["nodes"]["corpus"]["status"] == "done", run["nodes"]["corpus"]["error"]
    assert run["nodes"]["corpus"]["output"]["stats"]["posts"] == 3
    assert {r["kind"] for r in api.get_rulebook(ws)["rules"]} >= {"length", "faq", "opener"}


def test_corpus_needs_enough_posts(api, ws, mock):
    mock.on("GET", "/blog/a", b"<html><body><article><h1>Short</h1><p>Too short.</p></article></body></html>", headers={"Content-Type": "text/html"})
    _live_pipeline(api, ws, {"corpus": {"provider": "direct", "site_url": "", "urls": f"{mock.url}/blog/a"}})
    run = api.run_node(ws, start(api, ws)["id"], "corpus")
    assert "at least 3" in run["nodes"]["corpus"]["error"]


def test_web_search_needs_tinyfish_and_ssrf_blocked_urls_are_reported(api, ws, monkeypatch):
    _live_pipeline(api, ws, {"scrape": {"provider": "direct", "mode": "search_and_read"}})
    run = start(api, ws)
    for node in ("topic", "rss", "scrape"):
        run = api.run_node(ws, run["id"], node)
    assert "needs TinyFish" in run["nodes"]["scrape"]["error"]
    monkeypatch.delenv("STUDIO_ALLOW_PRIVATE_URLS")
    _live_pipeline(api, ws, {"scrape": {"provider": "direct", "mode": "read_urls", "urls": "http://169.254.169.254/latest/meta-data/"}})
    run = start(api, ws)
    for node in ("topic", "rss", "scrape"):
        run = api.run_node(ws, run["id"], node)
    assert run["nodes"]["scrape"]["status"] == "error" and "not public" in run["nodes"]["scrape"]["error"]
