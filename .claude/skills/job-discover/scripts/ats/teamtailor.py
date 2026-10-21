"""Teamtailor — RSS feed https://{id}.teamtailor.com/jobs.rss (or https://{domain}/jobs.rss if id contains a dot).

Teamtailor has no public API without a key, but every careers site publishes a complete RSS feed."""
import email.utils
import xml.etree.ElementTree as ET

from ats import job
from common import http_request

TT_NS = "{https://teamtailor.com/locations}"


def _rfc822_to_iso(s: str | None) -> str:
    if not s:
        return ""
    try:
        return email.utils.parsedate_to_datetime(s).isoformat()
    except (TypeError, ValueError):
        return ""


def fetch(board_id: str) -> list[dict]:
    host = board_id if "." in board_id else f"{board_id}.teamtailor.com"
    status, body, _ = http_request(f"https://{host}/jobs.rss", headers={"Accept": "application/rss+xml"},
                                   retry_network=False)
    if status != 200 or not body or "<rss" not in body[:500]:
        return []
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return []
    out = []
    for item in root.iter("item"):
        cities = [loc.findtext(f"{TT_NS}city") or loc.findtext(f"{TT_NS}name") or ""
                  for loc in item.iter(f"{TT_NS}location")]
        out.append(job(title=item.findtext("title"), url=item.findtext("link"),
                       location=", ".join(c for c in cities if c),
                       departments=[item.findtext(f"{TT_NS}department") or ""],
                       updated_at=_rfc822_to_iso(item.findtext("pubDate")), source="teamtailor",
                       remote=((item.findtext("remoteStatus") or "").lower() == "fully") or None))
    return out
