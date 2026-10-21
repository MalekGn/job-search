# Job discovery - {date}

<!-- Write the report in the output language (see SKILL.md, "Language"): translate every heading and label below,
     and use local terms where they are expected (French: "Missions freelance", "Postes CDI", "TJM"). -->

**Period:** postings published since {DD/MM/YYYY} ({label: today / this week / last N days...})
**Sources:** {name of each script source} ({n}{, degraded mode if applicable}) · {N} followed companies ({n}) · {K} web searches
**Found:** {total} relevant postings · **New:** {new} ({f} freelance, {p} permanent)
**Filter applied:** {argument or "none"}
**Criteria:** see criteria_used.md{; differs from the saved criteria: {what changed}, if applicable}

## Overview
<!-- One table per entry of report_group_by (config/search.json), in that order; scored postings only. A posting
     can sit in several technology rows. Numbers refer to the entries below (F1 = freelance #1, P2 = permanent #2). -->

### By region
| Region | Postings | Best score | Entries |
|---|---|---|---|
| {region} {📍 if home or neighbouring area} | {n} | {best}/10 | {F1, P3, P7} |

### By role
| Role | Postings | Best score | Entries |
|---|---|---|---|
| {target role from criteria.md, or "Other"} | {n} | {best}/10 | {P1, P2} |

### By technology
| Technology | Postings | Best score | Entries |
|---|---|---|---|
| {profile skill found in the posting} | {n} | {best}/10 | {F1, P1, P4} |

## Freelance missions

### F1. [{Company} - {Title}]({url})
- **Score:** {n}/10 - {one-line justification}
- **Tags:** {region} · {role} · {technologies}
- **Daily rate:** {amount or "not disclosed"}
- **Location:** {location} · {remote/hybrid/on site} {📍 near {home city}, if applicable}
- **Published:** {date} {· republished, created DD/MM, if applicable} · **Source:** {source}

### F2. [Same mission via several intermediaries - {Title}]({url of the most complete one})
- **Score:** {n}/10 - {justification}
- **Published by:** [{Intermediary A}]({url}) ({daily rate}) · [{Intermediary B}]({url}) ({daily rate}) - apply through only one
- **Location:** {location} · **Published:** {date}

### F3. ...

## Permanent roles

### P1. [{Company} - {Title}]({url})
- **Score:** {n}/10 - {justification}
- **Tags:** {region} · {role} · {technologies}
- **Salary:** {range or "not disclosed"}
- **Location:** {location} · {remote/hybrid/on site} {📍 near {home city}, if applicable}
- **Published:** {date} {· republished, created DD/MM, if applicable} · **Source:** {source}

## Outside the period (only if the period contains fewer than `widen_below` postings)
> Published since {DD/MM}, outside the requested period.

### O1. [{Company} - {Title}]({url})
- **Score:** {n}/10 - {justification} · **Published:** {date} · {contract} · {daily rate/salary}

## Unknown date (unscored)
- [{Company} - {Title}]({url}) · {contract} · {location}

## Other postings (unscored)
<!-- Grouped by region (merge.py's `region`), regions in the order of new_by_region; home region first. -->
### {Region} ({n})
- [{Company} - {Title}]({url}) · {contract} · {location}

## Already seen (in the tracker)
- [{Company} - {Title}]({url}) · status: {status}

## Automatic updates
- {company}: ATS found → {ats}

## Warnings
- {source or company}: {problem and how to fix it}

## Next actions
1. {e.g. Review the 3 postings scored 8+ this week}
2. {e.g. Create the API key for a source in degraded mode to widen coverage}
