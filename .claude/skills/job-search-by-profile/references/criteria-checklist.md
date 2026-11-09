# Criteria checklist (Step 2)

Use this file to run the criteria-validation step. It covers:

1. The criteria fields
2. The question groups
3. The recap template
4. Main job boards by country
5. The `profile-criteria.md` save format

Translate every question and label into the user's language. The wording below is a suggestion, not a script.

---

## 1. Criteria fields

For each field: what it means, how to pre-fill it from the CV, and the default to propose if it stays unknown. The user's explicit statements always win.

| # | Criterion | Pre-fill from CV | Default to propose |
|---|---|---|---|
| 1 | **Job titles and keywords** (with synonyms) | Current or last title, plus the titles the career path points to. Add 2–4 market synonyms (for example "Backend Developer" → "Backend Engineer", "Python Developer", "Software Engineer (Backend)"). Include French or local-language variants if searching a non-English market. | Last title and its synonyms |
| 2 | **Technical skills: MUST-HAVE / NICE-TO-HAVE** | Core skills become must-have candidates (cap at about 5, since too many must-haves kill recall). Secondary skills become nice-to-have. | Top 3–5 core skills as must-have, the rest nice-to-have |
| 3 | **Max posting age** | (none) | 30 days. Suggest 7 days if the market is busy. |
| 4 | **Salary**: min–max, currency, gross/net, yearly/daily | Never infer from the CV. You may mention a typical range for the role and location only if you are confident, and label it as an estimate. | "No minimum" (salary then scores neutral) |
| 5 | **Location**: country, region or city, radius | City or country on the CV | CV city + 30 km (or the whole country if remote) |
| 6 | **Remote policy**: onsite / hybrid / full remote (multi-select) | Remote history in past roles | Hybrid + full remote |
| 7 | **Contract type**: permanent, fixed-term, freelance, internship, apprenticeship (multi-select) | Freelance history implies freelance, a student implies an internship or apprenticeship | Permanent |
| 8 | **Seniority level** | Computed from years and responsibilities (see Step 1 in SKILL.md) | Computed level, plus one level up if the career trend is upward |
| 9 | **Languages required** | Languages listed on the CV with their levels | Languages the user can work in |
| 10 | **Company preferences and exclusions**: sectors, sizes (startup / scale-up / SME / large corp), blacklisted companies | Domains from experience can be offered as preferences. Never infer exclusions. | No preference, no exclusion |
| 11 | **Dealbreakers**: for example no travel, no on-call, needs visa sponsorship or work authorization, no security clearance, no night shifts | Nationality or authorization hints, only if stated on the CV | None |
| 12 | **Job boards** (optional) | (none) | General web + main boards for the country (section 4) |
| 13 | **Max number of jobs** | (none) | 20 |

Notes:

- **Work authorization.** If the CV location and the target country differ, ask whether sponsorship is needed. This is a common hidden dealbreaker.
- **Salary units.** Freelance roles usually show a daily rate (TJM in France), and permanent roles show a yearly figure. In some countries, yearly salaries are gross (FR "brut annuel", DE "brutto"). Record exactly what the user says.
- **Must-have inflation.** If the user lists more than 6 must-haves, gently point out that very few postings will match all of them, and propose moving some to nice-to-have. Accept their final call.

---

## 2. Question groups

Ask one group per message, and skip any group whose answers are already known. Show the pre-filled values inline so the user can reply "ok" or correct one item.

**Group A: Role and skills**

- "Which job titles should I search? I propose: <titles + synonyms> (from your CV)."
- "Which skills are MUST-HAVE (the job must use them) vs NICE-TO-HAVE? Proposal: MUST <…> / NICE <…>."
- "Seniority: I read your profile as <level> (<N> years). Target this level, or also <level+1>?"

**Group B: Place and format**

- "Where? <city/country> within <radius> km, or another place?"
- "Remote policy: onsite, hybrid, full remote? (several allowed)"
- "Contract type(s): permanent, fixed-term, freelance, internship, apprenticeship?"

**Group C: Money and freshness**

- "Salary: minimum (and optional maximum), currency, gross or net, yearly or daily? Or no minimum?"
- "Max posting age: 24h, 7 days, or 30 days?"
- "How many jobs at most in the report? (default 20)"

