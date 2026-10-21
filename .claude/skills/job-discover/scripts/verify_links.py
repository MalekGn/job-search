#!/usr/bin/env python3
"""
verify_links.py — checks that every link in a report comes from the run's data, not from memory.

  verify_links.py output/2026-10-18/discovery.md output/2026-10-18 [--allow URL ...]

A link is accepted if its normalized URL appears in a JSON file of the output folder (_raw_*.json, including
_raw_web.json where Claude records the pages it opened) or in output/tracker.csv ("Already seen" section).
--allow accepts extra non-posting links (e.g. an API signup page cited in a warning).
Exit code 0 if every link is known, 1 otherwise (unknown links printed).

Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # needed with python3 -I

import tracker  # noqa: E402

LINK_RE = re.compile(r"\]\((https?://[^)\s]+)\)|<(https?://[^>\s]+)>")
URL_RE = re.compile(r"https?://[^\s\"'<>)\]]+")


def report_links(report: str) -> list[str]:
    return list(dict.fromkeys(a or b for a, b in LINK_RE.findall(report)))


def collect_strings(value, out: set[str]) -> None:
    if isinstance(value, str):
        out.update(URL_RE.findall(value))
    elif isinstance(value, dict):
        for v in value.values():
            collect_strings(v, out)
    elif isinstance(value, list):
        for v in value:
            collect_strings(v, out)


def known_urls(output_dir: Path, tracker_path: Path) -> set[str]:
    urls: set[str] = set()
    for path in output_dir.glob("*.json"):
        try:
            collect_strings(json.loads(path.read_text()), urls)
        except json.JSONDecodeError:
            continue
    return {tracker.normalize_url(u) for u in urls} | tracker.tracked_urls(tracker_path)


def unknown_links(report: str, output_dir: Path, tracker_path: Path, allow: list[str]) -> list[str]:
    known = known_urls(output_dir, tracker_path) | {tracker.normalize_url(u) for u in allow}
    return [u for u in report_links(report) if tracker.normalize_url(u) not in known]


def main() -> None:
    p = argparse.ArgumentParser(description="Check that every report link comes from the run's data")
    p.add_argument("report", type=Path)
    p.add_argument("output_dir", type=Path)
    p.add_argument("--allow", nargs="*", default=[], help="extra accepted links (non-posting pages)")
    p.add_argument("--tracker", type=Path, default=tracker.DEFAULT_TRACKER)
    args = p.parse_args()

    report = args.report.read_text()
    bad = unknown_links(report, args.output_dir, args.tracker, args.allow)
    total = len(report_links(report))
    if bad:
        print(f"{len(bad)} of {total} links are not in the run's data:")
        for u in bad:
            print(f"  ✗ {u}")
        sys.exit(1)
    print(f"All {total} links come from the run's data.")


if __name__ == "__main__":
    main()
