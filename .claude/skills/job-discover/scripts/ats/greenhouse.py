"""Greenhouse — https://boards-api.greenhouse.io/v1/boards/{id}/jobs"""
from ats import job
from common import http_get_json


def fetch(board_id: str) -> list[dict]:
    status, data = http_get_json(f"https://boards-api.greenhouse.io/v1/boards/{board_id}/jobs", retry_network=False)
    if status != 200 or not isinstance(data, dict):
        return []
    return [
        job(title=j.get("title"), url=j.get("absolute_url"), location=(j.get("location") or {}).get("name"),
            departments=[d.get("name", "") for d in (j.get("departments") or [])],
            updated_at=j.get("updated_at"), source="greenhouse")
        for j in data.get("jobs", [])
    ]
