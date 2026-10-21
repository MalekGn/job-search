"""
france_travail — France Travail postings (also aggregates many partners: Collective, APEC, Hellowork...).

Two modes (options.mode = auto by default):
  api     official "Offres d'emploi v2" API, if FT_CLIENT_ID / FT_CLIENT_SECRET are set
          (application created on https://francetravail.io). Complete, structured data.
  public  otherwise: public search pages of candidat.francetravail.fr, read as HTML.
          Description excerpt and relative date only, but no key required.

Observed behaviour (Oct. 2026):
  - one department per request in both modes: one request per department;
  - the date filter only accepts 1, 3, 7, 14 or 31 days: we take the smallest window covering
    the period, then filter on the publication date ourselves;
  - results sorted newest first: we read pages until we leave the period;
  - frequent transient 500 errors, sometimes long ones: 3 spaced retries (RETRY);
  - multi-word terms and accents work; however the engine matches similar words
    ("activiti" → "activité"): a keyword that hits the limit with off-topic postings should be replaced.

The site is French: the HTML parsing below matches French labels ("Publié il y a 3 jours", "CDI"...).

Options (config/sources.json): mode, max_pages (default 10 pages of 150), departments (list, default:
all of France). The home department (SearchParams.base["department"]) is additionally queried on its own:
across all of France, a local posting may sit beyond the pages read. Its postings are flagged nearby.
"""
from __future__ import annotations

import datetime
import html
import json
import os
import re
import time
import urllib.parse
from typing import Any

from common import SearchParams, http_request, merge_by_id, posting, published_on_or_after, today_local

TOKEN_URL = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=%2Fpartenaire"
API_SEARCH_URL = "https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search"
PUBLIC_SEARCH_URL = "https://candidat.francetravail.fr/offres/recherche"
DETAIL_URL = "https://candidat.francetravail.fr/offres/recherche/detail/{id}"
SCOPE = "api_offresdemploiv2 o2dsoffre"
PAGE_SIZE = 150
PUBLIC_MAX_RESULTS = 750   # the public site answers HTTP 500 beyond this (observed Oct. 2026)
API_MAX_RESULTS = 3150     # documented API limit (range up to 3149)
WINDOWS = (1, 3, 7, 14, 31)
SIGNUP_HINT = ("for more complete data: create an application on https://francetravail.io "
               "(\"Offres d'emploi v2\" API) then export FT_CLIENT_ID / FT_CLIENT_SECRET")

# Site outages (HTTP 500) sometimes last a minute: 3 retries spaced 3, 12 then 27 s.
RETRY = {"retries": 3, "backoff": 3.0}

API_CONTRACT = {"CDI": "permanent", "LIB": "freelance"}                      # API codes → categories
PUBLIC_CONTRACT = {"cdi": "permanent", "profession libérale": "freelance"}   # site labels → categories
CONTRACT_TO_API = {"permanent": "CDI", "freelance": "LIB"}


class SourceError(Exception):
    pass


# ---------- Dates ----------

def window_for(cutoff: datetime.date) -> int:
    """Smallest allowed window covering the cutoff date (today = 1 day)."""
    days = (today_local() - cutoff).days + 1
    return next((w for w in WINDOWS if w >= days), WINDOWS[-1])


RELATIVE_DATE_RE = re.compile(r"il y a (\d+) jours?")


def parse_relative_date(label: str) -> str:
    """'Publié aujourd'hui' / 'hier' / 'il y a 3 jours' → YYYY-MM-DD; '' if vaguer ("plus de 30 jours")."""
    label = label.lower()
    if "aujourd" in label:
        return today_local().isoformat()
    if "hier" in label:
        return (today_local() - datetime.timedelta(days=1)).isoformat()
    m = RELATIVE_DATE_RE.search(label)
    if m and "plus de" not in label:
        return (today_local() - datetime.timedelta(days=int(m.group(1)))).isoformat()
    return ""


def truncation_warning(keyword: str, department: str | None, limit: int, site_limit: bool) -> str:
    where = f"department {department}" if department else "all of France"
    fix = "use a more specific keyword" if site_limit else "raise options.max_pages or use a more specific keyword"
    cause = "site limit" if site_limit else "page cap"
    return (f"France Travail: \"{keyword}\" ({where}) exceeds {limit} results ({cause}); postings from the "
            f"period are missing ({fix})")


def page_starts(max_pages: int, max_results: int) -> list[int]:
    return [p * PAGE_SIZE for p in range(max_pages) if p * PAGE_SIZE < max_results]


