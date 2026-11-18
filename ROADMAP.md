# Roadmap — Problem Radar

The MVP answers one question: *can a bounded harvest of public text produce ranked, sourced problem
leads with an explainable rationale?* Everything below is ordered by that question, not by feature
appeal.

## v0.1 — MVP (current)

**Status: complete**

- `init`, `collect`, `cluster`, `report`, `run`, `sources`, `list`, `show`, `status`, `solution`,
  `add`, `export`
- Hacker News (Algolia), GitHub issues (search API), RSS/Atom and manual JSONL collectors
- Title-level noise filter, IDF-weighted clustering, explainable score with corroboration
- JSONL signal store, cluster store with human state carry-over
- Markdown report + JSON export
- 168 tests, 94 % coverage, CI on Python 3.10–3.13

## v0.2 — Recurrence over time

- `radar history`: score evolution of a cluster across runs (new signals, score delta)
- store one snapshot per run instead of overwriting `clusters.json`
- `radar watch --since 7d`: only what changed since the last report
- weekly cron example with a diff-oriented report

## v0.3 — Better evidence

- capture the exact quote and its position (issue body, comment, release note)
- follow-up comment count and reactions as an independent corroboration signal
- link duplicate signals to their canonical source instead of dropping them
- import existing research notes (Palantir output) as solution checks

## v0.4 — Solution research assistance

- `radar research <id>`: build a checklist of places to search (GitHub, PyPI, npm, HN, docs)
- record `none_found` / `exists` / `inaccessible` / `poorly_documented` with links and dates
- penalise accordingly and show the decision trail in the report

## v0.5 — Editorial output

- one-page brief per approved cluster (problem, evidence, hypothesis, MVP, risks, success criteria)
- portfolio-ready write-up generated from the same data
- comparison view between runs for the "what changed this month" article

## Not planned

- automatic project creation, code generation or deployment from a cluster
- scraping sites whose terms forbid it, or bypassing rate limits
- a learned ranking model before the rule-based one has a measurable track record

## Principles

- Every claim links to public evidence.
- The score explains itself; a human decides.
- Respect the APIs, the rate limits and the data minimisation rules.
- A failure is reported, never hidden.
- Prefer a small tool that runs every week over a large one that runs once.
