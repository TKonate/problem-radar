# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [0.1.0] — 2026-11-18

First working version: the MVP described in the roadmap.

### Added

- **Collectors**: Hacker News (Algolia API), GitHub issue search, RSS/Atom, manual JSONL.
- **Politeness**: one request at a time per host (6 s for GitHub search), retries with backoff on
  429/5xx, explicit `User-Agent`, response size cap, per-query limit.
- **Noise filter**: title-level heuristics that reject commit prefixes, launch announcements and
  body-only matches; keeps questions, pain words, bug markers and category keywords.
- **Clustering**: IDF-weighted similarity (Jaccard + containment) with union-find; 0.30 default
  threshold; deterministic cluster ids; human state carried over by signal overlap or title.
- **Scoring**: six observable components, corroboration factor (×0.55 for a single signal), solution
  penalties, threshold-based recommendation, one explanation line per factor.
- **Pipeline**: `discovered → clustered → researched → proposed → approved | rejected → built →
  deployed`, with validated transitions.
- **Report**: Markdown summary table, per-cluster breakdown, evidence links and quotes, explicit
  "what the score does not measure" section, JSON export for a dashboard.
- **CLI**: twelve commands, short aliases, readable errors and exit codes, `--json` where useful.
- **Tests**: 168 tests including recorded HN/GitHub/Atom fixtures, HTTP retry and throttling,
  clustering sanity, score invariants, report rendering and end-to-end CLI runs. 94 % coverage.
- **First real run** committed under `data/` and `reports/` (68 signals, 67 clusters).

### Known limits

- One harvest yields leads, not corroborated opportunities: recurrence needs several runs.
- GitHub search relevance is uneven; broad queries return bot issues, hence the `comments:>` filter
  and targeted phrases in the default configuration.
- The RSS collector contributes little on general-purpose feeds; it exists for targeted ones.
