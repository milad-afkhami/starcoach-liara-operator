# R2a rendered QA plan

UI surface: yes. Isolated actual FastAPI operator with deterministic fixture observations/model output, seeded historical states and real loopback HTTP. No cloud/model/operation execution. First locked R2 review remains251 at74fcc35; this QA does not score.

| ID | Scenario and expected result | Status |
|---|---|---|
| A1 | Current cited failing repair_candidate shows conditional source-review handoff; export requests a fix only after repository cause confirmation, with no deploy authority. | ✅ outcome browser2 and22 behavior tests |
| A2 | no_app_change/healthy endpoint result has closed optional review export, no prominent repair request; original full summary/unknowns/citations retained. | ✅ outcome browser1; full original summary/export identity assertions |
| A3 | need_evidence and stale-generation diagnosis stay optional diagnostic/review-only, without requesting code edits. | ✅ outcome browser1; current-check and generation regressions |
| A4 | Recovered or already-submitted action shows historical review-only export; recovery result stays ahead of old diagnosis. | ✅ outcome browser2; timestamp chronology regression |
| A5 | Summary longer than300characters includes its final provider-gap instruction; no duplicate generic next-step line. | ✅ outcome browser1 >300-character exact-text assertion; no .next-action |
| A6 | At390px, recent investigations disclosure opens and selects an older actual record; correct service/record loads. Switching target and logging off clear private state. | ✅ outcome browser3; actual records/selection/target/logout and sticky history control |
| A7 | Operation explains source redeploy, bounded original-symptom/serving-version checks and limitations before exact hashes; exact fields and expired/stale/unknown guards retained. | ✅ outcome browser2 exact-field/order/approval assertions; stale guard in browser1; prior unchanged expiry/unknown evidence reused |
| A8 | Setup defaults are stated transparently, measured minima are optional/editable, submitted unchanged or edited values are correct; no capacity guess/provisioning. | ✅ outcome browser4 actual default and edited request bodies |
| A9 | Canonical browser regressions, copy/download/clipboard denial, resource aliases/unknowns/gaps and desktop/mobile overflow/error checks remain green. | ✅ canonical15 plus outcome4,22 behavior/build/Ruff/diff; captured desktop/phone screenshots inspected |

Missing-case review before driving: historical manual open with no operation, unavailable cited evidence conservatively diagnostic, same service older-history selection, stale summary text preserved without suggesting current action, double session/target changes while incident detail loads.

Owner QA9/9 is complete within the explicit fixture scope. Receipts and retained negative runs: [usability-r2a.json](../../qa-evidence/usability-r2a.json). Reproduce the seeded matrix with `LIARA_UI_QA_CASES=1` on a new private fixture instance and `LIARA_OUTCOME_FIXTURE=1` for outcomes.spec.ts; launch and drive together because real approval/freshness deadlines remain active. Root owns the independent scoped review and runtime/publication gate.
