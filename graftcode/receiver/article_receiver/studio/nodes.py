"""Node types for Pipeline Studio.

Every node has: a label and description, a config schema (rendered as a form by the dashboard),
and an executor ``fn(ctx, config, upstream) -> dict``. ``upstream`` is the merged output of every
node that runs before it in the graph, so nodes can be rewired freely.
"""
from __future__ import annotations

import re
from collections import Counter

from . import providers, rulebook, seo, sources, store
from .docs import words_in
from .store import StudioError

MAX_SOURCE_CHARS = 4000
COUNTRY_CODES = {"US": 2840, "GB": 2826, "IN": 2356, "CA": 2124, "AU": 2036, "DE": 2276, "FR": 2250, "ES": 2724, "BR": 2076}


class AwaitReview(Exception):
    """Raised by the review node: the run pauses until a person decides."""


class Ctx:
    """What a node can see and do during a run."""

    def __init__(self, ws: str, run: dict):
        self.ws, self.run = ws, run
        self.item = run.get("item") or {}
        self.cfg = store.get_config(ws)
        self.logs: list[str] = []

    def log(self, message: str) -> None:
        self.logs.append(message[:300])

    def rulebook(self) -> dict:
        return store.get_rulebook(self.ws)

    def key(self, provider: str, slot: str = "") -> str:
        return store.resolve_key(self.ws, provider, slot)

    def llm_settings(self, config: dict) -> tuple[str, str, str]:
        provider = config.get("provider") or self.cfg.get("default_provider") or "demo"
        spec = providers.LLM_PROVIDERS.get(provider)
        if not spec:
            raise StudioError(f"Unknown AI provider: {provider!r}")
        same_as_default = provider == self.cfg.get("default_provider")
        model = config.get("model") or (self.cfg.get("default_model") if same_as_default else "") or spec["default_model"]
        slot = config.get("key_slot") or (self.cfg.get("default_key_slot") if same_as_default else "")
        return provider, model, slot

    def llm(self, config: dict, task: str, system: str, user: str, max_tokens: int = 4096) -> str:
        provider, model, slot = self.llm_settings(config)
        key = self.key(provider, slot) if providers.LLM_PROVIDERS[provider]["needs_key"] else ""
        self.log(f"AI: {provider} / {model}")
        return providers.chat(provider, key, model, system, user, task, max_tokens)

    def add_ideas(self, ideas: list[dict], source: str) -> None:
        store.add_ideas(self.ws, ideas, source)


def _render(template: str, up: dict) -> str:
    out = template or ""
    for name in ("topic", "keyword", "category"):
        out = out.replace("{" + name + "}", str(up.get(name, "")))
    return out.strip()


def _lines(text: str, limit: int) -> list[str]:
    return [ln.strip() for ln in (text or "").splitlines() if ln.strip() and not ln.strip().startswith("#")][:limit]


def _trim(text: str, n: int) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + "..."


# ── source nodes ──────────────────────────────────────────────────────────────

def run_topic(ctx: Ctx, config: dict, up: dict) -> dict:
    item = ctx.item
    topic = (item.get("title") or config.get("topic") or "").strip()
    if not topic:
        raise StudioError("Give this node a topic, or start the run from a plan item in the Content Planner.")
    return {"topic": topic, "keyword": (item.get("keyword") or config.get("keyword") or "").strip(),
            "category": item.get("category") or config.get("category") or "", "notes": item.get("notes", "")}


def run_rss(ctx: Ctx, config: dict, up: dict) -> dict:
    urls = _lines(config.get("urls", ""), 10)
    if not urls:
        raise StudioError("Add at least one feed URL (one per line). Try sample:feed/industry to see how it works.")
    items, errors = [], []
    for url in urls:
        try:
            for entry in sources.read_feed(url):
                items.append({**entry, "feed": url})
        except StudioError as exc:
            errors.append({"url": url, "error": str(exc)})
    if not items:
        raise StudioError(errors[0]["error"] if errors else "No entries found in these feeds.")
    items = items[: max(1, min(int(config.get("max_items") or 15), 50))]
    ctx.add_ideas([{"title": i["title"], "note": i["link"]} for i in items], "rss")
    return {"items": items, "errors": errors}


