import glob as _glob
import importlib
import hashlib
import os
import sys
import re
import json
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Optional
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
            {
                "name": "Stays & Villas",
                "keywords": ["villa", "vacation rental", "homestay", "where to stay", "airbnb"],
                "description": "Where to stay in Goa: villas, vacation rentals, homestays, hotels, resorts and Airbnb alternatives",
            },
            {
                "name": "Beaches",
                "keywords": ["beach"],
                "description": "Goa beaches: the best, quiet and hidden beaches in North and South Goa",
            },
            {
                "name": "Food & Nightlife",
                "keywords": ["food", "cafe", "restaurant", "nightlife"],
                "description": "Eating and going out in Goa: restaurants, cafes, food, bars, clubs and nightlife",
            },
            {
                "name": "Trip Planning",
                "keywords": ["itinerary", "things to do", "budget", "family trip", "workation", "scooter", "travel guide"],
                "description": "Planning a Goa trip: itineraries, things to do, budgets, family trips, workations and getting around",
            },
            {
                "name": "Culture & Festivals",
                "keywords": ["temple", "festival", "heritage", "pilgrimage", "yatra"],
                "description": "Goa culture and heritage: temples, churches, pilgrimages, festivals and local traditions",
            },
            {
                "name": "Nature & Monsoon",
                "keywords": ["monsoon", "waterfall", "eco-tourism", "best time"],
                "description": "Goa nature and seasons: monsoon travel, waterfalls, wildlife, eco-tourism and the best time to visit",
            },
            {
                "name": "Travel Rules & Access",
                "keywords": ["visa", "flight", "airport", "charter", "fine"],
                "description": "Rules and access for visitors to Goa: visas, flights, airports, fines and safety rules for tourists",
            },
            {
                "name": "Tourism & Property News",
                "keywords": ["real estate", "second home", "appoints", "investment"],
                "description": "Goa tourism business and property news: tourism policy, hotel launches, hospitality appointments, real estate and second homes",
            },
            {
                "name": "Local News",
                "keywords": ["bjp", "congress", "court", "bail", "police"],
                "description": "Local news unrelated to travel: politics, crime, court cases, accidents, health and schools",
            },
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
    # Used only when a Superlinked SIE server is reachable (SIE_URL); otherwise ignored.
    "semantic": {
        # What an on-brand article is about. Empty means "<brand name>: <brand description>".
        "brand_profile": "Travel guide for tourists visiting Goa: where to stay, villas, beaches, food, things to do",
        # Suggest skips topics less similar than this to the brand profile.
        "min_relevance": 0.25,
        # Suggest skips topics at least this similar to an existing draft's title.
        "covered_threshold": 0.75,
        # Points added to a suggestion score per unit of relevance (relevance 0.4 -> +12).
        "relevance_weight": 30,
        # Related reads link to published posts listed in the site's blogPosts.ts. Empty means
        # <site_repo_path from the writer's config.yaml>/src/lib/blogPosts.ts.
        "site_posts_file": "",
        # A draft's text must be at least this similar to a post's title and description.
        "link_min_similarity": 0.6,
        # A draft title at least this similar to another title is flagged as a near-duplicate.
        "duplicate_threshold": 0.85,
        # Site URL of a post.
        "link_template": "/blog/{slug}",
        # A topic no keyword rule matches gets the category whose description it is closest to,
        # when at least this similar; otherwise categories.default.
        "category_min_similarity": 0.3,
        # Off-brand topics (below min_relevance) that no keyword rule matches go here. Empty to skip.
        "off_brand_category": "Local News",
        # Hand-labelled topics for the Evaluation page, relative to the config file.
        "eval_labels": "eval/wayzyy-labels.yaml",
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
        for section in ("brand", "categories", "suggestion", "style", "editorial", "semantic"):
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
        if not isinstance(rule.get("description", ""), str):
            raise ValueError(f"Config error: categories.rules[{rule['name']}].description must be a string.")
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
    sem = config["semantic"]
    for key in ("brand_profile", "site_posts_file", "eval_labels", "off_brand_category"):
        if not isinstance(sem.get(key), str):
            raise ValueError(f"Config error: semantic.{key} must be a string.")
    if not isinstance(sem.get("link_template"), str) or "{slug}" not in sem["link_template"]:
        raise ValueError("Config error: semantic.link_template must be a string containing {slug}.")
    for key in ("min_relevance", "covered_threshold", "relevance_weight", "link_min_similarity", "duplicate_threshold",
                "category_min_similarity"):
        if isinstance(sem.get(key), bool) or not isinstance(sem.get(key), (int, float)):
            raise ValueError(f"Config error: semantic.{key} must be a number.")
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
    # Filled only when Superlinked SIE is reachable: similarity to the brand profile,
    # and the existing draft that already covers this topic (if any).
    relevance: Optional[float] = None
    on_brand: Optional[bool] = None
    covered_by: str = ""
    # "keyword" (a rule matched), "sie" (closest category description) or "default".
    category_source: str = "default"


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
    relevance: Optional[float] = None
    engine: str = "keyword"
    skipped_off_brand: int = 0
    skipped_covered: int = 0


@dataclass
class RelatedLink:
    slug: str
    title: str
    url: str
    score: float
    # Already listed in this draft's "Related reads" section.
    included: bool


@dataclass
class NearDuplicate:
    title: str
    # "site" for a published post (ref is its URL) or "draft" (ref is the filename).
    kind: str
    ref: str
    score: float


@dataclass
class RelatedLinksResult:
    filename: str
    engine: str
    # URL of this draft's own published copy, when its title matches a live post.
    published_as: str
    links: list[RelatedLink]
    near_duplicates: list[NearDuplicate]
    message: str


@dataclass
class SimilarArticle:
    filename: str
    title: str
    score: float
    engine: str


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


SIE_URL = os.environ.get("SIE_URL", "")
SIE_MODEL = os.environ.get("SIE_MODEL", "sentence-transformers/all-MiniLM-L6-v2")


def _tokens(text: str) -> set:
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def _cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5)
    return dot / norm if norm else 0.0


