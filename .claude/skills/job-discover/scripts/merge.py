#!/usr/bin/env python3
"""
merge.py — merges every _raw_*.json of a run into one short _candidates.json for Claude to read.

  - drops the noise of ambiguous keywords: a keyword whose results on a source almost never contain it (a search
    engine matching "activiti" to "activité"), see ambiguous_keywords();
  - deduplicates by normalized URL, keeping the richest version (script sources before web) and merging
    matched keywords and the nearby flag;
  - marks each posting new or already seen (output/tracker.csv), with its tracker status;
  - flags postings published before the requested period (outside_period), which a widened rerun brings in;
  - sets aside postings without a publication date (unknown date, unscored);
  - groups new postings with the same company and the same title (one series counts as one posting) and ranks
    the groups by a relevance score (see relevance());
  - keeps the first --top groups as compact candidates to score, plus every home-area posting with a keyword in its
    title, the rest as a plain list;
  - adds each posting's region (regions.py) and counts new postings per region, to group the report;
  - flags candidate pairs with near-identical titles (possibly the same mission via two intermediaries);
  - collects source warnings, ATS mapping updates and web-only companies.

Web postings found by Claude go in <output>/_raw_web.json, same format as the other raw files:
  {"source": "web", "roles": [{"company", "title", "url", "source", "contracts", "published_at", ...}]}

Standard library only.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # needed with python3 -I

import tracker  # noqa: E402
from regions import region_of  # noqa: E402

DESCRIPTION_CHARS = 300
CANDIDATE_FIELDS = ("company", "title", "url", "source", "contracts", "location", "remote", "pay", "published_at",
                    "region", "outside_period", "republished", "nearby", "home", "matched_keywords", "description",
                    "duration", "experience")
LIST_FIELDS = ("company", "title", "url", "source", "contracts", "location", "region", "published_at", "outside_period",
               "nearby", "home", "same_title")
ANONYMOUS = {"", "(not disclosed)"}
DEPARTMENT_RE = re.compile(r"^\s*(\d{2,3}|2[ab])\b", re.IGNORECASE)  # "78 - Magny-les-Hameaux"
TITLE_NOISE_RE = re.compile(r"\(?\b[hf]\s*/\s*[hf]\b\)?|\(?\bm\s*/\s*f\b\)?|[^\w\s]", re.IGNORECASE)


def load_raw(output_dir: Path) -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(output_dir.glob("_raw_*.json"))]


AMBIGUOUS_MIN_RESULTS, AMBIGUOUS_MAX_SHARE = 20, 0.10


def contains_keyword(o: dict, keyword: str) -> bool:
    """All the keyword's words appear in the title or the description excerpt."""
    return words(keyword) <= words(o.get("title", "") + " " + o.get("description", ""))


def ambiguous_keywords(roles: list[dict]) -> list[dict]:
    """(source, keyword) pairs whose results almost never contain the keyword: the site's engine matched something
    else. Per source, because one engine may match exactly where another doesn't. Real keywords stay well above
    the threshold even though descriptions are only excerpts (Java ~56%, Kafka ~35% in a real run)."""
    found: dict[tuple[str, str], list[int]] = {}
    for o in roles:
        for kw in o.get("matched_keywords", []):
            stats = found.setdefault((o.get("source", ""), kw), [0, 0])
            stats[0] += 1
            stats[1] += contains_keyword(o, kw)
    return [{"keyword": kw, "source": source, "results": n, "literal_share": round(literal / n, 2)}
            for (source, kw), (n, literal) in found.items()
            if n >= AMBIGUOUS_MIN_RESULTS and literal / n < AMBIGUOUS_MAX_SHARE]


