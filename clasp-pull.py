#!/usr/bin/env python3
"""
clasp-pull.py

Iterate over all known Apps Script project directories in the repository.
For each directory containing a .clasp.json file, check if update is needed.
If needed, change into that directory and execute `clasp pull`, then fetch and save
deployments and versions.
"""
import os
import subprocess
import sys
import json
import re
import urllib.request
import urllib.error
import time

from project_paths import iter_project_dirs

def parse_deployments(raw_text):
    """
    Parse the output of `clasp deployments` into a list of dicts:
    [{"id": ..., "target": ..., "description": ...}, ...]
    """
    lines = raw_text.strip().splitlines()
    deployments = []
    for line in lines[1:]:  # skip header
        m = re.match(r"^-\s+(\S+)\s+@(\S+)(?:\s+-\s+(.*))?", line)
        if m:
            dep_id, target, desc = m.group(1), m.group(2), m.group(3) or ""
            deployments.append({
                "id": dep_id,
                "target": target,
                "description": desc
            })
    return deployments


def parse_versions(raw_text):
    """
    Parse the output of `clasp versions` into a list of dicts:
    [{"version": ..., "description": ...}, ...]
    """
    lines = raw_text.strip().splitlines()
    versions = []
    for line in lines[1:]:  # skip header
        m = re.match(r"^(\d+)\s*-\s*(.*)$", line)
        if m:
            ver_num, desc = m.group(1), m.group(2) or ""
            versions.append({
                "version": int(ver_num),
                "description": desc
            })
    return versions

