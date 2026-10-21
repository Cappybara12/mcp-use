import os
import sys
import re
import json
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from datetime import datetime

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

# --- Pipeline configuration ----------------------------------------------
# Everything niche-specific (brand, categories, suggestion keywords, style rules) lives in a
# YAML file so the same receiver, Graft and MCP tools can serve any blog. These built-in
# defaults equal receiver/config/wayzyy.yaml; a user file only needs the keys it changes.
_DEFAULT_CONFIG = {
    "brand": {
        "name": "Wayzyy",
        "description": "Goa vacation rental & travel marketplace",
        "topic_keyword": "Goa",
        "fallback_research_prompt": "Topic: {topic}. Write a comprehensive guide for {brand}'s audience based on your knowledge.",
    },
    "categories": {
        "default": "Guide",
        "rules": [
            {"name": "Beaches", "keywords": ["beach"]},
            {"name": "Stays & Villas", "keywords": ["rental", "villa"]},
            {"name": "Food & Cafes", "keywords": ["food", "cafe"]},
            {"name": "Seasonal", "keywords": ["monsoon"]},
        ],
    },
    "suggestion": {
        "tiers": [
            ["villa", "vacation rental", "airbnb alternative", "where to stay"],
            ["best beaches", "hidden beaches", "south goa", "north goa", "itinerary", "workation"],
            ["things to do", "travel guide", "family", "budget", "monsoon", "restaurants", "cafe", "nightlife"],
        ],
    },
    "style": {
        "banned_words": [
            "delve", "tapestry", "nestled", "picture-perfect", "hidden gem", "breathtaking", "vibrant",
            "moreover", "furthermore", "in conclusion", "leverage", "utilize", "optimal", "seamlessly", "must-visit",
        ],
        "banned_openers": ["are you planning", "looking for", "if you're planning"],
        "attribution_keyword": "pexels",
        "publish_threshold": 85,
    },
}


def _str_list(value, where: str) -> list:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ValueError(f"Config error: {where} must be a list of strings.")
    return value


def _load_config(path) -> dict:
    """Merge a YAML config over the built-in defaults and validate its shape."""
    import copy

    config = copy.deepcopy(_DEFAULT_CONFIG)
    if path:
        path = Path(path)
        if not path.is_file():
            raise FileNotFoundError(f"PIPELINE_CONFIG points to a missing file: {path}")
        if yaml is None:
            raise RuntimeError("PyYAML is required to read PIPELINE_CONFIG: pip install pyyaml")
        user = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(user, dict):
            raise ValueError(f"Config error: {path} must contain a mapping at the top level.")
        for section in ("brand", "categories", "suggestion", "style"):
            if section in user:
                if not isinstance(user[section], dict):
                    raise ValueError(f"Config error: '{section}' must be a mapping.")
                config[section].update(user[section])
        if user.get("data_dir"):
            config["data_dir"] = str((path.parent / str(user["data_dir"])).resolve())
        config["_path"] = str(path)

    for rule in config["categories"]["rules"]:
        if not isinstance(rule, dict) or "name" not in rule:
            raise ValueError("Config error: each category rule needs a 'name' and a 'keywords' list.")
        _str_list(rule.get("keywords", []), f"categories.rules[{rule['name']}].keywords")
    for i, tier in enumerate(config["suggestion"]["tiers"]):
        _str_list(tier, f"suggestion.tiers[{i}]")
    _str_list(config["style"]["banned_words"], "style.banned_words")
    _str_list(config["style"]["banned_openers"], "style.banned_openers")
    return config


# The Graftcode gateway runs this module from a temp copy, so scripts/run_gateway.sh passes the
# config path explicitly. Unset means "use the built-in defaults".
CONFIG = _load_config(os.environ.get("PIPELINE_CONFIG"))

# Paths are configurable through environment variables so the receiver runs on
# any machine. Defaults assume the standard Wayzyy checkout under ~/Documents.
_DEFAULT_ROOT = Path.home() / "Documents" / "wayzyy-site"
WAYZYY_WRITER_DIR = Path(os.environ.get("WAYZYY_WRITER_DIR", _DEFAULT_ROOT / "article-writer"))
CHRONICALLY_ONLINE_DIR = Path(os.environ.get("WAYZYY_SCANNER_DIR", _DEFAULT_ROOT / "24-7-chronically-online"))

