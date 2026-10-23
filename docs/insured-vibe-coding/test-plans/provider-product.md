# QA plan — provider readiness and owner guidance

App under test: isolated loopback operator8682, new temporary DB, read-only local fixture provider, existing actual local HTTP endpoints8771/8772. A deterministic model supplies clearly labelled UI-test prose; this is rendered-flow QA, not model or live-provider acceptance. Main8661 is not restarted. Screenshots, network/console checks and exact outcomes belong to docs/qa-evidence/provider-product.json.

| # | Scenario | Steps | Expected result | Status |
|---|----------|-------|-----------------|--------|
| PP1 | Fresh login | Type password into rendered form, sign in | Owner form works, private inventory appears; no secret in response | ✅ — [record](../../qa-evidence/provider-product.json) |
| PP2 | Initial setup requirements | Open setup guide, choose workload and minima, submit | Read-only current fixture catalogue quote and deployment/domain checklist; no operation created | ✅ — [record](../../qa-evidence/provider-product.json) |
| PP3 | Changed setup inputs | Change RAM after result | Old quote disappears; new submit reflects new requirement | ✅ — [record](../../qa-evidence/provider-product.json) |
| PP4 | Impossible plan and no fabricated price | Request more RAM than catalogue provides | Explicit no-matching-plan status, no zero/default quote; checklist remains | ✅ — [record](../../qa-evidence/provider-product.json) |
| PP5 | Evidence location | Open service and evidence | Citation/detail labels identify target and exact check, raw payload remains LTR | ✅ — [record](../../qa-evidence/provider-product.json) |
| PP6 | Actual progress | Start deterministic investigation; inspect during collection/analysis | Real stage/read/model-call information; no invented percent; cancel remains reachable | ✅ — [record](../../qa-evidence/provider-product.json) |
| PP7 | Unenrolled remediation | Wait for current diagnosis, inspect checklist and click citation | Specific manual steps and original endpoint recheck, correct evidence target, no deploy control | ✅ — [record](../../qa-evidence/provider-product.json) |
| PP8 | Mobile readability | Repeat setup and checklist at390px | Controls usable, no horizontal page/dialog overflow, readable text and target/check labels | ✅ — [record](../../qa-evidence/provider-product.json) |
| PP9 | Session reset | Open setup dialog then log out/expire own session | Private guide/evidence result cannot reappear on new session | ✅ — [record](../../qa-evidence/provider-product.json) |
| PP10 | Unavailable catalogue | Run isolated provider without catalogue access, submit form | Clear unavailable-price/access message; no fabricated plan; guidance still works | ✅ — [record](../../qa-evidence/provider-product.json) |
| PP11 | Browser errors and cleanup | Capture console/network throughout; inspect final state and stop own server | No page errors, no active watch/job/operation, no model/container/cloud write | ✅ — [record](../../qa-evidence/provider-product.json) |

| PP12 | Verified resource schema | Open isolated fixture with console-compatible CPU/RAM summary | Per-process12.5% CPU and64MiB RAM with sample timestamps/source; no capacity/healthy claim | ✅ — [record](../../qa-evidence/provider-product.json) |
| PP13 | Stale/future metric samples | Open stale and future fixture projections | Stale clearly dated; future/invalid consumption hidden; no zero or current-resource claim | ✅ — [record](../../qa-evidence/provider-product.json) |
| PP14 | Unknown metric schema | Open unknown/unavailable metrics fixture | Explicit unverified/unavailable values, no guessed percentage | ✅ — [record](../../qa-evidence/provider-product.json) |