def run_scrape(ctx: Ctx, config: dict, up: dict) -> dict:
    provider = config.get("provider") or "direct"
    max_pages = max(1, min(int(config.get("max_pages") or 3), 10))
    urls = _lines(config.get("urls", ""), 10)
    found, serp, warnings = [], [], []
    if provider == "sample":
        for url in sources.list_sample_posts()[:max_pages]:
            info = sources.fetch_document(url, "sample")
            doc = sources.to_analysed(info)
            found.append({"url": url, "title": doc["title"], "text": _trim(doc["text"], MAX_SOURCE_CHARS), "sample": True})
        return {"sources": found, "serp": [], "warnings": ["Sample data: these are bundled demo pages, not live research."]}
    key = ctx.key("tinyfish", config.get("key_slot", "")) if provider == "tinyfish" else ""
    if config.get("mode", "search_and_read") == "search_and_read":
        if provider != "tinyfish":
            raise StudioError("Searching the web needs TinyFish. Pick TinyFish as the provider, or switch the mode to 'Read these URLs'.")
        queries = _lines(config.get("queries") or "{topic}", 3)
        for q in queries:
            query = _render(q, up)
            results = providers.tinyfish_search(key, query)
            serp += [{"position": r.get("position"), "title": r.get("title"), "url": r.get("url"), "snippet": r.get("snippet")} for r in results[:10]]
            urls += [r["url"] for r in results[: max_pages] if r.get("url")]
    urls = list(dict.fromkeys(urls))[:max_pages]
    if not urls:
        raise StudioError("Nothing to read. Add URLs, or run a search.")
    if provider == "tinyfish":
        results, errors = providers.tinyfish_fetch(key, urls, "markdown")
        for r in results:
            found.append({"url": r.get("final_url") or r.get("url"), "title": r.get("title") or "", "text": _trim(str(r.get("text") or ""), MAX_SOURCE_CHARS)})
        warnings += [f"{e.get('url')}: {e.get('error')}" for e in errors]
    else:
        for url in urls:
            try:
                doc = sources.to_analysed(sources.fetch_document(url, "direct"))
                found.append({"url": url, "title": doc["title"], "text": _trim(doc["text"], MAX_SOURCE_CHARS)})
            except StudioError as exc:
                warnings.append(f"{url}: {exc}")
    if not found:
        raise StudioError("Could not read any page. " + (warnings[0] if warnings else ""))
    return {"sources": found, "serp": serp, "warnings": warnings}


# ── learning and rules ────────────────────────────────────────────────────────

def run_corpus(ctx: Ctx, config: dict, up: dict) -> dict:
    provider = config.get("provider") or "direct"
    key = ctx.key("tinyfish", config.get("key_slot", "")) if provider == "tinyfish" else ""
    limit = max(3, min(int(config.get("max_posts") or 12), 30))
    urls = _lines(config.get("urls", ""), limit)
    site = (config.get("site_url") or ctx.cfg.get("site_url") or "").strip()
    if not urls:
        if not site:
            raise StudioError("Add your blog's address (Settings or this node), or paste a few post URLs.")
        urls = sources.discover_posts(site, limit)
    posts, texts, summaries, errors = [], [], [], []
    for url in urls:
        try:
            doc = sources.to_analysed(sources.fetch_document(url, provider, key))
        except StudioError as exc:
            errors.append({"url": url, "error": str(exc)})
            continue
        if doc["words"] < 80:
            errors.append({"url": url, "error": "too short to learn from"})
            continue
        post = rulebook.analyze_post(doc, url)
        posts.append(post)
        texts.append(doc["text"])
        summaries.append({"url": url, "title": doc["title"], "words": doc["words"], "opener": post["opener"],
                          "faq_pairs": post["faq_pairs"], "em_dash_per_1000": post["em_dash_per_1000"]})
    if len(posts) < 3:
        raise StudioError(f"Need at least 3 readable posts to learn from; found {len(posts)}. "
                          + (errors[0]["error"] if errors else ""))
    learned = rulebook.learn(posts, texts)
    saved = bool(config.get("save", True))
    if saved:
        merged = rulebook.merge_rulebook(store.get_rulebook(ctx.ws), learned, [{"url": s["url"], "title": s["title"]} for s in summaries])
        store.save_rulebook(ctx.ws, merged)
    return {"posts": summaries, "stats": learned["stats"], "rules": learned["rules"], "errors": errors, "saved": saved}


