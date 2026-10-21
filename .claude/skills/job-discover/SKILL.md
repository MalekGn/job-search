---
name: job-discover
description: Finds job postings and freelance missions that fit the user's profile (CV and criteria read from profile/, whatever their format) by querying the configured sources - job boards, public APIs, careers pages of followed companies -, scores each posting against the profile, writes a dated report and keeps track of postings already seen. Use it whenever the user is looking for jobs, missions or contracts, or wants to know who is hiring, whatever the occupation, period ("today", "this week"), contract type or company, even if they never say "job posting" - and in any language (e.g. "trouve-moi des missions freelance", "des offres CDI cette semaine ?"). Also use it to add a company or a source to watch, or to record that the user applied to or dismissed a posting it found. Not for writing an application, analysing a posting the user already has, or preparing an interview.
allowed-tools: WebSearch WebFetch Read Write Edit AskUserQuestion Bash(python3 *)
argument-hint: "[optional filter: keyword, period, city, freelance, permanent, company]"
---

# job-discover

**Goal:** find the postings the user hasn't seen yet, ranked by fit with their profile, with direct links. The skill
feeds the top of the application funnel; it never applies.

Paths are relative to the project root (the folder that contains `profile/`). Scripts: `.claude/skills/job-discover/scripts/`
(Python standard library only). The skill contains nothing specific to an occupation or a source: the profile says
what to look for, the configuration says where.

## Language

These instructions are in English, but they say nothing about the language you write in. Pick the **output
language** - for `profile/criteria.md`, the report, the final summary and anything you say to the user - in this
order:

1. **An explicit request** wins ("write the report in English", "en français stp").
2. Otherwise, **the language of the user's request**: if they wrote "trouve-moi des missions cette semaine", answer
   in French.
3. If the request carries no language signal (empty argument, a bare company name or keyword, a slash command
   alone), use **the language of the profile** (the CV and `criteria.md`).

The templates in `assets/` are in English: translate their headings and labels into the output language rather
than mixing languages in one report. Use local terms where they are what the user expects (in French: "CDI", "TJM",
"Postes CDI", "Missions freelance").

The output language is not the **search language**. Keywords, job titles and web queries follow the language of the
job market being searched - French titles for postings in France, whatever language the report is written in -
because that is the language the postings are written in. Script identifiers and arguments (`permanent`,
`freelance`, `--since`...) and the values stored in the tracker's `contract` and `status` columns are always in
English, so later runs can read them; they never appear as-is in the report.

## User input

Argument received: `$ARGUMENTS`

Empty → full search. Otherwise it is a filter: keyword, period, city, `freelance` or `permanent`, company name.

## Step 1 - Read the profile

Read **all** files in `profile/`, whatever their format (Read handles text, markdown and PDF; for a .docx, use the
docx skill or extract the text). No format is imposed: understand the profile the way a recruiter would.

Then look for `profile/criteria.md`:

- **Missing (first run)**: read `assets/criteria_template.md`, fill it in from the profile, write
  `profile/criteria.md`, show it and **stop** so the user can validate it. A CV rarely says which contract or
  which companies the person is after; a search on guessed criteria will have to be redone. Mark what you guessed.
  Once the user has validated `criteria.md`, carry on to the confirmation of step 2 (table + AskUserQuestion) before
  searching, like on every other run.
- **Present**: it is authoritative. If it contradicts the CV, follow `criteria.md`: it is the most recent intent.

