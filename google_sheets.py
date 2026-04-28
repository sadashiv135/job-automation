"""
Google Sheets logging — replaces jobs.xlsx for cloud storage.
Falls back gracefully when env vars are missing.
"""

import json
import os
from datetime import datetime
from pathlib import Path

GOOGLE_SHEET_ID      = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")

HEADERS = [
    "Date",
    "Job Title",
    "Company",
    "Location",
    "Experience Level",
    "Visa Filter",
    "Salary",
    "Match Score",
    "Job URL",
    "Resume File",
    "Cover Letter File",
    "Application Status",
    "Match Reason",
]

_AUTO_STATUSES = {"To Apply", "Skipped (low match)", "Skipped (citizenship)"}

# Column positions (1-indexed)
COL_DATE    = 1
COL_TITLE   = 2
COL_COMPANY = 3
COL_URL     = 9
COL_STATUS  = 12
COL_SCORE   = 8


def _get_client():
    """Return an authenticated gspread client using service account JSON from env."""
    import gspread
    from google.oauth2.service_account import Credentials

    if not GOOGLE_CREDENTIALS_JSON:
        raise EnvironmentError("GOOGLE_CREDENTIALS_JSON env var is not set.")
    if not GOOGLE_SHEET_ID:
        raise EnvironmentError("GOOGLE_SHEET_ID env var is not set.")

    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    scopes = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds)


def _get_worksheet():
    """Open the spreadsheet and return the first sheet."""
    client = _get_client()
    sheet  = client.open_by_key(GOOGLE_SHEET_ID)
    return sheet.get_worksheet(0)


def _ensure_headers(ws) -> None:
    """Write header row if the sheet is empty."""
    first_row = ws.row_values(1)
    if not first_row:
        ws.append_row(HEADERS, value_input_option="USER_ENTERED")
        _format_headers(ws)


def _format_headers(ws) -> None:
    """Bold + dark-blue header row."""
    import gspread.utils
    sheet = ws.spreadsheet
    requests = [{
        "repeatCell": {
            "range": {
                "sheetId": ws.id,
                "startRowIndex": 0,
                "endRowIndex": 1,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": {"red": 0.122, "green": 0.306, "blue": 0.475},
                    "textFormat": {
                        "foregroundColor": {"red": 1, "green": 1, "blue": 1},
                        "bold": True,
                    },
                    "horizontalAlignment": "CENTER",
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)",
        }
    }]
    sheet.batch_update({"requests": requests})


def _find_existing_row(ws, job: dict, url: str) -> int | None:
    """
    Return 1-based row index if the job already exists, else None.
    Matches on Job URL first, then (Company + Job Title).
    """
    all_values = ws.get_all_values()
    if len(all_values) <= 1:
        return None

    url_lower   = (url or "").lower()
    title_lower = job.get("title", "").lower()
    company_lower = job.get("company", "").lower()

    for i, row in enumerate(all_values[1:], start=2):
        row_url     = (row[COL_URL - 1] if len(row) >= COL_URL else "").lower()
        row_title   = (row[COL_TITLE - 1] if len(row) >= COL_TITLE else "").lower()
        row_company = (row[COL_COMPANY - 1] if len(row) >= COL_COMPANY else "").lower()

        if url_lower and url_lower != "n/a" and url_lower in row_url:
            return i
        if title_lower and company_lower and title_lower == row_title and company_lower == row_company:
            return i

    return None


def _score_color(score: int) -> dict:
    if score >= 80:
        return {"red": 0.776, "green": 0.937, "blue": 0.808}  # green
    if score >= 60:
        return {"red": 1.0,   "green": 0.922, "blue": 0.612}  # yellow
    return     {"red": 1.0,   "green": 0.780, "blue": 0.808}  # red


def _apply_score_color(ws, row_num: int, score: int) -> None:
    sheet = ws.spreadsheet
    color = _score_color(score)
    requests = [{
        "repeatCell": {
            "range": {
                "sheetId":       ws.id,
                "startRowIndex": row_num - 1,
                "endRowIndex":   row_num,
                "startColumnIndex": COL_SCORE - 1,
                "endColumnIndex":   COL_SCORE,
            },
            "cell": {
                "userEnteredFormat": {
                    "backgroundColor": color,
                    "textFormat": {"bold": True},
                }
            },
            "fields": "userEnteredFormat(backgroundColor,textFormat)",
        }
    }]
    sheet.batch_update({"requests": requests})


def _build_row(job: dict, score: int, resume_path, cover_letter_path: Path,
               url: str, status: str, reason: str) -> list:
    hyperlink = f'=HYPERLINK("{url}", "Apply Here")' if url and url != "N/A" else "N/A"
    return [
        datetime.now().strftime("%Y-%m-%d"),
        job.get("title", "N/A"),
        job.get("company", "N/A"),
        job.get("location", "N/A"),
        job.get("experience_level", "Entry Level"),
        job.get("visa_filter", "OK"),
        job.get("salary", "Not disclosed"),
        score,
        hyperlink,
        str(resume_path) if resume_path else "N/A",
        str(cover_letter_path) if cover_letter_path else "N/A",
        status,
        reason,
    ]


def log_job_to_sheets(
    job: dict,
    score: int,
    resume_path,
    cover_letter_path,
    status: str = "To Apply",
    reason: str = "",
) -> None:
    """Upsert job entry into Google Sheets. Raises on any failure."""
    ws  = _get_worksheet()
    _ensure_headers(ws)

    url      = job.get("url", "N/A") or "N/A"
    row_data = _build_row(job, score, resume_path, cover_letter_path, url, status, reason)

    existing_row = _find_existing_row(ws, job, url)

    if existing_row:
        all_vals = ws.get_all_values()
        current_status = all_vals[existing_row - 1][COL_STATUS - 1] if len(all_vals) >= existing_row else ""
        final_status   = status if current_status in _AUTO_STATUSES else current_status
        row_data[COL_STATUS - 1] = final_status
        # Update entire row by column range
        col_end = len(HEADERS)
        ws.update(f"A{existing_row}:{chr(64 + col_end)}{existing_row}",
                  [row_data], value_input_option="USER_ENTERED")
        print(f"[sheets] Updated row {existing_row} — {job.get('title')} @ {job.get('company')}")
    else:
        ws.append_row(row_data, value_input_option="USER_ENTERED")
        new_row = len(ws.get_all_values())
        print(f"[sheets] Appended row {new_row}  — {job.get('title')} @ {job.get('company')}")
        existing_row = new_row

    _apply_score_color(ws, existing_row, score)


def test_connection() -> bool:
    """Quick connectivity check — returns True if Sheets is reachable."""
    try:
        ws = _get_worksheet()
        _ensure_headers(ws)
        title = ws.spreadsheet.title
        print(f"[sheets] Connection OK — spreadsheet: '{title}'")
        return True
    except Exception as e:
        print(f"[sheets] Connection FAILED: {e}")
        return False
