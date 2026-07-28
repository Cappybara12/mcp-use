"""
Fetch a free, licensed, watermark-free hero image for an article via Pexels.
No scraping random websites — Pexels' license is explicitly free for
commercial use, which matters since Wayzyy is a real business.
"""

import os
import sys
import requests

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"


def get_hero_image(query: str) -> dict | None:
    """Search Pexels for one relevant photo. Returns None if nothing found
    or the API key isn't set — callers should treat images as optional."""
    api_key = os.environ.get("PEXELS_API_KEY")
    if not api_key:
        return None

    try:
        r = requests.get(
            PEXELS_SEARCH_URL,
            headers={"Authorization": api_key},
            params={"query": query, "per_page": 1, "orientation": "landscape"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
    except Exception as e:
        print(f"[images] Pexels search failed for '{query}': {e}", file=sys.stderr)
        return None

    photos = data.get("photos", [])
    if not photos:
        return None

    photo = photos[0]
    return {
        "url": photo["src"]["large"],
        "alt": photo.get("alt") or query,
        "photographer": photo["photographer"],
        "photographer_url": photo["photographer_url"],
    }


def image_markdown(image: dict) -> str:
    """Render a fetched image as markdown with a credit line."""
    return (
        f'![{image["alt"]}]({image["url"]})\n'
        f'*Photo by [{image["photographer"]}]({image["photographer_url"]}) on [Pexels](https://www.pexels.com)*'
    )