# Demo mode: when the real article-writer pipeline is not present, the receiver
# serves bundled sample data so anyone can run and explore the Graftcode
# integration without API keys or the private pipeline.
# The Graftcode gateway runs the module from a temp copy, so __file__ is not
# reliable there; scripts/run_gateway.sh passes WAYZYY_SAMPLE_DIR explicitly.
SAMPLE_DIR = Path(os.environ.get("WAYZYY_SAMPLE_DIR") or CONFIG.get("data_dir") or Path(__file__).resolve().parent.parent / "sample_data")
WRITER_AVAILABLE = (WAYZYY_WRITER_DIR / "agent").is_dir()
SCANNER_AVAILABLE = (CHRONICALLY_ONLINE_DIR / "main.py").is_file()
DRAFTS_DIR = Path(os.environ.get("WAYZYY_DRAFTS_DIR", (WAYZYY_WRITER_DIR / "drafts") if WRITER_AVAILABLE else (SAMPLE_DIR / "drafts")))
REVIEW_DIR = Path(os.environ.get("WAYZYY_REVIEW_DIR", (CHRONICALLY_ONLINE_DIR / "review") if SCANNER_AVAILABLE else (SAMPLE_DIR / "review")))

# The receiver is normally started by Graftcode, not by the article-writer
# process. Load the writer's environment here so the receiver reports and uses
# the same provider configuration as the real pipeline.
try:
    from dotenv import load_dotenv
    load_dotenv(WAYZYY_WRITER_DIR / ".env", override=False)
except ImportError:
    pass


# --- Typed contract -------------------------------------------------------
# Only str / int / float / bool / simple classes / list[T], which is the
# portable baseline for Graftcode grafts. Dates are ISO strings.

@dataclass
class QueueStats:
    pending_topics_count: int
    completed_drafts_count: int


@dataclass
class Providers:
    primary_llm: str
    research_engine: str
    media_engine: str


@dataclass
class PipelineStatus:
    status: str
    runtime: str
    transport: str
    active_brand: str
    queue_stats: QueueStats
    providers: Providers
    timestamp: str


@dataclass
class Topic:
    id: str
    title: str
    filename: str
    category: str
    sources_count: int
    snippet: str


@dataclass
class TopicSource:
    platform: str
    title: str
    url: str


@dataclass
class ArticleResult:
    status: str
    filename: str
    title: str
    word_count: int
    saved_to: str
    preview_snippet: str
    style_flags: list[str]


@dataclass
class DraftSummary:
    filename: str
    title: str
    word_count: int
    size_bytes: int
    updated_at: str


@dataclass
class DraftContent:
    filename: str
    content: str
    word_count: int


@dataclass
class SaveResult:
    status: str
    filename: str
    size_bytes: int
    word_count: int


@dataclass
class StyleAudit:
    filename: str
    brand_score: int
    verdict: str
    ai_cliches_found: list[str]
    passive_instances: int
    passed_checks: list[str]
    recommendations: list[str]


@dataclass
class ScanResult:
    status: str
    message: str
    output: str
    pending_topics_count: int


@dataclass
class ArticleSuggestion:
    topic: str
    rationale: str
    score: int
    matched_signals: list[str]
    sources_count: int


@dataclass
class PullRequestResult:
    status: str
    branch: str
    target_repo: str
    target_branch: str
    pr_title: str
    commit_hash: str
    pr_url: str
    files_modified: list[str]
    message: str


def _to_json(result) -> str:
    """Serialize typed results to JSON for the wire.

    Typed dataclass returns reach Node callers as opaque handles in the alpha
    Graftcode SDK, so the public surface returns JSON strings while the
    dataclasses above stay as the internal schema.
    """
    if isinstance(result, list):
        return json.dumps([asdict(r) for r in result])
    return json.dumps(asdict(result))


def _writer_imports():
    """Import the production article pipeline lazily after its path is ready."""
    writer_root = str(WAYZYY_WRITER_DIR)
    if writer_root not in sys.path:
        sys.path.insert(0, writer_root)
    from agent.planner import generate_outline
    from agent.researcher import run_research
    from agent.style_checker import check_article
    from agent.writer import parse_outline, write_full_article
    return generate_outline, run_research, check_article, parse_outline, write_full_article


