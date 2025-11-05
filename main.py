"""Entry point for lead scraping and enrichment pipeline."""

from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
import time
from datetime import datetime
from typing import Dict, Iterable, List, Optional

import pandas as pd
from dotenv import load_dotenv

from scrapers import scrape_social
from scrapers.google_search import search_google
from utils.de_dupe import OUTPUT_COLUMNS, is_duplicate, normalize_record
from utils.google_sheets import GoogleSheetsClient, write_to_google_sheet


DEFAULT_CONFIG_PATH = "config.json"


def load_config(path: str) -> Dict:
    """Load configuration from JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_company_db(path_or_sheet_id: str, cfg: Dict) -> pd.DataFrame:
    """Load the company database from CSV or Google Sheets."""
    column_aliases = {
        "Nama": "name",
        "Jabatan": "title",
        "Perusahaan": "company",
        "Email": "email",
        "Telepon": "phone",
        "Kota": "city",
        "Negara": "country",
        "URL Sumber": "source",
        "Platform": "platform",
        "Tanggal Scrape": "scrape_date",
        "Catatan": "notes",
    }
    db_type = cfg.get("company_db", {}).get("type", "csv")
    if db_type == "csv":
        path = cfg.get("company_db", {}).get("path")
        if not path or not os.path.exists(path):
            logging.warning("Company database CSV not found. Starting with empty database.")
            return pd.DataFrame(columns=[
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
            ])
        df = pd.read_csv(path)
        df.rename(columns=column_aliases, inplace=True)
        for column in OUTPUT_COLUMNS:
            if column not in df.columns:
                df[column] = None
        return df

    if db_type == "google_sheet":
        sheet_id = cfg.get("company_db", {}).get("sheet_id") or path_or_sheet_id
        range_name = cfg.get("company_db", {}).get("range")
        credentials_path = cfg.get("google_sheets", {}).get("credentials_path")
        client = GoogleSheetsClient(credentials_path)
        df = client.read_sheet(sheet_id, range_name)
        df.rename(columns=column_aliases, inplace=True)
        for column in OUTPUT_COLUMNS:
            if column not in df.columns:
                df[column] = None
        return df

    raise ValueError(f"Unsupported company_db type: {db_type}")


def setup_logging(cfg: Dict) -> None:
    log_path = cfg.get("logging", {}).get("errors_path", "logs/errors.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path),
        ],
    )


def random_delay(cfg: Dict) -> None:
    rate_cfg = cfg.get("rate_limit", {})
    min_delay = rate_cfg.get("min_delay_seconds", 1)
    max_delay = rate_cfg.get("max_delay_seconds", 3)
    delay = random.uniform(min_delay, max_delay)
    logging.debug("Sleeping for %.2f seconds to respect rate limits", delay)
    time.sleep(delay)


def apply_rate_limit(cfg: Dict) -> None:
    rate_cfg = cfg.get("rate_limit", {})
    rpm = rate_cfg.get("requests_per_minute")
    if rpm:
        delay = 60 / max(rpm, 1)
        logging.debug("Applying rate limit delay of %.2f seconds", delay)
        time.sleep(delay)


def process_records(
    records: List[Dict],
    company_db: pd.DataFrame,
    cfg: Dict,
    dedupe_rules: Dict,
    new_records: List[Dict],
    duplicate_records: List[Dict],
) -> pd.DataFrame:
    for record in records:
        normalized = normalize_record(record, cfg.get("dedupe", {}))
        duplicate, match = is_duplicate(normalized, company_db, dedupe_rules)
        if duplicate:
            logging.info("Duplicate found for %s", normalized.get("name"))
            duplicate_entry = {**normalized, "matched": match}
            duplicate_records.append(duplicate_entry)
            continue

        new_records.append(normalized)
        company_db = pd.concat([company_db, pd.DataFrame([normalized])], ignore_index=True)

    return company_db


def run_batch(queries_list: Iterable[str], cfg: Dict) -> None:
    queries = list(queries_list)
    logging.info("Starting batch run with %d queries", len(queries))
    company_db = load_company_db("", cfg)
    sheet_cfg = cfg.get("google_sheets", {})
    duplicates_path = cfg.get("logging", {}).get("duplicates_path", "logs/duplicates.csv")
    run_log_path = cfg.get("logging", {}).get("run_summary_path", "logs/run_log.csv")
    if duplicates_path:
        os.makedirs(os.path.dirname(duplicates_path), exist_ok=True)
    if run_log_path:
        os.makedirs(os.path.dirname(run_log_path), exist_ok=True)

    credentials_path = sheet_cfg.get("credentials_path")
    sheet_id = sheet_cfg.get("sheet_id")
    write_range = sheet_cfg.get("write_range")

    dedupe_rules = cfg.get("dedupe", {})

    if not credentials_path:
        raise ValueError("Google Sheets credentials_path must be provided in config")

    sheets_client = GoogleSheetsClient(credentials_path)

    total_new = 0
    total_duplicate = 0
    errors: List[str] = []
    new_records: List[Dict] = []
    duplicate_records: List[Dict] = []

    for query in queries:
        logging.info("Processing query: %s", query)
        try:
            results = search_google(
                query=query,
                max_results=cfg.get("search", {}).get("max_results_per_query", 10),
                cfg=cfg,
            )
            apply_rate_limit(cfg)
            random_delay(cfg)
        except Exception as exc:  # pylint: disable=broad-except
            logging.exception("Error during Google search for %s", query)
            errors.append(f"Google search error for {query}: {exc}")
            continue

        company_db = process_records(
            records=results,
            company_db=company_db,
            cfg=cfg,
            dedupe_rules=dedupe_rules,
            new_records=new_records,
            duplicate_records=duplicate_records,
        )

        for platform_name in ("linkedin", "instagram"):
            try:
                social_results = scrape_social(
                    platform=platform_name,
                    query_or_profile_id=query,
                    max_results=cfg.get("search", {}).get("max_results_per_query", 10),
                    cfg=cfg,
                )
            except ValueError as missing_token:
                logging.debug("Skipping %s scrape: %s", platform_name, missing_token)
                continue
            except Exception as exc:  # pylint: disable=broad-except
                logging.exception("Error scraping %s for %s", platform_name, query)
                errors.append(f"{platform_name} error for {query}: {exc}")
                continue

            apply_rate_limit(cfg)
            random_delay(cfg)

            company_db = process_records(
                records=social_results,
                company_db=company_db,
                cfg=cfg,
                dedupe_rules=dedupe_rules,
                new_records=new_records,
                duplicate_records=duplicate_records,
            )

    if new_records:
        if not sheet_id or not write_range:
            raise ValueError("sheet_id and write_range must be configured to write leads")
        write_to_google_sheet(
            sheets_client=sheets_client,
            sheet_id=sheet_id,
            range_name=write_range,
            records=new_records,
        )
        total_new = len(new_records)

    total_duplicate = len(duplicate_records)

    if duplicate_records:
        duplicates_df = pd.DataFrame(duplicate_records)
        if os.path.exists(duplicates_path):
            duplicates_df.to_csv(duplicates_path, mode="a", header=False, index=False)
        else:
            duplicates_df.to_csv(duplicates_path, index=False)

    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "new_records": total_new,
        "duplicates": total_duplicate,
        "errors": len(errors),
    }
    logging.info("Run summary: %s", summary)

    summary_df = pd.DataFrame([summary])
    if os.path.exists(run_log_path):
        summary_df.to_csv(run_log_path, mode="a", header=False, index=False)
    else:
        summary_df.to_csv(run_log_path, index=False)

    if errors:
        with open(cfg.get("logging", {}).get("errors_path", "logs/errors.log"), "a", encoding="utf-8") as err_file:
            for err in errors:
                err_file.write(f"{datetime.utcnow().isoformat()} - {err}\n")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lead scraping automation tool")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Path to config JSON")
    parser.add_argument("--queries", action="append", default=[], help="Query to run (can be repeated)")
    parser.add_argument("--queries-file", help="Path to file with queries (one per line)")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    load_dotenv()
    cfg = load_config(args.config)
    setup_logging(cfg)

    queries: List[str] = list(args.queries)
    if args.queries_file:
        with open(args.queries_file, "r", encoding="utf-8") as f:
            queries.extend([line.strip() for line in f if line.strip()])

    if not queries:
        logging.error("No queries provided. Use --queries or --queries-file.")
        sys.exit(1)

    run_batch(queries, cfg)


if __name__ == "__main__":
    main()