def drop_ambiguous(roles: list[dict], flagged: list[dict]) -> list[dict]:
    """Removes postings found only by keywords flagged for their source and not containing any of them; a posting
    also found by another keyword, or that does contain the word, stays. Adds the dropped count to each flag."""
    bad = {(f["source"], f["keyword"]) for f in flagged}
    dropped: dict[tuple[str, str], int] = {}
    kept = []
    for o in roles:
        kws = o.get("matched_keywords", [])
        mine = [(o.get("source", ""), kw) for kw in kws]
        if kws and all(m in bad for m in mine) and not any(contains_keyword(o, kw) for kw in kws):
            for m in mine:
                dropped[m] = dropped.get(m, 0) + 1
            continue
        kept.append(o)
    for f in flagged:
        f["dropped"] = dropped.get((f["source"], f["keyword"]), 0)
    return kept


def richness(o: dict) -> tuple[bool, int]:
    """Script sources beat web results; then the version with the most filled-in fields wins."""
    return o.get("source") != "web", sum(1 for v in o.values() if v not in ("", None, [], False))


def dedupe(roles: list[dict]) -> list[dict]:
    by_url: dict[str, dict] = {}
    for o in roles:
        if not o.get("url"):
            continue
        key = tracker.normalize_url(o["url"])
        kept = by_url.get(key)
        if kept is None:
            by_url[key] = dict(o)
            continue
        best, other = (o, kept) if richness(o) > richness(kept) else (kept, o)
        merged = dict(best)
        merged["matched_keywords"] = list(dict.fromkeys(best.get("matched_keywords", []) +
                                                        other.get("matched_keywords", [])))
        merged["nearby"] = bool(best.get("nearby") or other.get("nearby"))
        merged["also_on"] = sorted({other.get("source", "")} | set(other.get("also_on", [])) - {""})
        by_url[key] = merged
    return list(by_url.values())


def words(text: str) -> set[str]:
    """Lowercase words without accents: 'Développeur Java/Spring' → {'developpeur', 'java', 'spring'}."""
    plain = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    return {w for w in re.findall(r"[a-z0-9+#.]+", plain) if len(w) > 1}


def in_area(o: dict, terms: list[str]) -> bool:
    """Location in one of these departments (leading code, e.g. '78 - Magny-les-Hameaux') or towns."""
    location = o.get("location", "")
    m = DEPARTMENT_RE.match(location)
    if m and m.group(1).lower() in {t.lower() for t in terms}:
        return True
    return bool(words(location) & {w for t in terms if not t.isdigit() for w in words(t)})


SPECIFIC_POINTS, GENERIC_POINTS, TITLE_POINTS_CAP = 3, 1, 9
GENERIC_SHARE, GENERIC_MIN_POSTINGS = 0.2, 20
HOME_BONUS, NEIGHBOUR_BONUS, HOME_RESERVED_MAX = 4, 2, 20


def generic_words(new: list[dict], keyword_words: set[str]) -> set[str]:
    """Keyword words found in more than GENERIC_SHARE of this run's titles: they don't tell postings apart
    ('développeur' when searching 'développeur Java'). Measured on the run itself, so it works for any occupation."""
    if len(new) < GENERIC_MIN_POSTINGS:
        return set()
    counts: dict[str, int] = {}
    for o in new:
        for w in words(o.get("title", "")) & keyword_words:
            counts[w] = counts.get(w, 0) + 1
    return {w for w, n in counts.items() if n > GENERIC_SHARE * len(new)}


