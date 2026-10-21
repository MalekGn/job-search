"""Lever — https://api.lever.co/v0/postings/{id}?mode=json"""
import datetime

from ats import job
from common import http_get_json


def _ms_to_iso(ms) -> str:
    try:
        return datetime.datetime.fromtimestamp(int(ms) / 1000, tz=datetime.timezone.utc).isoformat()
    except (TypeError, ValueError):
        return ""


def fetch(board_id: str) -> list[dict]:
    status, data = http_get_json(f"https://api.lever.co/v0/postings/{board_id}?mode=json", retry_network=False)
    if status != 200 or not isinstance(data, list):
        return []
    out = []
    for j in data:
        cats = j.get("categories") or {}
        out.append(job(title=j.get("text"), url=j.get("hostedUrl") or j.get("applyUrl"), location=cats.get("location"),
                       departments=[cats.get("team", "")], updated_at=_ms_to_iso(j.get("createdAt")),
                       source="lever", remote=(j.get("workplaceType") == "remote") or None))
    return out
