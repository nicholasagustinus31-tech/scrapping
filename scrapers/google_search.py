"""Google search scraper with API and Selenium fallback."""

from __future__ import annotations

import logging
import random
import time
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def _search_with_api(query: str, max_results: int, api_key: str, cx: str) -> List[Dict]:
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": min(max_results, 10),
    }
    logging.debug("Calling Google Custom Search API: %s", params)
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()

    results = []
    for item in data.get("items", [])[:max_results]:
        results.append(
            {
                "name": item.get("title"),
                "title": item.get("title"),
                "company": None,
                "email": None,
                "phone": None,
                "city": None,
                "country": None,
                "url": item.get("link"),
                "platform": "google_search",
                "source": item.get("link"),
                "notes": item.get("snippet"),
            }
        )
    return results


def _init_selenium_driver(user_agent: Optional[str] = None) -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    if user_agent:
        options.add_argument(f"--user-agent={user_agent}")
    return webdriver.Chrome(options=options)


def _search_with_selenium(query: str, max_results: int) -> List[Dict]:
    user_agent = random.choice(
        [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        ]
    )
    driver = _init_selenium_driver(user_agent)
    try:
        query_url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num={max_results}"
        driver.get(query_url)
        time.sleep(random.uniform(2, 5))
        html = driver.page_source
    finally:
        driver.quit()

    soup = BeautifulSoup(html, "html.parser")
    results = []
    for result in soup.select("div.g"):
        title_elem = result.select_one("h3")
        link_elem = result.select_one("a")
        if not title_elem or not link_elem:
            continue
        results.append(
            {
                "name": title_elem.text,
                "title": title_elem.text,
                "company": None,
                "email": None,
                "phone": None,
                "city": None,
                "country": None,
                "url": link_elem["href"],
                "platform": "google_search",
                "source": link_elem["href"],
                "notes": None,
            }
        )
        if len(results) >= max_results:
            break
    return results


def search_google(query: str, max_results: int, use_api: bool = True, cfg: Optional[Dict] = None) -> List[Dict]:
    """Search Google using API or Selenium fallback."""
    cfg = cfg or {}
    search_cfg = cfg.get("search", {})
    use_api = search_cfg.get("use_google_api", use_api)
    api_key = search_cfg.get("google_api_key")
    cx = search_cfg.get("google_cx")

    if use_api and api_key and cx:
        try:
            return _search_with_api(query, max_results, api_key, cx)
        except requests.HTTPError as exc:
            logging.warning("Google API error: %s", exc)
            if exc.response.status_code == 429:
                time.sleep(10)
            else:
                raise

    logging.info("Falling back to Selenium for Google search")
    return _search_with_selenium(query, max_results)
