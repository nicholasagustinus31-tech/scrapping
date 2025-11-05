"""Instagram Graph API client wrapper."""

from __future__ import annotations

import logging
from typing import Dict, List

import requests

INSTAGRAM_API_URL = "https://graph.facebook.com/v18.0"


def scrape_instagram(query: str, token: str, max_results: int = 10) -> List[Dict]:
    """Search public Instagram business accounts using the Graph API."""
    params = {
        "q": query,
        "type": "page",
        "fields": "name,link,location,phone",
        "access_token": token,
        "limit": min(max_results, 25),
    }
    url = f"{INSTAGRAM_API_URL}/search"
    logging.debug("Querying Instagram Graph API: %s", url)

    response = requests.get(url, params=params, timeout=30)
    if response.status_code == 400 and "permissions" in response.text.lower():
        raise PermissionError("Instagram token missing required permissions")
    if response.status_code == 429:
        raise RuntimeError("Instagram rate limit exceeded")
    response.raise_for_status()

    data = response.json()
    leads: List[Dict] = []
    for item in data.get("data", [])[:max_results]:
        location = item.get("location") or {}
        leads.append(
            {
                "name": item.get("name"),
                "title": None,
                "company": item.get("name"),
                "email": None,
                "phone": item.get("phone"),
                "city": location.get("city"),
                "country": location.get("country"),
                "url": item.get("link"),
                "platform": "instagram",
                "source": item.get("link"),
                "notes": None,
            }
        )
    return leads
