"""Recruitee — https://{id}.recruitee.com/api/offers/"""
import datetime

from ats import job
from common import http_get_json


def _date(s: str | None) -> str:
    """'2026-10-15 09:31:36 UTC' → ISO 8601."""
    if not s:
        return ""
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=datetime.timezone.utc).isoformat()
    except ValueError:
        return s


def fetch(board_id: str) -> list[dict]:
    status, data = http_get_json(f"https://{board_id}.recruitee.com/api/offers/", retry_network=False)
    if status != 200 or not isinstance(data, dict):
        return []
    return [
        job(title=j.get("title"), url=j.get("careers_url"), location=j.get("location"),
            departments=[j.get("department", "")], updated_at=_date(j.get("published_at") or j.get("created_at")),
            source="recruitee", remote=j.get("remote"))
        for j in data.get("offers", [])
    ]
