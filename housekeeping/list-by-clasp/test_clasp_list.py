import argparse
import re
import sys
from pathlib import Path

# Directory constants
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = SCRIPT_DIR.parent.parent / "projects"


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


def test_clasp_list():
    parser = argparse.ArgumentParser(description="Verify local project directories against a clasp list backup.")
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

    print(f"Checking projects based on: {latest_file.name}")
    print(f"Search directory:          {target_dir}")
    print("-" * 50)

    projects = extract_projects(latest_file)
    if not projects:
        print("No projects found in the latest backup file.")
        return 0

    if not PROJECTS_DIR.exists():
        print(f"Warning: projects/ directory not found at {PROJECTS_DIR}", file=sys.stderr)
    
    found_count = 0
    missing_projects = []

    for p in projects:
        project_path = PROJECTS_DIR / p["id"]
        if project_path.exists() and project_path.is_dir():
            found_count += 1
        else:
            missing_projects.append(p)

    # Output Results
    print(f"Total projects in list: {len(projects)}")
    print(f"Verified (exists):      {found_count}")
    print(f"Missing (no directory): {len(missing_projects)}")
    
    if missing_projects:
        print("\nMissing projects:")
        for p in missing_projects:
            print(f"  - {p['name']} ({p['id']})")
            
    # Extra check: Are there directories in projects/ that aren't in the list?
    if PROJECTS_DIR.exists():
        local_dirs = {d.name for d in PROJECTS_DIR.iterdir() if d.is_dir()}
        clasp_ids = {p["id"] for p in projects}
        # Generic exclusion list
        exclude = {"__pycache__", ".git", ".github", ".vscode", "housekeeping", "projects", "node_modules"}
        extra_dirs = local_dirs - clasp_ids - exclude
        
        if extra_dirs:
            print(f"\nExtra directories in projects/ (not in clasp list): {len(extra_dirs)}")

    return 0 if not missing_projects else 1


if __name__ == "__main__":
    sys.exit(test_clasp_list())
