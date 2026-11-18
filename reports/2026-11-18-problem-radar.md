# Problem Radar — 2026-11-18

> Generated 2026-11-18T00:41:03+00:00 · **68** signals · **67** clusters · 68 attached signals
> Sources: hackernews, github, rss, manual

> The score is an input to a decision, never the decision itself.

## Summary

| # | Score | Recommendation | Signals | Domain | Problem |
|---|-------|----------------|---------|--------|---------|
| 1 | 35.7 | watch | 1 | dev-tools | Fork sync: upstream and community fixes for pdf-inspector and AnyDoc (Mac + Windows hubs) |
| 2 | 35.7 | watch | 1 | other | Intel Arc A770: VK_ERROR_DEVICE_LOST after ~10 frames (0.2.4) |
| 3 | 35.7 | watch | 1 | ai-agents | lampOS voice: a load stall during an agent make makes the speaker reference start stale (40 ms) and the voice exits |
| 4 | 33.6 | watch | 1 | dev-tools | [doc] Documentation drift audit: 50 findings with fixes, open questions and commit plan |
| 5 | 33.6 | watch | 1 | data-infra | Helm chart: allow webhook lifecycle (preStop) and terminationGracePeriodSeconds to avoid refused admission calls during… |
| 6 | 33.6 | watch | 1 | ai-agents | MyMiniFactory: subscriber model fails with "could not be found, or isn't public" even though the account can download it |
| 7 | 33.6 | watch | 1 | data-infra | reading first: the platform's own audit write inside an action body's ctx.api.transaction logs 'Audit write FAILED on… |
| 8 | 33.6 | watch | 1 | ai-agents | tensor blk.0.ssm_beta.weight not found |
| 9 | 33.5 | watch | 1 | dev-tools | epic: documentation built on facts, with drift detected and fixed automatically (design needed) |
| 10 | 33.5 | watch | 1 | dev-tools | main-broken: developing-today/code id @86b594d — basic: nix flake check (biome-check) |
| 11 | 33.4 | watch | 1 | dev-tools | Issue with updating price information |
| 12 | 31.5 | watch | 1 | ai-agents | dogfood: Background job id lost after start |
| 13 | 31.5 | watch | 1 | ai-agents | Host shmem leak to 17 GB (unreclaimable) after `xe ... VM worker error: -12` while running OpenCL/OpenVINO on the PF… |
| 14 | 31.5 | watch | 1 | dev-tools | openai-codex: GPT-6.2 Sol missing after refresh and rejected while native Codex works |
| 15 | 31.5 | watch | 1 | dev-tools | Follow-up to #9418: Workflow heal: Test & Mark Stable Release failed on stable |

## Opportunities

## 1. Fork sync: upstream and community fixes for pdf-inspector and AnyDoc (Mac + Windows hubs) — 35.7/100 (watch)

status: **clustered** · signals: **1** · sources: github · domains: dev-tools · categories: recurring-bug · seen: 2026-11-17 → 2026-11-17

**Problem.** Fork sync: upstream and community fixes for pdf-inspector and AnyDoc (Mac + Windows hubs) — Its Windows failure was `test-ios-failed-tests.sh`, which #919 now skips.

**Why this score**

- volume: 1 signal(s), saturating at 10 → 7.2/25
- diversity: 1 distinct source(s) (github) → 5.0/20
- recency: last signal 1 day(s) old, half-life 90 days → 0.99
- severity: 4 distinct pain word(s) (crash, failed, fails, panic) → 15.0/15
- evidence: 100% of fields filled (url, author, date, quote) → 10.0/10
- confidence: mean source confidence 0.85 → 12.8/15
- corroboration: 1 signal(s) → ×0.55 (64.9 → 35.7)

**Solutions.** Not searched yet — this is the next human step (`radar solution <id> --status ...`).

**Evidence**

