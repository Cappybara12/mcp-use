import glob as _glob
import importlib
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

# Pipeline Studio lives in a sibling package. The Graftcode gateway runs this module from a temp
# copy, so scripts/run_gateway.sh passes the real folder in WAYZYY_RECEIVER_DIR.
_RECEIVER_DIR = os.environ.get("WAYZYY_RECEIVER_DIR") or str(Path(__file__).resolve().parent.parent)
if _RECEIVER_DIR not in sys.path:
    sys.path.insert(0, _RECEIVER_DIR)

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
        # Read by the article pipeline (agent/config.py) when it shares this file.
        "niche": "Goa travel",
        "offering": "villa or vacation rental",
        "offering_plural": "villas, beach houses, and homestays",
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
    "editorial": {
        "minimum_words": 900,
        "maximum_primary_keyword_uses": 8,
        "required_sections": ["FAQ"],
        "require_sources": True,
        "require_image_attribution": True,
        "require_human_review": True,
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
        for section in ("brand", "categories", "suggestion", "style", "editorial"):
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
    editorial = config["editorial"]
    if not isinstance(editorial.get("minimum_words"), int) or editorial["minimum_words"] < 0:
        raise ValueError("Config error: editorial.minimum_words must be a non-negative integer.")
    if not isinstance(editorial.get("maximum_primary_keyword_uses"), int) or editorial["maximum_primary_keyword_uses"] < 0:
        raise ValueError("Config error: editorial.maximum_primary_keyword_uses must be a non-negative integer.")
    _str_list(editorial["required_sections"], "editorial.required_sections")
    for key in ("require_sources", "require_image_attribution", "require_human_review"):
        if not isinstance(editorial[key], bool):
            raise ValueError(f"Config error: editorial.{key} must be true or false.")
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


def _studio():
    from article_receiver.studio import api

    return api


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


def _validated_name(filename) -> str:
    """Accept only a plain file name: no directories, no absolute paths, no traversal."""
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("Draft filename is required.")
    name = filename.strip()
    if "\x00" in name or "/" in name or "\\" in name or name in (".", "..") or name != Path(name).name:
        raise ValueError(f"Invalid draft filename {filename!r}: only a plain file name is allowed.")
    return name


def _inside_drafts(path: Path) -> Path:
    """Resolve symlinks and require the real location to be inside the drafts folder."""
    root = DRAFTS_DIR.resolve()
    resolved = path.resolve()
    if resolved != root and not resolved.is_relative_to(root):
        raise ValueError("Draft path resolves outside the drafts folder.")
    return resolved


def _find_draft(filename: str) -> Path:
    """Resolve an existing draft by exact name, falling back to a fuzzy name match.

    Every candidate is checked after symlink resolution, so neither a crafted name nor a
    symlink planted in the drafts folder can reach a file outside it.
    """
    name = _validated_name(filename)
    exact = DRAFTS_DIR / name
    if exact.is_file():
        return _inside_drafts(exact)
    for match in sorted(DRAFTS_DIR.glob(f"*{_glob.escape(name)}*")):
        if not match.is_file():
            continue
        try:
            return _inside_drafts(match)
        except ValueError:
            continue  # a symlink pointing outside is never a match
    raise ValueError(f"Draft '{filename}' not found.")


def _draft_write_path(filename: str) -> Path:
    """Path a draft may be written to: a plain *.md name that stays inside the drafts folder."""
    name = _validated_name(filename)
    if not name.lower().endswith(".md"):
        raise ValueError("Draft filenames must end in .md.")
    return _inside_drafts(DRAFTS_DIR / name)


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
        target_path = _draft_write_path(filename)
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
        target_path = _draft_write_path(filename)
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
        file_path = _draft_write_path(filename)
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

        raw_text = file_path.read_text(encoding="utf-8", errors="ignore")
        text = raw_text.lower()

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
        elif not CONFIG["editorial"]["require_image_attribution"]:
            passed_checks.append("Image attribution check disabled")
        if not found_cliches:
            passed_checks.append("No banned AI clichés")

        editorial = CONFIG["editorial"]
        word_count = len(raw_text.split())
        if word_count >= editorial["minimum_words"]:
            passed_checks.append(f"Meets minimum length ({editorial['minimum_words']} words)")
        if editorial["require_sources"] and re.search(r"https?://", raw_text):
            passed_checks.append("Includes source links")
        elif not editorial["require_sources"]:
            passed_checks.append("Source-link check disabled")
        for required in editorial["required_sections"]:
            if required.lower() in text:
                passed_checks.append(f"Includes required section: {required}")

        # The article's primary keyword is only known if the draft's front matter records it.
        # (The brand/destination keyword is deliberately not used: "Goa" would exceed any limit.)
        front = re.match(r"^---\n(.*?)\n---", raw_text, re.DOTALL)
        keyword_match = re.search(r"^(?:primary_)?keyword:\s*(.+)$", front.group(1), re.MULTILINE) if front else None
        keyword = keyword_match.group(1).strip().strip("\"'").lower() if keyword_match else ""
        keyword_uses = len(re.findall(rf"\b{re.escape(keyword)}\b", text)) if keyword else 0
        if keyword and keyword_uses <= editorial["maximum_primary_keyword_uses"]:
            passed_checks.append(f"Primary keyword '{keyword}' is within the limit ({keyword_uses} uses)")

        # Score calculation
        deductions = len(found_cliches) * 4 + min(passive_matches, 5) * 2
        if word_count < editorial["minimum_words"]:
            deductions += 10
        if editorial["require_sources"] and not re.search(r"https?://", raw_text):
            deductions += 10
        if editorial["require_image_attribution"] and attribution and attribution.lower() not in text:
            deductions += 10
        missing_sections = [s for s in editorial["required_sections"] if s.lower() not in text]
        deductions += len(missing_sections) * 5
        if keyword and keyword_uses > editorial["maximum_primary_keyword_uses"]:
            deductions += 5
        score = max(60, 100 - deductions)

        return _to_json(StyleAudit(
            filename=file_path.name,
            brand_score=score,
            verdict="Ready for Publication" if score >= style["publish_threshold"] else "Needs Minor Polish",
            ai_cliches_found=found_cliches,
            passive_instances=passive_matches,
            passed_checks=passed_checks,
            recommendations=(
                [f"Replace cliché '{w}' with a specific detail." for w in found_cliches[:3]]
                + ([f"Add at least {editorial['minimum_words']} words (currently {word_count})."] if word_count < editorial["minimum_words"] else [])
                + (["Add source links for factual claims."] if editorial["require_sources"] and not re.search(r"https?://", raw_text) else [])
                + ([f"Add an image credit that mentions '{attribution}'."] if editorial["require_image_attribution"] and attribution and attribution.lower() not in text else [])
                + ([f"Add required section: {s}." for s in missing_sections])
                + ([f"Reduce uses of '{keyword}' (found {keyword_uses}, limit {editorial['maximum_primary_keyword_uses']})."] if keyword and keyword_uses > editorial["maximum_primary_keyword_uses"] else [])
                + ([f"Rewrite passive phrases (found {passive_matches})."] if passive_matches else [])
            ),
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
        publisher_module = os.environ.get("PUBLISHER_MODULE", "agent.site_publisher")
        publisher_function = os.environ.get("PUBLISHER_FUNCTION", "publish_draft")
        try:
            publish_draft = getattr(importlib.import_module(publisher_module), publisher_function)
        except (ImportError, AttributeError) as exc:
            raise RuntimeError(
                f"Could not load publisher {publisher_module}.{publisher_function}. "
                "Set PUBLISHER_MODULE/PUBLISHER_FUNCTION to an adapter for your site."
            ) from exc

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


    # ── Pipeline Studio ─────────────────────────────────────────────────────────
    # Thin wrappers over article_receiver.studio.api. Arguments are plain strings/booleans and every
    # method returns JSON text. Secrets are write-only: no method ever returns an API key.

    def studio_catalog(self) -> str:
        """Node types, AI providers and plan statuses used by the Pipeline Studio."""
        return json.dumps(_studio().catalog())

    def studio_list_workspaces(self) -> str:
        """List workspaces (one per blog or organization)."""
        return json.dumps(_studio().list_workspaces())

    def studio_create_workspace(self, name: str, site_url: str, niche: str, template: str) -> str:
        """Create a workspace. template is 'demo' (offline samples) or 'live' (a real blog)."""
        return json.dumps(_studio().create_workspace(name, site_url, niche, template))

    def studio_get_workspace(self, ws: str) -> str:
        """Workspace settings, saved key names (masked), pipelines and counts."""
        return json.dumps(_studio().workspace(ws))

    def studio_delete_workspace(self, ws: str) -> str:
        """Delete a workspace and everything in it, including its saved keys."""
        return json.dumps(_studio().delete_workspace(ws))

    def studio_save_config(self, ws: str, patch_json: str) -> str:
        """Update workspace settings (brand, voice prompt, categories, GitHub target, schedule)."""
        return json.dumps(_studio().save_config(ws, patch_json))

    def studio_set_secret(self, ws: str, slot: str, provider: str, key: str) -> str:
        """Save an API key under a name for this workspace. Keys are never returned."""
        return json.dumps(_studio().set_secret(ws, slot, provider, key))

    def studio_delete_secret(self, ws: str, slot: str) -> str:
        """Delete a saved API key."""
        return json.dumps(_studio().delete_secret(ws, slot))

    def studio_get_pipeline(self, ws: str, pipeline_id: str) -> str:
        """A pipeline: its nodes, settings and connections."""
        return json.dumps(_studio().get_pipeline(ws, pipeline_id))

    def studio_save_pipeline(self, ws: str, pipeline_json: str) -> str:
        """Save a pipeline after validating node types and connections."""
        return json.dumps(_studio().save_pipeline(ws, pipeline_json))

    def studio_new_pipeline(self, ws: str, name: str, live: bool) -> str:
        """Create a new pipeline from the starter flow."""
        return json.dumps(_studio().new_pipeline(ws, name, live))

    def studio_delete_pipeline(self, ws: str, pipeline_id: str) -> str:
        """Delete a pipeline (a workspace keeps at least one)."""
        return json.dumps(_studio().delete_pipeline(ws, pipeline_id))

    def studio_preview_prompt(self, ws: str, pipeline_id: str, node_id: str, run_id: str) -> str:
        """The exact prompt an AI step would send, without calling the AI."""
        return json.dumps(_studio().preview_prompt(ws, pipeline_id, node_id, run_id))

    def studio_list_ideas(self, ws: str) -> str:
        """Content ideas found by source steps (RSS, keywords) or added by hand."""
        return json.dumps(_studio().list_ideas(ws))

    def studio_add_idea(self, ws: str, title: str, keyword: str, category: str) -> str:
        """Add a content idea."""
        return json.dumps(_studio().add_idea(ws, title, keyword, category))

    def studio_delete_idea(self, ws: str, idea_id: str) -> str:
        """Remove a content idea."""
        return json.dumps(_studio().delete_idea(ws, idea_id))

    def studio_list_plan(self, ws: str) -> str:
        """The content plan: items with a category, keyword, date and status."""
        return json.dumps(_studio().list_plan(ws))

    def studio_save_plan_item(self, ws: str, item_json: str) -> str:
        """Create or update a plan item (title, category, keyword, scheduled_for, status)."""
        return json.dumps(_studio().save_plan_item(ws, item_json))

    def studio_delete_plan_item(self, ws: str, item_id: str) -> str:
        """Remove a plan item."""
        return json.dumps(_studio().delete_plan_item(ws, item_id))

    def studio_get_rulebook(self, ws: str) -> str:
        """The writing rulebook: learned and custom rules with their evidence."""
        return json.dumps(_studio().get_rulebook(ws))

    def studio_save_rulebook(self, ws: str, rulebook_json: str) -> str:
        """Save an edited rulebook (enable, disable, edit or remove rules)."""
        return json.dumps(_studio().save_rulebook(ws, rulebook_json))

    def studio_add_custom_rule(self, ws: str, text: str, kind: str, phrases: str) -> str:
        """Add your own rule. kind is 'note' or 'banned_phrases' (phrases is comma separated)."""
        return json.dumps(_studio().add_custom_rule(ws, text, kind, phrases))

    def studio_start_run(self, ws: str, pipeline_id: str, item_json: str) -> str:
        """Start a run of a pipeline, optionally for one plan item."""
        return json.dumps(_studio().start_run(ws, pipeline_id, item_json))

    def studio_start_run_for_plan_item(self, ws: str, pipeline_id: str, item_id: str) -> str:
        """Start a run for a plan item (this is the Create draft button)."""
        return json.dumps(_studio().start_run_for_plan_item(ws, pipeline_id, item_id))

    def studio_run_node(self, ws: str, run_id: str, node_id: str) -> str:
        """Run one step of a run and return the updated run."""
        return json.dumps(_studio().run_node(ws, run_id, node_id))

    def studio_run_all(self, ws: str, run_id: str) -> str:
        """Run every pending step; stops at the human review step or the first error."""
        return json.dumps(_studio().run_all(ws, run_id))

    def studio_get_run(self, ws: str, run_id: str) -> str:
        """A run with the status and output of every step."""
        return json.dumps(_studio().get_run(ws, run_id))

    def studio_list_runs(self, ws: str) -> str:
        """Recent runs."""
        return json.dumps(_studio().list_runs(ws))

    def studio_reset_from(self, ws: str, run_id: str, node_id: str) -> str:
        """Clear a step and everything after it so it can be run again."""
        return json.dumps(_studio().reset_from(ws, run_id, node_id))

    def studio_review(self, ws: str, run_id: str, node_id: str, decision: str, notes: str, markdown: str) -> str:
        """Approve or reject a draft at the review step; markdown optionally replaces the draft."""
        return json.dumps(_studio().review(ws, run_id, node_id, decision, notes, markdown))

    def studio_get_draft(self, ws: str, run_id: str) -> str:
        """The draft of a run with a fresh SEO report."""
        return json.dumps(_studio().get_draft(ws, run_id))

    def studio_save_draft(self, ws: str, run_id: str, markdown: str) -> str:
        """Save edits to a run's draft and return it with a fresh SEO report."""
        return json.dumps(_studio().save_draft(ws, run_id, markdown))

    def studio_run_due(self, ws: str) -> str:
        """Create drafts now for every plan item whose date has passed."""
        return json.dumps(_studio().run_due(ws))

    def studio_export_workflow(self, ws: str, cron: str) -> str:
        """A GitHub Actions workflow that creates drafts on a schedule and opens a pull request."""
        return json.dumps(_studio().export_workflow(ws, cron))

    def studio_export_bundle(self, ws: str) -> str:
        """The workspace files (never API keys) to commit next to the workflow."""
        return json.dumps(_studio().export_bundle(ws))
