"""
common.py — helpers shared by sources and ATS adapters: HTTP with retries, dates, common posting format.

Standard library only.
"""
from __future__ import annotations

import datetime
import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SKILL_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(os.environ.get("JOB_DISCOVER_ROOT", SKILL_DIR.parents[2]))
USER_AGENT = "Mozilla/5.0 (compatible; job-discover/1.0)"
HTTP_TIMEOUT = 15

CONTRACTS = ("freelance", "permanent", "other")


# ---------- Search parameters ----------

@dataclass
class SearchParams:
    """What every source receives. Sources never read the profile: Claude translates it into these parameters."""
    keywords: list[str]
    since: datetime.date
    exclude: list[str] = field(default_factory=list)
    contracts: list[str] = field(default_factory=list)  # empty = all
    base: dict = field(default_factory=dict)            # e.g. {"city": "Lyon", "department": "69", "country": "FR"}
    options: dict = field(default_factory=dict)         # "options" of the source entry in sources.json
    project_root: Path = PROJECT_ROOT


# ---------- HTTP ----------

def http_request(url: str, *, data: bytes | None = None, headers: dict | None = None, retries: int = 2,
                 backoff: float = 1.5, retry_network: bool = True,
                 timeout: int = HTTP_TIMEOUT) -> tuple[int, str | None, dict]:
    """Returns (status, body, headers). Status 0 = network error.

    Retries server errors (5xx, 429), which are frequent and transient on job sites. 4xx are not retried:
    a 404 is often the expected answer (ATS probing). retry_network=False for probes where a non-existent
    domain is normal. Wait between attempts: backoff × 1, 4, 9..."""
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, **(headers or {})})
    status = 0
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.getcode(), r.read().decode("utf-8", errors="replace"), dict(r.headers)
        except urllib.error.HTTPError as e:
            status = e.code
            if e.code < 500 and e.code != 429:
                return status, None, {}
        except (urllib.error.URLError, TimeoutError, ConnectionError, socket.timeout, ssl.SSLError, OSError):
            status = 0
            if not retry_network:
                return 0, None, {}
        if attempt < retries:
            time.sleep(backoff * (attempt + 1) ** 2)
    return status, None, {}


def http_get_json(url: str, **kw) -> tuple[int, Any]:
    status, body, _ = http_request(url, headers={"Accept": "application/json", **kw.pop("headers", {})}, **kw)
    if body is None:
        return status, None
    try:
        return status, json.loads(body)
    except json.JSONDecodeError:
        return status, None


# ---------- Dates ----------

def today_local() -> datetime.date:
    return datetime.datetime.now().astimezone().date()


def local_midnight(day: datetime.date) -> datetime.datetime:
    return datetime.datetime.combine(day, datetime.time.min).astimezone()


def parse_iso(s: str | None) -> datetime.datetime | None:
    if not s:
        return None
    try:
        dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=datetime.timezone.utc)


def published_on_or_after(published: str | None, since: datetime.date) -> bool:
    """ISO date (or YYYY-MM-DD) from local midnight of `since` onwards. No date: False."""
    if not published:
        return False
    if len(published) == 10:
        try:
            return datetime.date.fromisoformat(published) >= since
        except ValueError:
            return False
    dt = parse_iso(published)
    return dt is not None and dt >= local_midnight(since)


# ---------- Posting format ----------

def posting(*, company: str, title: str, url: str, source: str, location: str = "", contracts: list[str] | None = None,
            published_at: str = "", description: str = "", pay: str = "", remote: str = "",
            source_job_id: str = "", **extra) -> dict:
    """Format shared by all sources. Source-specific fields go in **extra."""
    return {
        "company": company or "(not disclosed)",
        "title": title or "",
        "url": url or "",
        "location": location or "",
        "contracts": sorted(set(contracts or [])),  # subset of CONTRACTS; empty = unknown
        "pay": pay or "",
        "remote": remote or "",                     # full / partial / none / ""
        "published_at": published_at or "",
        "description": description or "",
        "source": source,
        "source_job_id": str(source_job_id or ""),
        **extra,
    }


def merge_by_id(found: list[tuple[str, dict]]) -> list[dict]:
    """Merges (keyword, posting) pairs from one source, recording which keywords found each posting."""
    by_id: dict[str, dict] = {}
    for kw, o in found:
        key = o["source_job_id"] or o["url"]
        entry = by_id.setdefault(key, o | {"matched_keywords": []})
        if kw and kw not in entry["matched_keywords"]:
            entry["matched_keywords"].append(kw)
        for flag in ("nearby",):
            if o.get(flag):
                entry[flag] = True
    return list(by_id.values())
