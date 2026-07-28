"""
Loads config.yaml — the brand/site settings that make this tool point at
YOUR blog instead of Wayzyy. Falls back to Wayzyy's own values if the file
is missing, so nothing changes for the existing deployment if config.yaml
ever isn't present.
"""

import yaml
from pathlib import Path
from functools import lru_cache

CONFIG_PATH = Path(__file__).parent.parent / "config.yaml"

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
    return merged
