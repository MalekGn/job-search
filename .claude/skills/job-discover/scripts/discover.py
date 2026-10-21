#!/usr/bin/env python3
"""
discover.py — runs every active source in config/sources.json with the same parameters.

  - type=script sources: run in parallel, raw result in <output>/_raw_<id>.json;
  - type=web sources   : listed in <output>/_web_sources.json for Claude to run the searches;
  - a rerun in the same folder never overwrites: its files get a suffix (_raw_<id>-2.json, _summary-2.json...);
  - on first run, copies the skill's default configuration into <project>/config/;
  - every run is appended to <project>/output/runs.csv, which `--since last` reads;
  - period defaults (default, widen) come from config/search.json; --resolve-only prints them and exits.

The script does not read the profile: Claude translates it into keywords, contracts, period and home city.

Standard library only.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import importlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # needed with python3 -I

from common import PROJECT_ROOT, SearchParams, today_local  # noqa: E402
from config import ensure_project_config, load_config  # noqa: E402

RUNS_LOG = PROJECT_ROOT / "output" / "runs.csv"
RUNS_COLUMNS = ["date", "since", "keywords", "contracts", "sources", "postings", "output_dir"]


def last_run_date(path: Path) -> datetime.date | None:
    """Date of the most recent run, or None if there is none."""
    if not path.exists():
        return None
    with path.open(newline="", encoding="utf-8") as f:
        dates = [r["date"][:10] for r in csv.DictReader(f) if r.get("date")]
    return datetime.date.fromisoformat(max(dates)) if dates else None


def last_days(n: int) -> datetime.date:
    """'The last n days' includes today: since today minus n-1 days."""
    return today_local() - datetime.timedelta(days=max(1, int(n)) - 1)


def resolve_since(value: str, periods: dict, runs_log: Path = RUNS_LOG) -> tuple[datetime.date, str]:
    """'YYYY-MM-DD', 'default', 'widen' (from config/search.json) or 'last' (day of the previous run, inclusive).
    Returns (date, note to print or '')."""
    default_days, widen_days = periods["default_period_days"], periods["widen_to_days"]
    if value == "default":
        return last_days(default_days), f"Default period: the last {default_days} days"
    if value == "widen":
        return last_days(widen_days), f"Widened period: the last {widen_days} days"
    if value != "last":
        return datetime.date.fromisoformat(value), ""
    last = last_run_date(runs_log)
    if last is None:
        return last_days(default_days), f"No previous run in {runs_log}: searching the last {default_days} days"
    return last, f"Since the last run: {last.isoformat()}"


def parse_keyword_sources(values: list[str]) -> dict[str, set[str]]:
    """['Activiti=free_work', 'GED=free_work,france_travail'] → {'Activiti': {'free_work'}, ...}"""
    restrict = {}
    for v in values:
        keyword, sep, ids = v.rpartition("=")
        if not sep or not keyword.strip():
            raise ValueError(v)
        restrict[keyword.strip()] = {i.strip() for i in ids.split(",") if i.strip()}
    return restrict


def keywords_for(source_id: str, keywords: list[str], restrict: dict[str, set[str]]) -> list[str]:
    """The keywords sent to one source: a keyword restricted to other sources is left out."""
    return [k for k in keywords if k not in restrict or source_id in restrict[k]]


def run_suffix(output_dir: Path, source_ids: list[str]) -> str:
    """'' for the first run in a folder, then '-2', '-3'...: a rerun (more specific keywords, widened period) adds
    files next to the first ones instead of replacing them, and merge.py reads them all."""
    n = 1
    while True:
        suffix = "" if n == 1 else f"-{n}"
        names = [f"_raw_{sid}{suffix}.json" for sid in source_ids] + [f"_summary{suffix}.json"]
        if not any((output_dir / name).exists() for name in names):
            return suffix
        n += 1


def log_run(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RUNS_COLUMNS)
        if new_file:
            w.writeheader()
        w.writerow({c: row.get(c, "") for c in RUNS_COLUMNS})


def applies(source: dict, country: str | None, domain: str | None, contracts: list[str]) -> bool:
    """A source applies if it is active and covers the country, the domain and at least one of the contracts."""
    if not source.get("active", True):
        return False
    if country and not ({"*", country} & set(source.get("countries", ["*"]))):
        return False
    if domain and not ({"*", domain} & set(source.get("domains", ["*"]))):
        return False
    if contracts and not set(contracts) & set(source.get("contracts", contracts)):
        return False
    return True


def select(sources: list[dict], args) -> list[dict]:
    chosen = [s for s in sources if applies(s, args.country, args.domain, args.contracts)]
    if args.sources:
        chosen = [s for s in chosen if s["id"] in args.sources]
    return chosen


def run_script_source(source: dict, base_params: dict) -> tuple[dict, dict]:
    module = importlib.import_module(f"sources.{source['id']}")
    extra = base_params.pop("_extra", {})
    r = SearchParams(**base_params, options=dict(source.get("options", {}), **extra))
    start = time.time()
    try:
        result = module.search(r)
    except Exception as e:  # a broken source must not stop the others
        result = {"roles": [], "warnings": [f"{source['name']}: failed ({type(e).__name__}: {e})"]}
    result["elapsed_seconds"] = round(time.time() - start, 2)
    return source, result


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Run the configured job sources")
    p.add_argument("--keywords", nargs="+",
                   help="one term per search (a multi-word term often requires all of its words)")
    p.add_argument("--exclude", nargs="*", default=[], help="terms that rule out a posting (title)")
    p.add_argument("--contracts", default="", help="freelance, permanent, other, comma-separated (empty = all)")
    p.add_argument("--since", required=True, metavar="YYYY-MM-DD|default|widen|last",
                   help="published on or after this day; 'default' / 'widen' = periods of config/search.json; "
                        "'last' = day of the previous run")
    p.add_argument("--city", default="", help="home city (used to spot nearby postings, not to filter)")
    p.add_argument("--department", default="", help="department/region of the home city, if the source supports it")
    p.add_argument("--country", default="", help="ISO country code (e.g. FR): keep only sources for this country")
    p.add_argument("--domain", default="", help="job domain (e.g. it): skips irrelevant sources")
    p.add_argument("--sources", nargs="*", help="restrict to these source ids")
    p.add_argument("--only", nargs="*", help="companies source: restrict to these slugs")
    p.add_argument("--keyword-sources", action="append", default=[], metavar="KEYWORD=id1,id2",
                   help="send this keyword only to these sources (e.g. a keyword another site's engine confuses)")
    p.add_argument("--output-dir", type=Path, help="e.g. output/2026-10-18")
    p.add_argument("--resolve-only", action="store_true",
                   help="print the resolved start date and the period settings as JSON, then exit (no search)")
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.resolve_only and (not args.keywords or not args.output_dir):
        parser.error("--keywords and --output-dir are required (unless --resolve-only)")
    args.contracts = [c.strip() for c in args.contracts.split(",") if c.strip()]
    try:
        restrict = parse_keyword_sources(args.keyword_sources)
    except ValueError as e:
        parser.error(f"--keyword-sources must look like KEYWORD=id1,id2, got: {e}")

    created = ensure_project_config(PROJECT_ROOT)
    for path in created:
        print(f"Default configuration copied: {path}", file=sys.stderr)

    periods = load_config("search.json", PROJECT_ROOT)
    try:
        since, note = resolve_since(args.since, periods)
    except ValueError:
        sys.exit(f"--since must be YYYY-MM-DD, default, widen or last, got: {args.since!r}")
    if note:
        print(note, file=sys.stderr)
    if since > today_local():
        sys.exit(f"--since is in the future: {since}")
    if args.resolve_only:
        print(json.dumps({"since": since.isoformat(), **{k: v for k, v in periods.items() if not k.startswith("_")}}))
        return

    sources = select(load_config("sources.json", PROJECT_ROOT).get("sources", []), args)
    script_sources = [s for s in sources if s.get("type") == "script"]
    web_sources = [s for s in sources if s.get("type") == "web"]
    base = {k: v for k, v in {"city": args.city, "department": args.department, "country": args.country}.items() if v}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    suffix = run_suffix(args.output_dir, [s["id"] for s in script_sources])

    def params(source: dict) -> dict:
        extra = {"only": args.only} if args.only and source["id"] == "companies" else {}
        return {"keywords": keywords_for(source["id"], args.keywords, restrict), "exclude": args.exclude,
                "contracts": args.contracts, "since": since,
                "base": base, "project_root": PROJECT_ROOT, "_extra": extra}

    summary = {"since": since.isoformat(), "keywords": args.keywords, "contracts": args.contracts,
               "config_created": created, "sources": {}, "warnings": []}
    with ThreadPoolExecutor(max_workers=max(1, len(script_sources))) as pool:
        for source, result in pool.map(lambda s: run_script_source(s, params(s)), script_sources):
            out = args.output_dir / f"_raw_{source['id']}{suffix}.json"
            out.write_text(json.dumps({"source": source["id"], "name": source["name"], "since": since.isoformat(),
                                       **result}, indent=2, ensure_ascii=False) + "\n")
            summary["sources"][source["id"]] = {"name": source["name"], "postings": len(result["roles"]),
                                                "file": str(out), "seconds": result["elapsed_seconds"]}
            summary["warnings"] += result.get("warnings", [])
            if result.get("failed_keywords"):
                summary.setdefault("failed_keywords", {})[source["id"]] = result["failed_keywords"]

    web_path = args.output_dir / f"_web_sources{suffix}.json"
    web_path.write_text(json.dumps(web_sources, indent=2, ensure_ascii=False) + "\n")
    summary["web_sources"] = [s["id"] for s in web_sources]
    (args.output_dir / f"_summary{suffix}.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    log_run(RUNS_LOG, {"date": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
                       "since": since.isoformat(), "keywords": " | ".join(args.keywords),
                       "contracts": ",".join(args.contracts), "sources": ",".join(summary["sources"]),
                       "postings": sum(s["postings"] for s in summary["sources"].values()),
                       "output_dir": str(args.output_dir)})

    print(f"Period: since {since.isoformat()}")
    for keyword, ids in restrict.items():
        print(f"  \"{keyword}\" sent only to: {', '.join(sorted(ids))}")
    for sid, s in summary["sources"].items():
        print(f"  {s['name']:<45} {s['postings']:>5} postings  ({s['seconds']} s) → {s['file']}")
    print(f"  Web sources to query: {', '.join(summary['web_sources']) or 'none'} → {web_path}")
    for w in summary["warnings"]:
        print(f"  ⚠ {w}")
    for sid, kws in summary.get("failed_keywords", {}).items():
        terms = " ".join(f'"{k}"' if " " in k else k for k in kws)
        print(f"  ✗ {sid}: still failing after retries for {terms}. Retry once, a minute from now, with the same "
              f"arguments plus --sources {sid} --keywords {terms}")


if __name__ == "__main__":
    main()
