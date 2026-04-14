import argparse
import json
import os
import re
import sys
from pathlib import Path

def get_latest_backup_file(directory: Path):
    """Find the latest YYYYMMDD-HHMMSS.json file in the given directory."""
    pattern = re.compile(r"^\d{8}-\d{6}\.json$")
    backups = [f for f in directory.iterdir() if f.is_file() and pattern.match(f.name)]
    
    if not backups:
        return None
    
    # Sort by filename (timestamped) and return the last one
    backups.sort(key=lambda x: x.name)
    return backups[-1]

def update_metadata(backup_file: Path, projects_dir: Path):
    """Update metadata.json for each project found in the backup file."""
    print(f"Reading backup from: {backup_file}")
    
    try:
        with open(backup_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading backup file: {e}", file=sys.stderr)
        return

    files_list = data.get("files", [])
    if not files_list:
        print("No project files found in the backup data.")
        return

    updated_count = 0
    skipped_count = 0

    for item in files_list:
        script_id = item.get("id")
        name = item.get("name")
        created_time = item.get("createdTime")
        modified_time = item.get("modifiedTime")
        
        if not script_id or not name:
            continue
            
        # Locate project directory
        project_path = projects_dir / script_id
        meta_file = project_path / "metadata.json"
        
        if meta_file.exists():
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    meta_data = json.load(f)
                
                # Update main properties using Drive API names
                meta_data["name"] = name
                if created_time:
                    meta_data["createdTime"] = created_time
                if modified_time:
                    meta_data["modifiedTime"] = modified_time
                
                # Cleanup redundant properties
                meta_data.pop("titleByClaspList", None)
                meta_data.pop("titleByDriveApi", None)
                
                with open(meta_file, "w", encoding="utf-8") as f:
                    json.dump(meta_data, f, indent=2, ensure_ascii=False)
                
                print(f"  Updated & Cleaned: {script_id} -> {name}")
                updated_count += 1
            except Exception as e:
                print(f"  Error updating {script_id}: {e}", file=sys.stderr)
        else:
            skipped_count += 1

    print(f"\nUpdate Summary:")
    print(f"  Total projects in backup: {len(files_list)}")
    print(f"  Successfully updated:     {updated_count}")
    print(f"  Skipped (not in repo):    {skipped_count}")

def main():
    parser = argparse.ArgumentParser(description="Update project metadata titles from Drive API JSON backups.")
    parser.add_argument("-d", "--dir", type=str, help="Directory containing JSON backup files.")
    parser.add_argument("-p", "--projects", type=str, help="Path to projects directory.")
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).resolve().parent
    backup_dir = Path(args.dir) if args.dir else script_dir
    projects_root = Path(args.projects) if args.projects else script_dir.parent.parent / "projects"
    
    backup_file = get_latest_backup_file(backup_dir)
    
    if not backup_file:
        print(f"No backup files found in {backup_dir}")
        sys.exit(1)
        
    update_metadata(backup_file, projects_root)

if __name__ == "__main__":
    main()
