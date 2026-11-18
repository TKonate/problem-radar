# Decisions

Chronological, with the reason. Superseded decisions are kept.

## 2026-11-17 — A radar, not a factory

**Decision.** The tool stops at a ranked report. It never creates a project, generates code or
publishes anything.

**Why.** The expensive mistake is building a solution to a problem nobody has. Automating the
construction before the detection is measured would industrialise that mistake.

## 2026-11-17 — Public APIs only, no scraping

**Decision.** Hacker News via the Algolia API, GitHub via the search API, RSS/Atom feeds, and a
manual JSONL path. No HTML scraping, no login, no proxy rotation.

**Why.** Terms of service, rate limits and maintenance cost. A radar that breaks every time a site
changes its markup is a liability, and "it works if you scrape harder" is not a foundation.

## 2026-11-17 — The title is the problem statement

**Decision.** Filtering and clustering use the title only; the body is kept as a 2 000-character
excerpt for evidence.

**Why.** Search APIs match bodies, so body-based filtering let "Papers — November 2026" through
because its text mentioned "rate limit". The resulting cluster was named after a title that said
nothing. Precision is worth more than recall here.

## 2026-11-17 — IDF weighting in clustering

**Decision.** Token similarity is weighted by inverse document frequency within the run.

**Why.** Unweighted Jaccard merged "Why birds keep crashing into planes" with "Why ships keep
crashing in storms" at low thresholds. Common words must count, but they must not decide alone.

## 2026-11-17 — Corroboration multiplier instead of a hard cap

**Decision.** The final score is multiplied by 0.55 / 0.75 / 0.90 / 1.00 depending on the number of
signals (1 / 2 / 3 / 4+).

**Why.** A single well-formed GitHub issue reached 65/100 on recency, severity and source confidence
alone — above corroborated problems. A flat cap at 42 fixed the ordering but flattened every
singleton to the same score, which destroyed the ranking. A multiplier keeps singletons comparable
with each other while keeping corroborated clusters ahead.

## 2026-11-17 — Human state survives re-clustering

**Decision.** Status, note and solution checks are carried over to the new clusters by signal
overlap (≥ 50 %) or exact title; scores are always recomputed.

**Why.** Cluster ids derive from their members, so adding one signal changes the id. Losing an
`approved` status because a new issue appeared would make the pipeline unusable.

## 2026-11-17 — No secrets in the configuration

**Decision.** `GITHUB_TOKEN` is read from the environment only.

**Why.** The configuration is committed with the repository. A token in `config/radar.json` would be
a secret in the git history, and rotating it would require rewriting history.

## 2026-11-18 — A committed real run, including its weaknesses

**Decision.** The first harvest (68 signals, 67 clusters, no corroborated cluster) is committed as
`data/` and `reports/`.

**Why.** A demo generated from invented signals would be a lie about what the tool does. The honest
output shows both the mechanics and the limit: one harvest yields leads; recurrence needs several
runs.
