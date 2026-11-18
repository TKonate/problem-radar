# Methodology

This document is the reference for *how* a score is produced and *what it means*. Every number in a
report traces back to a rule written here.

## 1. What counts as a signal

A signal is one public item: a story, an issue, a feed entry, or a hand-written note. It is stored
as one JSON object with:

| Field | Meaning |
|---|---|
| `source`, `source_id` | where it comes from, stable identifier (dedupe key) |
| `url` | public evidence link |
| `title` | raw title, the problem statement |
| `body` | 2 000-character excerpt at most |
| `author`, `published_at` | attribution and date, when published |
| `domain`, `category` | inferred from keywords, whole-word matched |
| `problem`, `evidence` | cleaned statement and the supporting quote |
| `confidence` | source family reliability |

The **title is the problem**. Search APIs match bodies too, so filtering on the body lets a release
note through whenever it mentions "rate limit" and the resulting cluster is named after a title that
says nothing.

## 2. Noise filter

An item is kept when its title:

- is a question (`?`), or
- carries an explicit bug marker (`[Bug]`, `[Regression]`), or
- contains a severity word (`crash`, `data loss`, `not found`, `timeout`…), or
- starts with a conventional issue prefix (`fix:`, `[P1]`), or
- matches a category keyword (`missing`, `expensive`, `slow`, `integration`…).

and is rejected when it starts with a commit prefix (`docs:`, `chore(`, `feat(`) or an announcement
prefix (`Introducing`, `Announcing`, `We built`).

Precision over recall: a radar full of launch posts is unusable, and a missed item costs nothing
while a noisy report costs trust.

## 3. Clustering

Two titles belong to the same problem when their **IDF-weighted similarity** is at or above 0.30.

For each token, the weight is `ln((1 + N) / (1 + df)) + 1`, where `N` is the number of titles in the
run and `df` its document frequency. Similarity mixes:

- weighted Jaccard: `mass(intersection) / mass(union)`;
- weighted containment: `mass(intersection) / min(mass(a), mass(b))`;

with weights `0.6` and `0.4`. Clustering is a greedy union-find over all pairs (O(n²), capped at
2 000 signals).

Why IDF: without it, "keeps crashing" merges a plane crash with a software crash. With it, common
words still count but cannot carry a pair over the threshold on their own.

Cluster ids derive from the sorted member ids, so they are deterministic for a given set of signals.

## 4. Score

```
subtotal = volume + diversity + recency + severity + evidence + confidence + penalties
total    = clamp(subtotal × corroboration, 0, 100)
```

| Component | Max | Formula |
|---|---|---|
| volume | 25 | `min(1, log2(1+n) / log2(11)) × 25` |
| diversity | 20 | `min(1, distinct_sources / 4) × 20` |
| recency | 15 | `0.5 ** (days_since_last / 90) × 15`, neutral 7.5 without a date |
| severity | 15 | `min(1, distinct_pain_words / 4) × 15` |
| evidence | 10 | mean of URL 0.4, author 0.2, date 0.2, quote 0.2, × 10 |
| confidence | 15 | mean source tier weight × 15 |

Penalties: `exists` −30, `poorly_documented` −8, `inaccessible` 0, `none_found` 0, `unknown` 0.

Corroboration: `n=1 → ×0.55`, `n=2 → ×0.75`, `n=3 → ×0.90`, `n≥4 → ×1.00`.

Recommendation thresholds, out of 100:

| Score | Recommendation |
|---|---|
| ≥ 65 | submit to validation |
| ≥ 45 | research further |
| ≥ 30 | watch |
| < 30 | ignore |

## 5. What the score does not measure

- **Demand.** Mentions are not willingness to pay.
- **Feasibility.** A hard problem and an easy one score the same.
- **Solution landscape.** Only a recorded solution check affects the score.
- **Risk.** Legal, security, reputational and maintenance risks are absent by construction.
- **Strategic fit.** Whether *you* should build it is not a property of the text.

## 6. Known biases

- A noisy source with many items dominates volume. Diversity and corroboration mitigate, not remove.
- Recency favours this week's complaints over chronic problems.
- Keyword taxonomies favour problems phrased in English with the expected vocabulary.
- GitHub issue trackers over-represent developers and open-source users.
- The first run of a fresh portfolio has no recurrence: every cluster is a single-signal lead.
