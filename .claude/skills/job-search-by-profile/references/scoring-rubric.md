# Scoring rubric (Step 5)

Each job gets a **compatibility score from 0 to 100**. The score is the sum of six criteria, adjusted by the caps at the end.

**Unknowns get generous partial credit.** Missing details such as salary, contract type and seniority are common, and they don't mean the job is a worse fit. Score them high enough that a job matching everything the posting *does* say can still reach Strong, and record each unknown as a weakness, so the user knows what to ask.

The rubric is deliberately simple. The aim is a score the user can sanity-check by reading the strengths and weaknesses, not false precision. Score from the **posting's text** compared with the **profile and confirmed criteria**, never from impressions of the company.

| # | Criterion | Max points |
|---|---|---|
| 1 | Must-have skills match | 35 |
| 2 | Nice-to-have skills match | 15 |
| 3 | Seniority and experience fit | 15 |
| 4 | Location, remote and contract fit | 15 |
| 5 | Salary fit | 10 |
| 6 | Domain and industry fit | 10 |
| | **Total** | **100** |

---

## 1. Must-have skills match (35)

Which of the user's MUST-HAVE skills the posting asks for or clearly uses, and whether the candidate covers what the **posting** requires.

Compute two ratios:

- **coverage** = the user's must-haves that the posting mentions ÷ the user's must-haves. This shows whether the job is the kind of job the user wants.
- **requirement fit** = the posting's *required* skills that the CV shows ÷ the posting's required skills. This shows whether the user can get the job. Count at most about 8 headline requirements, ignoring boilerplate.

Points = round(35 × (0.5 × coverage + 0.5 × requirement fit)).

Treat close equivalents as matches and say so in a strength, for example "PostgreSQL ≈ MySQL requirement: relational SQL experience transfers". Don't treat different tools as matches (React ≠ Angular).

## 2. Nice-to-have skills match (15)

Points = round(15 × the user's nice-to-haves present in the posting ÷ the user's nice-to-haves). If the user has no nice-to-haves, score the posting's "bonus" or "plus" skills that the CV shows, on the same ratio. If neither exists, give 10 (neutral).

## 3. Seniority and experience fit (15)

