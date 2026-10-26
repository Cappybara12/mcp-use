"""
Loads config.yaml — the brand/site settings that make this tool point at
YOUR blog instead of Wayzyy. Falls back to Wayzyy's own values if the file
is missing, so nothing changes for the existing deployment if config.yaml
ever isn't present.
"""

import yaml
import os
from pathlib import Path
from functools import lru_cache

CONFIG_PATH = Path(os.environ.get("PIPELINE_CONFIG", Path(__file__).parent.parent / "config.yaml"))

_DEFAULTS = {
    "brand": {
        "name": "Wayzyy",
        "blog_url": "https://wayzyy.com",
        "contact_email": "hello@wayzyy.com",
        "niche": "Goa travel",
        "location_keyword": "Goa",
        "offering": "villa or vacation rental",
        "offering_plural": "villas, beach houses, and homestays",
    },
    "site_repo_path": "/Users/akshay/.gemini/antigravity-ide/scratch/wayzyy-site",
    "editorial": {
        "minimum_words": 900,
        "maximum_primary_keyword_uses": 8,
        "required_sections": ["FAQ"],
        "require_sources": True,
        "require_image_attribution": True,
        "require_human_review": True,
    },
    "editorial_rules": {
        "tone": "Helpful, specific, practical, and honest; avoid generic praise.",
        "required_elements": ["concrete examples", "source links", "original recommendations"],
        "banned_phrases": ["in today's fast-paced world", "unlock the power of"],
    },
}


@lru_cache(maxsize=1)
def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return _DEFAULTS
    try:
        with open(CONFIG_PATH) as f:
            user_config = yaml.safe_load(f) or {}
    except Exception:
        return _DEFAULTS

    merged = dict(_DEFAULTS)
    merged["brand"] = {**_DEFAULTS["brand"], **user_config.get("brand", {})}
    merged["site_repo_path"] = user_config.get("site_repo_path", _DEFAULTS["site_repo_path"])
    merged["editorial"] = {**_DEFAULTS["editorial"], **user_config.get("editorial", {})}
    merged["editorial_rules"] = {**_DEFAULTS["editorial_rules"], **user_config.get("editorial_rules", {})}
    return merged


def editorial_contract() -> str:
    """Return project-specific rules injected into the writing prompts."""
    cfg = load_config()
    rules = cfg["editorial_rules"]
    gates = cfg["editorial"]
    return (
        f"BRAND: {cfg['brand']['name']} — {cfg['brand'].get('niche') or cfg['brand'].get('description', '')}\n"
        f"TONE: {rules['tone']}\n"
        f"REQUIRED ELEMENTS: {', '.join(rules['required_elements'])}\n"
        f"BANNED PHRASES: {', '.join(rules['banned_phrases'])}\n"
        f"MINIMUM LENGTH: {gates['minimum_words']} words\n"
        f"REQUIRED SECTIONS: {', '.join(gates['required_sections'])}\n"
        f"PRIMARY KEYWORD LIMIT: {gates['maximum_primary_keyword_uses']} uses\n"
        "Do not invent facts. Use the research brief and cite useful sources. "
        "The output must be reviewed by a human before publication."
    )
