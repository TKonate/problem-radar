# Taxonomy

Deliberately small: its job is to keep the report readable and to reward source diversity, not to be
an ontology. Every list lives in `problem_radar/taxonomy.py` and can be extended without touching
the logic.

## Domains

| Domain | Examples of keywords |
|---|---|
| `ai-agents` | llm, agent, prompt, rag, embedding, mcp, inference, model |
| `dev-tools` | cli, editor, git, debug, compiler, linter, test, dependency |
| `data-infra` | database, postgres, docker, kubernetes, backup, queue, deploy |
| `security` | vulnerability, cve, auth, secret, encryption, permission |
| `productivity` | obsidian, notion, calendar, task, notes, email, sync |
| `other` | no match |

## Categories

| Category | Examples of keywords |
|---|---|
| `recurring-bug` | crash, regression, bug, fails, panic, data loss |
| `missing-feature` | feature request, no way to, cannot, support for, missing |
| `integration-pain` | integration, webhook, api, sdk, plugin, compatible |
| `docs-gap` | documentation, undocumented, no example, tutorial |
| `cost` | expensive, pricing, quota, rate limit, paywall |
| `performance` | slow, latency, timeout, oom, throughput |
| `ux-friction` | confusing, annoying, tedious, manual, unusable |
| `maintenance` | abandoned, unmaintained, stale, deprecated, fork |
| `other` | no match |

Matching is **whole-word** and case/accent-insensitive: "bug" does not match "debug", "api" does not
match "capital". Without that, every other issue looks like a bug report.

## Source tiers

| Tier | Weight | Used for |
|---|---|---|
| `official` | 0.95 | vendor changelog, release notes |
| `issue-tracker` | 0.85 | public bug tracker of a project |
| `community` | 0.60 | forum, Q&A, mailing list |
| `blog` | 0.55 | technical blog post |
| `social` | 0.35 | aggregator, social network |
| `unknown` | 0.25 | manual note without provenance |

These weights are a judgement, not a measurement. They exist so that ten tweets cannot outweigh
three confirmed issue threads. Changing them is a configuration change, and the report recomputes.

## Severity words

Pain vocabulary (`crash`, `data loss`, `regression`, `not found`, `timeout`, `exceeded`, …) is counted
per cluster, saturating at four distinct words. The saturation prevents keyword stuffing from
inflating a score.
