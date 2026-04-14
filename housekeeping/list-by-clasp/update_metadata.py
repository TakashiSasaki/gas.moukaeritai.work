import argparse
import json
import re
import sys
from pathlib import Path

# Directory constants
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
PROJECTS_DIR = PROJECT_ROOT / "projects"


def find_latest_clasp_list_file(directory: Path) -> Path | None:
    """Find the most recent YYYYMMDD-HHMMSS.txt file in the given directory."""
    if not directory.exists():
        return None
        
    pattern = re.compile(r"^\d{8}-\d{6}\.txt$")
    files = [f for f in directory.iterdir() if f.is_file() and pattern.match(f.name)]

    if not files:
        return None

    # Sort lexicographically and return the latest
    files.sort(key=lambda x: x.name)
    return files[-1]


def extract_projects(file_path: Path) -> list[dict[str, str]]:
    """Extract project names and IDs from the clasp list backup file."""
    # Pattern to match: Name - https://script.google.com/d/ID/edit
    parser_regex = re.compile(r"^(?P<name>.*?) - https://script\.google\.com/d/(?P<id>[a-zA-Z0-9_-]+)/")
    
    projects = []
    try:
        content = file_path.read_text(encoding="utf-8")
        for line in content.splitlines():
            match = parser_regex.search(line)
            if match:
                projects.append({
                    "name": match.group("name").strip(),
                    "id": match.group("id")
                })
    except Exception as e:
        print(f"Error reading file {file_path}: {e}", file=sys.stderr)
        
    return projects


def update_metadata(project_id: str, title: str) -> bool:
    """Update metadata.json for the given project ID with titleByClaspList."""
    metadata_path = PROJECTS_DIR / project_id / "metadata.json"
    
    if not metadata_path.exists():
        return False
        
    try:
        # Load existing metadata
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        
        # Update or add the property
        metadata["titleByClaspList"] = title
        
        # Save back with pretty printing
        metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8"
        )
        return True
    except Exception as e:
        print(f"Error updating {metadata_path}: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Sync project titles from clasp list backups into project metadata.json files."
    )
    parser.add_argument(
        "-d", "--dir",
        help="Directory to search for clasp list backup files. Defaults to script's directory."
    )
    
    args = parser.parse_args()
    
    target_dir = Path(args.dir) if args.dir else SCRIPT_DIR
    latest_file = find_latest_clasp_list_file(target_dir)
    
    if not latest_file:
        print(f"No clasp list backup files found in {target_dir}", file=sys.stderr)
        return 1

    print(f"Processing updates based on: {latest_file.name}")
    print("-" * 50)

    projects = extract_projects(latest_file)
    if not projects:
        print("No projects found in the latest backup file.")
        return 0

    updated_count = 0
    missing_count = 0
    
    for p in projects:
        success = update_metadata(p["id"], p["name"])
        if success:
            updated_count += 1
        else:
            missing_count += 1
            # Optional: print(f"Skipped: {p['id']} (metadata.json not found)")

    print(f"Total projects in list: {len(projects)}")
    print(f"Successfully updated:   {updated_count}")
    print(f"Skipped (missing file): {missing_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
