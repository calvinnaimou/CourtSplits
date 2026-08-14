"""Downloads the latest BigDataBall export from a Google Drive folder.

UNVERIFIED -- the Drive folder this points at doesn't exist yet (BigDataBall's
daily sync only starts once the 2026-27 season begins and you've set it up
with them). This is a best-effort scaffold based on how Drive's API
normally works, written so the rest of the pipeline (scripts/ingest_live_data.py,
already tested end-to-end) doesn't have to change once this piece is
finished. Test this file for real against the actual folder before trusting
it in the scheduled workflow -- see .github/workflows/daily-refresh.yml.

Needs two things once the season starts:
  1. A Google Cloud service account with read access to the synced Drive
     folder (share the folder with the service account's email address).
     Its JSON key goes in the GDRIVE_SERVICE_ACCOUNT_JSON env var (as a
     GitHub Actions secret, not a file -- the whole JSON key as one string).
  2. GDRIVE_FOLDER_ID -- the target folder's ID (the long string in its
     Drive URL after /folders/).

Picks the most-recently-modified file in that folder whose name contains
`name_contains` (case-insensitive) -- adjust the match if BigDataBall's
actual filenames turn out to look different than guessed here.

Not added to requirements.txt -- google-api-python-client/google-auth are
only needed for this one script, imported lazily below, so a broken/
unfinished Drive integration can never affect the running app or the rest
of the test suite (which doesn't import this file at all).
"""

import argparse
import io
import json
import os
import sys
from pathlib import Path


def _drive_service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds_json = os.environ.get("GDRIVE_SERVICE_ACCOUNT_JSON")
    if not creds_json:
        sys.exit("GDRIVE_SERVICE_ACCOUNT_JSON is not set.")
    credentials = service_account.Credentials.from_service_account_info(
        json.loads(creds_json), scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=credentials)


def fetch_latest(name_contains: str, dest: Path) -> Path:
    from googleapiclient.http import MediaIoBaseDownload

    folder_id = os.environ.get("GDRIVE_FOLDER_ID")
    if not folder_id:
        sys.exit("GDRIVE_FOLDER_ID is not set.")

    service = _drive_service()
    results = service.files().list(
        q=f"'{folder_id}' in parents and name contains '{name_contains}' and trashed = false",
        orderBy="modifiedTime desc",
        pageSize=1,
        fields="files(id, name, modifiedTime)",
    ).execute()
    files = results.get("files", [])
    if not files:
        sys.exit(f"No file matching {name_contains!r} found in Drive folder {folder_id}.")
    latest = files[0]

    dest.parent.mkdir(parents=True, exist_ok=True)
    request = service.files().get_media(fileId=latest["id"])
    with io.FileIO(dest, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

    print(f"Downloaded {latest['name']!r} (modified {latest['modifiedTime']}) -> {dest}")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("name_contains", help="Substring to match in the Drive filename, e.g. 'PLAYER'")
    parser.add_argument("dest", type=Path, help="Local path to save the downloaded file to")
    args = parser.parse_args()
    fetch_latest(args.name_contains, args.dest)


if __name__ == "__main__":
    main()
