"""SmartRecruiters — https://api.smartrecruiters.com/v1/companies/{id}/postings

An unknown company returns 200 + an empty list: "not a customer" can't be told apart from "no postings",
both are treated as a failed probe."""
from ats import job
from common import http_get_json

MAX_PAGES = 10  # 100 postings per page


def fetch(board_id: str) -> list[dict]:
    out = []
    for page in range(MAX_PAGES):
        status, data = http_get_json(
            f"https://api.smartrecruiters.com/v1/companies/{board_id}/postings?limit=100&offset={page * 100}",
            retry_network=False)
        if status != 200 or not isinstance(data, dict):
            break
        content = data.get("content") or []
        for j in content:
            loc = j.get("location") or {}
            ident = (j.get("company") or {}).get("identifier") or board_id
            out.append(job(title=j.get("name"), url=f"https://jobs.smartrecruiters.com/{ident}/{j.get('id', '')}",
                           location=loc.get("fullLocation") or loc.get("city"),
                           departments=[(j.get("department") or {}).get("label", ""),
                                        (j.get("function") or {}).get("label", "")],
                           updated_at=j.get("releasedDate"), source="smartrecruiters", remote=loc.get("remote")))
        if len(content) < 100 or (page + 1) * 100 >= data.get("totalFound", 0):
            break
    return out
