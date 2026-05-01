"""
Google Drive integration — uploads resumes and cover letters, returns shareable URLs.
Uses the same service account credentials as Google Sheets.
"""

import json
import os
from pathlib import Path

GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON", "")

_ROOT_FOLDER   = "Job Applications"
_RESUMES_SUB   = "Resumes"
_CL_SUB        = "Cover Letters"
_OWNER_EMAIL   = "sadashivmhaskar007@gmail.com"

_drive_service = None
_folder_cache: dict[str, str] = {}


def _get_service():
    global _drive_service
    if _drive_service:
        return _drive_service

    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build

    if not GOOGLE_CREDENTIALS_JSON:
        raise EnvironmentError("GOOGLE_CREDENTIALS_JSON env var is not set.")

    creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    _drive_service = build("drive", "v3", credentials=creds)
    return _drive_service


def _get_or_create_folder(name: str, parent_id: str | None = None) -> str:
    """Return folder ID, creating the folder if it does not exist."""
    cache_key = f"{parent_id}:{name}"
    if cache_key in _folder_cache:
        return _folder_cache[cache_key]

    svc   = _get_service()
    query = (
        f"name='{name}' "
        "and mimeType='application/vnd.google-apps.folder' "
        "and trashed=false"
    )
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = svc.files().list(q=query, fields="files(id)").execute()
    files   = results.get("files", [])

    if files:
        folder_id = files[0]["id"]
    else:
        meta: dict = {
            "name":     name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            meta["parents"] = [parent_id]
        folder    = svc.files().create(body=meta, fields="id").execute()
        folder_id = folder["id"]
        print(f"[drive] Created folder '{name}' (id: {folder_id})")
        # Share the root folder with the owner so it appears in their Drive
        if parent_id is None:
            _share_with_user(folder_id, _OWNER_EMAIL, role="writer")

    _folder_cache[cache_key] = folder_id
    return folder_id


def _mime_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if suffix == ".pdf":
        return "application/pdf"
    return "application/octet-stream"


def _share_with_user(file_id: str, email: str, role: str = "writer") -> None:
    """Grant a specific Google account access to a file or folder."""
    _get_service().permissions().create(
        fileId=file_id,
        body={"type": "user", "role": role, "emailAddress": email},
        sendNotificationEmail=False,
    ).execute()
    print(f"[drive] Shared {file_id} with {email} as {role}")


def _make_public(file_id: str) -> None:
    """Grant anyone-with-link read access."""
    _get_service().permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()


def _upload_file(path: Path, subfolder_name: str) -> str:
    """Upload *path* into the correct subfolder; return its shareable view URL."""
    from googleapiclient.http import MediaFileUpload

    svc          = _get_service()
    root_id      = _get_or_create_folder(_ROOT_FOLDER)
    sub_id       = _get_or_create_folder(subfolder_name, root_id)
    mime         = _mime_type(path)
    media        = MediaFileUpload(str(path), mimetype=mime, resumable=False)

    # Upsert: update if file with same name already exists in this folder
    query   = f"name='{path.name}' and '{sub_id}' in parents and trashed=false"
    results = svc.files().list(q=query, fields="files(id)").execute()
    existing = results.get("files", [])

    if existing:
        file_id = existing[0]["id"]
        svc.files().update(fileId=file_id, media_body=media).execute()
        print(f"[drive] Updated  {path.name}")
    else:
        meta    = {"name": path.name, "parents": [sub_id]}
        f       = svc.files().create(body=meta, media_body=media, fields="id").execute()
        file_id = f["id"]
        print(f"[drive] Uploaded {path.name}")

    _make_public(file_id)
    url = f"https://drive.google.com/file/d/{file_id}/view"
    print(f"[drive] Share URL: {url}")
    return url


def upload_resume(path: Path) -> str:
    """Upload a tailored resume and return its shareable Drive URL."""
    return _upload_file(path, _RESUMES_SUB)


def upload_cover_letter(path: Path) -> str:
    """Upload a cover letter and return its shareable Drive URL."""
    return _upload_file(path, _CL_SUB)


def test_connection() -> bool:
    """Verify Drive access and ensure folder structure exists."""
    try:
        root_id = _get_or_create_folder(_ROOT_FOLDER)
        _get_or_create_folder(_RESUMES_SUB, root_id)
        _get_or_create_folder(_CL_SUB, root_id)
        print("[drive] Connection OK — 'Job Applications/Resumes' and 'Job Applications/Cover Letters' verified")
        return True
    except Exception as e:
        print(f"[drive] Connection FAILED: {e}")
        return False
