"""
Google Sheets logging — replaces jobs.xlsx for cloud storage.
Falls back gracefully when env vars are missing.
"""

import json
import os
from datetime import datetime
import pytz
from pathlib import Path

GOOGLE_SHEET_ID         = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")

_central = pytz.timezone('US/Central')

HEADERS = [
    "First Seen",          # A  1
    "Last Updated",        # B  2
    "Job Title",           # C  3
    "Company",             # D  4
    "Location",            # E  5
    "Experience Level",    # F  6
    "Visa Filter",         # G  7
    "Salary",              # H  8
    "Match Score",         # I  9
    "Apply URL",           # J  10
    "Resume Link",         # K  11
    "Cover Letter Link",   # L  12
    "Application Status",  # M  13
    "Match Reason",        # N  14
]

_AUTO_STATUSES = {"To Apply", "Skipped (low match)", "Skipped (citizenship)"}

# Column positions (1-indexed)
COL_FIRST_SEEN    = 1   # A
COL_LAST_UPDATED  = 2   # B
COL_TITLE         = 3   # C
COL_COMPANY       = 4   # D
COL_URL           = 10  # J (Apply URL)
COL_STATUS        = 13  # M
COL_SCORE         = 9   # I


def _now_cdt() -> str:
    return datetime.now(_central).strftime('%Y-%m-%d %H:%M CDT')


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
    """Write header row if absent or outdated."""
    first_row = ws.row_values(1)
    if first_row != HEADERS:
        ws.update("A1", [HEADERS], value_input_option="USER_ENTERED")
        _format_headers(ws)


def _format_headers(ws) -> None:
    """Bold + dark-blue header row."""
    sheet    = ws.spreadsheet
    requests = [{
        "repeatCell": {
            "range": {
                "sheetId":        ws.id,
                "startRowIndex":  0,
                "endRowIndex":    1,
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
    Matches on Apply URL (col J) first, then Company + Job Title (cols D + C).
    """
    all_values = ws.get_all_values()
    if len(all_values) <= 1:
        return None

    url_lower     = (url or "").lower()
    title_lower   = job.get("title", "").lower()
    company_lower = job.get("company", "").lower()

    for i, row in enumerate(all_values[1:], start=2):
        row_url     = (row[COL_URL     - 1] if len(row) >= COL_URL     else "").lower()
        row_title   = (row[COL_TITLE   - 1] if len(row) >= COL_TITLE   else "").lower()
        row_company = (row[COL_COMPANY - 1] if len(row) >= COL_COMPANY else "").lower()

        if url_lower and url_lower != "n/a" and url_lower in row_url:
            return i
        if title_lower and company_lower and title_lower == row_title and company_lower == row_company:
            return i

    return None


def _score_color(score: int) -> dict:
    if score >= 80:
        return {"red": 0.776, "green": 0.937, "blue": 0.808}   # green
    if score >= 60:
        return {"red": 1.0,   "green": 0.922, "blue": 0.612}   # yellow
    return     {"red": 1.0,   "green": 0.780, "blue": 0.808}   # red


def _apply_score_color(ws, row_num: int, score: int) -> None:
    sheet    = ws.spreadsheet
    color    = _score_color(score)
    requests = [{
        "repeatCell": {
            "range": {
                "sheetId":          ws.id,
                "startRowIndex":    row_num - 1,
                "endRowIndex":      row_num,
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


def _build_row(job: dict, score: int, resume_url: str, cover_letter_url: str,
               url: str, status: str, reason: str, first_seen: str = None) -> list:
    hyperlink = f'=HYPERLINK("{url}", "Apply Here")' if url and url != "N/A" else "N/A"
    now_str   = _now_cdt()
    return [
        first_seen or now_str,                        # A: First Seen
        now_str,                                       # B: Last Updated
        job.get("title", "N/A"),                       # C: Job Title
        job.get("company", "N/A"),                     # D: Company
        job.get("location", "N/A"),                    # E: Location
        job.get("experience_level", "Entry Level"),    # F: Experience Level
        job.get("visa_filter", "OK"),                  # G: Visa Filter
        job.get("salary", "Not disclosed"),            # H: Salary
        score,                                         # I: Match Score
        hyperlink,                                     # J: Apply URL
        resume_url or "N/A",                           # K: Resume Link
        cover_letter_url or "N/A",                     # L: Cover Letter Link
        status,                                        # M: Application Status
        reason,                                        # N: Match Reason
    ]


def log_job_to_sheets(
    job: dict,
    score: int,
    resume_url: str,
    cover_letter_url: str,
    status: str = "To Apply",
    reason: str = "",
) -> None:
    """Upsert job entry into Google Sheets. Raises on any failure."""
    ws  = _get_worksheet()
    _ensure_headers(ws)

    url          = job.get("url", "N/A") or "N/A"
    existing_row = _find_existing_row(ws, job, url)

    if existing_row:
        all_vals      = ws.get_all_values()
        existing_data = all_vals[existing_row - 1]

        # Preserve First Seen — never overwrite
        first_seen = (
            existing_data[COL_FIRST_SEEN - 1]
            if len(existing_data) >= COL_FIRST_SEEN else None
        )

        # Preserve Application Status if manually changed
        current_status = (
            existing_data[COL_STATUS - 1]
            if len(existing_data) >= COL_STATUS else ""
        )
        final_status = status if current_status in _AUTO_STATUSES else current_status

        row_data = _build_row(
            job, score, resume_url, cover_letter_url,
            url, final_status, reason, first_seen,
        )
        col_end = len(HEADERS)
        ws.update(
            f"A{existing_row}:{chr(64 + col_end)}{existing_row}",
            [row_data],
            value_input_option="USER_ENTERED",
        )
        print(f"[sheets] Updated row {existing_row} — {job.get('title')} @ {job.get('company')}")
    else:
        row_data = _build_row(job, score, resume_url, cover_letter_url, url, status, reason)
        ws.append_row(row_data, value_input_option="USER_ENTERED")
        new_row = len(ws.get_all_values())
        print(f"[sheets] Appended row {new_row}  — {job.get('title')} @ {job.get('company')}")
        existing_row = new_row

    _apply_score_color(ws, existing_row, score)


def test_connection() -> bool:
    """Quick connectivity check — returns True if Sheets is reachable."""
    try:
        ws    = _get_worksheet()
        _ensure_headers(ws)
        title = ws.spreadsheet.title
        print(f"[sheets] Connection OK — spreadsheet: '{title}'")
        return True
    except Exception as e:
        print(f"[sheets] Connection FAILED: {e}")
        return False
