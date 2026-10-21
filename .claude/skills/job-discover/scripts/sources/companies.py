"""
companies — postings of the followed companies, read from their ATS (applicant tracking system).

Company list: <project>/output/companies.json (kept up to date by Claude from criteria.md).
Usable ATS and probing order: config/ats.json (project copy, otherwise the skill default).

For each company:
  - ats set → query that ATS;
  - ats null, or mapped ATS with no result → probe the ATS in the configured order;
  - mapping found → written back to companies.json (confidence = probe_verified);
  - ats null and no ATS answers → ats = "web": the company is left to web search and
    is no longer probed on later runs.

Options (config/sources.json): parallelism (default 8, recommended max 16).
The filter applies to title and department: ATS listings don't include descriptions.
"""
from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import ats
from common import SearchParams, published_on_or_after
from config import load_config


def build_pattern(terms: list[str]) -> re.Pattern | None:
    """A term 'tech lead' matches 'Tech  Lead' or 'Tech-Lead'; word boundaries at both ends."""
    parts = []
    for raw in terms:
        tokens = [re.escape(t) for t in raw.split()]
        if tokens:
            parts.append(r"\b" + r"[\s,\-/]+".join(tokens) + r"\b")
    return re.compile("|".join(parts), re.IGNORECASE) if parts else None


def matches(job: dict, include: re.Pattern | None, exclude: re.Pattern | None) -> bool:
    title = job.get("title", "") or ""
    if not title:
        return False
    if exclude and exclude.search(title):
        return False
    if include is None:
        return True
    return bool(include.search(" ".join([title] + job.get("departments", []))))


def fetch_one_company(company: dict, fetchers: dict) -> tuple[dict, str | None, str | None, list[dict], str | None]:
    """Returns (company, ats_used, board_id_found, postings, warning)."""
    slug = company["slug"]
    mapped = company.get("ats")
    board_id = company.get("board_id") or slug

    if mapped in fetchers:
        jobs = fetchers[mapped](board_id)
        if jobs:
            return company, mapped, None, jobs, None

    candidates = [board_id] + ([slug] if slug != board_id else [])
    for cand in candidates:
        for name, fetch in fetchers.items():
            jobs = fetch(cand)
            if jobs:
                return company, name, cand, jobs, None

    if mapped in fetchers:
        # An ATS that used to work may be temporarily empty: keep the mapping and warn.
        return company, None, None, [], f"{slug}: ATS '{mapped}' (board_id={board_id}) has no postings; probing failed"
    return company, None, None, [], None


def search(r: SearchParams) -> dict:
    path = Path(r.options.get("companies_file") or r.project_root / "output" / "companies.json")
    result = {"roles": [], "warnings": [], "mapping_updates": [], "web_companies": [], "companies_polled": 0}
    if not path.exists():
        result["warnings"].append(f"No followed companies ({path} missing): source skipped")
        return result

    cfg = json.loads(path.read_text())
    companies = cfg.get("companies", [])
    if r.options.get("only"):
        wanted = {s.lower() for s in r.options["only"]}
        companies = [c for c in companies if c["slug"].lower() in wanted]
    web = [c for c in companies if c.get("ats") == "web"]
    to_poll = [c for c in companies if c.get("ats") != "web"]
    result["companies_polled"] = len(to_poll)

    ats_cfg = load_config("ats.json", r.project_root)
    fetchers = ats.load([a for a in ats_cfg.get("probe_order", []) if a in ats_cfg.get("enabled", [])])
    include_re, exclude_re = build_pattern(r.keywords), build_pattern(r.exclude)
    updates = []

    with ThreadPoolExecutor(max_workers=int(r.options.get("parallelism", 8))) as pool:
        futures = [pool.submit(fetch_one_company, c, fetchers) for c in to_poll]
        for fut in as_completed(futures):
            company, used, found_board, jobs, warning = fut.result()
            if warning:
                result["warnings"].append(warning)
            if used and (used != company.get("ats") or (found_board and found_board != company.get("board_id"))):
                updates.append({"slug": company["slug"], "ats": used, "board_id": found_board})
            elif not used and company.get("ats") is None:
                updates.append({"slug": company["slug"], "ats": "web", "board_id": None})
                web.append(company)
            for j in jobs:
                # ATS only expose an update date: it is used as the date for the period.
                if matches(j, include_re, exclude_re) and published_on_or_after(j["updated_at"], r.since):
                    result["roles"].append(j | {"company": company.get("display", company["slug"]),
                                                "company_slug": company["slug"], "tier": company.get("tier", 0)})

    if updates:
        by_slug = {u["slug"]: u for u in updates}
        for c in cfg.get("companies", []):
            u = by_slug.get(c["slug"])
            if u:
                c["ats"] = u["ats"]
                if u["board_id"]:
                    c["board_id"] = u["board_id"]
                c["confidence"] = "probe_verified" if u["ats"] != "web" else "no_ats_found"
        path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")

    result["mapping_updates"] = updates
    result["web_companies"] = [{"slug": c["slug"], "display": c.get("display", c["slug"])} for c in web]
    result["roles"].sort(key=lambda j: j["updated_at"], reverse=True)
    return result