- [Fork sync: upstream and community fixes for pdf-inspector and AnyDoc (Mac + Windows hubs)](https://github.com/lawkitt/mdoc/issues/925) — github, @tebriz91 2026-11-17
  > Its Windows failure was `test-ios-failed-tests.sh`, which #919 now skips.

## 2. Intel Arc A770: VK_ERROR_DEVICE_LOST after ~10 frames (0.2.4) — 35.7/100 (watch)

status: **clustered** · signals: **1** · sources: github · domains: other · categories: performance · seen: 2026-11-17 → 2026-11-17

**Problem.** Intel Arc A770: VK_ERROR_DEVICE_LOST after ~10 frames (0.2.4) — ### What happened The attached files are runtime logs only (fefw.log, setup.log, fefw_crash.txt).

**Why this score**

- volume: 1 signal(s), saturating at 10 → 7.2/25
- diversity: 1 distinct source(s) (github) → 5.0/20
- recency: last signal 1 day(s) old, half-life 90 days → 0.99
- severity: 6 distinct pain word(s) (crash, error, failed, lost, missing, timeout) → 15.0/15
- evidence: 100% of fields filled (url, author, date, quote) → 10.0/10
- confidence: mean source confidence 0.85 → 12.8/15
- corroboration: 1 signal(s) → ×0.55 (64.9 → 35.7)

**Solutions.** Not searched yet — this is the next human step (`radar solution <id> --status ...`).

**Evidence**

- [Intel Arc A770: VK_ERROR_DEVICE_LOST after ~10 frames (0.2.4)](https://github.com/metrist38/fefw-recomp/issues/45) — github, @qaz9631356 2026-11-17
  > ### What happened The attached files are runtime logs only (fefw.log, setup.log, fefw_crash.txt).

## 3. lampOS voice: a load stall during an agent make makes the speaker reference start stale (40 ms) and the voice exits — 35.7/100 (watch)

status: **clustered** · signals: **1** · sources: github · domains: ai-agents · categories: missing-feature · seen: 2026-11-17 → 2026-11-17

**Problem.** lampOS voice: a load stall during an agent make makes the speaker reference start stale (40 ms) and the voice exits — ## Seen: lamp-c0a4, 13584, 17 Nov ``` 08:31:54.955 lamp-voice: no capture frame kept for 63 ms while a turn is held: it is cut 40 ms before its lease lapses, as a gap cuts it 08:31:55.040 lamp-voice: ref.d.speaker: Connection refused (os error 111) 08:31:55.046 lamp-voice: reference InvalidStart:…

**Why this score**

- volume: 1 signal(s), saturating at 10 → 7.2/25
- diversity: 1 distinct source(s) (github) → 5.0/20
- recency: last signal 1 day(s) old, half-life 90 days → 0.99
- severity: 4 distinct pain word(s) (can't, error, failed, invalid) → 15.0/15
- evidence: 100% of fields filled (url, author, date, quote) → 10.0/10
- confidence: mean source confidence 0.85 → 12.8/15
- corroboration: 1 signal(s) → ×0.55 (64.9 → 35.7)

**Solutions.** Not searched yet — this is the next human step (`radar solution <id> --status ...`).

**Evidence**

- [lampOS voice: a load stall during an agent make makes the speaker reference start stale (40 ms) and the voice exits](https://github.com/autonomous-ai/lampOS/issues/7420) — github, @darren101004 2026-11-17
  > ## Seen: lamp-c0a4, 13584, 17 Nov ``` 08:31:54.955 lamp-voice: no capture frame kept for 63 ms while a turn is held: it is cut 40 ms before its lease lapses, as a gap cuts it 08:31:55.040 lamp-voice: ref.d.speaker: Connection refused (os…

## 4. [doc] Documentation drift audit: 50 findings with fixes, open questions and commit plan — 33.6/100 (watch)

status: **clustered** · signals: **1** · sources: github · domains: dev-tools · categories: docs-gap · seen: 2026-11-17 → 2026-11-17

**Problem.** [doc] Documentation drift audit: 50 findings with fixes, open questions and commit plan — ## Summary | Category | Count (main findings) | Additional one-liners in Appendix | |---|---|---| | stale-fact | 21 | 10 | | missing | 7 | 4 | | orphan | 6 | 3 | | example-broken | 9 | 0 | | structural | 0 | 1 | | versioning | 3 | 2 | | gap | 4 | 3 | | **Total** | **50** | **23** | Top 5…

**Why this score**

- volume: 1 signal(s), saturating at 10 → 7.2/25
- diversity: 1 distinct source(s) (github) → 5.0/20
- recency: last signal 1 day(s) old, half-life 90 days → 0.99
- severity: 3 distinct pain word(s) (broken, missing, timeout) → 11.2/15
- evidence: 100% of fields filled (url, author, date, quote) → 10.0/10
- confidence: mean source confidence 0.85 → 12.8/15
- corroboration: 1 signal(s) → ×0.55 (61.1 → 33.6)

**Solutions.** Not searched yet — this is the next human step (`radar solution <id> --status ...`).

**Evidence**

- [[doc] Documentation drift audit: 50 findings with fixes, open questions and commit plan](https://github.com/els0r/goProbe/issues/524) — github, @els0r 2026-11-17
  > ## Summary | Category | Count (main findings) | Additional one-liners in Appendix | |---|---|---| | stale-fact | 21 | 10 | | missing | 7 | 4 | | orphan | 6 | 3 | | example-broken | 9 | 0 | | structural | 0 | 1 | | versioning | 3 | 2 | |…

## 5. Helm chart: allow webhook lifecycle (preStop) and terminationGracePeriodSeconds to avoid refused admission calls during drains — 33.6/100 (watch)

status: **clustered** · signals: **1** · sources: github · domains: data-infra · categories: integration-pain · seen: 2026-11-17 → 2026-11-17

**Problem.** Helm chart: allow webhook lifecycle (preStop) and terminationGracePeriodSeconds to avoid refused admission calls during drains — Admission calls dialled in that gap fail: ``` failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post "https://external-secrets-webhook.external-secrets.svc:443/validate-external-secrets-io-v1-externalsecret?timeout=5s": dial tcp <pod-ip>:10250: connect:…

**Why this score**

- volume: 1 signal(s), saturating at 10 → 7.2/25
- diversity: 1 distinct source(s) (github) → 5.0/20
- recency: last signal 1 day(s) old, half-life 90 days → 0.99
- severity: 3 distinct pain word(s) (failed, fails, timeout) → 11.2/15
- evidence: 100% of fields filled (url, author, date, quote) → 10.0/10
- confidence: mean source confidence 0.85 → 12.8/15
- corroboration: 1 signal(s) → ×0.55 (61.1 → 33.6)

**Solutions.** Not searched yet — this is the next human step (`radar solution <id> --status ...`).

**Evidence**

- [Helm chart: allow webhook lifecycle (preStop) and terminationGracePeriodSeconds to avoid refused admission calls during drains](https://github.com/external-secrets/external-secrets/issues/7322) — github, @raufer 2026-11-17
  > Admission calls dialled in that gap fail: ``` failed calling webhook "validate.externalsecret.external-secrets.io": failed to call webhook: Post…

## 6. MyMiniFactory: subscriber model fails with "could not be found, or isn't public" even though the account can download it — 33.6/100 (watch)

status: **clustered** · signals: **1** · sources: github · domains: ai-agents · categories: recurring-bug · seen: 2026-11-17 → 2026-11-17

**Problem.** MyMiniFactory: subscriber model fails with "could not be found, or isn't public" even though the account can download it — Importing https://www.myminifactory.com/object/3d-print-tiny-cookie-dragon-and-wyvern-875764 fails, both by pasting the link in Thingport and with Thingport Grab, with: "This MyMiniFactory object could not be found, or isn't public." The backend log shows the same message on each retry: [import]…

**Why this score**

- volume: 1 signal(s), saturating at 10 → 7.2/25
- diversity: 1 distinct source(s) (github) → 5.0/20
- recency: last signal 1 day(s) old, half-life 90 days → 0.99
- severity: 3 distinct pain word(s) (error, failed, fails) → 11.2/15
- evidence: 100% of fields filled (url, author, date, quote) → 10.0/10
- confidence: mean source confidence 0.85 → 12.8/15
- corroboration: 1 signal(s) → ×0.55 (61.1 → 33.6)

**Solutions.** Not searched yet — this is the next human step (`radar solution <id> --status ...`).

**Evidence**

- [MyMiniFactory: subscriber model fails with "could not be found, or isn't public" even though the account can download it](https://github.com/TautvydasDerzinskas/Thingport/issues/377) — github, @bbright20 2026-11-17
  > Importing https://www.myminifactory.com/object/3d-print-tiny-cookie-dragon-and-wyvern-875764 fails, both by pasting the link in Thingport and with Thingport Grab, with: "This MyMiniFactory object could not be found, or isn't public." The…

## 7. reading first: the platform's own audit write inside an action body's ctx.api.transaction logs 'Audit write FAILED on sys_audit_log (no such table)' on 18.5.0 and main — 33.6/100 (watch)

status: **clustered** · signals: **1** · sources: github · domains: data-infra · categories: integration-pain · seen: 2026-11-17 → 2026-11-17

**Problem.** reading first: the platform's own audit write inside an action body's ctx.api.transaction logs 'Audit write FAILED on sys_audit_log (no such table)' on 18.5.0 and main — ## What happens In an action body's `ctx.api.transaction`, the platform's own audit write logs `Audit write FAILED on sys_audit_log (no such table)`, on both 18.5.0 and main.

**Why this score**

- volume: 1 signal(s), saturating at 10 → 7.2/25
- diversity: 1 distinct source(s) (github) → 5.0/20
- recency: last signal 1 day(s) old, half-life 90 days → 0.99
- severity: 3 distinct pain word(s) (failed, lost, security) → 11.2/15
- evidence: 100% of fields filled (url, author, date, quote) → 10.0/10
- confidence: mean source confidence 0.85 → 12.8/15
- corroboration: 1 signal(s) → ×0.55 (61.1 → 33.6)

**Solutions.** Not searched yet — this is the next human step (`radar solution <id> --status ...`).

**Evidence**

- [reading first: the platform's own audit write inside an action body's ctx.api.transaction logs 'Audit write FAILED on sys_audit_log (no…](https://github.com/objectstack-ai/objectstack/issues/35028) — github, @objectstack-fleet[bot] 2026-11-17
  > ## What happens In an action body's `ctx.api.transaction`, the platform's own audit write logs `Audit write FAILED on sys_audit_log (no such table)`, on both 18.5.0 and main.

## 8. tensor blk.0.ssm_beta.weight not found — 33.6/100 (watch)

status: **clustered** · signals: **1** · sources: github · domains: ai-agents · categories: missing-feature · seen: 2026-11-17 → 2026-11-17

**Problem.** tensor blk.0.ssm_beta.weight not found — When I run the command (ollama run mymodel),the error occured: <img width="1339" height="64" alt="image-20261116202425332" src="https://github.com/user-attachments/assets/506fdcef-71ce-4cd4-995d-fc1ee3807f1a" /> The gguf model file can be loaded by by llama-server.exe(in…

**Why this score**

- volume: 1 signal(s), saturating at 10 → 7.2/25
- diversity: 1 distinct source(s) (github) → 5.0/20
- recency: last signal 1 day(s) old, half-life 90 days → 0.99
- severity: 3 distinct pain word(s) (cannot, error, not found) → 11.2/15
- evidence: 100% of fields filled (url, author, date, quote) → 10.0/10
- confidence: mean source confidence 0.85 → 12.8/15
- corroboration: 1 signal(s) → ×0.55 (61.1 → 33.6)

**Solutions.** Not searched yet — this is the next human step (`radar solution <id> --status ...`).

**Evidence**

- [tensor blk.0.ssm_beta.weight not found](https://github.com/ollama/ollama/issues/19733) — github, @uflexnihao 2026-11-17
  > When I run the command (ollama run mymodel),the error occured: <img width="1339" height="64" alt="image-20261116202425332" src="https://github.com/user-attachments/assets/506fdcef-71ce-4cd4-995d-fc1ee3807f1a" /> The gguf model file can be…

## 9. epic: documentation built on facts, with drift detected and fixed automatically (design needed) — 33.5/100 (watch)

status: **clustered** · signals: **1** · sources: github · domains: dev-tools · categories: integration-pain · seen: 2026-11-16 → 2026-11-16

**Problem.** epic: documentation built on facts, with drift detected and fixed automatically (design needed) — A read-only sweep of main `95c7b40b` (2026-11-16) found **183 findings: 61 WRONG, 60 STALE, 33 MISSING and 29 style/nit** across four slices.

**Why this score**

- volume: 1 signal(s), saturating at 10 → 7.2/25
- diversity: 1 distinct source(s) (github) → 5.0/20
- recency: last signal 2 day(s) old, half-life 90 days → 0.98
- severity: 3 distinct pain word(s) (error, missing, security) → 11.2/15
- evidence: 100% of fields filled (url, author, date, quote) → 10.0/10
- confidence: mean source confidence 0.85 → 12.8/15
- corroboration: 1 signal(s) → ×0.55 (61.0 → 33.5)

**Solutions.** Not searched yet — this is the next human step (`radar solution <id> --status ...`).

**Evidence**

- [epic: documentation built on facts, with drift detected and fixed automatically (design needed)](https://github.com/okeefeco/pyeye-mcp/issues/818) — github, @hangie 2026-11-16
  > A read-only sweep of main `95c7b40b` (2026-11-16) found **183 findings: 61 WRONG, 60 STALE, 33 MISSING and 29 style/nit** across four slices.

## 10. main-broken: developing-today/code id @86b594d — basic: nix flake check (biome-check) — 33.5/100 (watch)

status: **clustered** · signals: **1** · sources: github · domains: dev-tools · categories: recurring-bug · seen: 2026-11-15 → 2026-11-15

**Problem.** main-broken: developing-today/code id @86b594d — basic: nix flake check (biome-check) — Main-tier workflow `id` failed on main.

**Why this score**

- volume: 1 signal(s), saturating at 10 → 7.2/25
- diversity: 1 distinct source(s) (github) → 5.0/20
- recency: last signal 3 day(s) old, half-life 90 days → 0.98
- severity: 3 distinct pain word(s) (broken, crash, failed) → 11.2/15
- evidence: 100% of fields filled (url, author, date, quote) → 10.0/10
- confidence: mean source confidence 0.85 → 12.8/15
- corroboration: 1 signal(s) → ×0.55 (60.9 → 33.5)

**Solutions.** Not searched yet — this is the next human step (`radar solution <id> --status ...`).

**Evidence**

- [main-broken: developing-today/code id @86b594d — basic: nix flake check (biome-check)](https://github.com/developing-today/code/issues/10461) — github, @developing-today[bot] 2026-11-15
  > Main-tier workflow `id` failed on main.

## 11. Issue with updating price information — 33.4/100 (watch)

status: **clustered** · signals: **1** · sources: github · domains: dev-tools · categories: missing-feature · seen: 2026-11-14 → 2026-11-14

**Problem.** Issue with updating price information — **Describe the bug** Go to Set to Price Guide and it cannot update items **To Reproduce** Steps to reproduce the behavior: 1.

**Why this score**

- volume: 1 signal(s), saturating at 10 → 7.2/25
- diversity: 1 distinct source(s) (github) → 5.0/20
- recency: last signal 4 day(s) old, half-life 90 days → 0.97
- severity: 3 distinct pain word(s) (cannot, error, missing) → 11.2/15
- evidence: 100% of fields filled (url, author, date, quote) → 10.0/10
- confidence: mean source confidence 0.85 → 12.8/15
- corroboration: 1 signal(s) → ×0.55 (60.8 → 33.4)

**Solutions.** Not searched yet — this is the next human step (`radar solution <id> --status ...`).

**Evidence**

- [Issue with updating price information](https://github.com/rgriebl/brickstore/issues/1097) — github, @jcgoodacre 2026-11-14
  > **Describe the bug** Go to Set to Price Guide and it cannot update items **To Reproduce** Steps to reproduce the behavior: 1.

## 12. dogfood: Background job id lost after start — 31.5/100 (watch)

status: **clustered** · signals: **1** · sources: github · domains: ai-agents · categories: other · seen: 2026-11-17 → 2026-11-17

**Problem.** dogfood: Background job id lost after start — A later `job: "job-2"` read answered `Tool job not found`, although the same command run in the foreground then exited 0.

**Why this score**

- volume: 1 signal(s), saturating at 10 → 7.2/25
- diversity: 1 distinct source(s) (github) → 5.0/20
- recency: last signal 1 day(s) old, half-life 90 days → 0.99
- severity: 2 distinct pain word(s) (lost, not found) → 7.5/15
- evidence: 100% of fields filled (url, author, date, quote) → 10.0/10
- confidence: mean source confidence 0.85 → 12.8/15
- corroboration: 1 signal(s) → ×0.55 (57.4 → 31.5)

**Solutions.** Not searched yet — this is the next human step (`radar solution <id> --status ...`).

**Evidence**

- [dogfood: Background job id lost after start](https://github.com/oxstack/ox-llm/issues/921) — github, @oxa-agent[bot] 2026-11-17
  > A later `job: "job-2"` read answered `Tool job not found`, although the same command run in the foreground then exited 0.

## 13. Host shmem leak to 17 GB (unreclaimable) after `xe ... VM worker error: -12` while running OpenCL/OpenVINO on the PF (2026.10.28, kernel 7.0.14) — 31.5/100 (watch)

status: **clustered** · signals: **1** · sources: github · domains: ai-agents · categories: performance · seen: 2026-11-17 → 2026-11-17

**Problem.** Host shmem leak to 17 GB (unreclaimable) after `xe ... VM worker error: -12` while running OpenCL/OpenVINO on the PF (2026.10.28, kernel 7.0.14) — The leak starts ~3 s after the driver logs its only warning: ``` [114336.691483] xe 0000:00:02.0: [drm] VM worker error: -12 ``` Note: this looks different from #425 / #254 — no guest/VM uses a GPU VF here.

**Why this score**

- volume: 1 signal(s), saturating at 10 → 7.2/25
- diversity: 1 distinct source(s) (github) → 5.0/20
- recency: last signal 1 day(s) old, half-life 90 days → 0.99
- severity: 2 distinct pain word(s) (error, leak) → 7.5/15
- evidence: 100% of fields filled (url, author, date, quote) → 10.0/10
- confidence: mean source confidence 0.85 → 12.8/15
- corroboration: 1 signal(s) → ×0.55 (57.4 → 31.5)

**Solutions.** Not searched yet — this is the next human step (`radar solution <id> --status ...`).

**Evidence**

- [Host shmem leak to 17 GB (unreclaimable) after `xe ... VM worker error: -12` while running OpenCL/OpenVINO on the PF (2026.10.28, kernel…](https://github.com/strongtz/i915-sriov-dkms/issues/515) — github, @GreenTeodoro839 2026-11-17
  > The leak starts ~3 s after the driver logs its only warning: ``` [114336.691483] xe 0000:00:02.0: [drm] VM worker error: -12 ``` Note: this looks different from #425 / #254 — no guest/VM uses a GPU VF here.

## 14. openai-codex: GPT-6.2 Sol missing after refresh and rejected while native Codex works — 31.5/100 (watch)

status: **clustered** · signals: **1** · sources: github · domains: dev-tools · categories: recurring-bug · seen: 2026-11-17 → 2026-11-17

**Problem.** openai-codex: GPT-6.2 Sol missing after refresh and rejected while native Codex works — A direct OMP request for Sol fails model resolution.

**Why this score**

- volume: 1 signal(s), saturating at 10 → 7.2/25
- diversity: 1 distinct source(s) (github) → 5.0/20
- recency: last signal 1 day(s) old, half-life 90 days → 0.99
- severity: 2 distinct pain word(s) (fails, missing) → 7.5/15
- evidence: 100% of fields filled (url, author, date, quote) → 10.0/10
- confidence: mean source confidence 0.85 → 12.8/15
- corroboration: 1 signal(s) → ×0.55 (57.4 → 31.5)

**Solutions.** Not searched yet — this is the next human step (`radar solution <id> --status ...`).

**Evidence**

- [openai-codex: GPT-6.2 Sol missing after refresh and rejected while native Codex works](https://github.com/can1357/oh-my-pi/issues/19578) — github, @cc-syntax 2026-11-17
  > A direct OMP request for Sol fails model resolution.

## 15. Follow-up to #9418: Workflow heal: Test & Mark Stable Release failed on stable — 31.5/100 (watch)

status: **clustered** · signals: **1** · sources: github · domains: dev-tools · categories: integration-pain · seen: 2026-11-16 → 2026-11-16

**Problem.** Follow-up to #9418: Workflow heal: Test & Mark Stable Release failed on stable — Follow-up: Follow-up: make a Phase 4 review timeout caused by a run that never started classify as environmental.

**Why this score**

- volume: 1 signal(s), saturating at 10 → 7.2/25
- diversity: 1 distinct source(s) (github) → 5.0/20
- recency: last signal 2 day(s) old, half-life 90 days → 0.98
- severity: 2 distinct pain word(s) (failed, timeout) → 7.5/15
- evidence: 100% of fields filled (url, author, date, quote) → 10.0/10
- confidence: mean source confidence 0.85 → 12.8/15
- corroboration: 1 signal(s) → ×0.55 (57.2 → 31.5)

**Solutions.** Not searched yet — this is the next human step (`radar solution <id> --status ...`).

**Evidence**

- [Follow-up to #9418: Workflow heal: Test & Mark Stable Release failed on stable](https://github.com/shubhodeep1/coding-workflows/issues/9619) — github, @shubhodeep1 2026-11-16
  > Follow-up: Follow-up: make a Phase 4 review timeout caused by a run that never started classify as environmental.

### Not detailed in this report

52 lower-scored cluster(s) are stored in `/opt/data/work/problem-radar/data/clusters.json`. Use `radar list` to see them.

## How to read this report

Each score is the sum of six observable components, minus solution penalties:

- **volume** — independent signals describing the problem (logarithmic, saturates at 10);
- **diversity** — how many different source families report it (saturates at 4);
- **recency** — how recent the last signal is (90-day half-life);
- **severity** — how painful the wording is (distinct pain words, saturates at 4);
- **evidence** — how complete the evidence is (URL, author, date, quote);
- **confidence** — the reliability of the source family.

**What the score does not measure.** Mentions are not demand; the score says nothing about
willingness to pay, feasibility, solution cost, legal risk or strategic interest. An existing
solution is only accounted for when a human recorded a solution check. The recommendation is a
reading aid, never a decision: every cluster that matters must be validated by a person before a
project is created.


## Provenance

- Configuration: `/opt/data/work/problem-radar/config/radar.json`
- Signals: `/opt/data/work/problem-radar/data/signals.jsonl`
- Clusters: `/opt/data/work/problem-radar/data/clusters.json`
- Tool: problem-radar, data collected from public APIs only.