def relevance(o: dict, keyword_words: set[str], generic: set[str] = frozenset()) -> int:
    """Pre-sort score, not the fit score Claude gives later.

    Keyword words in the title weigh most: a title says what the posting is about, while a keyword matched somewhere
    in the text says little (+1 at most). Words are counted once, so the overlapping searches 'Tech Lead', 'Lead
    Java' and 'Tech Lead Java' add up to 3 words, not 7 matches. A specific word earns 3, a generic one 1, capped at
    9 so a title stuffed with keywords can't push local postings out. Home area +4, neighbouring area +2 (home
    postings with a title keyword are also always kept, see select()). Small
    penalties for anonymous listings (-1) and republications (-2)."""
    in_title = words(o.get("title", "")) & keyword_words
    elsewhere = words(" ".join(o.get("matched_keywords", []))) & keyword_words - in_title
    title_points = sum(GENERIC_POINTS if w in generic else SPECIFIC_POINTS for w in in_title)
    return (min(title_points, TITLE_POINTS_CAP) + min(len(elsewhere), 1)
            + (HOME_BONUS if o.get("home") else NEIGHBOUR_BONUS if o.get("nearby") else 0)
            - (o.get("company", "") in ANONYMOUS) - 2 * bool(o.get("republished")))


def rank(new: list[dict], home: list[str], near: list[str], country: str = "") -> list[dict]:
    """One entry per (company, title) group, best first; the others of a group are listed in its 'same_title'.
    Sources flag postings of the home department themselves (nearby=True): those count as home."""
    keyword_words = {w for o in new for kw in o.get("matched_keywords", []) for w in words(kw)}
    generic = generic_words(new, keyword_words)
    for o in new:
        o["home"] = bool(o.get("nearby")) or in_area(o, home)
        o["nearby"] = o["home"] or in_area(o, near)
        o["region"] = region_of(o.get("location", ""), o.get("remote", ""), country)
        o["_title_hit"] = bool(words(o.get("title", "")) & keyword_words)
        o["_score"] = relevance(o, keyword_words, generic)
    new.sort(key=lambda o: o.get("published_at", "")[:10], reverse=True)
    new.sort(key=lambda o: -o["_score"])  # stable: most recent first at equal score
    groups: dict[tuple[str, str], dict] = {}
    for o in new:
        key = (o.get("company", "").lower(), normalize_title(o.get("title", "")))
        if key in groups:
            groups[key].setdefault("same_title", []).append(o["url"])
        else:
            groups[key] = o
    return list(groups.values())


def compact(o: dict, fields: tuple[str, ...]) -> dict:
    out = {k: o[k] for k in fields if o.get(k) not in (None, "", [], False)}
    if "description" in out and len(out["description"]) > DESCRIPTION_CHARS:
        out["description"] = out["description"][:DESCRIPTION_CHARS] + "…"
    return out


def normalize_title(title: str) -> str:
    return " ".join(TITLE_NOISE_RE.sub(" ", title.lower()).split())


def possible_duplicates(candidates: list[dict], threshold: float = 0.85) -> list[list[str]]:
    """Pairs of candidates whose titles are near-identical: same mission via two intermediaries, or a repost."""
    pairs = []
    titles = [normalize_title(c.get("title", "")) for c in candidates]
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            if titles[i] and difflib.SequenceMatcher(None, titles[i], titles[j]).ratio() >= threshold:
                pairs.append([candidates[i]["url"], candidates[j]["url"]])
    return pairs


def select(ranked: list[dict], top: int) -> tuple[list[dict], list[dict]]:
    """The first `top` groups, plus every home-area posting with a keyword in its title (up to HOME_RESERVED_MAX):
    there are few of them and they are what the user can least afford to miss."""
    chosen = ranked[:top]
    reserved = [o for o in ranked[top:] if o["home"] and o["_title_hit"]][:HOME_RESERVED_MAX]
    ids = {id(o) for o in chosen + reserved}
    candidates = sorted(chosen + reserved, key=lambda o: -o["_score"])
    return candidates, [o for o in ranked if id(o) not in ids]


