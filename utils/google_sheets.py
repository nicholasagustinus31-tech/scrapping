"""Google Sheets helper utilities."""

from __future__ import annotations

import logging
from typing import Dict, Iterable, List, Optional

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build


SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


class GoogleSheetsClient:
    """Wrapper around Google Sheets API service."""

    def __init__(self, credentials_path: str):
        if not credentials_path:
            raise ValueError("Google Sheets credentials path is required")
        self.credentials_path = credentials_path
        self.service = self._build_service()

    def _build_service(self):
        credentials = service_account.Credentials.from_service_account_file(
            self.credentials_path, scopes=SCOPES
        )
        return build("sheets", "v4", credentials=credentials)

    def read_sheet(self, sheet_id: str, range_name: Optional[str]) -> pd.DataFrame:
        if not range_name:
            raise ValueError("range_name is required to read Google Sheet")
        sheet = self.service.spreadsheets()
        result = sheet.values().get(spreadsheetId=sheet_id, range=range_name).execute()
        values = result.get("values", [])
        if not values:
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
            ])
        header = values[0]
        rows = values[1:]
        return pd.DataFrame(rows, columns=header)


def _prepare_rows(records: Iterable[Dict]) -> List[List[Optional[str]]]:
    rows: List[List[Optional[str]]] = []
    for record in records:
        rows.append(
            [
                record.get("name"),
                record.get("title"),
                record.get("company"),
                record.get("email"),
                record.get("phone"),
                record.get("city"),
                record.get("country"),
                record.get("source") or record.get("url"),
                record.get("platform"),
                record.get("scrape_date"),
                record.get("notes"),
            ]
        )
    return rows


def write_to_google_sheet(
    sheets_client: GoogleSheetsClient,
    sheet_id: str,
    range_name: str,
    records: Iterable[Dict],
) -> None:
    """Append records to Google Sheet."""
    if not sheet_id or not range_name:
        raise ValueError("sheet_id and range_name are required for writing")

    rows = _prepare_rows(records)
    body = {"values": rows}
    logging.info("Appending %d rows to Google Sheet", len(rows))
    sheets_client.service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        body=body,
    ).execute()
