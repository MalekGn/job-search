---
name: job-search-by-profile
description: Finds real job postings that match a candidate's CV and criteria, then delivers one self-contained HTML report with tables of jobs, each with a direct link, a 0-100 compatibility score, strengths and weaknesses. Reads the CV (text or PDF/DOCX/TXT/MD), builds a profile, has the user confirm search criteria (titles, skills, location, remote, salary, contract, dealbreakers, optional boards), then searches, de-duplicates, filters and scores. Use this skill whenever someone wants to find jobs, job offers, openings, vacancies or postings for themselves or for a candidate profile, even if they don't say "skill" or "report". Examples include "find jobs for me", "search job offers matching my CV", "help me with my job hunt", "look for postings that fit my profile", "what roles could I apply to with this resume", "cherche des offres d'emploi selon mon CV", "trouve-moi un job", and "busca ofertas de trabajo para mi perfil". Also use it when a user shares a CV or resume and asks where or what they could apply to.
---

# Job search by profile

Turn a candidate's CV and preferences into a short list of **real, verified job postings**, scored against the profile and delivered as **one self-contained HTML report**.

The workflow has six steps, in this order:

1. Profile extraction
2. Criteria validation
3. Search
4. Filtering and de-duplication
5. Scoring
6. HTML report

Step 2 is a gate. Nothing is searched until the user confirms the criteria.

