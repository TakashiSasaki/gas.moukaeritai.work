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

# Constants
SCRIPT_DIR = Path(__file__).resolve().parent
URL = "https://script.google.com/macros/s/AKfycbz0a4RTpHE5Bxn3AeHWEAD7QHreptLqpa3HLxatARciZwYLJk8jd494G3Dd5_PF3WsJFg/exec?json"

def fetch_finder_data():
    """Fetch JSON data from the GAS Web App URL."""
    print(f"Fetching data from: {URL}")
    try:
        # requests handles redirects automatically
        response = requests.get(URL, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data: {e}", file=sys.stderr)
        return None

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
    data = fetch_finder_data()
    if data is None:
        sys.exit(1)
        
    # Save to timestamped file
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    output_file = SCRIPT_DIR / f"{timestamp}.json"
    
    try:
        output_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Successfully saved data to {output_file.name}")
    except Exception as e:
        print(f"Error saving data: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Retention
    cleanup_old_files(SCRIPT_DIR, 5)

if __name__ == "__main__":
    main()