def refresh_clasp_token():
    """Run `clasp list` to force token refresh."""
    print("Refreshing clasp token via `clasp list`...")
    try:
        subprocess.run('clasp list', shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        print("Warning: `clasp list` failed. Token might be invalid.", file=sys.stderr)

def get_access_token():
    """Read access token from ~/.clasprc.json"""
    rc_path = os.path.expanduser('~/.clasprc.json')
    # print(f"Debug: Checking for credentials at {rc_path}", file=sys.stderr)

    if not os.path.exists(rc_path):
        return None

    try:
        with open(rc_path, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                return None
            data = json.loads(content)
        
        # Try to find 'access_token' in common structures
        access_token_found = None
        if 'token' in data and isinstance(data['token'], dict) and 'access_token' in data['token']:
            access_token_found = data['token']['access_token']
        elif 'access_token' in data:
            access_token_found = data['access_token']
        elif 'tokens' in data and isinstance(data['tokens'], dict):
            for key, token_data in data['tokens'].items():
                if isinstance(token_data, dict) and 'access_token' in token_data:
                    access_token_found = token_data['access_token']
                    break
        
        return access_token_found

    except Exception as e:
        print(f"Error reading .clasprc.json: {e}", file=sys.stderr)
    return None

def get_remote_project_metadata(script_id, access_token):
    """Fetch full project resource from Apps Script API."""
    url = f"https://script.googleapis.com/v1/projects/{script_id}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {access_token}")
    try:
        with urllib.request.urlopen(req) as res:
            return json.load(res)
    except Exception as e:
        print(f"Error fetching metadata for {script_id}: {e}", file=sys.stderr)
        return None

def get_local_apps_script_update_time(project_dir):
    """Get updateTime from local metadata.json (appsScriptApi block)."""
    meta_path = os.path.join(project_dir, 'metadata.json')
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Try nested structure first
            if "appsScriptApi" in data and isinstance(data["appsScriptApi"], dict):
                return data["appsScriptApi"].get('updateTime')
            # Fallback for migration
            return data.get('lastUpdated')
        except:
            return None
    return None

def update_local_metadata(project_dir, api_metadata):
    """Merge Apps Script API metadata into metadata.json and clean up old properties."""
    meta_path = os.path.join(project_dir, 'metadata.json')
    data = {}
    if os.path.exists(meta_path):
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except:
            pass
    
    # Save full response under appsScriptApi
    data['appsScriptApi'] = api_metadata
    
    # Cleanup root properties as requested (consolidation)
    root_to_remove = ["lastUpdated", "name", "createdTime", "modifiedTime", "titleByClaspList", "titleByDriveApi"]
    for prop in root_to_remove:
        data.pop(prop, None)
    
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def run_clasp_with_retry(cmd, cwd=None, capture_output=False, retries=3):
    """
    Run a clasp command with retries.
    If it fails, try to refresh token via `clasp list` and retry.
    """
    attempt = 0
    while attempt < retries:
        attempt += 1
        print(f"  Running: {cmd} (Attempt {attempt}/{retries})")
        
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                cwd=cwd,
                check=True,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                encoding='utf-8',
                errors='replace'
            )
            return result
        except subprocess.CalledProcessError as e:
            print(f"    Command failed with exit code {e.returncode}.", file=sys.stderr)
            if capture_output:
                print(f"    Stdout: {e.stdout}", file=sys.stderr)
                print(f"    Stderr: {e.stderr}", file=sys.stderr)
            
            # If it's an auth error, try to refresh
            if attempt < retries:
                print("    Attempting to refresh token via `clasp list`...", file=sys.stderr)
                try:
                    subprocess.run('clasp list', shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except:
                    pass
                time.sleep(2)  # Wait a bit
            else:
                raise e

def main():
    base_dir = os.getcwd()
    project_dirs = list(iter_project_dirs(base_dir))
    
    # Check clasp version
    try:
        subprocess.run('clasp -v', shell=True, check=True)
    except:
        pass

    # Refresh token once at the start
    refresh_clasp_token()
    access_token = get_access_token()
    
    if not access_token:
        print("Warning: Could not read access token from .clasprc.json. Optimization disabled. Proceeding with full pull.", file=sys.stderr)

    for project_dir in project_dirs:
        entry = os.path.relpath(project_dir, base_dir)
        clasp_config = os.path.join(project_dir, '.clasp.json')
        print(f"Processing project '{entry}'...")

        should_pull = True
        script_id = None
        remote_metadata = None

        if access_token:
            try:
                with open(clasp_config, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                    script_id = cfg.get('scriptId')
            except:
                pass

            if script_id:
                remote_metadata = get_remote_project_metadata(script_id, access_token)
                remote_update_time = remote_metadata.get('updateTime') if remote_metadata else None
                local_last_updated = get_local_apps_script_update_time(project_dir)

                if remote_update_time and local_last_updated:
                    if remote_update_time <= local_last_updated:
                         print(f"  Skipping pull: Remote ({remote_update_time}) <= Local ({local_last_updated})")
                         should_pull = False
                    else:
                         print(f"  Update needed: Remote ({remote_update_time}) > Local ({local_last_updated})")
                elif not remote_update_time:
                     print("  Pulling: Could not fetch remote metadata.")
                elif not local_last_updated:
                     print("  Pulling: No local metadata.")

        if should_pull:
            try:
                # 1) Refresh metadata if not already fetched
                if access_token and script_id and not remote_metadata:
                    remote_metadata = get_remote_project_metadata(script_id, access_token)

                # 2) Pull latest files via shell
                print("  Running `clasp pull` via shell...")
                run_clasp_with_retry('clasp pull', cwd=project_dir)

                # 3) Fetch deployments via shell
                print("  Fetching deployments via shell...")
                proc_dep = run_clasp_with_retry(
                    'clasp deployments',
                    cwd=project_dir,
                    capture_output=True
                )
                raw_dep = proc_dep.stdout
                with open(os.path.join(project_dir, 'deployments.txt'), 'w', encoding='utf-8') as f:
                    f.write(raw_dep)
                deps = parse_deployments(raw_dep)
                with open(os.path.join(project_dir, 'deployments.json'), 'w', encoding='utf-8') as f:
                    json.dump(deps, f, ensure_ascii=False, indent=2)

                # 4) Fetch versions via shell
                print("  Fetching versions via shell...")
                proc_ver = run_clasp_with_retry(
                    'clasp versions',
                    cwd=project_dir,
                    capture_output=True
                )
                raw_ver = proc_ver.stdout
                with open(os.path.join(project_dir, 'versions.txt'), 'w', encoding='utf-8') as f:
                    f.write(raw_ver)
                vers = parse_versions(raw_ver)
                with open(os.path.join(project_dir, 'versions.json'), 'w', encoding='utf-8') as f:
                    json.dump(vers, f, ensure_ascii=False, indent=2)

                # Update metadata if we have the info
                if remote_metadata:
                    update_local_metadata(project_dir, remote_metadata)

                print(f"  Completed project '{entry}'.")

            except subprocess.CalledProcessError as e:
                print(f"Error: command failed in {entry}: {e}", file=sys.stderr)
            finally:
                pass

    print("All projects processed.")


if __name__ == '__main__':
    main()