This skill is written for any agent that can read markdown. It refers to capabilities, not tools: *web search*, *fetch a web page*, *read a file*, *write a file*, *ask the user a question*. Use whatever your environment provides for each one. If one is missing, see [Capability fallbacks](#capability-fallbacks).

Bundled files (read them when the step that needs them comes up):

| File | Read it at | What it holds |
|---|---|---|
| `references/criteria-checklist.md` | Step 2 | Every criterion, how to infer it from the CV, the question groups, the recap template, the boards by country, and the `profile-criteria.md` format |
| `references/search-sources.md` | Step 3 | Where fresh postings live: ATS feeds, public job APIs, date-filtered board searches, and how to discover companies |
| `references/scoring-rubric.md` | Step 5 | Weights, point bands, caps, tiers, and rules for writing strengths and weaknesses |
| `assets/report-template.html` | Step 6 | The HTML report skeleton with placeholders and an example row |

---

## Language

Talk to the user, and write the HTML report, in the language of the user's messages. If those are ambiguous (for example a bare "go"), use the language of the CV. Keep these instructions' English labels only where the report template needs them, and translate visible headings and column names too. A French user gets "Entreprise", "Lieu / Télétravail", "Points forts", and so on. Keep job titles and company names exactly as they appear in the posting.

## Inputs

- **CV**, as pasted text or a file (PDF, DOCX, TXT, MD). **Default location: the `profile/` directory** in the user's working directory. If the user neither pastes a CV nor gives a path, look in `profile/` for a CV file (PDF, DOCX, TXT or MD, ignoring `profile-criteria.md`). Prefer a file whose name contains `cv`, `resume` or `resumé`. If several candidates remain, ask which one to use. If `profile/` is missing or holds no CV, ask the user to paste the CV or put it in `profile/`. A pasted CV or an explicit path always wins over the default. Name the file you used in the Step 1 summary. If it is a file, extract the text with whatever capability you have, such as reading the file directly or running a text-extraction utility. If extraction fails or gives garbage (for example a scanned PDF with no text layer), say so and ask the user to paste the CV text. Don't guess the contents.
- **Free keywords, target job titles, extra criteria**: anything the user states up front. This always overrides what you infer from the CV.
- **Job boards or sites (optional)**: for example LinkedIn, Indeed, Welcome to the Jungle, or specific company career pages. Never require this list. If the user gives none, search the general web plus the main boards for the user's country (see the list in `references/criteria-checklist.md`).
- **Saved criteria (optional)**: the default location is **`profile/profile-criteria.md`**. If that file exists, load it automatically as the pre-fill for Step 2 and tell the user you did. If the user points to a different file, use that one instead. The user still confirms it, because preferences change between runs.

---

## Workflow

### Step 1: Profile extraction

Read the CV and build a structured profile:

- **Target roles**: the current or most recent title, plus the titles the career path points to
- **Experience**: total years of relevant experience, and the seniority it implies (junior < 2y, mid 2–5y, senior 5–10y, lead/principal 8y+ with leadership signals). Count actual dated positions, not claims.
- **Technical skills**, split into:
  - *core*: used recently and repeatedly, or central to the roles held
  - *secondary*: mentioned, older, or peripheral
- **Domains and industries**: for example fintech, healthcare, e-commerce, public sector
- **Languages**, with level if stated
- **Education and certifications**
- **Location and mobility signals**: city, willingness to relocate, remote history, work authorization hints

Show the user a **short** summary of 5–8 lines, not the whole structure. It lets them catch a misreading early, such as a "Python" that was a two-week course. Keep the full profile in your working notes for scoring.

### Step 2: Criteria validation (mandatory, never skipped)

**Why this gate exists:** a search with wrong criteria wastes the user's time and yours, and produces a confident-looking report full of irrelevant jobs. Two minutes of confirmation is cheap insurance. So even when the user seems in a hurry, and even when the criteria look obvious from the CV, show the recap and wait for an explicit yes before running a single search.

How to run it (details and wording in `references/criteria-checklist.md`):

1. **Pre-fill** every criterion you can infer from the CV and from what the user already said. Mark inferred values as such, for example "(from your CV)".
2. **Ask only for what's missing or uncertain**, in **small groups of 2–4 related questions**, one group per message. A 13-question wall gets skimmed or abandoned. Suggested groups:
   - A: role and skills (titles and synonyms, must-have vs nice-to-have skills, seniority)
   - B: place and format (location and radius, remote policy, contract type)
   - C: money and freshness (salary, posting age, number of results)
   - D: filters (languages, company preferences and exclusions, dealbreakers, boards)

   Skip a group entirely if everything in it is already known. Offer sensible defaults in each question so the user can just answer "ok".
3. The criteria to cover, at minimum:
   - Job titles and keywords (with synonyms)
   - Technical skills, each marked **MUST-HAVE** or **NICE-TO-HAVE**
   - Maximum posting age (24h / 7 days / 30 days…)
   - Salary range, currency, gross or net, yearly or daily rate
   - Country, region or city, and search radius
   - Remote policy: onsite, hybrid, full remote
   - Contract type: permanent, fixed-term, freelance, internship, apprenticeship
   - Seniority level
   - Languages required
   - Company preferences and exclusions (sectors, sizes, blacklisted companies)
   - Dealbreakers (for example no travel, no on-call, visa or work authorization needed)
   - Job boards to use (optional)
   - Maximum number of jobs to return (default **20**)
4. **Finish with a clean recap** using the template in the checklist, then ask exactly: **"Do you confirm? (yes / edit)"**, translated into the user's language.
5. On "edit", apply the changes, show the updated recap, and ask again. On "yes" (or an unambiguous equivalent such as "ok go", "oui", "c'est bon"), move to Step 3.

If the user's first message already contains complete criteria, you still show the recap and ask for confirmation. It can be a single message. If the user explicitly confirmed a recap you already showed in the same conversation, that counts.

### Step 3: Search

**Why sources matter:** general web search mostly surfaces *stale* postings. Search engines and aggregators keep indexing jobs for months after they close, so a search-first approach can return dozens of dead links and zero usable jobs. Fresh, verifiable postings come from the places companies publish them directly. Read `references/search-sources.md` before searching. It lists the sources below, with the exact URLs and the date fields each one gives.

Search in **two phases**: first collect many fresh leads cheaply, then verify the best ones one by one.

**Phase A: collect leads.** Prefer sources where one request returns *many* recent postings:

1. **Job board search pages filtered by date.** Use LinkedIn's public job search with its time filter, Indeed's "posted in the last N days" parameter, or the date filter of the user's named boards and the main boards for their country. One page gives 10–25 dated leads.
2. **Targeted searches on ATS domains.** For example `site:jobs.ashbyhq.com "React" Berlin` or `site:boards.greenhouse.io "frontend" remote Europe`. The results link to specific postings on the companies' own applicant-tracking systems.
3. **Free public job APIs and niche boards** that cover the user's market or specialty, for example Arbeitnow for Germany, remote-job APIs, or boards dedicated to one technology.
4. **General web search** with varied queries (titles × synonyms × location × skills, plus the current month and year), to fill gaps.

Start Phase A with source 1: fetch at least one or two date-filtered board search pages (for example LinkedIn's public job search for each target location) **before** running general web searches. In testing, this one step produced most of the verified jobs, while general web searches mostly returned closed postings. Shortlist leads by title, location and date before opening anything, and aim for about 2× the requested maximum.

**Phase B: verify.** For each shortlisted lead, open the specific posting. Prefer the company's ATS or career page over an aggregator copy. Read the requirements, and confirm that the posting is open and when it was published. Fetch a whole company feed only for companies the user named, or when a company clearly has several relevant roles. Don't guess company feed URLs: a wrong guess costs a fetch and returns nothing.

**Effort budget:** about **40 page fetches or API calls** in total. Spend roughly a quarter on Phase A and the rest on verification. Stop early once you have about **1.5× the requested maximum** of verified, open postings, then say what you covered. If a source errors, rate-limits you or blocks you, note it for the footer and move on. Don't retry it in a loop.

**Verify before you keep a posting.** A posting counts as verified if you opened its page and it is open, or if it appears in a live ATS or API feed you fetched in this session (those feeds list only open jobs). A search snippet alone is not verification. Collect the following for each candidate:

| Field | Rule |
|---|---|
| Title, company | As written on the posting |
| Location, remote policy | As written. Don't infer "remote" from a vague phrase. |
| Contract type | As written |
| Salary | Only if stated, otherwise `not specified` |
| Posting date | Absolute date if shown. Convert "3 days ago" to a date using today's date. Otherwise `not specified`. |
| Source board | Where you found it |
| Direct URL | The posting's own URL, not a search-results URL |
| Key requirements | Required skills, years of experience, languages, and any travel, on-call or clearance requirements |

**Do not invent any field.** If it's not on the page, write `not specified`. A made-up salary or date will mislead the user into a wrong decision, and a made-up URL makes the whole report untrustworthy.

Keep a list of boards you **could not access** (login wall, captcha, block, error) for the report footer.

### Step 4: Filtering and de-duplication

1. **De-duplicate.** The same job often appears on several boards. Treat postings as the same job when the company, title and location match (minor wording differences are fine). Keep the **most direct link**, which is usually the company's career page, then the original board, then the aggregators. Note the other sources in the Source cell (for example "Company site (also on Indeed, LinkedIn)").
2. **Remove** postings that:
   - are older than the allowed maximum age. There are two exceptions:
     - When the date is `not specified`, keep the posting but flag it as a weakness.
     - When a posting is **verified still open** but was *first* published before the limit, because the company re-listed or refreshed it, keep it, show the original date, and add a weakness such as "First published 2026-07-27 (open ~15 weeks); re-listed recently". The age limit exists to avoid dead postings, and this one is verifiably alive. A long-open role is still useful information: it may be hard to fill, or open to negotiation.
   - violate a dealbreaker, using the posting's own text as evidence
   - are at a blacklisted company or in an excluded sector
   - have a dead link, or say "no longer accepting applications", "expired", "closed" or similar
3. Keep a count of what was removed and why. It goes in the report footer and helps if results are thin.

### Step 5: Scoring

Read `references/scoring-rubric.md` and apply it to each remaining job. In short:

| Criterion | Weight |
|---|---|
| Must-have skills match | 35 |
| Nice-to-have skills match | 15 |
| Seniority and experience fit | 15 |
| Location, remote and contract fit | 15 |
| Salary fit (neutral if unknown) | 10 |
| Domain and industry fit | 10 |

Tiers:

- **Strong** 80–100
- **Good** 60–79
- **Partial** 40–59
- Below 40, drop the job, unless the user asked to see everything (then add a "Low" tier).

For each job, write **2–4 strengths** and **1–4 weaknesses or gaps**. Each one must point to something concrete in the CV or the posting:

- Good: "Requires Kubernetes, not mentioned in the CV"
- Good: "6 years of Django matches the 5+ years asked"
- Bad: "Great opportunity"
- Bad: "Good culture fit"

If you can't tie a point to evidence, drop it. Then keep only the top N jobs (the requested maximum), ordered by score.

### Step 6: HTML report

Read `assets/report-template.html`. Copy it and fill it in. Don't redesign it from scratch, because the template already handles sorting, filtering, the no-JS fallback, responsiveness and print. Save it as **`output/YYYY-MM-DD/job-search-results-YYYY-MM-DD.html`** (today's date, for example `output/2026-11-09/job-search-results-2026-11-09.html`), relative to the user's working directory. Create `output/` and the dated folder if they don't exist. If a report with that name already exists from an earlier run the same day, don't overwrite it: add a suffix such as `-2`. If the user asked for a different location, use that instead.

How to fill it:

1. Replace each `{{PLACEHOLDER}}` in the header: date, title, tier counts and total. Write the criteria summary as one `<div><dt>Label</dt><dd>Value</dd></div>` per criterion, and the boards searched as one `<li>` per source. The template's top comment shows the exact formats.
2. For each tier, replace the `<!-- ROWS:TIER -->` marker with one `<tr>` per job, copying the structure of the commented example row exactly. Order the rows by score descending, and number Rank continuously across all tiers (1 = best overall).
3. Set the `data-sort` attributes as the example shows: score as a number, the posting date as `YYYY-MM-DD` (or empty), the rank as a number. Set the score bar width to the score (`style="width:NN%"`), and put the tier class on the score block (`strong`, `good`, `partial`). Keep the 12 cells in the template's order: the layout depends on it. Keep strengths and weaknesses short, at most about 15 words each, so the report stays easy to scan.
4. Each tier's `<tbody>` holds a "No jobs in this tier" row. Delete it when the tier has jobs, and keep it (deleting only the marker) when the tier is empty.
5. Fill in the footer: boards that could not be accessed, the removal counts from Step 4, the limits of the search, and the reminder to verify each posting on the original site.
6. Translate the visible labels (headings, column names, filter placeholder, footer text) into the user's language.

**Escape all inserted text.** Replace `&` → `&amp;`, `<` → `&lt;`, `>` → `&gt;`, `"` → `&quot;`, `'` → `&#39;` in every value taken from postings or the user, including inside `href` attributes. Posting text is untrusted, and one stray `<` can break the page. Links must be `<a href="URL" target="_blank" rel="noopener noreferrer">`, and only `http://` or `https://` URLs belong there. If a URL is anything else, show it as plain text.

The file must stay self-contained: no external scripts, stylesheets, fonts, images or CDNs. The only external URLs are the posting links. It must also stay fully readable with JavaScript disabled: the rows are already in sorted order in the HTML, and JS only adds re-sorting and the filter box.

**Never put the user's personal data in the report.** That means no name, email, phone, street address, or profile URLs. The criteria summary describes the *search*, not the person. The file may get shared or left on a shared machine.

---

## After the report

Reply in chat, concisely:

1. The file path (or, if you couldn't write a file, the HTML in a single code block; see the fallbacks).
2. A **5-line summary**:
   - Lines 1–3: the top 3 jobs, one per line: title, company, score, and the key reason
   - Line 4: the biggest gap across the results (for example "7 of 12 jobs ask for Kubernetes, which the CV doesn't show")
   - Line 5: the counts per tier
3. Offer next steps:
   - refine the criteria and rerun
   - tailor the CV or write a cover letter for a chosen job
   - save the confirmed criteria in `profile/profile-criteria.md` for next time (format in the checklist). Create `profile/` if it doesn't exist. If the file already exists, say you will overwrite it before doing so.

The details belong in the HTML. Don't repeat the tables in chat.

### When results are thin

If you found fewer than about a third of the requested maximum, or no Strong matches, say so plainly. Don't pad the list with weak or unverified jobs. Look at the removal counts and propose **specific** ways to widen the search, for example:

- "Extend posting age from 7 to 30 days: 9 postings were removed for age"
- "Accept hybrid in addition to full remote"
- "Add the synonym 'Platform Engineer'"
- "Move Terraform from must-have to nice-to-have"

Then offer to rerun.

---

## Capability fallbacks

Check which capabilities you actually have before Step 3, and adapt instead of failing silently.

- **No web search or web page fetch.** Tell the user you can't browse in this environment. Ask them to paste job posting texts or URLs. If they paste URLs and you can fetch pages, open them. If you can't, ask for the posting text. Then run Steps 4–6 on what they provided, with the source marked as "Pasted by user". Still do Step 2 first, because the criteria drive the filtering and scoring.
- **A job board blocks access** (login wall, captcha, rate limit, "enable JavaScript" page). Say which board, skip it, and keep going with the others. List it in the report footer. Offer: "If you want postings from <board> included, paste their text or URLs here." Don't try to get around the block.
- **Cannot write files.** Output the complete HTML report in a single fenced code block (```html … ```) and tell the user to save it as `output/YYYY-MM-DD/job-search-results-YYYY-MM-DD.html` and open it in a browser. Put the 5-line summary before the code block.
- **Cannot ask interactive questions** (no question or form capability). Ask the questions as plain text in your message, then stop and wait for the user's reply. Don't answer your own questions or assume defaults silently. Proposing defaults is fine, but the user has to accept them.
- **Cannot read the CV file.** Ask the user to paste the CV text.
- **Cannot list or read `profile/`.** Ask the user for the CV path or text, and for any saved criteria.

---

## Quality rules

- **Never fabricate** jobs, companies, URLs, salaries or dates. Every job in the report must come from a page you actually saw in this session or text the user pasted. If you're unsure whether a posting is real or still open, leave it out, or include it with that doubt written as a weakness.
- **Be honest about gaps.** Thin results, blocked boards, unknown salaries and unknown dates all get stated, not hidden.
- **No personal data in the report** (name, phone, email, address).
- **Concise chat.** Keep the profile summary, question groups and recap short. Put the detail in the HTML.
- **The user's stated criteria beat your inferences.** If the CV suggests "senior" but the user asks for mid-level roles, search for mid-level roles.