def run_rulebook(ctx: Ctx, config: dict, up: dict) -> dict:
    rb = ctx.rulebook()
    enabled = [r for r in rb.get("rules", []) if r.get("enabled", True)]
    voice = "\n".join(x for x in (ctx.cfg.get("voice_prompt", ""), config.get("prompt", "")) if x.strip())
    return {"rules": enabled, "rules_prompt": rulebook.rules_prompt(rb), "voice": voice, "rule_count": len(enabled)}


# ── SEO and keywords ──────────────────────────────────────────────────────────

_MODIFIERS = ("how to {k}", "best {k}", "{k} examples", "{k} vs alternatives", "{k} for beginners", "{k} checklist",
              "{k} mistakes", "what is {k}", "{k} template", "{k} cost")


def _serp_candidates(results: list[dict], seed: str) -> list[dict]:
    """Phrases that recur in what already ranks. No volumes: TinyFish Search does not provide them."""
    seed_words = {w for w in re.findall(r"[a-z0-9]+", seed.lower()) if len(w) > 2}
    counts: Counter = Counter()
    for r in results:
        words = re.findall(r"[a-z0-9]+", f"{r.get('title', '')} {r.get('snippet', '')}".lower())
        for n in (2, 3, 4):
            for i in range(len(words) - n + 1):
                gram = words[i:i + n]
                if seed_words & set(gram) and gram[0] not in {"the", "a", "of", "to", "and", "in"} and gram[-1] not in {"the", "a", "of", "to", "and"}:
                    counts[" ".join(gram)] += 1
    return [{"keyword": k, "volume": None, "difficulty": None, "intent": "", "seen_in": n} for k, n in counts.most_common(40) if n >= 2]


def run_keywords(ctx: Ctx, config: dict, up: dict) -> dict:
    provider = config.get("provider") or "manual"
    seed = _render(config.get("seed") or "{topic}", up) or up.get("topic", "")
    limit = max(5, min(int(config.get("limit") or 30), 100))
    country = (config.get("country") or "US").upper()
    if provider == "manual":
        items = [{"keyword": k.lower(), "volume": None, "difficulty": None, "intent": ""} for k in _lines(config.get("manual", ""), limit)]
        if not items and seed:
            items = [{"keyword": seed.lower(), "volume": None, "difficulty": None, "intent": ""}]
    elif provider == "sample":
        base = re.sub(r"^(how to|how do i|what is|what are|best|why)\s+", "", seed.lower()).strip() or "your topic"
        items = [{"keyword": m.format(k=base), "volume": None, "difficulty": None, "intent": "informational" if m.startswith(("how", "what")) else ""} for m in _MODIFIERS]
    elif provider == "dataforseo":
        if not seed:
            raise StudioError("Add a seed keyword.")
        items = providers.dataforseo_suggestions(ctx.key("dataforseo", config.get("key_slot", "")), seed,
                                                 COUNTRY_CODES.get(country, 2840), config.get("language") or "en", limit)
    elif provider == "tinyfish":
        if not seed:
            raise StudioError("Add a seed keyword.")
        results = providers.tinyfish_search(ctx.key("tinyfish", config.get("key_slot", "")), seed, country, config.get("language") or "en")
        items = _serp_candidates(results, seed) or [{"keyword": seed.lower(), "volume": None, "difficulty": None, "intent": ""}]
    else:
        raise StudioError(f"Unknown keyword provider: {provider!r}")
    if not items:
        raise StudioError("No keywords found. Try a broader seed.")
    for it in items:
        it["score"] = seo.opportunity(it)
    items.sort(key=lambda i: i["score"], reverse=True)
    items = items[:limit]
    plan_kw = (up.get("keyword") or "").strip().lower()
    primary = plan_kw or items[0]["keyword"]
    ctx.add_ideas([{"title": it["keyword"], "keyword": it["keyword"],
                    "note": f"volume {it['volume']}" if it.get("volume") else ""} for it in items[:10]], "keywords")
    return {"keywords": items, "primary": primary, "provider": provider, "has_volumes": any(i.get("volume") for i in items)}


def run_seo(ctx: Ctx, config: dict, up: dict) -> dict:
    draft = up.get("draft")
    if not draft:
        raise StudioError("There is no draft to check. Connect this node after the writing step.")
    keyword = up.get("primary") or up.get("keyword") or ""
    report = seo.check(draft, keyword, ctx.rulebook(), ctx.cfg.get("site_url", ""))
    return {"seo": report}


# ── writing ───────────────────────────────────────────────────────────────────

