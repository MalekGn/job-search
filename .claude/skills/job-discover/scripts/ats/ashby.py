"""Ashby — https://api.ashbyhq.com/posting-api/job-board/{id}"""
from ats import job
from common import http_get_json


def fetch(board_id: str) -> list[dict]:
    status, data = http_get_json(
        f"https://api.ashbyhq.com/posting-api/job-board/{board_id}?includeCompensation=false", retry_network=False)
    if status != 200 or not isinstance(data, dict):
        return []
    return [
        job(title=j.get("title"), url=j.get("jobUrl"), location=j.get("location") or j.get("locationName"),
            departments=[j.get("department", "") or j.get("departmentName", ""), j.get("team", "")],
            updated_at=j.get("publishedAt") or j.get("updatedAt"), source="ashby", remote=j.get("isRemote"))
        for j in data.get("jobs", [])
    ]
