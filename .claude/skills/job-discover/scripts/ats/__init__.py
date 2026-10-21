"""
ats — one module per applicant tracking system (ATS) that exposes its postings publicly.

Each module defines:
    fetch(board_id: str) -> list[dict]    postings in common.posting() format, [] if the company isn't there

Adding an ATS: create ats/<name>.py with fetch(), then add <name> to config/ats.json.
"""
from __future__ import annotations

import importlib
import re
from typing import Callable

from common import posting

REMOTE_RE = re.compile(r"\bremote\b|\bt[ée]l[ée]travail\b|\bfull[\s-]?remote\b|\banywhere\b", re.IGNORECASE)


def job(*, title, url, location, departments, updated_at, source, remote=None) -> dict:
    """ATS posting: neither the contract nor the publication date is known (only the update date)."""
    loc = location or ""
    is_remote = bool(remote) if remote is not None else bool(REMOTE_RE.search(loc))
    return posting(company="", title=title, url=url, source=source, location=loc,
                   remote="full" if is_remote else "", published_at=updated_at or "",
                   departments=[d for d in departments if d], updated_at=updated_at or "")


def load(names: list[str]) -> dict[str, Callable[[str], list[dict]]]:
    """Loads the requested ATS modules, in order (= probing order)."""
    return {name: importlib.import_module(f"ats.{name}").fetch for name in names}
