# Lead Scraping Automation

## Overview
This project automates the discovery of potential leads from Google Search and social media platforms, deduplicates them against an existing company database, and appends unique leads directly into Google Sheets. The system respects rate limits, captures structured logs, and provides a configurable pipeline for managing enrichment runs.

## Features
- Configurable Google Custom Search API integration with Selenium fallback for compliant scraping.
- Official API clients for LinkedIn and Instagram Graph (requires valid access tokens).
- Automatic deduplication using email, phone, and fuzzy name/company matching powered by RapidFuzz.
- Direct Google Sheets write support via service account credentials.
- CSV or Google Sheet source for existing company database.
- Structured logging including duplicate and error tracking with appendable CSV/LOG files.
- Batch execution with randomized delays to respect rate limits.

## Project Structure
```
config.example.json      # Sample configuration file
main.py                  # CLI entry point
scrapers/google_search.py
scrapers/linkedin_api.py
scrapers/instagram_api.py
utils/de_dupe.py
utils/google_sheets.py
requirements.txt
tests/test_de_dupe.py
```

## Installation
1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd scrapping
   ```
2. **Create and activate a virtual environment (optional but recommended)**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration
1. Copy `config.example.json` to `config.json` and update the values:
   - `google_sheets.credentials_path`: Path to your Google service account credentials.
   - `google_sheets.sheet_id` / `write_range`: Target Google Sheet and tab range for output.
   - `company_db`: Configure CSV path or Google Sheet source for existing leads.
   - `search`: Provide Google Custom Search API key and CX ID if using the API.
   - `social`: Provide LinkedIn, Instagram Graph, and Twitter (X) tokens as available.
   - `dedupe`: Adjust fuzzy threshold and phone normalization behaviour.
   - `rate_limit`: Tune delays to comply with API/service terms.
2. Ensure Google Cloud project is configured for Sheets API access and download `credentials.json` for a service account with edit permissions on the target sheet.

## Usage
Run ad-hoc queries from the CLI:
```bash
python main.py --queries "Toko furniture Tangerang" --queries "arsitek interior Jakarta"
```

Or execute a batch from a file (one query per line):
```bash
python main.py --queries-file queries.txt
```

### Output Columns
Results appended to Google Sheets follow this order:
1. Nama
2. Jabatan
3. Perusahaan
4. Email
5. Telepon
6. Kota
7. Negara
8. URL Sumber
9. Platform
10. Tanggal Scrape
11. Catatan

## Logging
- Duplicate leads are appended to `logs/duplicates.csv` with the matched record included.
- Errors are written to `logs/errors.log`.
- Each run writes a summary row to `logs/run_log.csv` with counts for new records, duplicates, and errors.

## Testing
Run the included unit tests for deduplication:
```bash
pytest
```

## Legal & Ethical Notice
- Always review and comply with the Terms of Service for any website or API you access.
- Use official APIs wherever possible (Google Custom Search, LinkedIn, Instagram Graph, Twitter/X).
- When scraping public web pages via Selenium, respect robots.txt, use realistic user agents, and configure appropriate delays to avoid overloading services.
- Only collect and store publicly available business information (e.g., name, title, company, public email/phone, and source URL).
- Ensure compliance with relevant privacy regulations, including GDPR and Indonesia’s data protection laws. Obtain consent before processing personal data when required.

## Disclaimer
This codebase is provided for educational and compliant business-use scenarios. The maintainers are not responsible for misuse, regulatory violations, or unauthorized data collection performed with this software.
