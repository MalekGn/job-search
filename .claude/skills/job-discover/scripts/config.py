"""
config.py — source and ATS configuration.

Defaults: <skill>/config/*.json (shipped with the skill; don't edit them for personal settings).
User copy: <project>/config/*.json, created on first run; this copy is authoritative.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from common import PROJECT_ROOT, SKILL_DIR

DEFAULT_DIR = SKILL_DIR / "config"
FILES = ("sources.json", "ats.json", "search.json")


def project_dir(project_root: Path = PROJECT_ROOT) -> Path:
    return project_root / "config"


def ensure_project_config(project_root: Path = PROJECT_ROOT) -> list[str]:
    """Copies missing config files into the project. Returns the list of files created."""
    created = []
    target = project_dir(project_root)
    for name in FILES:
        dest = target / name
        if not dest.exists():
            target.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(DEFAULT_DIR / name, dest)
            created.append(str(dest))
    return created


def load_config(name: str, project_root: Path = PROJECT_ROOT) -> dict:
    path = project_dir(project_root) / name
    if not path.exists():
        path = DEFAULT_DIR / name
    return json.loads(path.read_text())
