# ---
# dependencies = ["requests"]
# ---

import datetime
import json
import os
import re
import sys
from pathlib import Path

# Try to use requests, managed by uv run
try:
    import requests
except ImportError:
    print("Error: 'requests' library not found. Please run with 'uv run --with requests ...'", file=sys.stderr)
    sys.exit(1)

# Directory constants
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent


def get_credentials():
    """Read tokens from ~/.clasprc.json"""
    rc_path = Path.home() / ".clasprc.json"
    if not rc_path.exists():
        print(f"Error: Credentials file not found at {rc_path}", file=sys.stderr)
        return None

    try:
        data = json.loads(rc_path.read_text(encoding="utf-8"))
        # Support both 'token' and 'tokens' structure
        if "tokens" in data and "default" in data["tokens"]:
            return data["tokens"]["default"]
        elif "token" in data:
            return data["token"]
        return None
    except Exception as e:
        print(f"Error reading credentials: {e}", file=sys.stderr)
        return None


def refresh_access_token(creds):
    """Get a fresh access token using the refresh token."""
    print("Refreshing access token...")
    payload = {
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": creds["refresh_token"],
        "grant_type": "refresh_token",
    }
    
    response = requests.post("https://oauth2.googleapis.com/token", data=payload)
    if response.status_code != 200:
        print(f"Error refreshing token: {response.text}", file=sys.stderr)
        return None
        
    return response.json().get("access_token")


def fetch_projects(access_token):
    """Fetch all projects using Google Drive API v3 with pagination."""
    print("Fetching projects from Google Drive API...")
    url = "https://www.googleapis.com/drive/v3/files"
    all_files = []
    page_token = None
    
    while True:
        params = {
            "q": "mimeType = 'application/vnd.google-apps.script' and trashed = false",
            "pageSize": 100,
            "fields": "nextPageToken, files(id, name, createdTime, modifiedTime)",
        }
        if page_token:
            params["pageToken"] = page_token
            
        headers = {"Authorization": f"Bearer {access_token}"}
        
        response = requests.get(url, params=params, headers=headers)
        if response.status_code != 200:
            print(f"Error fetching projects: {response.text}", file=sys.stderr)
            return None
            
        data = response.json()
        files = data.get("files", [])
        all_files.extend(files)
        print(f"  Fetched {len(files)} projects (Total: {len(all_files)})")
        
        page_token = data.get("nextPageToken")
        if not page_token:
            break
            
    return {"files": all_files}


def cleanup_old_files(directory: Path, keep_count: int):
    """Keep only the N latest timestamped JSON files."""
    pattern = re.compile(r"^\d{8}-\d{6}\.json$")
    files = [f for f in directory.iterdir() if f.is_file() and pattern.match(f.name)]
    
    if len(files) <= keep_count:
        return
        
    # Sort lexicographically (names are timestamped)
    files.sort(key=lambda x: x.name)
    
    to_delete = files[: len(files) - keep_count]
    for f in to_delete:
        print(f"Deleting old backup: {f.name}")
        f.unlink()


def main():
    creds = get_credentials()
    if not creds:
        return 1
        
    access_token = refresh_access_token(creds)
    if not access_token:
        return 1
        
    data = fetch_projects(access_token)
    if not data:
        return 1
        
    # Save to timestamped file
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    output_file = SCRIPT_DIR / f"{timestamp}.json"
    
    output_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Successfully saved data to {output_file.name}")
    
    # Retention
    cleanup_old_files(SCRIPT_DIR, 5)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