def merge(output_dir: Path, tracker_path: Path, top: int, near: list[str] | None = None,
          home: list[str] | None = None, country: str = "") -> dict:
    raws = load_raw(output_dir)
    raw_roles = [o for raw in raws for o in raw.get("roles", [])]
    flagged = ambiguous_keywords(raw_roles)
    kept = drop_ambiguous(raw_roles, flagged)
    roles = dedupe(kept)
    statuses = {tracker.normalize_url(r["url"]): r.get("status", "") for r in tracker.read_rows(tracker_path)
                if r.get("url")}

    # The requested period is the latest start date: a widened rerun (--since widen) starts earlier.
    since = max((raw["since"] for raw in raws if raw.get("since")), default="")
    seen, unknown_date, new = [], [], []
    for o in roles:
        status = statuses.get(tracker.normalize_url(o["url"]))
        if status is not None:
            seen.append(compact(o, LIST_FIELDS) | {"status": status})
        elif not o.get("published_at"):
            unknown_date.append(compact(o, LIST_FIELDS))
        else:
            if since and o["published_at"][:10] < since:
                o["outside_period"] = True
            new.append(o)
    ranked = rank(new, home or [], near or [], country)
    chosen, rest = select(ranked, top)
    candidates = [compact(o, CANDIDATE_FIELDS + ("same_title",)) for o in chosen]
    by_region: dict[str, int] = {}
    for o in new:
        by_region[o["region"]] = by_region.get(o["region"], 0) + 1

    by_source: dict[str, int] = {}
    for raw in raws:  # a source searched twice (rerun) has several raw files: add them up
        by_source[raw.get("source", "?")] = by_source.get(raw.get("source", "?"), 0) + len(raw.get("roles", []))
    by_contract: dict[str, int] = {}
    for o in new:
        for c in o.get("contracts") or ["unknown"]:
            by_contract[c] = by_contract.get(c, 0) + 1

    return {
        "since": since,
        "counts": {"total": len(roles), "new": len(new), "new_by_contract": by_contract,
                   "already_seen": len(seen), "unknown_date": len(unknown_date),
                   "dropped_ambiguous": len(raw_roles) - len(kept)},
        "ambiguous_keywords": flagged,
        "postings_by_source": by_source,
        "new_by_region": dict(sorted(by_region.items(), key=lambda kv: -kv[1])),
        "candidates": candidates,
        "possible_duplicates": possible_duplicates(candidates),
        "others": [compact(o, LIST_FIELDS) for o in rest],
        "unknown_date": unknown_date,
        "already_seen": seen,
        "warnings": [w for raw in raws for w in raw.get("warnings", [])],
        "mapping_updates": [u for raw in raws for u in raw.get("mapping_updates", [])],
        "web_companies": [c for raw in raws for c in raw.get("web_companies", [])],
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Merge the raw results of a run into _candidates.json")
    p.add_argument("output_dir", type=Path, help="e.g. output/2026-10-18")
    p.add_argument("--top", type=int, default=40, help="number of ranked groups kept as candidates")
    p.add_argument("--home", nargs="*", default=[], help="home department and town, e.g. 95 Cergy")
    p.add_argument("--near", nargs="*", default=[], help="neighbouring departments and towns, e.g. 78 92 93 77 60 27")
    p.add_argument("--country", default="", help="ISO code (e.g. FR): which region table to use")
    p.add_argument("--tracker", type=Path, default=tracker.DEFAULT_TRACKER)
    args = p.parse_args()

    result = merge(args.output_dir, args.tracker, args.top, args.near, args.home, args.country)
    out = args.output_dir / "_candidates.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    c = result["counts"]
    print(f"{c['total']} postings after deduplication · {c['new']} new {c['new_by_contract']} · "
          f"{c['already_seen']} already seen · {c['unknown_date']} unknown date")
    for f in result["ambiguous_keywords"]:
        print(f"⚠ \"{f['keyword']}\" looks ambiguous on {f['source']}: {f['literal_share']:.0%} of {f['results']} "
              f"results contain it, {f['dropped']} dropped")
    print(f"{len(result['candidates'])} candidates to score, {len(result['possible_duplicates'])} possible "
          f"duplicate pairs → {out}")


if __name__ == "__main__":
    main()