def _embed_with_sie(texts: list) -> list:
    """Embed texts through a self-hosted Superlinked SIE server (optional)."""
    from sie_sdk import SIEClient
    from sie_sdk.types import Item

    # Fail fast when the server is down; allow time for a model's first-call download.
    client = SIEClient(SIE_URL, connect_timeout_s=3, timeout_s=120)
    results = client.encode(SIE_MODEL, [Item(text=t) for t in texts], wait_for_capacity=False)
    return [[float(v) for v in r["dense"]] for r in results]


# Embeddings keyed by "model|sha1 of the text": a draft, topic or query is embedded once,
# and an edited draft is re-embedded because its text changed. With SIE_CACHE_FILE set
# (scripts/run_gateway.sh sets it), the cache is kept on disk and survives restarts.
_EMBED_CACHE: dict = {}
SIE_CACHE_FILE = os.environ.get("SIE_CACHE_FILE", "")
_disk_cache_loaded = False


def _read_disk_cache() -> dict:
    try:
        data = json.loads(Path(SIE_CACHE_FILE).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_disk_cache(new: dict) -> None:
    """Merge new vectors into the cache file (other gateway processes share it)."""
    try:
        path = Path(SIE_CACHE_FILE)
        path.parent.mkdir(parents=True, exist_ok=True)
        merged = {**_read_disk_cache(), **{k: [round(x, 6) for x in v] for k, v in new.items()}}
        tmp = path.with_suffix(f".{os.getpid()}.tmp")
        tmp.write_text(json.dumps(merged), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        print(f"[sie] could not write {SIE_CACHE_FILE}: {exc}", file=sys.stderr, flush=True)


def _embed_cached(texts: list) -> list:
    global _disk_cache_loaded
    if SIE_CACHE_FILE and not _disk_cache_loaded:
        _EMBED_CACHE.update({k: v for k, v in _read_disk_cache().items() if k not in _EMBED_CACHE})
        _disk_cache_loaded = True
    keys = [f"{SIE_MODEL}|{hashlib.sha1(t.encode('utf-8')).hexdigest()}" for t in texts]
    missing = list(dict.fromkeys(k for k in keys if k not in _EMBED_CACHE))
    if missing:
        text_of = dict(zip(keys, texts))
        new = dict(zip(missing, _embed_with_sie([text_of[k] for k in missing])))
        _EMBED_CACHE.update(new)
        if SIE_CACHE_FILE:
            _save_disk_cache(new)
    return [_EMBED_CACHE[k] for k in keys]


def _embed_drafts_and_query(query: str, files: list, texts: list) -> tuple:
    vectors = _embed_cached([query] + texts)
    return vectors[0], vectors[1:]


def _draft_title(path: Path, text: str) -> str:
    """Front-matter `title:` or the first `# ` heading, else the filename."""
    for line in text.splitlines()[:5]:
        if line.startswith("title:"):
            return line.replace("title:", "").strip().strip('"').strip("'")
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ").title()


def _log_sie_fallback(exc: Exception) -> None:
    """SIE is optional, so failures fall back to keywords; say why in the gateway log."""
    print(f"[sie] {SIE_URL} unavailable, using keywords: {type(exc).__name__}: {exc}"[:500], file=sys.stderr, flush=True)


def _draft_named_for(topic: dict, files: list) -> str:
    """The draft whose filename contains the topic's slug, or "" (no embeddings needed)."""
    slugs = {_slug(topic["title"])}
    if "_" in topic["filename"]:
        slugs.add(_slug(topic["filename"].split("_", 1)[1].rsplit(".", 1)[0]))
    for f in files:
        if any(slug and slug in f.stem.lower() for slug in slugs):
            return f.name
    return ""


RELATED_HEADING = "## Related reads"


def _split_related(text: str) -> tuple:
    """Splits a draft into (body, existing "Related reads" section or "")."""
    m = re.search(rf"^{re.escape(RELATED_HEADING)}\s*$", text, re.MULTILINE)
    if not m:
        return text, ""
    rest = text[m.start():]
    nxt = re.search(r"^#{1,2} ", rest[len(RELATED_HEADING):], re.MULTILINE)
    end = m.start() + len(RELATED_HEADING) + nxt.start() if nxt else len(text)
    return text[: m.start()] + text[end:], text[m.start():end]


def _site_posts_path():
    configured = CONFIG["semantic"]["site_posts_file"].strip()
    if configured:
        return Path(configured).expanduser()
    writer_cfg = WAYZYY_WRITER_DIR / "config.yaml"
    if yaml is None or not writer_cfg.is_file():
        return None
    try:
        repo = (yaml.safe_load(writer_cfg.read_text(encoding="utf-8")) or {}).get("site_repo_path")
    except Exception:
        return None
    return Path(repo).expanduser() / "src" / "lib" / "blogPosts.ts" if repo else None


_POST_RE = re.compile(
    r'slug:\s*"([^"]+)",\s*title:\s*"((?:[^"\\]|\\.)*)",\s*description:\s*"((?:[^"\\]|\\.)*)"', re.S)


def _site_posts() -> list:
    """Published posts as (slug, title, description), read from the site's blogPosts.ts."""
    path = _site_posts_path()
    if not path or not path.is_file():
        return []
    return [(slug, title.replace('\\"', '"'), desc.replace('\\"', '"'))
            for slug, title, desc in _POST_RE.findall(path.read_text(encoding="utf-8", errors="ignore"))]


def _post_url(slug: str) -> str:
    return CONFIG["semantic"]["link_template"].format(slug=slug)


# Titles this similar are the same article (a draft and its published copy).
_SAME_TITLE = 0.97


def _publisher_slug(title: str) -> str:
    """The site publisher's base slug: the title before ':', without '(2026)'. It may
    append a word when the slug is taken, so a published copy's slug starts with this."""
    core = re.sub(r"\(\d{4}\)", "", title.split(":")[0]).strip()
    return re.sub(r"[^a-z0-9]+", "-", core.lower()).strip("-")


def _is_published_copy(draft_title: str, post_slug: str) -> bool:
    base = _publisher_slug(draft_title)
    # Too short a base ("goa") would match most posts, so only use specific ones.
    return base.count("-") >= 2 and (post_slug == base or post_slug.startswith(base + "-"))


def _keyword_category(title: str):
    """The first category rule whose keyword appears in the title, else None."""
    for rule in CONFIG["categories"]["rules"]:
        if any(k.lower() in title.lower() for k in rule.get("keywords", [])):
            return rule["name"]
    return None


def _semantic_categories(titles: list, min_similarity=None):
    """
    For each title, the category whose description it is closest to in meaning (with
    Superlinked SIE), or None when below category_min_similarity. Returns None when SIE
    is not configured or unreachable. Rules without a description use their name.
    """
    rules = CONFIG["categories"]["rules"]
    if not SIE_URL or not titles or not rules:
        return None
    floor = CONFIG["semantic"]["category_min_similarity"] if min_similarity is None else min_similarity
    texts = [f"{r['name']}: {r.get('description') or r['name']}" for r in rules]
    try:
        v = _embed_cached(texts + list(titles))
    except Exception as exc:
        _log_sie_fallback(exc)
        return None
    cats, tv = v[: len(rules)], v[len(rules):]
    out = []
    for x in tv:
        scores = [_cosine(x, c) for c in cats]
        best = max(range(len(scores)), key=scores.__getitem__)
        out.append(rules[best]["name"] if scores[best] >= floor else None)
    return out


def _eval_labels_path():
    rel = CONFIG["semantic"]["eval_labels"].strip()
    if not rel:
        return None
    base = Path(CONFIG["_path"]).parent if CONFIG.get("_path") else Path(__file__).resolve().parent.parent / "config"
    return (base / rel).resolve()


def _brand_profile() -> str:
    profile = CONFIG["semantic"]["brand_profile"].strip()
    return profile or f"{CONFIG['brand']['name']}: {CONFIG['brand']['description']}"


def _topic_signals(topics: list, files: list, texts: list):
    """
    With SIE reachable, returns for each topic (relevance to the brand profile,
    closest draft filename, similarity to that draft's title). Returns None when SIE
    is not configured or unreachable, so callers keep their keyword-only behaviour.

    Coverage compares the topic with draft *titles*: a short topic is loosely similar
    to every long article on the same destination, so whole-text scores over-match.
    """
    if not SIE_URL or not topics:
        return None
    titles = [_draft_title(f, t) for f, t in zip(files, texts)]
    try:
        vectors = _embed_cached([_brand_profile()] + [t["title"] for t in topics] + titles)
    except Exception as exc:
        _log_sie_fallback(exc)
        return None
    profile, topic_vecs, draft_vecs = vectors[0], vectors[1:1 + len(topics)], vectors[1 + len(topics):]
    signals = []
    for v in topic_vecs:
        relevance = _cosine(profile, v)
        best_file, best_score = "", 0.0
        for f, d in zip(files, draft_vecs):
            score = _cosine(v, d)
            if score > best_score:
                best_file, best_score = f.name, score
        signals.append((round(relevance, 3), best_file, round(best_score, 3)))
    return signals


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


def _title_from_filename(stem: str) -> str:
    """Readable title from a queue filename such as 2026-01-05_quiet-beaches."""
    return re.sub(r"^\d{4}-\d{2}-\d{2}_?", "", stem).replace("-", " ").replace("_", " ").strip().title()


def _strip_front_matter(text: str) -> str:
    match = re.match(r"^---\n.*?\n---\n?", text, re.DOTALL)
    return text[match.end():] if match else text


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


def _find_draft(filename: str, exact_only: bool = False) -> Path:
    """Resolve an existing draft by exact name, falling back to a partial name match.

    A partial name must match exactly one draft, so a vague name never picks an arbitrary
    file. Every candidate is checked after symlink resolution, so neither a crafted name
    nor a symlink planted in the drafts folder can reach a file outside it.
    """
    name = _validated_name(filename)
    exact = DRAFTS_DIR / name
    if exact.is_file():
        return _inside_drafts(exact)
    if exact_only:
        raise ValueError(f"Draft '{filename}' not found (an exact file name is required).")
    matches = []
    for match in sorted(DRAFTS_DIR.glob(f"*{_glob.escape(name)}*")):
        if not match.is_file():
            continue
        try:
            matches.append(_inside_drafts(match))
        except ValueError:
            continue  # a symlink pointing outside is never a match
    if len(matches) > 1:
        names = ", ".join(m.name for m in matches[:5])
        raise ValueError(f"Draft name '{filename}' is ambiguous; it matches: {names}")
    if matches:
        return matches[0]
    raise ValueError(f"Draft '{filename}' not found.")


def _draft_write_path(filename: str) -> Path:
    """Path a draft may be written to: a plain *.md name that stays inside the drafts folder."""
    name = _validated_name(filename)
    if not name.lower().endswith(".md"):
        raise ValueError("Draft filenames must end in .md.")
    return _inside_drafts(DRAFTS_DIR / name)


def _new_draft_path(topic: str) -> Path:
    """A fresh draft path for a topic. Never reuses an existing file, so edits are not overwritten.

    Topics with no Latin letters or digits (for example Hindi) get a short hash instead of
    an empty slug, so different topics do not collide.
    """
    slug = _slug(topic) or "topic-" + hashlib.sha1(topic.encode("utf-8")).hexdigest()[:8]
    base = f"{datetime.now().strftime('%Y-%m-%d')}_{slug}"
    path, n = _draft_write_path(f"{base}.md"), 2
    while path.exists():
        path, n = _draft_write_path(f"{base}-{n}.md"), n + 1
    return path


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
        With Superlinked SIE reachable, each topic also gets a brand-relevance score and
        the existing draft that already covers it, if any.
        """
        topics = self._load_topics()[:12]
        files, texts = self._draft_corpus()
        signals = _topic_signals([asdict(t) for t in topics], files, texts)
        if signals:
            threshold = CONFIG["semantic"]["covered_threshold"]
            for t, (relevance, draft, draft_score) in zip(topics, signals):
                t.relevance = relevance
                t.on_brand = relevance >= CONFIG["semantic"]["min_relevance"]
                t.covered_by = draft if draft_score >= threshold else ""
        for t in topics:
            t.covered_by = t.covered_by or _draft_named_for(asdict(t), files)
        unmatched = [t for t in topics if t.category_source == "default"]
        semantic = _semantic_categories([t.title for t in unmatched]) if unmatched else None
        off_brand = CONFIG["semantic"]["off_brand_category"]
        for t, name in zip(unmatched, semantic or []):
            name = (off_brand or name) if t.on_brand is False else name
            if name:
                t.category, t.category_source = name, "sie"
        return _to_json(topics)

    def _load_topics(self) -> list:
        """All pending topics (private helper: Graftcode does not apply Python default args)."""
        topics = []
        if REVIEW_DIR.exists():
            for f in sorted(REVIEW_DIR.glob("*.md"), reverse=True):
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    title = _title_from_filename(f.stem)
                    # extract sources count
                    sources_count = len(re.findall(r"^- \[([^\]]+)\]", content, re.MULTILINE))
                    keyword = re.search(r"^keyword:\s*(.+)$", content, re.MULTILINE)
                    if keyword:
                        title = keyword.group(1).strip().strip('"').strip("'")
                    # extract category
                    keyword_category = _keyword_category(title)
                    category = keyword_category or CONFIG["categories"]["default"]

                    topics.append(Topic(
                        id=f.name,
                        title=title,
                        filename=f.name,
                        category=category,
                        category_source="keyword" if keyword_category else "default",
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
        if not (topic or "").strip():
            raise ValueError("Topic cannot be empty.")
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

        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
        target_path = _new_draft_path(clean_topic)
        filename = target_path.name
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
        DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
        body = (
            f"# {topic}\n\n"
            "> Demo-mode placeholder. Attach the real article-writer pipeline "
            "(set WAYZYY_WRITER_DIR) to generate a researched article.\n\n"
            f"This draft was created by `write_article(\"{topic}\")` over Graftcode.\n"
        )
        target_path = _new_draft_path(topic)
        target_path.write_text(body, encoding="utf-8")
        return _to_json(ArticleResult(
            status="completed (demo)",
            filename=target_path.name,
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

        body = _strip_front_matter(text)
        first_line = next((l for l in body.splitlines() if l.strip() and not l.startswith(("#", ">"))), "")
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

        With Superlinked SIE reachable it also skips off-brand topics and topics an
        existing draft already covers (by meaning, not filename), and adds the topic's
        similarity to the brand profile to its score. Thresholds live in `semantic:`.
        """
        topics = [asdict(t) for t in self._load_topics()]
        if not topics:
            raise ValueError("No pending topics in the queue. Run the scanner first.")

        # The review queue is not pruned when an article is written, so skip topics
        # that already have a draft (matched on the topic slug inside the draft filename).
        files, texts = self._draft_corpus()
        topics = [t for t in topics if not _draft_named_for(t, files)]
        if not topics:
            raise ValueError("Every pending topic already has a draft. Run the scanner for new topics.")

        sem = CONFIG["semantic"]
        signals = _topic_signals(topics, files, texts)
        skipped_off_brand = skipped_covered = 0
        if signals:
            kept = []
            for t, (relevance, draft, draft_score) in zip(topics, signals):
                if draft_score >= sem["covered_threshold"]:
                    skipped_covered += 1
                elif relevance < sem["min_relevance"]:
                    skipped_off_brand += 1
                else:
                    kept.append({**t, "relevance": relevance})
            if not kept:
                raise ValueError(
                    f"No on-brand, uncovered topics left ({skipped_off_brand} off-brand, "
                    f"{skipped_covered} already covered by a draft). Run the scanner, or lower "
                    "semantic.min_relevance in the pipeline config."
                )
            topics = kept

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
            if signals:
                score += round(t["relevance"] * sem["relevance_weight"])
            if best is None or score > best[0]:
                best = (score, t, matched)
        score, t, matched = best

        rationale = (
            f"Highest-scoring pending topic: {t['sources_count']} trend sources"
            + (f"; matches business signals: {', '.join(matched)}" if matched else "; no business-keyword match")
        )
        if signals:
            rationale += (
                f"; brand relevance {t['relevance']:.2f} (Superlinked SIE). Skipped "
                f"{skipped_off_brand} off-brand and {skipped_covered} already-covered topics"
            )
        return _to_json(ArticleSuggestion(
            topic=t["title"],
            rationale=rationale + ".",
            score=score,
            matched_signals=matched,
            sources_count=t["sources_count"],
            relevance=t["relevance"] if signals else None,
            engine=f"keyword + sie:{SIE_MODEL}" if signals else "keyword",
            skipped_off_brand=skipped_off_brand,
            skipped_covered=skipped_covered,
        ))

    def find_similar_articles(self, query: str, limit: int = 3) -> str:
        """
        Finds existing drafts closest in meaning to a topic or question, so a new
        article can reuse the blog's own wording and avoid duplicates.

        Uses embeddings from a self-hosted Superlinked SIE server when SIE_URL is set
        and reachable; otherwise falls back to keyword overlap (no extra service needed).
        """
        limit = self._check_similar_args(query, limit)
        files, texts = self._draft_corpus()
        results, _, _ = self._rank_similar(query, limit, files, texts, use_sie=True)
        return _to_json(results)

    def compare_search_engines(self, query: str, limit: int = 3) -> str:
        """
        Runs the same query through keyword overlap and through Superlinked SIE
        embeddings, side by side, with the time each engine took. Used by the
        dashboard to show what semantic search adds over plain keyword matching.
        """
        limit = self._check_similar_args(query, limit)
        files, texts = self._draft_corpus()
        keyword, k_engine, k_ms = self._rank_similar(query, limit, files, texts, use_sie=False)
        out = {
            "query": query,
            "drafts_searched": len(files),
            "keyword": {"engine": k_engine, "ms": k_ms, "results": [asdict(r) for r in keyword]},
            "sie": {"engine": f"sie:{SIE_MODEL}", "ms": 0, "available": False, "results": [], "message": ""},
        }
        if not SIE_URL:
            out["sie"]["message"] = "SIE_URL is not set. Start sie-server and restart with SIE_URL=http://localhost:8090."
        elif files:
            semantic, s_engine, s_ms = self._rank_similar(query, limit, files, texts, use_sie=True)
            if s_engine.startswith("sie:"):
                out["sie"].update(available=True, ms=s_ms, results=[asdict(r) for r in semantic])
            else:
                out["sie"]["message"] = f"SIE server at {SIE_URL} is not reachable."
        return json.dumps(out)

    @staticmethod
    def _check_similar_args(query: str, limit) -> int:
        if not (query or "").strip():
            raise ValueError("query must not be empty")
        return int(limit) if limit else 3  # Graftcode does not apply Python default args

    @staticmethod
    def _draft_corpus():
        files = sorted(DRAFTS_DIR.glob("*.md")) if DRAFTS_DIR.exists() else []
        return files, [f.read_text(encoding="utf-8", errors="ignore") for f in files]

    @staticmethod
    def _rank_similar(query: str, limit: int, files: list, texts: list, use_sie: bool):
        """Returns (results, engine used, milliseconds)."""
        if not files:
            return [], "keyword-overlap", 0
        t0 = time.perf_counter()
        engine, scores = "keyword-overlap", None
        if use_sie and SIE_URL:
            try:
                q_vec, doc_vecs = _embed_drafts_and_query(query, files, texts)
                scores = [_cosine(q_vec, v) for v in doc_vecs]
                engine = f"sie:{SIE_MODEL}"
            except Exception as exc:
                _log_sie_fallback(exc)
                scores = None  # SIE missing or unreachable: use the fallback
        if scores is None:
            q = _tokens(query)
            scores = [len(q & _tokens(t)) / (len(q) or 1) for t in texts]
        ms = round((time.perf_counter() - t0) * 1000)

        ranked = sorted(zip(files, texts, scores), key=lambda x: x[2], reverse=True)[: max(1, limit)]
        results = []
        for f, text, score in ranked:
            results.append(SimilarArticle(filename=f.name, title=_draft_title(f, text), score=round(score, 3), engine=engine))
        return results, engine, ms

    def suggest_related_links(self, filename: str, limit: int = 3) -> str:
        """
        Suggests published posts (from the site's blogPosts.ts) to link from this draft
        as "Related reads", with their real URLs, and flags near-duplicate titles among
        posts and drafts. Uses Superlinked SIE embeddings when reachable (off-brand
        drafts get no suggestions); otherwise falls back to shared-word overlap.
        Nothing is written: see insert_related_links.
        """
        source = _find_draft(filename)
        limit = int(limit) if limit else 3  # Graftcode does not apply Python default args
        sem = CONFIG["semantic"]
        text = source.read_text(encoding="utf-8", errors="ignore")
        body, related = _split_related(text)
        title = _draft_title(source, text)
        posts = _site_posts()
        files, texts = self._draft_corpus()
        others = [(f, _draft_title(f, t)) for f, t in zip(files, texts) if f.resolve() != source.resolve()]
        if not posts:
            path = _site_posts_path()
            return _to_json(RelatedLinksResult(
                filename=source.name, engine="none", published_as="", links=[], near_duplicates=[],
                message=f"No published posts found ({path or 'set semantic.site_posts_file'}), so there is nothing to link to.",
            ))

        post_texts = [f"{t}. {d}" for _, t, d in posts]
        engine, on_brand, link_scores, title_scores, draft_title_scores = "keyword-overlap", None, None, None, None
        if SIE_URL:
            try:
                n = len(posts)
                v = _embed_cached([body, title, _brand_profile()] + post_texts + [t for _, t, _ in posts] + [t for _, t in others])
                b, tv, profile = v[0], v[1], v[2]
                link_scores = [_cosine(b, x) for x in v[3:3 + n]]
                title_scores = [_cosine(tv, x) for x in v[3 + n:3 + 2 * n]]
                draft_title_scores = [_cosine(tv, x) for x in v[3 + 2 * n:]]
                on_brand = _cosine(profile, tv) >= sem["min_relevance"]
                engine = f"sie:{SIE_MODEL}"
            except Exception as exc:
                _log_sie_fallback(exc)
        if link_scores is None:
            words, norm = _tokens(body), title.strip().lower()
            link_scores = [len(words & _tokens(p)) / (len(_tokens(p)) or 1) for p in post_texts]
            title_scores = [1.0 if t.strip().lower() == norm else 0.0 for _, t, _ in posts]
            draft_title_scores = [1.0 if t.strip().lower() == norm else 0.0 for _, t in others]

        same = [j for j, sc in enumerate(title_scores)
                if sc >= _SAME_TITLE or _is_published_copy(title, posts[j][0])]
        own = max(same, key=lambda j: link_scores[j]) if same else None
        duplicates = [
            NearDuplicate(title=posts[j][1], kind="site", ref=_post_url(posts[j][0]), score=round(title_scores[j], 3))
            for j in sorted(range(len(posts)), key=lambda j: -title_scores[j])
            if j != own and title_scores[j] >= sem["duplicate_threshold"]
        ] + [
            NearDuplicate(title=t, kind="draft", ref=f.name, score=round(sc, 3))
            for (f, t), sc in zip(others, draft_title_scores) if sc >= sem["duplicate_threshold"]
        ]

        candidates = [
            j for j in sorted(range(len(posts)), key=lambda j: -link_scores[j])
            if j != own and title_scores[j] < sem["duplicate_threshold"] and f"]({_post_url(posts[j][0])})" not in body
        ]
        message = ""
        if on_brand is False:
            links, message = [], "This draft looks off-brand, so no related reads are suggested for it."
        else:
            floor = sem["link_min_similarity"] if on_brand is not None else 0.0
            links = [
                RelatedLink(slug=posts[j][0], title=posts[j][1], url=_post_url(posts[j][0]),
                            score=round(link_scores[j], 3), included=f"]({_post_url(posts[j][0])})" in related)
                for j in candidates if link_scores[j] > floor
            ][:limit]
            if on_brand is None:
                message = "Keyword overlap only: start Superlinked SIE (SIE_URL) for meaning-based suggestions."
            elif not links:
                message = f"No published post is similar enough (link_min_similarity {sem['link_min_similarity']})."
        return _to_json(RelatedLinksResult(
            filename=source.name, engine=engine, published_as=_post_url(posts[own][0]) if own is not None else "",
            links=links, near_duplicates=duplicates, message=message,
        ))

    def insert_related_links(self, filename: str, slugs: str) -> str:
        """
        Writes a "## Related reads" section linking to the given published posts
        (comma-separated slugs, usually from suggest_related_links), replacing any
        existing one. An empty list removes the section. Returns the saved draft's details.
        """
        source = _find_draft(filename, exact_only=True)
        posts = {slug: title for slug, title, _ in _site_posts()}
        lines = []
        for slug in [x.strip() for x in (slugs or "").split(",") if x.strip()]:
            if slug not in posts:
                raise ValueError(f"No published post with slug '{slug}'.")
            lines.append(f"[{posts[slug]}]({_post_url(slug)})")
        body, _ = _split_related(source.read_text(encoding="utf-8", errors="ignore"))
        body = body.rstrip() + "\n"
        if lines:
            # One link per paragraph: the site publisher turns each line into a <p>.
            body += f"\n{RELATED_HEADING}\n\n" + "\n\n".join(lines) + "\n"
        return self.save_draft(source.name, body)

    def evaluate_semantic_engine(self) -> str:
        """
        Scores keyword matching against Superlinked SIE on hand-labelled topics
        (semantic.eval_labels): brand relevance, "already covered by a draft" and
        category. Returns accuracy/precision/recall per engine, a threshold sweep,
        and every labelled topic with both engines' answers, so threshold or model
        changes can be compared with numbers.
        """
        path = _eval_labels_path()
        if not path or not path.is_file():
            raise ValueError(f"No labels file found ({path or 'set semantic.eval_labels'}).")
        if yaml is None:
            raise RuntimeError("PyYAML is required to read the labels file.")
        raw = (yaml.safe_load(path.read_text(encoding="utf-8")) or {}).get("labels") or []
        labels = [x for x in raw if isinstance(x, dict) and str(x.get("topic", "")).strip()]
        if not labels:
            raise ValueError(f"{path} has no labels.")
        sem, tiers = CONFIG["semantic"], CONFIG["suggestion"]["tiers"]
        default = CONFIG["categories"]["default"]
        files, texts = self._draft_corpus()
        titles = [str(x["topic"]) for x in labels]

        # Keyword engine: what the pipeline does without SIE.
        kw_brand = [any(w.lower() in t.lower() for tier in tiers for w in tier) for t in titles]
        kw_covered = [bool(_draft_named_for({"title": t, "filename": ""}, files)) for t in titles]
        kw_category = [_keyword_category(t) or default for t in titles]

        t0 = time.perf_counter()
        signals = _topic_signals([{"title": t, "filename": ""} for t in titles], files, texts)
        sie_only = _semantic_categories(titles, min_similarity=-1.0) if signals else None
        sie_ms = round((time.perf_counter() - t0) * 1000)

        def binary(pred, key):
            gold = [bool(x.get(key)) for x in labels]
            tp = sum(p and g for p, g in zip(pred, gold))
            fp = sum(p and not g for p, g in zip(pred, gold))
            fn = sum(g and not p for p, g in zip(pred, gold))
            correct = sum(p == g for p, g in zip(pred, gold))
            precision = tp / (tp + fp) if tp + fp else 0.0
            recall = tp / (tp + fn) if tp + fn else 0.0
            return {
                "accuracy": round(correct / len(gold), 3),
                "precision": round(precision, 3),
                "recall": round(recall, 3),
                "correct": correct,
                "total": len(gold),
            }

        def category(pred):
            gold = [str(x.get("category", "")) for x in labels]
            correct = sum(p == g for p, g in zip(pred, gold))
            return {"accuracy": round(correct / len(gold), 3), "correct": correct, "total": len(gold)}

        tasks = [
            {"id": "on_brand", "name": "Brand relevance", "positive": "on-brand",
             "keyword_rule": "title contains a suggestion-tier keyword", "keyword": binary(kw_brand, "on_brand")},
            {"id": "covered", "name": "Already covered by a draft", "positive": "covered",
             "keyword_rule": "draft filename contains the topic slug", "keyword": binary(kw_covered, "covered")},
            {"id": "category", "name": "Category", "positive": "",
             "keyword_rule": "first matching keyword rule, else the default", "keyword": category(kw_category)},
        ]
        items = [{"topic": t, "label": {"on_brand": bool(x.get("on_brand")), "covered": bool(x.get("covered")),
                                        "category": str(x.get("category", ""))},
                  "keyword": {"on_brand": b, "covered": c, "category": k}}
                 for t, x, b, c, k in zip(titles, labels, kw_brand, kw_covered, kw_category)]

        if signals:
            rel = [r for r, _, _ in signals]
            cov = [sc for _, _, sc in signals]
            sie_brand = [r >= sem["min_relevance"] for r in rel]
            sie_covered = [sc >= sem["covered_threshold"] for sc in cov]
            floor = sem["category_min_similarity"]
            sem_cat = _semantic_categories(titles)
            off_brand = sem["off_brand_category"]
            sem_cat = [(off_brand or c) if not b else c for c, b in zip(sem_cat, sie_brand)]
            combined = [k or c or default for k, c in zip([_keyword_category(t) for t in titles], sem_cat)]
            sie_first = [c or k or default for k, c in zip([_keyword_category(t) for t in titles], sem_cat)]

            def sweep(values, scores, key):
                return [{"value": v, **binary([sc >= v for sc in scores], key)} for v in values]

            tasks[0].update(sie=binary(sie_brand, "on_brand"), threshold={"name": "min_relevance", "value": sem["min_relevance"]},
                            sweep=sweep([0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45], rel, "on_brand"))
            tasks[1].update(sie=binary(sie_covered, "covered"), threshold={"name": "covered_threshold", "value": sem["covered_threshold"]},
                            sweep=sweep([0.6, 0.65, 0.7, 0.75, 0.8, 0.85], cov, "covered"))
            tasks[2].update(sie=category(combined), threshold={"name": "category_min_similarity", "value": floor},
                            variants=[{"name": "Keyword rules, then SIE (used)", **category(combined)},
                                      {"name": "SIE first, then keyword rules", **category(sie_first)},
                                      {"name": "SIE only", **category(sie_only)}])
            for item, r, sc, d, b, c, cat in zip(items, rel, cov, [d for _, d, _ in signals], sie_brand, sie_covered, combined):
                item["sie"] = {"on_brand": b, "covered": c, "category": cat,
                               "relevance": r, "covered_score": sc, "closest_draft": d}
        return json.dumps({
            "labels_file": str(path),
            "labelled": len(labels),
            "drafts": len(files),
            "engine": f"sie:{SIE_MODEL}" if signals else "keyword only",
            "sie_available": bool(signals),
            "sie_ms": sie_ms if signals else 0,
            "message": "" if signals else "Superlinked SIE is not reachable: only keyword results are shown.",
            "tasks": tasks,
            "items": items,
        })

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

        # Publishing is irreversible, so it needs the exact draft file name.
        file_path = _find_draft(filename, exact_only=True)

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

    def studio_write_article(self, ws: str, topic: str, keyword: str) -> str:
        """Write an article for a topic in one call. Runs the workspace's pipeline up to human review and returns the draft, its SEO report and what to fix. Use studio_list_workspaces first to get ws."""
        return json.dumps(_studio().write_article(ws, topic, keyword))

    def studio_decide(self, ws: str, run_id: str, decision: str, notes: str, publish: bool) -> str:
        """Approve or reject a draft that studio_write_article returned. Call this only after the user has explicitly decided. decision is 'approve' or 'reject'. Set publish to true only if the user asked to publish; otherwise nothing is published."""
        return json.dumps(_studio().decide(ws, run_id, decision, notes, publish))

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

    def studio_list_templates(self, ws: str) -> str:
        """List reusable workspace templates for rulebooks, prompts, RSS, keywords, SEO, Reddit and pipelines."""
        return json.dumps(_studio().list_templates(ws))

    def studio_save_template(self, ws: str, template_json: str) -> str:
        """Save or replace a reusable template. It never contains API keys unless the caller puts secrets in the payload."""
        return json.dumps(_studio().save_template(ws, template_json))

    def studio_delete_template(self, ws: str, template_id: str) -> str:
        """Delete a reusable workspace template."""
        return json.dumps(_studio().delete_template(ws, template_id))

    def studio_set_secret(self, ws: str, slot: str, provider: str, key: str) -> str:
        """Save an API key under a name for this workspace. Keys are never returned."""
        return json.dumps(_studio().set_secret(ws, slot, provider, key))

    def studio_test_key(self, ws: str, provider: str, slot: str) -> str:
        """Check that a saved API key works, with one tiny request. Returns ok true/false and a message. Never returns the key."""
        return json.dumps(_studio().test_key(ws, provider, slot))

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