def _topic_snippet(content: str) -> str:
    """One-line summary for a queue entry: front-matter facts, else the first prose line."""
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if match:
        meta = dict(
            (k.strip(), v.strip())
            for k, _, v in (line.partition(":") for line in match.group(1).splitlines())
            if v.strip()
        )
        parts = []
        if meta.get("platforms"):
            parts.append(f"Seen on: {meta['platforms']}")
        if meta.get("classification"):
            parts.append(f"Type: {meta['classification'].replace('_', ' ')}")
        if parts:
            return " · ".join(parts)
        content = content[match.end():]
    prose = next((l.strip() for l in content.splitlines() if l.strip() and not l.startswith(("#", ">", "-"))), "")
    return prose[:180]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _find_draft(filename: str) -> Path:
    """Resolve a draft by exact name, falling back to a fuzzy match."""
    file_path = DRAFTS_DIR / filename
    if file_path.exists():
        return file_path
    matches = list(DRAFTS_DIR.glob(f"*{filename}*"))
    if matches:
        return matches[0]
    raise ValueError(f"Draft '{filename}' not found.")

class ArticlePipelineService:
    """
    Graftcode Receiver Service:
    Exposes the Wayzyy Autonomous Content Engine methods to:
    1. Next.js / TypeScript front-end callers (via auto-generated strongly typed Graft).
    2. Claude Desktop / Cursor agents (via auto-exposed MCP tool calling).
    """

    def get_pipeline_status(self) -> str:
        """
        Returns real-time pipeline status, model providers, and queue counts.
        """
        pending_count = len(list(REVIEW_DIR.glob("*.md"))) if REVIEW_DIR.exists() else 0
        drafts_count = len(list(DRAFTS_DIR.glob("*.md"))) if DRAFTS_DIR.exists() else 0

        # Check API key configuration
        has_kimi = bool(os.environ.get("KIMI_API_KEY"))
        has_openai = bool(os.environ.get("OPENAI_API_KEY"))
        has_groq = bool(os.environ.get("GROQ_API_KEY"))
        has_firecrawl = bool(os.environ.get("FIRECRAWL_API_KEY"))
        has_pexels = bool(os.environ.get("PEXELS_API_KEY"))

        if has_openai:
            primary_llm = f"OpenAI {os.environ.get('OPENAI_MODEL', 'gpt-5.5')} (primary; Groq fallback)"
        elif has_kimi:
            primary_llm = "Kimi Moonshot (primary; Groq fallback)"
        elif has_groq:
            primary_llm = "Groq LLaMA 3.3 70B (active; Kimi unavailable)"
        else:
            primary_llm = "Not configured"
        if not WRITER_AVAILABLE:
            primary_llm = "Demo mode (article-writer pipeline not attached)"

        return _to_json(PipelineStatus(
            status="online (demo mode)" if not WRITER_AVAILABLE else "online",
            runtime=f"Python {sys.version_info.major}.{sys.version_info.minor} (Native Graftcode Receiver)",
            transport="Hypertube / Binary RPC + WebSocket + MCP",
            active_brand=f"{CONFIG['brand']['name']} ({CONFIG['brand']['description']})",
            queue_stats=QueueStats(
                pending_topics_count=pending_count,
                completed_drafts_count=drafts_count,
            ),
            providers=Providers(
                primary_llm=primary_llm,
                research_engine="Firecrawl Web Search" if has_firecrawl else "Not configured (limited context)",
                media_engine="Pexels License API" if has_pexels else "Local placeholder (Pexels unavailable)",
            ),
            timestamp=datetime.now().isoformat(),
        ))

    def list_pending_topics(self) -> str:
        """
        Retrieves pending topics in the review queue with metadata and source counts.
        """
        return _to_json(self._load_topics()[:12])

    def _load_topics(self) -> list:
        """All pending topics (private helper: Graftcode does not apply Python default args)."""
        topics = []
        if REVIEW_DIR.exists():
            for f in sorted(REVIEW_DIR.glob("*.md"), reverse=True):
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    title = f.stem.replace("2026-", "").replace("2025-", "").replace("-", " ").title()
                    # extract sources count
                    sources_count = len(re.findall(r"^- \[([^\]]+)\]", content, re.MULTILINE))
                    keyword = re.search(r"^keyword:\s*(.+)$", content, re.MULTILINE)
                    if keyword:
                        title = keyword.group(1).strip().strip('"').strip("'")
                    # extract category
                    category = CONFIG["categories"]["default"]
                    for rule in CONFIG["categories"]["rules"]:
                        if any(k.lower() in title.lower() for k in rule.get("keywords", [])):
                            category = rule["name"]
                            break

                    topics.append(Topic(
                        id=f.name,
                        title=title,
                        filename=f.name,
                        category=category,
                        sources_count=sources_count,
                        snippet=_topic_snippet(content),
                    ))
                except Exception:
                    continue

        return topics

    def get_topic_sources(self, topic: str) -> str:
        """
        Retrieves verified sources, headlines, and platform URLs for a specific topic.
        """
        sources = []
        if REVIEW_DIR.exists():
            for fname in REVIEW_DIR.glob("*.md"):
                content = fname.read_text(encoding="utf-8", errors="ignore")
                if topic.lower() in fname.name.lower() or topic.lower() in content.lower():
                    for m in re.finditer(r"^- \[([^\]]+)\] \[([^\]]+)\]\(([^)]*)\)", content, re.MULTILINE):
                        platform, title, url = m.groups()
                        sources.append(TopicSource(platform=platform, title=title, url=url))

        return _to_json(sources)

    def write_article(self, topic: str, skip_research: bool = False, extra_research: str = "") -> str:
        """
        Executes the full generation pipeline for an article:
        Topic Analysis -> Research Synthesis -> Tone Formatting -> Image Attribution -> Draft Output.
        """
        clean_topic = topic.strip()
        if not clean_topic:
            raise ValueError("Topic cannot be empty.")

        if not WRITER_AVAILABLE:
            return self._write_demo_article(clean_topic)

        generate_outline, run_research, check_article, parse_outline, write_full_article = _writer_imports()
        research_brief = ""
        if skip_research:
            research_brief = CONFIG["brand"]["fallback_research_prompt"].format(topic=clean_topic, brand=CONFIG["brand"]["name"])
        else:
            research_result = run_research(clean_topic)
            research_brief = research_result["brief"]
        if (extra_research or "").strip():
            research_brief += (
                "\n\nADDITIONAL RESEARCH PROVIDED BY THE USER (treat as authoritative):\n"
                + (extra_research or "").strip()
            )

        outline = generate_outline(clean_topic, research_brief)
        parsed = parse_outline(outline)
        parsed["title"] = parsed.get("title") or clean_topic
        parsed["primary_keyword"] = parsed.get("primary_keyword") or clean_topic
        article_content = write_full_article(parsed, research_brief)
        style_result = check_article(article_content)
        article_content = style_result["article"]

        slug = re.sub(r"[^a-z0-9]+", "-", clean_topic.lower()).strip("-")
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"{date_str}_{slug}.md"
        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
        target_path = DRAFTS_DIR / filename
        target_path.write_text(article_content, encoding="utf-8")

        return _to_json(ArticleResult(
            status="completed",
            filename=filename,
            title=str(parsed["title"]),
            word_count=len(article_content.split()),
            saved_to=str(target_path),
            preview_snippet=article_content[:250],
            style_flags=[str(flag) for flag in style_result.get("flags", [])],
        ))

    def _write_demo_article(self, topic: str) -> str:
        """Demo mode: write a clearly-labelled placeholder draft (no LLM, no API keys)."""
        slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
        filename = f"{datetime.now().strftime('%Y-%m-%d')}_{slug}.md"
        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
        body = (
            f"# {topic}\n\n"
            "> Demo-mode placeholder. Attach the real article-writer pipeline "
            "(set WAYZYY_WRITER_DIR) to generate a researched article.\n\n"
            f"This draft was created by `write_article(\"{topic}\")` over Graftcode.\n"
        )
        target_path = DRAFTS_DIR / filename
        target_path.write_text(body, encoding="utf-8")
        return _to_json(ArticleResult(
            status="completed (demo)",
            filename=filename,
            title=topic,
            word_count=len(body.split()),
            saved_to=str(target_path),
            preview_snippet=body[:250],
            style_flags=["demo-mode"],
        ))

    def list_drafts(self) -> str:
        """
        Lists all generated drafts with file size, modified date, and word count.
        """
        drafts = []
        if DRAFTS_DIR.exists():
            for f in sorted(DRAFTS_DIR.glob("*.md"), reverse=True):
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    lines = content.splitlines()
                    title = f.stem.replace("-", " ").title()
                    for line in lines[:5]:
                        if line.startswith("title:"):
                            title = line.replace("title:", "").strip().strip('"').strip("'")
                            break
                        elif line.startswith("# "):
                            title = line.replace("# ", "").strip()
                            break

                    drafts.append(DraftSummary(
                        filename=f.name,
                        title=title,
                        word_count=len(content.split()),
                        size_bytes=f.stat().st_size,
                        updated_at=datetime.fromtimestamp(f.stat().st_mtime).strftime("%b %d, %Y %H:%M"),
                    ))
                except Exception:
                    continue

        return _to_json(drafts)

    def get_draft(self, filename: str) -> str:
        """
        Returns the raw markdown content of a draft.
        """
        file_path = _find_draft(filename)
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        return _to_json(DraftContent(
            filename=file_path.name,
            content=content,
            word_count=len(content.split()),
        ))

    def save_draft(self, filename: str, content: str) -> str:
        """
        Saves updated markdown content back to the draft file.
        """
        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
        file_path = DRAFTS_DIR / Path(filename).name
        file_path.write_text(content, encoding="utf-8")
        return _to_json(SaveResult(
            status="success",
            filename=file_path.name,
            size_bytes=file_path.stat().st_size,
            word_count=len(content.split()),
        ))

    def run_style_check(self, filename: str) -> str:
        """
        Heuristic style audit of a draft (a few rule-based checks, not a full style guide):
        Checks for AI clichés, banned openers, passive-voice density and basic structure.
        """
        file_path = _find_draft(filename)

        text = file_path.read_text(encoding="utf-8", errors="ignore").lower()

        style = CONFIG["style"]
        found_cliches = [w for w in style["banned_words"] if re.search(rf"\b{re.escape(w.lower())}\b", text)]

        # Check passive voice occurrences
        passive_matches = len(re.findall(r"\b(is|are|was|were|been)\s+\w+ed\b", text))

        first_line = next((l for l in text.splitlines() if l.strip() and not l.startswith(("#", "---", ">"))), "")
        passed_checks = []
        if not first_line.startswith(tuple(o.lower() for o in style["banned_openers"])):
            passed_checks.append("No banned generic opener")
        if re.search(r"^## ", text, re.MULTILINE):
            passed_checks.append("Has an H2 section structure")
        topic_keyword = CONFIG["brand"]["topic_keyword"]
        if topic_keyword and topic_keyword.lower() in text:
            passed_checks.append(f"Mentions the topic keyword ('{topic_keyword}')")
        attribution = style["attribution_keyword"]
        if attribution and attribution.lower() in text:
            passed_checks.append(f"Includes {attribution.title()} attribution")
        if not found_cliches:
            passed_checks.append("No banned AI clichés")

        # Score calculation
        deductions = len(found_cliches) * 4 + min(passive_matches, 5) * 2
        score = max(60, 100 - deductions)

        return _to_json(StyleAudit(
            filename=file_path.name,
            brand_score=score,
            verdict="Ready for Publication" if score >= style["publish_threshold"] else "Needs Minor Polish",
            ai_cliches_found=found_cliches,
            passive_instances=passive_matches,
            passed_checks=passed_checks,
            recommendations=[f"Replace cliché '{w}' with a specific detail." for w in found_cliches[:3]],
        ))

    def run_scanner(self) -> str:
        """
        Runs the real trend scanner (`main.py --scan` in the scanner project) and
        reports the resulting queue size. In demo mode it reports that nothing ran.
        """
        if not SCANNER_AVAILABLE:
            return _to_json(ScanResult(
                status="skipped (demo mode)",
                message="Scanner project not found. Set WAYZYY_SCANNER_DIR to enable real scans.",
                output="",
                pending_topics_count=len(list(REVIEW_DIR.glob("*.md"))) if REVIEW_DIR.exists() else 0,
            ))
        result = subprocess.run(
            [sys.executable, "main.py", "--scan"],
            cwd=CHRONICALLY_ONLINE_DIR,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Scanner failed: {result.stderr[-1000:]}")
        return _to_json(ScanResult(
            status="success",
            message="Scanner finished.",
            output=result.stdout[-2000:],
            pending_topics_count=len(list(REVIEW_DIR.glob("*.md"))) if REVIEW_DIR.exists() else 0,
        ))

    def suggest_next_article(self) -> str:
        """
        Ranks the pending topics by business relevance (keyword tiers) and the
        number of real trend sources, and returns the best one to write next.
        """
        topics = [asdict(t) for t in self._load_topics()]
        if not topics:
            raise ValueError("No pending topics in the queue. Run the scanner first.")

        # The review queue is not pruned when an article is written, so skip topics
        # that already have a draft (matched on the topic slug inside the draft filename).
        draft_names = [f.stem.lower() for f in DRAFTS_DIR.glob("*.md")] if DRAFTS_DIR.exists() else []

        def has_draft(topic: dict) -> bool:
            slugs = {_slug(topic["title"])}
            if "_" in topic["filename"]:
                slugs.add(_slug(topic["filename"].split("_", 1)[1].rsplit(".", 1)[0]))
            return any(slug and slug in name for slug in slugs for name in draft_names)

        topics = [t for t in topics if not has_draft(t)]
        if not topics:
            raise ValueError("Every pending topic already has a draft. Run the scanner for new topics.")

        tiers = CONFIG["suggestion"]["tiers"]
        best = None
        for t in topics:
            title = t["title"].lower()
            matched, tier_score = [], 0
            for i, words in enumerate(tiers):
                hits = [w for w in words if w.lower() in title]
                if hits:
                    matched += hits
                    tier_score = max(tier_score, (len(tiers) - i) * 10)
            score = tier_score + t["sources_count"]
            if best is None or score > best[0]:
                best = (score, t, matched)
        score, t, matched = best
        return _to_json(ArticleSuggestion(
            topic=t["title"],
            rationale=(
                f"Highest-scoring pending topic: {t['sources_count']} trend sources"
                + (f"; matches business signals: {', '.join(matched)}" if matched else "; no business-keyword match")
                + "."
            ),
            score=score,
            matched_signals=matched,
            sources_count=t["sources_count"],
        ))

    def push_to_github(self, filename: str) -> str:
        """
        Publishes the draft through the production publisher, pushes a new branch,
        and creates a real GitHub pull request when GITHUB_TOKEN/GH_TOKEN is set.
        """
        if not WRITER_AVAILABLE:
            raise RuntimeError("push_to_github needs the real article-writer pipeline (set WAYZYY_WRITER_DIR).")
        if str(WAYZYY_WRITER_DIR) not in sys.path:
            sys.path.insert(0, str(WAYZYY_WRITER_DIR))
        from agent.site_publisher import publish_draft

        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if not token:
            raise RuntimeError(
                "GITHUB_TOKEN/GH_TOKEN is not configured. The publisher will not push a branch "
                "until GitHub PR authorization is available."
            )

        site_dir = os.environ.get("WAYZYY_SITE_DIR")
        if not site_dir:
            raise RuntimeError("WAYZYY_SITE_DIR is not set. Point it at your local checkout of the site repo.")

        file_path = _find_draft(filename)

        result = publish_draft(str(file_path), dry_run=False)
        branch_name = f"add-blog-{result['slug']}"
        remote = subprocess.check_output(
            ["git", "-C", str(Path(site_dir)), "remote", "get-url", "origin"],
            text=True,
        ).strip()
        match = re.search(r"github\.com[:/](.+?)(?:\.git)?$", remote)
        if not match:
            raise RuntimeError(f"Origin is not a GitHub repository: {remote}")
        owner_repo = match.group(1)
        pr_title = f"feat(blog): publish {result['slug'].replace('-', ' ').title()}"
        payload = json.dumps({
            "title": pr_title,
            "head": branch_name,
            "base": "main",
            "body": f"Generated {CONFIG['brand']['name']} article for `{result['slug']}`. Please review content, links, and image attribution before merging.",
        }).encode()
        request = urllib.request.Request(
            f"https://api.github.com/repos/{owner_repo}/pulls",
            data=payload,
            method="POST",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "wayzyy-graftcode-publisher",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                pr = json.loads(response.read().decode())
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")
            raise RuntimeError(f"GitHub PR creation failed ({error.code}): {detail}") from error

        return _to_json(PullRequestResult(
            status="pr_created",
            branch=branch_name,
            target_repo=owner_repo,
            target_branch="main",
            pr_title=pr_title,
            commit_hash=result.get("commit_hash", ""),
            pr_url=pr["html_url"],
            files_modified=[str(p) for p in (result.get("tsx_path"), result.get("hero_image_path")) if p],
            message="Real GitHub pull request created. Nothing was merged into main.",
        ))
