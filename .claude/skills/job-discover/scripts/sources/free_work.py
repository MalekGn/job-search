"""
free_work — IT freelance missions and permanent jobs in France, via Free-Work's public JSON API.

  https://www.free-work.com/api/job_postings?searchKeywords=...&contracts=...&itemsPerPage=50&page=N

API behaviour observed (Oct. 2026):
  - searchKeywords requires ALL words of a query ("alfresco java" → 0): one series of queries per
    keyword, merged, recording which keywords found each posting;
  - date filters (createdAt[after]) are ignored and order[...] is rejected: we filter ourselves
    on publishedAt, the order being roughly chronological;
  - publishedAt changes on every republication, createdAt does not: republished = created before the period;
  - contracts: contractor = freelance, permanent = permanent.

Options (config/sources.json): max_pages (default 20 pages of 50 per keyword).
"""
from __future__ import annotations

import datetime
import html
import re
import time
import urllib.parse

from common import SearchParams, http_get_json, local_midnight, merge_by_id, parse_iso, posting

API_URL = "https://www.free-work.com/api/job_postings"
SITE_URL = "https://www.free-work.com/fr/tech-it"
PAGE_SIZE = 50

CONTRACT_PARAM = {"freelance": "contractor", "permanent": "permanent"}
CONTRACT_LABEL = {"contractor": "freelance", "permanent": "permanent"}
EXCLUDED_CONTRACTS = {"internship", "apprenticeship"}
TAG_RE = re.compile(r"<[^>]+>")


def excerpt(text: str | None, n: int = 400) -> str:
    if not text:
        return ""
    clean = re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", text))).strip()
    return clean[:n] + ("…" if len(clean) > n else "")


def normalize(m: dict, cutoff) -> dict:
    loc = m.get("location") or {}
    job = m.get("job") or {}
    # Canonical form (the other form, /{job}/job-mission/{posting}, redirects to this one).
    url = f"{SITE_URL}/job-mission/{job['slug']}/{m.get('slug', '')}" if job.get("slug") \
        else f"https://www.free-work.com{m.get('@id', '')}"
    created = parse_iso(m.get("createdAt"))
    return posting(
        company=(m.get("company") or {}).get("name") or "",
        title=html.unescape(m.get("title", "")),
        url=url,
        source="free_work",
        location=loc.get("label") or "",
        contracts=[CONTRACT_LABEL.get(c, "other") for c in (m.get("contracts") or [])],
        published_at=m.get("publishedAt") or "",
        description=excerpt(m.get("description")),
        pay=m.get("dailySalary") or m.get("annualSalary") or "",
        remote=m.get("remoteMode") or "",
        source_job_id=m.get("id", ""),
        daily_rate=m.get("dailySalary") or "",
        salary=m.get("annualSalary") or "",
        duration=f"{m['durationValue']} {m.get('durationPeriod') or ''}".strip() if m.get("durationValue") else "",
        experience=m.get("experienceLevel") or "",
        created_at=m.get("createdAt") or "",
        expires_at=m.get("expiredAt") or "",
        country_code=loc.get("countryCode") or "",
        republished=bool(created and created < cutoff),
    )


def search_keyword(keyword: str, contract: str | None, cutoff, max_pages: int, warnings: list[str],
                   failed: list[str] | None = None) -> list[dict]:
    failed = [] if failed is None else failed
    out = []
    now = datetime.datetime.now().astimezone()
    for page in range(1, max_pages + 1):
        params = {"searchKeywords": keyword, "itemsPerPage": PAGE_SIZE, "page": page}
        if contract:
            params["contracts"] = contract
        status, data = http_get_json(f"{API_URL}?{urllib.parse.urlencode(params)}",
                                     headers={"Accept": "application/ld+json"})
        if status != 200 or not isinstance(data, dict):
            warnings.append(f"Free-Work: HTTP {status} for \"{keyword}\" (page {page})")
            failed.append(keyword)
            break
        members = data.get("hydra:member") or []
        fresh_on_page = 0
        for m in members:
            if m.get("status") != "published":
                continue
            if set(m.get("contracts") or []) and set(m.get("contracts")) <= EXCLUDED_CONTRACTS:
                continue
            expires = parse_iso(m.get("expiredAt"))
            if expires and expires < now:
                continue
            published = parse_iso(m.get("publishedAt"))
            if published is None or published < cutoff:
                continue
            fresh_on_page += 1
            out.append(m)
        # Roughly chronological order: a whole page that is too old = stop.
        if len(members) < PAGE_SIZE or fresh_on_page == 0 or "hydra:next" not in (data.get("hydra:view") or {}):
            break
        if page == max_pages:
            warnings.append(f"Free-Work: \"{keyword}\" exceeds {max_pages} pages of {PAGE_SIZE}; postings from "
                            f"the period are missing (raise options.max_pages or use a more specific keyword)")
        time.sleep(0.3)
    return out


def search(r: SearchParams) -> dict:
    cutoff = local_midnight(r.since)
    wanted = [c for c in r.contracts if c in CONTRACT_PARAM]
    # A single contract type requested: filter on the API side. Otherwise take everything and sort afterwards.
    contract_param = CONTRACT_PARAM[wanted[0]] if len(wanted) == 1 and len(r.contracts) == 1 else None
    max_pages = int(r.options.get("max_pages", 20))
    warnings: list[str] = []
    failed: list[str] = []
    found = [(kw, normalize(m, cutoff))
             for kw in r.keywords
             for m in search_keyword(kw, contract_param, cutoff, max_pages, warnings, failed)]
    roles = merge_by_id(found)
    if r.contracts:
        roles = [o for o in roles if set(o["contracts"]) & set(r.contracts)]
    roles.sort(key=lambda o: o["published_at"], reverse=True)
    roles.sort(key=lambda o: (-len(o["matched_keywords"]), o["republished"]))
    return {"roles": roles, "warnings": warnings, "failed_keywords": list(dict.fromkeys(failed)),
            "by_keyword": {kw: sum(kw in o["matched_keywords"] for o in roles) for kw in r.keywords}}