| Situation | Points |
|---|---|
| Level and required years both match (within ±1 year) | 15 |
| One level off, or 1–2 years short | 10 |
| Clearly over-qualified (two or more levels above) | 7 |
| 3+ years short, or two levels below what is required | 3 |
| Posting gives no level or years | 13 (most postings omit it; don't punish the job for that) |

## 4. Location, remote and contract fit (15)

Split into three sub-scores:

- **Location (5):**
  - 5: inside the area or radius, or full remote within an allowed country or timezone
  - 2: up to 2× the radius, or remote with a timezone constraint the user didn't mention
  - 0: elsewhere
- **Remote policy (5):**
  - 5: matches one of the user's accepted policies
  - 3: the posting says "flexible" or "some remote" with no detail
  - 0: conflicts (for example onsite-only when the user wants full remote)
- **Contract (5):**
  - 5: an accepted contract type
  - 4: not stated. Many postings say only "full-time". With no end date and no "fixed-term", "freelance" or "temporary" wording, it is most likely permanent: score 4 and add the weakness "Contract type not stated (full-time; likely permanent)".
  - 0: a non-accepted type

A 0 on location or remote for a hard user requirement usually means the job should have been filtered out in Step 4 as a dealbreaker. Score it only if the user treated that criterion as flexible.

## 5. Salary fit (10)

| Situation | Points |
|---|---|
| Stated range reaches or exceeds the user's minimum | 10 |
| Stated range tops out within 10% below the minimum | 6 |
| Stated range is clearly below the minimum | 0 |
| Salary `not specified`, or the user set no minimum | 8. Most postings in many countries don't state pay, so a missing salary shouldn't keep a strong fit out of the Strong tier. Add the weakness "Salary not stated" when the user did set a minimum. |

Compare like with like. Convert daily ↔ yearly (about 218 working days a year in France, about 230 elsewhere) and gross ↔ net only roughly, and say that the conversion is an estimate.

## 6. Domain and industry fit (10)

| Situation | Points |
|---|---|
| Same industry as recent experience, or a sector the user said they prefer | 10 |
| Adjacent industry (for example fintech ↔ insurance, e-commerce ↔ retail) | 6 |
| Unrelated but neutral | 4 |
| A sector the user said they'd rather avoid (soft preference, not an exclusion) | 0 |

---

## Caps and adjustments

Apply these after summing. They stop a job that fails the main point from ranking high on secondary criteria.

- If the candidate covers **less than half of the posting's required skills**, cap the score at **59**. The job can be Partial at best.
- If the posting asks for **half or fewer of the user's MUST-HAVE skills**, cap the score at **59**. A must-have is something the user said the job must involve, so a job that drops half of them isn't a Good match, however well the rest fits. Say which must-haves are missing in a weakness. Example: "No Spark or Airflow: only 2 of your 4 must-haves."
- If a **mandatory language** in the posting is not on the CV, cap the score at **49**.
- If the posting date is `not specified`, subtract **3** and add the weakness "Posting date not shown; check it's still open".
- Don't score postings seen only as a search snippet. They aren't verified, so they belong in the footer as unverified leads, not in the tables.

Clamp the final score to the range 0–100.

## Tiers

| Score | Tier |
|---|---|
| 80–100 | **Strong** |
| 60–79 | **Good** |
| 40–59 | **Partial** |
| < 40 | Dropped, unless the user asked for everything (then **Low**) |

---

## Strengths and weaknesses

For each job, write **2–4 strengths** and **1–4 weaknesses or gaps**. Each line is one short sentence that names the evidence, from the CV, the posting, or both.

Good:

- "6 years of Django vs 4+ required"
- "Fintech background (2 payment companies) matches the domain"
- "Full remote within the EU, as requested"
- "Requires Kubernetes, not mentioned in the CV"
- "Salary not stated; your minimum is 55k EUR"
- "German C1 required; the CV lists only French and English"

Bad (too generic, so rewrite or drop them):

- "Great opportunity"
- "Interesting company"
- "Good culture fit"
- "Strong technical match"
- "May require learning"

Weaknesses are the most useful part for the user. They show what to address in a cover letter or what to check before applying, so never leave them empty. If the fit really is excellent, the weakness can be an unknown, such as an unstated salary or an unclear on-call policy.

---

## Worked example

**Criteria:**

- Must-have: Python, Django, PostgreSQL
- Nice-to-have: Docker, AWS, Celery
- Senior (6 years)
- Lyon + 30 km, hybrid or remote
- Permanent contract
- ≥ 50k EUR
- Preferred sector: fintech

**Posting:** "Senior Backend Engineer, payments scale-up, Lyon, hybrid 2 days/week, CDI, 55–65k. Required: Python, Django, PostgreSQL, Kubernetes, 5+ years. Nice: AWS, Kafka."

| Criterion | Reasoning | Points |
|---|---|---|
| Must-have | coverage 3/3; required fit 3/4 (Kubernetes missing). 35 × (0.5 × 1 + 0.5 × 0.75) = 30.6 | 31 |
| Nice-to-have | AWS only: 1/3 → 15 × 0.33 | 5 |
| Seniority | Senior, 6y vs 5+ | 15 |
| Location / remote / contract | 5 + 5 + 5 | 15 |
| Salary | 55–65k ≥ 50k | 10 |
| Domain | payments = fintech | 10 |
| **Total** | | **86 → Strong** |

**Strengths:**

- "Python/Django/PostgreSQL: all 3 must-haves required"
- "6 years vs 5+ asked"
- "Payments scale-up matches your fintech preference"
- "55–65k EUR, above your 50k minimum"

**Weaknesses:**

- "Requires Kubernetes, not mentioned in the CV"
- "Kafka listed as a plus; no streaming experience in the CV"
