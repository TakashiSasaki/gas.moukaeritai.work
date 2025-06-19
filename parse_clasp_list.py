import json
import re

def parse_clasp_list(input_filepath="clasp-list.txt", output_filepath="clasp-list.json"):
    """
    Parses a list of Google Apps Script projects from a text file and outputs a JSON file.

    Args:
        input_filepath (str): Path to the input text file (default: "clasp-list.txt").
        output_filepath (str): Path to the output JSON file (default: "clasp-list.json").
    """
    projects = []
    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: Input file '{input_filepath}' not found.")
        return
    except IOError as e:
        print(f"Error reading file '{input_filepath}': {e}")
        return

    if not lines:
        print(f"Warning: Input file '{input_filepath}' is empty.")
        return

    # Regex to capture script name (handling potential "..." and whitespace)
    # and script ID from the URL.
    # Example line: Script Name (...) - https://script.google.com/d/SCRIPT_ID_FOOBAR/edit
    # Another example: Another Script Name - https://script.google.com/d/SCRIPT_ID_BAZQUX/edit
    project_line_regex = re.compile(r"^(.*?)(?:\s*\(\.\.\.\))?\s+-\s+https://script\.google\.com/d/([^/]+)/edit.*$")

    for line in lines[1:]:  # Skip the first line "Found X scripts."
        line = line.strip()
        if not line:
            continue

        match = project_line_regex.match(line)
        if match:
            script_name = match.group(1).strip()
            script_id = match.group(2).strip()
            projects.append({"name": script_name, "id": script_id})
        else:
            print(f"Warning: Could not parse line: '{line}'")

    try:
        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(projects, f, indent=4, ensure_ascii=False)
        print(f"Successfully parsed {len(projects)} projects and saved to '{output_filepath}'")
    except IOError as e:
        print(f"Error writing JSON to file '{output_filepath}': {e}")
    except Exception as e:
        print(f"An unexpected error occurred during JSON writing: {e}")


if __name__ == "__main__":
    parse_clasp_list()
    # Example of how to use it with different file names:
    # parse_clasp_list(input_filepath="my_scripts.txt", output_filepath="my_scripts.json")
