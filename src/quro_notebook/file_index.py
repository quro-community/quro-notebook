"""Build a stem→path index by scanning project_root for editable files."""

import os
from pathlib import Path

EDITABLE_EXTENSIONS = {".md", ".mdx", ".txt", ".rst", ".adoc"}

SKIP_DIRS = {".git", "_output", "node_modules", ".venv", "__pycache__", ".mypy_cache"}


def build_file_index(project_root: str) -> dict[str, str]:
    """Scan project_root for editable files, return {stem: absolute_path}.

    If multiple files share the same stem, the first encountered wins
    (sorted by path depth, then alphabetically).
    """
    index: dict[str, str] = {}
    root = Path(project_root).resolve()

    all_files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            filepath = Path(dirpath) / fname
            if filepath.suffix in EDITABLE_EXTENSIONS:
                all_files.append(filepath)

    all_files.sort(key=lambda p: (len(p.parts), str(p)))

    for fp in all_files:
        stem = fp.stem
        if stem not in index:
            index[stem] = str(fp)

    return index