# ---------- API mode ----------

def get_token(client_id: str, client_secret: str) -> str:
    body = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": client_id,
                                   "client_secret": client_secret, "scope": SCOPE}).encode()
    status, text, _ = http_request(TOKEN_URL, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if status != 200 or not text:
        raise SourceError(f"authentication refused (HTTP {status})")
    return json.loads(text)["access_token"]


def api_page(token: str, params: dict, start: int) -> tuple[list[dict], int | None]:
    """The API answers 206 when more results remain, 204 when there are none."""
    q = dict(params, range=f"{start}-{start + PAGE_SIZE - 1}")
    status, text, headers = http_request(f"{API_SEARCH_URL}?{urllib.parse.urlencode(q)}",
                                         headers={"Authorization": f"Bearer {token}", "Accept": "application/json"}, **RETRY)
    if status == 204:
        return [], 0
    if status not in (200, 206) or text is None:
        raise SourceError(f"HTTP {status}")
    total = None
    content_range = headers.get("Content-Range", "")  # e.g. "offres 0-149/1234"
    if "/" in content_range:
        try:
            total = int(content_range.rsplit("/", 1)[1])
        except ValueError:
            pass
    return json.loads(text).get("resultats", []), total


def normalize_api(o: dict) -> dict:
    place = o.get("lieuTravail") or {}
    salary = o.get("salaire") or {}
    return posting(
        company=(o.get("entreprise") or {}).get("nom") or "",
        title=o.get("intitule", ""),
        url=(o.get("origineOffre") or {}).get("urlOrigine") or DETAIL_URL.format(id=o.get("id", "")),
        source="france_travail",
        location=place.get("libelle", ""),
        contracts=[API_CONTRACT.get(o.get("typeContrat", ""), "other")],
        published_at=o.get("dateCreation") or "",
        description=(o.get("description") or "")[:400],
        pay=salary.get("libelle") or salary.get("commentaire") or "",
        source_job_id=o.get("id", ""),
        contract_label=o.get("typeContratLibelle", ""),
        experience=o.get("experienceLibelle", ""),
        updated_at=o.get("dateActualisation") or "",
    )


def search_api(token: str, keyword: str, department: str | None, contracts: str | None, window: int,
               cutoff: datetime.date, max_pages: int, warnings: list[str]) -> list[dict]:
    # sort=1: creation date descending, so we can stop as soon as we leave the period
    params: dict[str, Any] = {"motsCles": keyword, "publieeDepuis": window, "sort": 1}
    if department:
        params["departement"] = department
    if contracts:
        params["typeContrat"] = contracts
    out = []
    starts = page_starts(max_pages, API_MAX_RESULTS)
    for i, start in enumerate(starts):
        try:
            results, total = api_page(token, params, start)
        except (SourceError, json.JSONDecodeError) as e:
            warnings.append(f"France Travail (API): error for \"{keyword}\" {department or ''} ({e})")
            break
        normalized = [normalize_api(o) for o in results]
        out.extend(normalized)
        if len(results) < PAGE_SIZE or (total is not None and start + PAGE_SIZE >= total):
            break
        if not published_on_or_after(normalized[-1]["published_at"], cutoff):
            break
        if i == len(starts) - 1:
            warnings.append(truncation_warning(keyword, department, start + PAGE_SIZE,
                                               site_limit=start + PAGE_SIZE >= API_MAX_RESULTS))
        time.sleep(0.2)  # the API rate-limits per second
    return out


# ---------- Public mode (HTML) ----------

LI_RE = re.compile(r'<li data-id-offre="(\w+)" class="result">(.*?)</li>', re.S)


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _first(pattern: str, block: str) -> str:
    m = re.search(pattern, block, re.S)
    return _text(m.group(1)) if m else ""


def parse_public_page(page_html: str) -> list[dict]:
    out = []
    for offer_id, block in LI_RE.findall(page_html):
        # Subtitle: "Company - <span>Location</span>", or just "<span>Location</span>"
        sub = re.search(r'<p translate="no" class="subtext">(.*?)<span>(.*?)</span>', block, re.S)
        contract_label = _first(r'<p class="contrat">([^<]*)', block)
        out.append(posting(
            company=_text(sub.group(1)).rstrip(" -") if sub else "",
            title=_first(r'<span class="media-heading-title">(.*?)</span>', block),
            url=DETAIL_URL.format(id=offer_id),
            source="france_travail",
            location=_text(sub.group(2)) if sub else "",
            contracts=[PUBLIC_CONTRACT.get(contract_label.lower(), "other")],
            published_at=parse_relative_date(_first(r'<p class="date">(.*?)</p>', block)),
            description=_first(r'<p class="description">(.*?)</p>', block),
            source_job_id=offer_id,
            contract_label=contract_label,
        ))
    return out


def fetch_public(params: dict) -> str:
    status, body, _ = http_request(f"{PUBLIC_SEARCH_URL}?{urllib.parse.urlencode(params)}",
                                   headers={"Accept": "text/html"}, timeout=20, **RETRY)
    if status != 200 or body is None:
        raise SourceError(f"HTTP {status}")
    return body


def search_public(keyword: str, department: str | None, window: int, cutoff: datetime.date, max_pages: int,
                  warnings: list[str]) -> list[dict]:
    out = []
    starts = page_starts(max_pages, PUBLIC_MAX_RESULTS)
    for i, start in enumerate(starts):
        # tri=1: newest first, so we can stop as soon as we leave the period
        params = {"motsCles": keyword, "offresPartenaires": "true", "tri": 1, "emission": window,
                  "range": f"{start}-{start + PAGE_SIZE - 1}"}
        if department:
            params["lieux"] = f"{department}D"
        try:
            body = fetch_public(params)
        except SourceError as e:
            warnings.append(f"France Travail (public site): error for \"{keyword}\" {department or ''} ({e})")
            break
        results = parse_public_page(body)
        if not results and i == 0 and 'class="result-list' not in body and "Aucune offre" not in body:
            warnings.append("France Travail (public site): unexpected page structure, results may be missing")
        out.extend(results)
        if len(results) < PAGE_SIZE or not published_on_or_after(results[-1]["published_at"], cutoff):
            break
        if i == len(starts) - 1:
            warnings.append(truncation_warning(keyword, department, start + PAGE_SIZE,
                                               site_limit=start + PAGE_SIZE >= PUBLIC_MAX_RESULTS))
        time.sleep(0.5)
    return out


# ---------- Entry point ----------

def search(r: SearchParams) -> dict:
    window = window_for(r.since)
    mode = r.options.get("mode", "auto")
    max_pages = int(r.options.get("max_pages", 10))
    departments = [str(d) for d in r.options.get("departments", [])]
    base_dep = str(r.base.get("department") or "") or None
    client_id = os.environ.get("FT_CLIENT_ID", "").strip()
    client_secret = os.environ.get("FT_CLIENT_SECRET", "").strip()
    warnings: list[str] = []
    if mode == "auto":
        mode = "api" if client_id and client_secret else "public"

    token = None
    if mode == "api":
        try:
            token = get_token(client_id, client_secret)
        except (SourceError, KeyError, json.JSONDecodeError) as e:
            warnings.append(f"France Travail: API authentication failed ({e}), falling back to the public site")
            mode = "public"
    if mode == "public":
        warnings.append(f"France Travail read via the public site (no key); {SIGNUP_HINT}")

    searches = [(d, False) for d in (departments or [None])]
    if base_dep and base_dep not in departments:
        searches.append((base_dep, True))
    api_contracts = ",".join(CONTRACT_TO_API[c] for c in r.contracts if c in CONTRACT_TO_API) or None

    found, failed = [], []
    for kw in r.keywords:
        for dep, is_base in searches:
            errors_before = len(warnings)
            if mode == "api":
                rows = search_api(token, kw, dep, api_contracts, window, r.since, max_pages, warnings)
            else:
                rows = search_public(kw, dep, window, r.since, max_pages, warnings)
            # search_api / search_public report a request that still failed after RETRY as an "error for" warning
            if any("error for" in w for w in warnings[errors_before:]) and kw not in failed:
                failed.append(kw)
            for o in rows:
                if r.contracts and not set(o["contracts"]) & set(r.contracts):
                    continue
                if not published_on_or_after(o["published_at"], r.since):
                    continue
                found.append((kw, o | {"nearby": is_base or (base_dep is not None and dep == base_dep)}))

    roles = merge_by_id(found)
    roles.sort(key=lambda o: o["published_at"], reverse=True)
    roles.sort(key=lambda o: (-len(o["matched_keywords"]), not o.get("nearby")))
    return {"roles": roles, "warnings": warnings, "mode": mode, "failed_keywords": failed}