SYSTEM_OUTLINE = (
    "You plan blog articles. Answer the reader's search intent. Output Markdown only: an H1 title, then H2 sections, "
    "then an FAQ section with 3 to 5 questions. Do not write the article itself."
)
SYSTEM_WRITE = (
    "You write blog articles in the author's voice. Output Markdown only. Start with YAML front matter containing "
    "title, description (under 155 characters) and primary_keyword, then the article starting with an H1 that matches "
    "the title. Follow the outline and the rulebook exactly. Cite sources by linking them. Never invent facts, statistics "
    "or quotes: if the research notes do not support a claim, leave it out. End with an FAQ section using '### Question?' headings."
)
SYSTEM_REDDIT = (
    "You help a blog owner share their article on Reddit in a way that is useful to readers and respects each community's "
    "rules. Write post drafts that give value first. Never ask for upvotes or comments. Put the link in a comment or the "
    "last line and disclose that it is the author's own blog. Output Markdown with one section per post."
)


def _opener(ctx: Ctx) -> str:
    for r in ctx.rulebook().get("rules", []):
        if r.get("kind") == "opener" and r.get("enabled", True):
            allowed = r.get("params", {}).get("allowed") or []
            return allowed[0] if allowed else ""
    return ""


def _briefing(ctx: Ctx, up: dict) -> str:
    lines = [f"TOPIC: {up.get('topic', ctx.item.get('title', ''))}",
             f"PRIMARY KEYWORD: {up.get('primary') or up.get('keyword') or up.get('topic', '')}",
             f"CATEGORY: {up.get('category', '')}", f"BRAND: {ctx.cfg.get('name', '')}", f"NICHE: {ctx.cfg.get('niche', '')}"]
    opener = _opener(ctx)
    if opener:
        lines.append(f"OPENER: {opener}")
    if up.get("notes"):
        lines.append(f"NOTES FROM THE EDITOR: {up['notes']}")
    secondary = [k["keyword"] for k in (up.get("keywords") or [])[:8] if k["keyword"] != (up.get("primary") or "")]
    if secondary:
        lines.append("SECONDARY KEYWORDS: " + ", ".join(secondary))
    return "\n".join(lines)


def _research_block(up: dict) -> str:
    notes = []
    for s in (up.get("sources") or [])[:5]:
        notes.append(f"SOURCE: {s.get('title') or s.get('url')} ({s.get('url')})\n{_trim(s.get('text', ''), 1500)}")
    for it in (up.get("items") or [])[:8]:
        notes.append(f"NEWS: {it.get('title')} ({it.get('link')}) {it.get('summary', '')}")
    return "RESEARCH NOTES (the only facts you may rely on):\n" + "\n\n".join(notes) if notes else ""


def build_prompt(ctx: Ctx, ntype: str, config: dict, up: dict) -> tuple[str, str, str]:
    """(system, user, task) for an AI node. Shared by real runs and the prompt preview."""
    rules = up.get("rules_prompt") or rulebook.rules_prompt(ctx.rulebook())
    voice = up.get("voice") or ctx.cfg.get("voice_prompt", "")
    extra = (config.get("prompt") or "").strip()
    if ntype == "outline":
        system, task = SYSTEM_OUTLINE, "outline"
        parts = [_briefing(ctx, up), _research_block(up), rules, ("VOICE: " + voice) if voice else ""]
    elif ntype == "write":
        system, task = SYSTEM_WRITE, "write"
        parts = [_briefing(ctx, up), ("OUTLINE TO FOLLOW:\n" + up["outline"]) if up.get("outline") else "", _research_block(up), rules,
                 ("VOICE: " + voice) if voice else ""]
    elif ntype == "reddit":
        system, task = SYSTEM_REDDIT + "\n\nTHE AUTHOR'S REDDIT PLAYBOOK:\n" + ctx.cfg.get("reddit_playbook", ""), "reddit"
        report = up.get("seo") or {}
        heads = [h["text"] for h in report.get("headings", []) if h["level"] == 2][:8]
        url = (ctx.cfg.get("site_url", "").rstrip("/") + "/" + report.get("slug", "")).strip("/") if ctx.cfg.get("site_url") else "(blog link)"
        parts = [f"TOPIC: {up.get('topic', '')}", f"ARTICLE TITLE: {report.get('title', up.get('topic', ''))}", f"ARTICLE URL: {url}",
                 "ARTICLE SECTIONS: " + "; ".join(heads), ("SUBREDDITS TO CONSIDER: " + config["subreddits"]) if config.get("subreddits") else "",
                 ("VOICE: " + voice) if voice else ""]
    else:
        raise StudioError(f"{ntype} is not an AI node.")
    if extra:
        system = system + "\n\nADDITIONAL INSTRUCTIONS FROM THE OWNER:\n" + extra
    return system, "\n\n".join(p for p in parts if p), task


