"""LinkedIn API client wrapper."""

from __future__ import annotations

import logging
from typing import Dict, List

import requests


LINKEDIN_API_URL = "https://api.linkedin.com/v2"


def _build_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "X-Restli-Protocol-Version": "2.0.0",
    }


def scrape_linkedin(query: str, token: str, max_results: int = 10) -> List[Dict]:
    """Scrape leads using the official LinkedIn API search endpoint."""
    headers = _build_headers(token)
    params = {
        "q": "search",
        "query": query,
        "count": min(max_results, 25),
    }

    url = f"{LINKEDIN_API_URL}/people/(keywords:({query}))"
    logging.debug("Querying LinkedIn API: %s", url)

    response = requests.get(url, headers=headers, params=params, timeout=30)
    if response.status_code == 401:
        raise PermissionError("LinkedIn token invalid or expired")
    if response.status_code == 429:
        raise RuntimeError("LinkedIn rate limit exceeded")
    response.raise_for_status()

    data = response.json()
    elements = data.get("elements", [])

    leads: List[Dict] = []
    for element in elements:
        profile = element.get("hitInfo", {})
        name = profile.get("name", {}).get("text")
        occupation = profile.get("occupation", {}).get("text")
        leads.append(
            {
                "name": name,
                "title": occupation,
                "company": profile.get("companyName"),
                "email": None,
                "phone": None,
                "city": profile.get("location", {}).get("defaultLocalizedName"),
                "country": profile.get("location", {}).get("countryCode"),
                "url": profile.get("publicProfileUrl"),
                "platform": "linkedin",
                "source": profile.get("publicProfileUrl"),
                "notes": None,
            }
        )
        if len(leads) >= max_results:
            break
    return leads
