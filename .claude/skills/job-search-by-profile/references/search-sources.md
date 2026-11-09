# Search sources (Step 3)

This file lists where to find **fresh, verifiable** postings, and how to reach each source with only "web search" and "fetch a web page".

How the sections map to SKILL.md Step 3:

- **Phase A (collect leads):** sections 3 and 1A first, then 2 and 4. These give many dated leads per request.
- **Phase B (verify):** open each shortlisted posting. Use the section 1B feeds only for companies the user named, or companies with several relevant roles.

The endpoints below were public, and needed no login, when this file was written. Sites change, so if one errors, returns HTML instead of JSON, or rate-limits you, note it for the report footer and move on.

Feeds can be large. When fetching JSON, look only at the title, location, date and URL fields first. Fetch the full description only for jobs whose title matches.

---

## 1. ATS feeds (best source)

Most tech and many non-tech companies publish jobs through an applicant tracking system (ATS). ATS feeds list **only currently open jobs**, include a publication or update date, and link to the canonical apply page. That makes them the most reliable source of verified postings.

### Step A: Discover companies

Run web searches such as:

- `site:boards.greenhouse.io "<title>" <city or "remote">`
- `site:job-boards.greenhouse.io "<title>" <city>`
- `site:jobs.lever.co "<title>" <city>`
- `site:jobs.ashbyhq.com "<title>" <city>`
- `site:apply.workable.com "<title>" <city>`
- `site:jobs.personio.de "<title>"` (or `.personio.com`; common in DACH)
- `site:jobs.smartrecruiters.com "<title>" <city>`
- `site:recruitee.com "<title>" <city>`
- `"<title>" "<city>" careers`, plus well-known employers in the user's domain

Each result URL contains the company's slug, for example `jobs.ashbyhq.com/forto/…` gives the slug `forto`. Also add any companies the user listed, and well-known employers in their domain and city. You can usually guess the slug from the company name (lowercase, no spaces).

### Step B: Fetch the company feed

| ATS | Feed URL (replace `{slug}`) | Date field | Posting URL field |
|---|---|---|---|
| Greenhouse | `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs` (add `?content=true` for descriptions) | `first_published`, otherwise `updated_at` | `absolute_url` |
| Lever | `https://api.lever.co/v0/postings/{slug}?mode=json` (EU-hosted companies: `api.eu.lever.co`) | `createdAt` (milliseconds since epoch) | `hostedUrl` |
| Ashby | `https://api.ashbyhq.com/posting-api/job-board/{slug}?includeCompensation=true` | `publishedAt` | `jobUrl` |
| Workable | `https://apply.workable.com/api/v1/widget/accounts/{slug}` | `published_on` / `created_at` | `url` / `shortlink` |
| Personio | `https://{slug}.jobs.personio.de/xml` (or `.personio.com`) | `createdAt` | build it as `https://{slug}.jobs.personio.de/job/{id}` |
| SmartRecruiters | `https://api.smartrecruiters.com/v1/companies/{slug}/postings` | `releasedDate` | `ref`, or the job page link |
| Recruitee | `https://{slug}.recruitee.com/api/offers/` | `published_at` / `created_at` | `careers_url` |

If a feed URL fails, fetch the human career page instead (for example `https://jobs.ashbyhq.com/{slug}`). It is still a direct, current source.

**Dates:** an ATS "updated" date can be newer than the original posting, because companies re-publish old roles. When only an updated date is available, use it, but mark the posting date as "updated YYYY-MM-DD". If the first-published date is older than the age limit but the job is still open in the feed, keep it with its original date and a weakness such as "First published YYYY-MM-DD; re-listed recently" (see Step 4 in SKILL.md).

---

## 2. Public job APIs and aggregators

Use these when they cover the user's market. Filter by keyword, location and date.

| Source | Endpoint | Covers |
|---|---|---|
| Arbeitnow | `https://www.arbeitnow.com/api/job-board-api?page=N` | Germany / Europe, many English-speaking tech roles. Paginated; stop after a few pages if the dates are getting old. |
| Remotive | `https://remotive.com/api/remote-jobs?search=<keyword>` | Remote, worldwide |
| Remote OK | `https://remoteok.com/api` | Remote, worldwide (the first array item is metadata) |
| Himalayas | `https://himalayas.app/jobs/api?limit=50` | Remote |
| Jobicy | `https://jobicy.com/api/v2/remote-jobs?count=50&tag=<keyword>` | Remote, with region filters |

Some national services and aggregators have APIs that need a free key, for example France Travail, Adzuna and the Bundesagentur für Arbeit. Use them only if the user provides a key, or the environment already has access.

Aggregator links often redirect to the original posting. Follow the link once to get the direct URL, and prefer it.

---

## 3. Job board searches with a date filter

Board search result pages are usually the **highest-yield first step**: one page lists 10–25 recent postings with dates, when it loads without login. Always apply the board's date filter, so only fresh postings appear:

- **Indeed** (country domains such as indeed.fr, de.indeed.com, uk.indeed.com): `/jobs?q=<title>&l=<city>&fromage=<days>`, where `fromage` is the maximum age in days.
- **LinkedIn** public job search: `https://www.linkedin.com/jobs/search/?keywords=<title>&location=<place>&f_TPR=r<seconds>`. For example, `r604800` is 7 days and `r2592000` is 30 days. The public (logged-out) search page often works. It sometimes blocks automated access; if so, apply the "blocked board" fallback. Individual posting pages are at `linkedin.com/jobs/view/<id>`. Prefer the company's own ATS link when the posting gives one.
- **Welcome to the Jungle, StepStone, APEC, HelloWork, jobs.ch, Reed, Totaljobs**: use their search page with the board's own "posted in the last …" option when one is visible in the URL.

Open each promising result's posting page before keeping it.

---

## 4. General web search

Use general web search for discovery and gap-filling, not as the final source. Search results include many closed postings.

- Add the current month and year, or words like "hiring now", to queries, for example `"Senior React Developer" Berlin remote November 2026`.
- Treat any hit from a job board or aggregator as a lead. Confirm it on the company's ATS or career page (sections 1–2) or by opening the posting.
- A hit you cannot verify can appear in the report footer as an "unverified lead", never in the tables.

---

## Market notes

- **France:** many companies use Welcome to the Jungle (`welcometothejungle.com/fr/companies/{slug}/jobs`), Teamtailor (`{slug}.teamtailor.com/jobs`), Lever, or their own career site. Freelance roles are on Free-Work and Malt.
- **DACH:** Personio and Join (`join.com/companies/{slug}`) are common. Arbeitnow covers many English-speaking roles.
- **UK and US:** Greenhouse, Lever, Ashby and Workable cover most tech companies.
- **Public sector:** use the official portal for the country (for example USAJobs, Place de l'emploi public, Civil Service Jobs).