Then read the period settings (this also creates the project's `config/` on first use):

```bash
python3 .claude/skills/job-discover/scripts/discover.py --since default --resolve-only
```

It prints `config/search.json` as JSON: `default_period_days` (period when the request gives none),
`widen_below` and `widen_to_days` (when a search finds too few postings, how far to widen it), `confirmed`, and the
resulting start date. These numbers live in the config, not in these instructions: always take them from there.
**If `confirmed` is false**, this is the first search with these settings: show them to the user in plain words
("with no period given, I search the last {default_period_days} days; if I find fewer than {widen_below}
postings, I widen to the last {widen_to_days} days") in the confirmation table of step 2, validated through the same
prompt as the criteria. Once they answer, write their values to
`config/search.json` with `"confirmed": true`. Later, "search 3 days by default" or "widen to a month" → update the
same file.

## Step 2 - Build the search parameters

- **Keywords** (3 to 8): target job titles and distinctive skills from the profile. Prefer discriminating terms; a
  title that is too generic brings back anything and everything. Start from the priority keywords of `criteria.md` and
  keep them all: the user chose them. Don't drop one in advance because it *might* be ambiguous: that is measured
  from the results (step 5) and settled with the user (step 7). A keyword that `criteria.md` limits to some sources
  (step 7) is passed as `--keyword-sources Activiti=free_work` and left out of the other sources' web queries; show
  the limit in the confirmation table.
- **Exclusions**: internships, apprenticeships (in the market's language, e.g. `stage alternance` in France), and
  whatever `criteria.md` excludes.
- **Contracts**: `freelance`, `permanent` (CDI in France), `other` (fixed-term, temp...), or several.
- **Domain** of the occupation (e.g. `it`, `health`, `design`) and **country** (ISO code, e.g. `FR`): they are used to
  choose the relevant sources, not to filter postings.
- **Home city** and, if the country has them, its department/region: this is **not a filter**. We search everywhere
  and no posting is discarded for its location; the city is used to spot nearby postings (score bonus) and some
  sources query the department separately so that no local posting goes unnoticed.
- **No pay filter**: daily rate and salary are shown when known, never used to discard a posting or lower its score.
- **Period**: start date `YYYY-MM-DD` (inclusive). Derive it from the request, don't fix it in advance: "today" =
  today's date; "since yesterday" = yesterday; "this week" = 6 days ago; "since Monday" = this Monday; "this month" =
  the 1st of the month; "since last time" = `--since last` (the script reads the day of the previous run from
  `output/runs.csv`; tracker rows are not a reliable clock, since a run that finds nothing new adds none). With no
  indication: `--since default` (step 1; `--since last` falls back to it too when there is no previous run). "The last N days" always counts today as one of them, so it starts on today minus N-1 days; the
  script applies the same rule. The **publication** date is what counts (careers pages only have an update date:
  say so if the period is short).

### Confirm the criteria before every search

Before running anything, show the user the criteria this search will use and **stop** until they answer. This is
**mandatory on every launch that runs a search**, with no exception: auto mode, scheduled or `/loop` runs, and
requests such as "go" or "same criteria as usual" all still ask. Auto mode never authorises skipping it, and no search
(`discover.py`, web searches) runs before the user's answer. Each search is its own: the user may want a different period, contract or city today than last week without touching their saved
preferences, and a search on criteria they would have changed wastes the run and pollutes the tracker.

Show one short table with the current value of each criterion:

| Criterion | Value for this search |
|---|---|
| Target roles | from `criteria.md` |
| Search keywords | the 3-8 terms built above |
| Exclusions | |
| Contracts | |
| Domain and country | |
| Home city (department) | |
| Target companies | or "none" |
| To avoid | |
| Period | e.g. "since 14/10/2026 (this week)" |
| Period settings | only while `confirmed` is false (step 1) |

Values that come from the request rather than from `criteria.md` (a period, "freelance only", a city) are already
applied in the table and marked as such, so the user sees exactly what will run. Then call **AskUserQuestion** with
one question (e.g. "Use these criteria for this search?", in the output language), not one per criterion, with these
options:

- **Confirm**: search with these values.
- **Change for this search only**: the user gives the changes ("add Lyon", "only permanent", "drop the keyword X") in
  the free-text answer. Apply them to this search; if the change is large or ambiguous, show the updated table and ask
  again.
- **Change and save as default**: apply the changes, write them to `criteria.md`, then search.

When the user changes something without saying where it should go, keep it for this search only: a one-off "only
freelance this week" should not quietly become a permanent preference.

If AskUserQuestion is unavailable (non-interactive run), show the table, ask the same question in text and **stop**
without searching.

The only runs that skip the confirmation are requests that run **no search**: adding a company or a source, changing
saved criteria, updating a tracker status.

**Followed companies:** once the criteria are confirmed, sync the companies section of `criteria.md` to
`output/companies.json`. A company added for this search only is not synced (every later search would poll it): cover
it with a targeted web search in step 4 instead. Format:
`{"companies": [{"slug": "acme", "display": "Acme", "tier": 1, "ats": null, "board_id": "acme"}]}`. Add new ones with
`"ats": null`: the script will find their recruiting tool on its own. Never delete a verified entry
(`"confidence": "probe_verified"`).

## Step 3 - Script sources

Create the run folder `output/YYYY-MM-DD/`; if a search already ran today, use `output/YYYY-MM-DD-2/` (then `-3`...)
so that two searches with different criteria don't overwrite each other. Below, `output/YYYY-MM-DD` means this run's
folder. Save the confirmed table there as `criteria_used.md`: the report then says what it was searched on, even when
the criteria differ from `criteria.md`. Then run:

```bash
python3 .claude/skills/job-discover/scripts/discover.py \
  --keywords {keyword 1} {keyword 2} "{target title}" \
  --exclude stage alternance \
  --contracts freelance,permanent --since {YYYY-MM-DD | default | last} \
  --city {home city} --department {department} --country {FR} --domain {domain} \
  --output-dir output/YYYY-MM-DD
```

The script reads `config/sources.json` (copied from the skill on first run), keeps the active sources that cover the
country, domain and contracts, and runs the `script` ones in parallel:

- one `_raw_<source>.json` file per source, in the common format (company, title, URL, location, contracts, pay,
  remote, date, description excerpt, matched keywords);
- `_web_sources.json`: the `web` sources to query in step 4;
- a summary on screen, with warnings.

Include the market's own wording of the target titles (see *Language*), e.g. in France "leader technique" or
"référent technique" for "Tech Lead": postings are pre-sorted on the keywords found in their title (step 5), so a
title written in local terms that no keyword matches can drop out of the candidates.

Pass **one term per keyword**: most site search engines require every word of a term, so a combined term ("A B")
only brings back postings that mention both. `--sources id1 id2` restricts to some sources; `--only slug1 slug2`
restricts the followed companies.

Read the warnings, they change how the report should be read. Every rerun below goes into the same `--output-dir`:
a rerun never overwrites, its files get a suffix (`_raw_<id>-2.json`) and `merge.py` reads them all.
- "**exceeds N results**": postings from the period are missing. Rerun that source with more specific keywords (or
  a larger `max_pages` in its config if it is the page cap, not a site limit), with `--sources <id>`.
- **ambiguous keyword**: some site engines match similar words (a little-known tool name becomes a common word, e.g.
  "activiti" → "activité"). Don't judge it from the counts here and don't rerun with a replacement: step 5 drops
  the noise and step 7 settles the keyword with the user.
- source in **degraded mode** (e.g. no API key): say so in the report, with how to fix it.
- **still failing after retries** (`✗` line, `failed_keywords` in `_summary.json`): the sources already retry server
  errors several times, so these keywords were not searched at all. Retry them **once**, about a minute later, with
  the command the script prints (same arguments, `--sources <id> --keywords <failed ones>`). If they fail again,
  stop retrying (see *Rules of conduct*) and list them in the report's warnings as not searched.

A failing source does not stop the others.

## Step 4 - Web sources

For each source in `_web_sources.json`, run its `queries`, substituting `{keyword}`, `{title}` and `{city}` (3 to 6
searches in total, prioritising the sources that cover the requested contracts). Add a
`site:{careers-domain} {keyword}` search for every followed company switched to `"ats": "web"`. Sources already
queried by script are not searched on the web: their pages are often rendered in JavaScript and look empty.

The `site:` operator isn't always honoured: judge results by their actual URL. Open (WebFetch) the most promising
ones. Keep only **real postings** still open and published within the period, or without a visible date (step 5
lists those apart, unscored). Discard listicles, generic careers pages and expired postings (see *Rules of
conduct*).

Record every posting you keep in `output/YYYY-MM-DD/_raw_web.json`, in the same format as the script sources, with
the URL copied from the page you opened:

```json
{"source": "web", "roles": [{"company": "...", "title": "...", "url": "...", "source": "welcometothejungle",
  "contracts": ["permanent"], "location": "...", "published_at": "2026-10-15", "pay": "", "description": "..."}]}
```

Leave `published_at` empty when the page shows no date. This file is what lets the next two steps merge web finds with
the rest and accept their links.

## Step 5 - Merge, deduplicate, score

```bash
python3 .claude/skills/job-discover/scripts/merge.py output/YYYY-MM-DD \
  --home {home dept} {home city} --near {neighbouring depts} --country {FR}
```

`--home` is the home department and town, `--near` the neighbouring departments (e.g. `--home 95 Cergy
--near 78 92 93 77 60 27`); `--country` picks the region table used to group the report.

The script reads every `_raw_*.json` (web included), removes duplicate URLs keeping the richest version, checks each
posting against the tracker and sets aside the ones without a date. It then groups the new postings that share a
company and a title (an agency's series of identical listings takes one slot, the rest in `same_title`) and ranks the
groups: keyword words found in the **title** count most, except generic ones (a word found in more than a fifth of
the run's titles, such as "développeur" when searching "développeur Java", counts little); keywords matched only in
the text count little; home and neighbouring areas get a boost; anonymous listings and republications a small
penalty. Every home-area posting with a keyword in its title is kept as a candidate whatever its rank. Each posting
gets its `region`. It writes `output/YYYY-MM-DD/_candidates.json`: `candidates` (the top 40 groups plus those home
postings, to score), `others` (with `region`, `nearby`, `home` and `same_title`), `new_by_region`, `unknown_date`,
`already_seen` (with their tracker status),
`possible_duplicates` (candidate pairs with near-identical titles), `ambiguous_keywords` (keyword, source, share of
results containing it, number dropped: a keyword whose results on a source almost never contain it is the site's
engine matching another word, and its noise is already removed - say so in the report's warnings), and the
sources' `warnings`, `mapping_updates` and
`web_companies`. **Read this file rather than the raw files**: they can hold thousands of postings, and the
mechanical part is already done. Open a raw file only to look up a detail about one posting. `--top N` widens the
selection if many candidates turn out off-topic.

What is left is judgement:

1. **Contract**: `freelance`, `permanent` or `other`. A "permanent or freelance" posting goes in both sections.
   Unknown contract (common on careers pages): infer it from the text, otherwise file it under `permanent` and say so.
2. **Same posting under different URLs**: the script only merges identical URLs. Look at `possible_duplicates` and
   at same-company postings with similar titles; when they are the same posting, keep the richest version - usually
   the one from a script source (see *Rules of conduct*).
3. **Same mission, several intermediaries**: agencies and IT services firms often publish the same client mission
   under their own name. Group obviously identical postings (same location, same duration and context, same skills,
   very similar descriptions) into **one entry** listing each intermediary with its link and pay. The user should
   apply only once: two applications for the same client through two agencies hurt them. When in doubt, keep them
   separate and point out the resemblance.
4. **Republications**: a `republished` posting (created before the period, republished during it) stays in the
   report but is not new. Mark it "republished (created DD/MM)" and place it after the genuinely new ones, especially
   on a short period, where that is precisely what the user wants to tell apart.
5. **Fit score 1-10** for the ~25 best candidates: shared skills, expected seniority, contract type. Location and pay
   don't lower the score (step 2). **+1 bonus** (capped at 10) for a posting near the home city (same or neighbouring department, or
   `nearby: true`): at equal fit, that's the one the user wants to see first. It adds to `merge.py`'s ranking boost
   on purpose: one decides what gets scored, the other the order of the report. One-line justification. Be demanding:
   8+ = "I'd apply this week". Beyond the top 25, a plain unscored list (the rest of `candidates`, then `others`).
6. **Tags** for each scored posting, used to group the report: its `region` (from `_candidates.json`), its **role** -
   the target role of `criteria.md` it matches best, or "Other" - and its **technologies** - the skills of the
   profile that the posting asks for (from its title and description; several per posting, none invented). Use the
   same spelling for the same role or technology everywhere, so the groups add up.

**Empty or near-empty period:** respect the requested period - this month's postings are not presented as today's.
Say how many postings the period contains (even zero). If there are fewer than `widen_below` (step 1), rerun
`discover.py` with `--since widen` (the last `widen_to_days` days) into the same run folder (step 3), run `merge.py`
again, and add a
separate "Outside the period (published since DD/MM)" section with the best of the postings it flags
`outside_period`, scored. If the requested period was already that long or longer, don't widen it: report
what there is.

## Step 6 - Write the report and check its links

**Every link comes from the data, never from memory.** Copy a posting's URL from `_candidates.json` (or a raw file);
don't rebuild it or guess it from the company or site name. An invented link sends the user to a dead page or to
another posting, and makes them doubt the whole report. If you don't have a posting's exact URL, leave it out.

Read `assets/report_template.md` and write `output/YYYY-MM-DD/discovery.md` following it: an **overview** with one
small table per grouping listed in `report_group_by` (`config/search.json`, default region, role, technology), each
row giving the number of scored postings, the best score and the entry numbers; then sections by contract, ranked by
score, new postings first, intermediaries grouped, republications flagged; unscored postings grouped by region;
already-seen postings with their status; source warnings. The main list stays ranked by fit - the overview is how the
user browses by region, role or technology without losing that order. Short and readable. Then:

```bash
python3 .claude/skills/job-discover/scripts/verify_links.py output/YYYY-MM-DD/discovery.md output/YYYY-MM-DD
```

It lists every link that is neither in the run's data nor in the tracker. Fix or remove each one before showing the
report; pass `--allow URL` only for links that are not postings (e.g. an API signup page cited in a warning).

## Step 7 - Update the tracker and summarise

For each **new** scored posting:

```bash
python3 .claude/skills/job-discover/scripts/tracker.py add \
  --company "..." --role "..." --contract freelance --url "..." \
  --score 8 --source {source id} --status "to review"
```

The status is always `to review` when a posting is added: the user decides whether to apply, and a tracker that
wrongly claims "applied" corrupts everything that follows. It changes only when the user says so (see *Special
cases*). `contract` and `status` take the English values (see *Language*); `--company` and `--role` are copied as
they appear in the posting.

End with a summary: number of new postings per contract, top 3 with links, failed or degraded
sources, path to the report.

**Ambiguous keywords:** if `ambiguous_keywords` (step 5) flagged a keyword that `criteria.md` has no decision for yet, end by
asking the user, once, what to do with it - otherwise every search pays for the same noise again:
- **replace** it with a more specific term (e.g. "Activiti BPMN", or a related tool they would accept);
- **keep it only on the sources that matched it exactly** (those not flagged for it in `ambiguous_keywords`);
- **drop** it.
Save the answer in `criteria.md`, in plain words next to the keyword (`Activiti (Free-Work only: France Travail
confuses it with "activité")`), the replacement term instead of it, or the keyword removed. Once recorded, don't ask
again.

## Source configuration

The user should never have to edit a JSON file (`config/*.json`, `output/companies.json`): update it from what they
say.

- `config/sources.json` (project): one entry per source - `id`, `name`, `type` (`script` or `web`), `active`,
  `countries`, `domains`, `contracts`, `options` (scripts) or `queries` (web). The project copy is authoritative; the
  skill defaults (`.claude/skills/job-discover/config/`) are only used to create it.
- `config/ats.json` (project): recruiting tools probed for followed companies (`enabled`), and their order
  (`probe_order`).
- `config/search.json` (project): period settings (see step 1) and `report_group_by`, the overview's groupings (`region`, `role`, `technology`,
  `contract`, `company`, `remote`). "Also group by company" / "drop the technology table" → update this list.
- **Adding a job board** searchable through web search: a `type: "web"` entry with its `queries`, written in the
  language of that board's postings. Nothing else.
- **Adding a source with an API**: a module `scripts/sources/<id>.py` exposing `search(params) -> {"roles",
  "warnings"}` (see `scripts/sources/__init__.py`), then a `type: "script"` entry.
- **Adding a recruiting tool (ATS)**: a module `scripts/ats/<name>.py` exposing `fetch(board_id)`, then its name in
  `config/ats.json`.
- **Disabling** a source: `"active": false` rather than deleting it.

After any code change: `cd .claude/skills/job-discover/scripts && python3 -m unittest test_scripts`.

## Special cases

- **"Freelance only" / "permanent only"**: `--contracts freelance` (or `permanent`); the report only has that section.
- **"Just [company]"**: `--sources companies --only slug` plus a targeted web search; no job boards.
- **No profile** (`profile/` empty or missing): ask the user to drop their CV there; run nothing.
- **"Add X to my targets"**: add X to the companies section of `criteria.md` and carry on.
- **"Add source Y" / "stop using Y"**: see *Source configuration*.
- **"Change my saved criteria"** (without asking for a search): edit `profile/criteria.md`, show what changed; no
  search.
- **"I applied to X" / "not interested in Y" / "I have an interview with Z"**: find the posting's URL with
  `tracker.py list`, then `tracker.py set-status URL applied` (or `ignored`, `interview`, `rejected`;
  `--notes "..."` to keep a remark). No search needed.

## Rules of conduct

- **Never apply** or contact anyone: the skill discovers, the user chooses.
- **Honesty about sources**: script sources are authoritative; web searches are for discovery. A dubious posting is
  left out rather than included: a fake posting costs the user more time than a missed one. No company, date or
  amount is written from memory (for links, see step 6).
- **Be kind to servers**: don't rerun `discover.py` more than once an hour without a reason; retry failed keywords
  only once (step 3), since a struggling server won't recover faster for being hit; don't raise `parallelism` above
  16.
- **Personal data**: the CV stays local. Send only keywords (and possibly a city) to web search, never the user's
  name, address or phone number.
