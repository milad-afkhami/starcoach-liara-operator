# Historical CPU/RAM observations

Scope: native historical points from documented CPU/memory GETs, separate from the unchanged summary contract. This is a read-only observation, not a capacity or current-clock claim.

| ID | Rendered assertion |
|---|---|
| HM1 | Invalid summary remains visibly invalid; historical fallback shows native CPU/RAM values, timestamps, sample ages, source and explicit clock uncertainty. |
| HM2 | Owner can open the retained raw series, including rejected future points; those values are absent from the ordinary resource cards. |
| HM3 | An empty/unusable historical response remains unavailable, with exclusion counters and no invented zero values. |
| HM4 | A valid summary uses the existing summary presentation and does not blend in history. |
| HM5 | At 390px the resource panel and raw-evidence dialog fit the viewport; no page errors. |

Local test intent: strict <=cutoff and <=300-second boundary; native validation and per-applet selection; raw series immutable in storage; source-to-model projection excludes all raw/rejected values; since-only exact client query and explicit partial failures. Actual GET acceptance is separate in docs/qa-evidence/historical-metrics-live.json. No real model calls or provider mutations are permitted in this QA.