**Group D: Filters**

- "Working languages required or excluded?"
- "Any sectors, company sizes or specific companies to prefer or exclude?"
- "Dealbreakers? (for example no travel, no on-call, visa sponsorship needed)"
- "Any specific job boards or company career pages to include? (optional; otherwise I use the general web + <country boards>)"

---

## 3. Recap template

Show this after the last group. Keep it compact and translate the labels.

```markdown
**Search criteria — recap**

- **Titles / keywords:** Backend Developer, Backend Engineer, Python Developer
- **Must-have skills:** Python, Django, PostgreSQL
- **Nice-to-have skills:** Docker, AWS, Celery
- **Seniority:** Senior (6 years)
- **Location:** Lyon + 30 km · **Remote:** hybrid, full remote
- **Contract:** permanent
- **Salary:** ≥ 50 000 EUR gross / year
- **Posted within:** 30 days
- **Languages:** French, English
- **Prefer:** fintech, scale-ups · **Exclude:** Acme Corp, gambling sector
- **Dealbreakers:** no on-call
- **Boards:** general web + Welcome to the Jungle, Indeed FR, LinkedIn, APEC
- **Max results:** 20

Do you confirm? (yes / edit)
```

---

## 4. Main job boards by country

These are the defaults when the user names no boards. Always add the general web, company career pages (search `"<title>" careers <city>` or `jobs.<company>.com`) and ATS-hosted pages (Lever, Greenhouse, Workable, Ashby, SmartRecruiters, Teamtailor, Welcome Kit). ATS pages are often public, direct, and current.

| Country | Boards |
|---|---|
| France | Welcome to the Jungle, Indeed FR, LinkedIn, APEC (cadres), France Travail, HelloWork, Free-Work (freelance / IT), Malt (freelance) |
| Belgium | Indeed BE, LinkedIn, StepStone BE, Jobat, Actiris / VDAB / Le Forem |
| Switzerland | jobs.ch, jobup.ch, LinkedIn, Indeed CH |
| Canada | Indeed CA, LinkedIn, Job Bank (Guichet-Emplois), Jobillico (QC) |
| United Kingdom | LinkedIn, Indeed UK, Reed, Totaljobs, CWJobs (IT), Otta / Welcome to the Jungle UK |
| United States | LinkedIn, Indeed, Glassdoor, Wellfound (startups), Dice (tech), USAJobs (federal) |
| Germany | StepStone, LinkedIn, Indeed DE, XING, Arbeitsagentur |
| Tunisia | Tanitjobs, Keejob, Emploi.nat, LinkedIn, OptionCarriere |
| Morocco | ReKrute, Emploi.ma, LinkedIn |
| Remote / international | We Work Remotely, Remote OK, Remotive, Working Nomads, LinkedIn (remote filter), EU Remote Jobs |
| Other / unknown | LinkedIn, Indeed (country domain), Glassdoor, the local public employment service |

LinkedIn, Glassdoor and some Indeed pages often block automated access or require a login. If so, apply the "board blocks access" fallback in SKILL.md, and look for the same job on the company's career page or ATS.

---

## 5. `profile-criteria.md` save format

When the user accepts the offer to save the criteria, write this file to **`profile/profile-criteria.md`** in the user's working directory, next to the CV. Create `profile/` if needed. Never include personal data (name, email, phone, address).

```markdown
# Job search criteria
_Last confirmed: YYYY-MM-DD_

## Profile (summary)
- Seniority: Senior, 6 years
- Core skills: Python, Django, PostgreSQL
- Secondary skills: Docker, AWS, Celery, React
- Domains: fintech, e-commerce
- Languages: French (native), English (C1)

## Criteria
- Titles / keywords: …
- Must-have skills: …
- Nice-to-have skills: …
- Seniority: …
- Location / radius: …
- Remote policy: …
- Contract types: …
- Salary: …
- Max posting age: …
- Languages: …
- Prefer / exclude: …
- Dealbreakers: …
- Boards: …
- Max results: …
```

On the next run, load `profile/profile-criteria.md` automatically (if it exists) as the pre-fill, show the recap, and ask for confirmation again.