def _ai_node(ntype: str):
    def run(ctx: Ctx, config: dict, up: dict) -> dict:
        if ntype == "reddit" and not up.get("draft") and not up.get("seo"):
            raise StudioError("Connect the Reddit step after the writing/SEO steps so it has an article to promote.")
        system, user, task = build_prompt(ctx, ntype, config, up)
        text = ctx.llm(config, task, system, user, 6000 if ntype == "write" else 3000)
        if ntype == "outline":
            return {"outline": text}
        if ntype == "write":
            store.save_draft(ctx.ws, ctx.run["id"], text)
            return {"draft": text, "draft_words": words_in(text)}
        return {"reddit": text}
    return run


# ── review and publish ────────────────────────────────────────────────────────

def run_review(ctx: Ctx, config: dict, up: dict) -> dict:
    if not up.get("draft"):
        raise StudioError("There is no draft to review yet.")
    raise AwaitReview()


def run_publish(ctx: Ctx, config: dict, up: dict) -> dict:
    review = up.get("review") or {}
    if not review.get("approved"):
        raise StudioError("Approve the draft in the Review step before publishing.")
    draft = review.get("final_markdown") or up.get("draft") or ""
    report = up.get("seo") or {}
    slug = report.get("slug") or seo.slugify(up.get("topic", "post"))
    gh = ctx.cfg.get("github", {})
    template = config.get("path_template") or gh.get("path_template") or "content/blog/{slug}.md"
    path = template.replace("{slug}", slug)
    if config.get("append_faq_schema", True) and report.get("faq_script") and "application/ld+json" not in draft:
        draft = draft.rstrip() + "\n\n" + report["faq_script"] + "\n"
    branch = f"graft-studio/{slug[:50]}-{ctx.run['id'][:6]}"
    repo = (config.get("repo") or gh.get("repo") or "").strip()
    base = (config.get("base_branch") or gh.get("base_branch") or "main").strip()
    title = f"Add blog post: {report.get('title') or up.get('topic', slug)}"[:200]
    if (config.get("mode") or "dry_run") == "dry_run":
        return {"result": {"mode": "dry_run", "repo": repo or "(not set)", "base_branch": base, "branch": branch, "path": path,
                           "title": title, "chars": len(draft), "note": "Nothing was sent. Switch the mode to 'Open a GitHub pull request' to publish."}}
    if not repo:
        raise StudioError("Set the GitHub repo (owner/name) in Settings or on this node.")
    token = ctx.key("github", config.get("key_slot", ""))
    pr = providers.github_open_pr(token, repo, base, branch, path, draft, title,
                                  f"Draft generated by Graft Studio (run {ctx.run['id']}). Reviewed and approved by a person before publishing.")
    return {"result": {"mode": "github_pr", "repo": repo, "path": path, "pull_request": pr["url"], "branch": branch}}


# ── registry ──────────────────────────────────────────────────────────────────

def _llm_fields(prompt_default: str, prompt_help: str) -> list[dict]:
    return [
        {"key": "provider", "label": "AI provider", "type": "llm_provider", "help": "Leave empty to use the workspace default."},
        {"key": "model", "label": "Model", "type": "model"},
        {"key": "key_slot", "label": "API key", "type": "key_slot", "help": "Pick a saved key, or leave empty for the default."},
        {"key": "prompt", "label": "Your instructions", "type": "textarea", "default": prompt_default, "help": prompt_help},
    ]


