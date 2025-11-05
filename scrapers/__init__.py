"""Social scraper dispatch utilities."""

from __future__ import annotations

from typing import Dict, List, Optional

from .google_search import search_google  # re-export
from .instagram_api import scrape_instagram
from .linkedin_api import scrape_linkedin


def scrape_social(
    platform: str,
    query_or_profile_id: str,
    max_results: int = 10,
    cfg: Optional[Dict] = None,
) -> List[Dict]:
    """Dispatch to the appropriate social scraper based on platform name."""
    cfg = cfg or {}
    tokens = cfg.get("social", {})
    platform = platform.lower()

    if platform == "linkedin":
        token = tokens.get("linkedin_token")
        if not token:
            raise ValueError("LinkedIn token not configured")
        return scrape_linkedin(query_or_profile_id, token, max_results)

    if platform == "instagram":
        token = tokens.get("instagram_token")
        if not token:
            raise ValueError("Instagram token not configured")
        return scrape_instagram(query_or_profile_id, token, max_results)

    raise ValueError(f"Unsupported platform: {platform}")
