# QA plan — recovered incident presentation

Surface: isolated private snapshot fixture on8686; seeded original diagnosis and completed recovery record. No provider/model calls, root state changes or restarts. This checks the rendered product's treatment of historical information, not another recovery.

| # | Scenario | Expected result | Status |
|---|----------|-----------------|--------|
| RP1 | Recovered incident | Prominent verified recovery result and verification end time precede the historical analysis | ✅ — [record](../../qa-evidence/recovery-presentation-ui.json) |
| RP2 | Preserved original diagnosis | Closed pre-action section includes evidence cutoff; opening reveals original repair_candidate prose and citations unchanged, with past-tense outcome/unknown labels | ✅ — [record](../../qa-evidence/recovery-presentation-ui.json) |
| RP3 | Release labels | Before-release ID is labelled pre-deployment; submitted release ID is separately labelled verified only for completed/recovered operation | ✅ — [record](../../qa-evidence/recovery-presentation-ui.json) |
| RP4 | Pending comparison | Unfinished operation uses submitted-release label; no verified-recovery claim or collapsed historical diagnosis | ✅ — [record](../../qa-evidence/recovery-presentation-ui.json) |
| RP5 | Desktop/mobile and evidence access |390px has no overflow, original citation opens correct target/check, no page errors; exact approval fields remain available | ✅ — [record](../../qa-evidence/recovery-presentation-ui.json) |
