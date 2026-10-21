#!/usr/bin/env python3
"""
tracker.py — tracking of discovered postings in output/tracker.csv.

Commands:
  add   --company --role --contract --url [--score] [--source] [--status] [--notes]
        (skips the row if the URL is already tracked, and says so)
  set-status URL STATUS [--notes]
                             updates the status of a tracked posting (e.g. applied, interview, rejected, ignored)
  list  [--status]           prints the rows
  urls                       prints the normalized URLs already tracked (one per line)
  has   URL                  exit code 0 if tracked, 1 otherwise

URLs are compared after normalization (tracking parameters utm_*, ref, etc. removed, trailing slash
removed) so that one posting seen through two links is only counted once.
"""
from __future__ import annotations

import argparse
import csv
import datetime
import os
import sys
import urllib.parse
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_PROJECT_ROOT = SCRIPT_DIR.parents[3]
PROJECT_ROOT = Path(os.environ.get("JOB_DISCOVER_ROOT", DEFAULT_PROJECT_ROOT))
DEFAULT_TRACKER = PROJECT_ROOT / "output" / "tracker.csv"

COLUMNS = ["date", "company", "role", "contract", "url", "score", "source", "status", "notes"]
TRACKING_PARAMS = {"ref", "source", "src", "trk", "trackingid", "refid", "from", "origin", "gh_src", "lever-source"}


def normalize_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url.strip())
    query = [(k, v) for k, v in urllib.parse.parse_qsl(parts.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in TRACKING_PARAMS]
    path = parts.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path,
                                    urllib.parse.urlencode(query), ""))


def read_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def tracked_urls(path: Path) -> set[str]:
    return {normalize_url(r["url"]) for r in read_rows(path) if r.get("url")}


def add(path: Path, row: dict) -> bool:
    """Appends the row; returns False if the URL is already tracked."""
    if normalize_url(row["url"]) in tracked_urls(path):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        if new_file:
            w.writeheader()
        w.writerow({c: row.get(c, "") for c in COLUMNS})
    return True


def set_status(path: Path, url: str, status: str, notes: str | None = None) -> bool:
    """Updates the status (and optionally the notes) of a tracked posting; returns False if it isn't tracked."""
    rows = read_rows(path)
    key = normalize_url(url)
    matched = [r for r in rows if r.get("url") and normalize_url(r["url"]) == key]
    if not matched:
        return False
    for r in matched:
        r["status"] = status
        if notes is not None:
            r["notes"] = notes
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows({c: r.get(c, "") for c in COLUMNS} for r in rows)
    return True


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Tracking of discovered postings")
    p.add_argument("--file", type=Path, default=DEFAULT_TRACKER, help=f"default: {DEFAULT_TRACKER}")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add")
    a.add_argument("--company", required=True)
    a.add_argument("--role", required=True)
    a.add_argument("--contract", required=True, help="freelance, permanent or other")
    a.add_argument("--url", required=True)
    a.add_argument("--score", default="")
    a.add_argument("--source", default="")
    a.add_argument("--status", default="to review")
    a.add_argument("--notes", default="")

    s = sub.add_parser("set-status")
    s.add_argument("url")
    s.add_argument("status", help="e.g. to review, applied, interview, rejected, ignored")
    s.add_argument("--notes")

    l = sub.add_parser("list")
    l.add_argument("--status")

    sub.add_parser("urls")

    h = sub.add_parser("has")
    h.add_argument("url")
    return p


def main() -> None:
    args = build_parser().parse_args()
    path = args.file

    if args.cmd == "add":
        row = {
            "date": datetime.date.today().isoformat(),
            "company": args.company, "role": args.role, "contract": args.contract,
            "url": args.url, "score": args.score, "source": args.source,
            "status": args.status, "notes": args.notes,
        }
        if add(path, row):
            print(f"Added: {args.company} - {args.role}")
        else:
            print(f"Already tracked, skipped: {args.url}")
    elif args.cmd == "set-status":
        if not set_status(path, args.url, args.status, args.notes):
            sys.exit(f"Not tracked: {args.url}")
        print(f"Status set to \"{args.status}\": {args.url}")
    elif args.cmd == "list":
        for r in read_rows(path):
            if args.status and r.get("status") != args.status:
                continue
            print(f"{r['date']} | {r['status']:<10} | {r['score']:>2} | {r['contract']:<9} | "
                  f"{r['company']} - {r['role']} | {r['url']}")
    elif args.cmd == "urls":
        for u in sorted(tracked_urls(path)):
            print(u)
    elif args.cmd == "has":
        sys.exit(0 if normalize_url(args.url) in tracked_urls(path) else 1)


if __name__ == "__main__":
    main()
