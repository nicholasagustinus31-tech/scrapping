"""Duplicate detection utilities."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Dict, Optional, Tuple

import pandas as pd
from rapidfuzz import fuzz


OUTPUT_COLUMNS = [
    "name",
    "title",
    "company",
    "email",
    "phone",
    "city",
    "country",
    "url",
    "platform",
    "source",
    "notes",
    "scrape_date",
]


def normalize_email(email: Optional[str]) -> Optional[str]:
    return email.lower().strip() if email else None


def normalize_phone(phone: Optional[str], region: str = "id") -> Optional[str]:
    if not phone:
        return None
    digits = re.sub(r"[^0-9+]", "", phone)
    if region == "id":
        if digits.startswith("+62"):
            digits = "0" + digits[3:]
        if digits.startswith("62"):
            digits = "0" + digits[2:]
    return digits


def normalize_record(record: Dict, dedupe_cfg: Dict) -> Dict:
    normalized = {key: record.get(key) for key in OUTPUT_COLUMNS}
    normalized["email"] = normalize_email(record.get("email"))
    normalized["phone"] = normalize_phone(record.get("phone"), dedupe_cfg.get("phone_normalization", "id"))
    normalized["name"] = (record.get("name") or "").strip()
    normalized["company"] = (record.get("company") or "").strip()
    normalized["title"] = (record.get("title") or "").strip()
    normalized["city"] = (record.get("city") or "").strip() or None
    normalized["country"] = (record.get("country") or "").strip() or None
    normalized["platform"] = record.get("platform") or "unknown"
    normalized["source"] = record.get("source") or record.get("url")
    normalized["notes"] = record.get("notes")
    normalized["scrape_date"] = record.get("scrape_date") or datetime.utcnow().date().isoformat()
    return normalized


def is_duplicate(
    record: Dict,
    company_db: pd.DataFrame,
    rules: Dict,
) -> Tuple[bool, Optional[Dict]]:
    """Return True if record is duplicate based on rules."""
    if company_db.empty:
        return False, None

    email = record.get("email")
    phone = record.get("phone")
    threshold = rules.get("fuzzy_threshold", 90)

    if email and "email" in company_db.columns:
        email_matches = company_db[company_db["email"].fillna("").str.lower() == email]
        if not email_matches.empty:
            logging.debug("Exact email duplicate found for %s", email)
            return True, email_matches.iloc[0].to_dict()

    if phone and "phone" in company_db.columns:
        phone_matches = company_db[company_db["phone"].fillna("") == phone]
        if not phone_matches.empty:
            logging.debug("Exact phone duplicate found for %s", phone)
            return True, phone_matches.iloc[0].to_dict()

    name = record.get("name")
    company = record.get("company")
    if not name or not company:
        return False, None

    best_score = 0
    best_match: Optional[Dict] = None
    for _, row in company_db.iterrows():
        row_name = row.get("name") or ""
        row_company = row.get("company") or ""
        score = fuzz.token_sort_ratio(f"{name} {company}", f"{row_name} {row_company}")
        if score > best_score:
            best_score = score
            best_match = row.to_dict()

    if best_score >= threshold:
        logging.debug("Fuzzy duplicate detected (score=%s) for %s", best_score, name)
        return True, best_match

    return False, None
