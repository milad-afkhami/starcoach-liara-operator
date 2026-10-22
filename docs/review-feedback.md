# Blind review feedback and corrections

[← Documentation](README.md) · [Recorded review scope](qa-evidence/blind-judging.json)

Reviewers received original challenge requirements, isolated source-only snapshots and the real local product. They did not receive implementation documents/plans or builder descriptions. **Scores are simulated critical-review estimates, not official judging or a forecast.**

| Finding | Correction and verification |
|---|---|
| English interface for Persian customers | Persian labels, states, errors, new model prose and RTL layout; technical IDs/JSON remain unchanged LTR |
| Returning owner loses history/watch control | Stable instance owner separated from revocable random sessions; actual relogin restored exact incident/watch, and revoked cookie returned401 |
| Assistant question too low on mobile | Visible service-navigation action focuses and scrolls to the ready question; loading-layout race reproduced and fixed |
| Long-log prefix hid decisive recent request | Bounded structured recent-tail excerpt preserves newest timestamps/messages and explicit truncation/omission markers; immutable full evidence unchanged |
| Raw need_evidence label, missing date/zone and tiny metadata | Explicit Persian state mapping, absolute Persian date/Tehran time, at least11px mobile evidence metadata; rendered checks passed |

The final judge used one genuine fresh investigation. Its29-line/11,517-byte source log yielded a4,033-byte excerpt retaining10recent entries, including the matching current request. The Persian diagnosis cited that request and the dependency-field mismatch, kept uncertainty about the intended fix, and made no application change. Two model calls completed the observed run in50.4seconds.

Scores progressed205→218→223 out of300. The final review retained the largest deduction: authenticated Liara provider discovery, live baseline enrollment, cloud fault/deployment and actual recovery remain unproven. Local packaged-container tests and source-level operation boundaries do not replace those requirements. Metric units/capacity, continuous availability and production MTTR are not established.

One concurrent development run saw the release-refresh regression's transient stale state before failed; the isolated rerun and final full213-test run passed. The observation is retained in implementation progress. No silent migration of pre-fix ephemeral-owner records occurred.
