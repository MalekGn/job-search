# job-search

A [Claude Code](https://claude.com/claude-code) workspace for a job search. It uses project skills
to find job postings and freelance missions that fit the CV, rank them by fit, and keep track of
what was already seen. It also includes a data-analysis skill for reports and visualisations.

## Layout

```
.
├── .claude/skills/
│   ├── job-discover/     # finds, scores and tracks job postings (see below)
│   └── data-analysis/    # data analysis & HTML reports (third-party, see below)
├── profile/              # your CV (any format) and criteria.md (search preferences)
├── config/               # search.json, sources.json, ats.json (created on first run)
└── output/
    ├── YYYY-MM-DD/       # one folder per search: discovery.md, offres.html, raw data
    ├── tracker.csv       # every posting seen, with its status
    └── runs.csv          # history of searches
```

## job-discover skill

Finds the postings you haven't seen yet, ranked by fit with your profile, with direct links.
It never applies or contacts anyone: it finds the postings, and you decide what to do with them.

**How a search works**

1. Reads every file in `profile/`. On the first run it writes `profile/criteria.md` from the CV
   and stops so you can check it.
2. Shows the criteria for this search (keywords, contracts, period, city…) and waits for your OK.
3. Queries the sources, merges and deduplicates the results, and scores the best candidates from 1 to 10.
4. Writes `output/YYYY-MM-DD/discovery.md`, checks every link in it against the collected data,
   and adds the new postings to `output/tracker.csv`.

**Sources** (configured in `config/sources.json`)

- Script sources: Free-Work, France Travail, and the careers pages of the companies you follow,
  through their recruiting tool (Greenhouse, Lever, Ashby, SmartRecruiters, Recruitee, Teamtailor).
- Web sources, searched by Claude: Welcome to the Jungle, APEC, HelloWork, Collective, LinkedIn, Indeed.

France Travail uses its official API when `FT_CLIENT_ID` and `FT_CLIENT_SECRET` (France Travail
API credentials) are set in the environment; otherwise it reads the public website.

**Usage examples**

- `/job-discover` (a full search with the saved criteria)
- "find me freelance missions this week", "permanent jobs in Lyon since Monday"
- "add Acme to my target companies", "stop using Indeed"
- "I applied to the Acme posting", "not interested in X" (updates the tracker)

**Tests**

```bash
cd .claude/skills/job-discover/scripts && python3 -m unittest test_scripts
```

## data-analysis skill

End-to-end data analysis assistant: Excel/CSV analysis, business metrics and KPIs, ROI
calculations, charts, and HTML reports (converted to PPTX only on request). Its helper scripts
are `scripts/read_csv.py` and `scripts/read_excel.py`, which need pandas, and `scripts/html2pptx.js`,
which needs Node.js with puppeteer and pptxgenjs. The scripts install their dependencies
automatically when they are missing.

> **Credit:** this skill is not original work. It is copied from
> [dongzhang84/data-analysis-skill](https://github.com/dongzhang84/data-analysis-skill/),
> and all credit goes to its author.

## Getting started

**Requirements:** Claude Code and Python 3 (job-discover uses only the standard library).
Node.js is needed only for the PPTX export of data-analysis.

1. Put your CV in `profile/` (PDF, Markdown, DOCX, text…).
2. In Claude Code, from the project root, run `/job-discover` or just ask for jobs.
3. On the first run, check the `profile/criteria.md` it generates and the period settings it
   proposes, then confirm.
4. Read the report in `output/YYYY-MM-DD/discovery.md`.

## Privacy

`profile/`, `output/` and `config/` are git-ignored: the CV, the reports and the tracker stay on
your machine. Web searches send only keywords and possibly a city, never your name or contact
details.
