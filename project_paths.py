import os
from typing import Iterator


PROJECTS_DIRNAME = "projects"


def get_projects_root(base_dir: str | None = None) -> str:
    base = os.path.abspath(base_dir or os.getcwd())
    return os.path.join(base, PROJECTS_DIRNAME)


def iter_project_dirs(base_dir: str | None = None) -> Iterator[str]:
    base = os.path.abspath(base_dir or os.getcwd())
    projects_root = get_projects_root(base)
    search_roots = []

    if os.path.isdir(projects_root):
        search_roots.append(projects_root)

    search_roots.append(base)

    seen: set[str] = set()
    for root in search_roots:
        for entry in sorted(os.listdir(root)):
            dir_path = os.path.join(root, entry)
            clasp_path = os.path.join(dir_path, ".clasp.json")

            if not os.path.isdir(dir_path) or not os.path.isfile(clasp_path):
                continue

            real_path = os.path.realpath(dir_path)
            if real_path in seen:
                continue

            seen.add(real_path)
            yield dir_path
