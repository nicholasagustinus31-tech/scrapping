"""Unit tests for deduplication logic."""

import pandas as pd
from utils.de_dupe import is_duplicate, normalize_record


def test_exact_email_duplicate():
    company_db = pd.DataFrame([
        {"name": "John Doe", "company": "Acme", "email": "john@example.com", "phone": None},
    ])
    record = {
        "name": "John Doe",
        "company": "Acme",
        "email": "JOHN@example.com",
    }
    normalized = normalize_record(record, {"phone_normalization": "id"})
    duplicate, _ = is_duplicate(normalized, company_db, {"fuzzy_threshold": 90})
    assert duplicate


def test_exact_phone_duplicate():
    company_db = pd.DataFrame([
        {"name": "Jane", "company": "Builders", "phone": "08123456789"},
    ])
    record = {
        "name": "Jane Smith",
        "company": "Builders",
        "phone": "+62 812-3456-789",
    }
    normalized = normalize_record(record, {"phone_normalization": "id"})
    duplicate, _ = is_duplicate(normalized, company_db, {"fuzzy_threshold": 90})
    assert duplicate


def test_fuzzy_name_company_duplicate():
    company_db = pd.DataFrame([
        {"name": "Andi Wijaya", "company": "Interior Bandung"},
    ])
    record = {
        "name": "Andi Wijaya",
        "company": "InteriorBandung",
    }
    normalized = normalize_record(record, {"phone_normalization": "id"})
    duplicate, _ = is_duplicate(normalized, company_db, {"fuzzy_threshold": 85})
    assert duplicate