NODE_TYPES: dict[str, dict] = {
    "topic": {"label": "Topic", "group": "Start", "description": "The article to write: from a plan item, or typed here.",
              "run": run_topic, "defaults": {"topic": ""},
              "fields": [{"key": "topic", "label": "Topic (used when not started from a plan item)", "type": "text"},
                         {"key": "keyword", "label": "Primary keyword (optional)", "type": "text"}]},
    "rss": {"label": "RSS feeds", "group": "Sources", "description": "Pull fresh headlines to find ideas and research.",
            "run": run_rss, "defaults": {"urls": "sample:feed/industry", "max_items": 15},
            "fields": [{"key": "urls", "label": "Feed URLs (one per line)", "type": "textarea", "help": "Use sample:feed/industry to try it offline."},
                       {"key": "max_items", "label": "Max items", "type": "number"}]},
    "scrape": {"label": "Web research", "group": "Sources", "description": "Search the web and read pages (TinyFish), or read URLs you give.",
               "run": run_scrape, "defaults": {"provider": "sample", "mode": "search_and_read", "queries": "{topic}", "max_pages": 3},
               "fields": [{"key": "provider", "label": "Provider", "type": "select", "options": [["sample", "Sample data (offline)"], ["direct", "Direct fetch (free)"], ["tinyfish", "TinyFish (search + clean pages)"]]},
                          {"key": "key_slot", "label": "TinyFish key", "type": "key_slot", "keyProvider": "tinyfish"},
                          {"key": "mode", "label": "Mode", "type": "select", "options": [["search_and_read", "Search, then read top results"], ["read_urls", "Read these URLs"]]},
                          {"key": "queries", "label": "Search queries ({topic} is replaced)", "type": "textarea"},
                          {"key": "urls", "label": "URLs to read (one per line)", "type": "textarea"},
                          {"key": "max_pages", "label": "Max pages", "type": "number"}]},
    "corpus": {"label": "Learn from your blog", "group": "Rules", "description": "Read existing posts and learn how you write: openers, em dashes, FAQs, length.",
               "run": run_corpus, "defaults": {"provider": "sample", "max_posts": 12, "save": True, "site_url": "sample:blog/acme"},
               "fields": [{"key": "site_url", "label": "Blog address", "type": "text", "help": "Leave empty to use the workspace site. sample:blog/acme uses bundled demo posts."},
                          {"key": "urls", "label": "Or paste post URLs (one per line)", "type": "textarea"},
                          {"key": "provider", "label": "Reader", "type": "select", "options": [["sample", "Sample data (offline)"], ["direct", "Direct fetch (free)"], ["tinyfish", "TinyFish"]]},
                          {"key": "key_slot", "label": "TinyFish key", "type": "key_slot", "keyProvider": "tinyfish"},
                          {"key": "max_posts", "label": "Posts to read", "type": "number"},
                          {"key": "save", "label": "Save the learned rules to the rulebook", "type": "bool"}]},
    "rulebook": {"label": "Rulebook", "group": "Rules", "description": "The rules every draft must follow. Edit them in the Rulebook panel.",
                 "run": run_rulebook, "defaults": {"prompt": ""},
                 "fields": [{"key": "prompt", "label": "Extra voice notes for this pipeline", "type": "textarea",
                             "help": "Added to the workspace voice. Example: 'Write like a friendly senior engineer. No jargon.'"}]},
    "keywords": {"label": "Keyword research", "group": "SEO", "description": "Find what people search for and pick a primary keyword.",
                 "run": run_keywords, "defaults": {"provider": "sample", "seed": "{topic}", "limit": 30, "country": "US", "language": "en"},
                 "fields": [{"key": "provider", "label": "Provider", "type": "select", "options": [["sample", "Sample data (no real volumes)"], ["manual", "My own list"], ["dataforseo", "DataForSEO (OpenSEO's data source)"], ["tinyfish", "TinyFish Search (what ranks)"]]},
                            {"key": "key_slot", "label": "API key", "type": "key_slot", "keyProviderFrom": "provider"},
                            {"key": "seed", "label": "Seed keyword ({topic} is replaced)", "type": "text"},
                            {"key": "manual", "label": "Your keywords (one per line)", "type": "textarea"},
                            {"key": "country", "label": "Country", "type": "text"},
                            {"key": "limit", "label": "How many", "type": "number"}]},
    "outline": {"label": "Outline", "group": "Write", "description": "Plan the article structure.", "run": _ai_node("outline"),
                "defaults": {"provider": "", "model": "", "key_slot": "", "prompt": "Plan around the main question a searcher has. Use 5 to 7 H2 sections and end with an FAQ."},
                "fields": _llm_fields("Plan around the main question a searcher has. Use 5 to 7 H2 sections and end with an FAQ.",
                                      "Extra instructions for the outline step.")},
    "write": {"label": "Write draft", "group": "Write", "description": "Write the article following the outline and rulebook.", "run": _ai_node("write"),
              "defaults": {"provider": "", "model": "", "key_slot": "", "prompt": "Write for a smart beginner. Use concrete examples and short paragraphs."},
              "fields": _llm_fields("Write for a smart beginner. Use concrete examples and short paragraphs.", "Extra instructions for the writing step. The rulebook is added automatically.")},
    "seo": {"label": "SEO check", "group": "SEO", "description": "Check keywords, headings, links and your rulebook; build FAQ schema.", "run": run_seo, "defaults": {}, "fields": []},
    "review": {"label": "Human review", "group": "Approve", "description": "A person reads the draft and approves, edits or rejects it.", "run": run_review, "defaults": {}, "fields": []},
    "reddit": {"label": "Reddit post ideas", "group": "Promote", "description": "Draft Reddit posts that promote the article without spamming.",
               "run": _ai_node("reddit"),
               "defaults": {"provider": "", "model": "", "key_slot": "", "subreddits": "", "prompt": ""},
               "fields": [{"key": "subreddits", "label": "Subreddits to consider (optional)", "type": "text"},
                          *_llm_fields("", "Describe how you like to post. This overrides the default style.")]},
    "publish": {"label": "Publish", "group": "Publish", "description": "Open a GitHub pull request with the approved article. Never merges.",
                "run": run_publish, "defaults": {"mode": "dry_run", "repo": "", "base_branch": "", "path_template": "", "append_faq_schema": True},
                "fields": [{"key": "mode", "label": "Mode", "type": "select", "options": [["dry_run", "Dry run (nothing is sent)"], ["github_pr", "Open a GitHub pull request"]]},
                           {"key": "repo", "label": "Repository (owner/name)", "type": "text", "help": "Leave empty to use the workspace setting."},
                           {"key": "base_branch", "label": "Base branch", "type": "text"},
                           {"key": "path_template", "label": "File path ({slug} is replaced)", "type": "text"},
                           {"key": "key_slot", "label": "GitHub token", "type": "key_slot", "keyProvider": "github"},
                           {"key": "append_faq_schema", "label": "Append FAQ JSON-LD to the article", "type": "bool"}]},
}


def describe_types() -> list[dict]:
    return [{"type": t, "label": s["label"], "group": s["group"], "description": s["description"],
             "defaults": s["defaults"], "fields": s["fields"], "ai": t in ("outline", "write", "reddit")} for t, s in NODE_TYPES.items()]


def default_pipeline(live: bool = False) -> dict:
    """The starter flow for a new workspace. 'demo' runs offline on bundled samples; 'live' is for a real blog."""
    if live:
        order = [("topic", 0, 160), ("corpus", 234, 20), ("rulebook", 234, 200), ("keywords", 234, 380), ("outline", 468, 160),
                 ("write", 702, 160), ("seo", 936, 160), ("review", 1170, 160), ("reddit", 1404, 60), ("publish", 1404, 260)]
        pairs = [("topic", "keywords"), ("corpus", "rulebook"), ("rulebook", "outline"), ("keywords", "outline"),
                 ("outline", "write"), ("write", "seo"), ("seo", "review"), ("review", "reddit"), ("review", "publish")]
        overrides = {"corpus": {"provider": "direct", "site_url": ""}, "keywords": {"provider": "manual"}}
    else:
        order = [("topic", 0, 120), ("rss", 0, 300), ("corpus", 234, 20), ("rulebook", 234, 200), ("keywords", 234, 380),
                 ("scrape", 468, 300), ("outline", 468, 120), ("write", 702, 120), ("seo", 936, 120), ("review", 1170, 120),
                 ("reddit", 1404, 20), ("publish", 1404, 220)]
        pairs = [("topic", "keywords"), ("topic", "scrape"), ("rss", "scrape"), ("corpus", "rulebook"), ("rulebook", "outline"),
                 ("keywords", "outline"), ("scrape", "outline"), ("outline", "write"), ("write", "seo"), ("seo", "review"),
                 ("review", "reddit"), ("review", "publish")]
        overrides = {}
    nodes_ = [{"id": t, "type": t, "position": {"x": x, "y": y}, "config": {**NODE_TYPES[t]["defaults"], **overrides.get(t, {})}}
              for t, x, y in order]
    return {"id": "blog-engine", "name": "Blog engine", "nodes": nodes_,
            "edges": [{"id": f"{a}->{b}", "source": a, "target": b} for a, b in pairs]}
