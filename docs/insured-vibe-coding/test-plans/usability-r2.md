# QA — Liara usability R2

UI surface: yes; rendered QA owed. App: owned isolated fixture operator, deterministic test model, no cloud writes or real model calls. Independent source/rendered QA supplements the owner pass. To reproduce the additional five browser scenarios, start `uv run python harness/serve_usability.py` in a fresh private directory (optional `LIARA_UI_QA_DIR`, `LIARA_UI_QA_PORT`, `LIARA_UI_QA_STORE_PORT`, `LIARA_UI_QA_DEP_PORT`); use its private access file with `LIARA_TEST_ACCESS_FILE` and `APP_URL`, plus `LIARA_USABILITY_FIXTURE=1 npm --prefix frontend run test:e2e`. This server has deterministic model/log/metric fixtures and actual loopback HTTP checks; it cannot write to Liara or call a genuine model. Ordinary canonical fixtures run the ten general browser regressions; the five fixture-specific rows require this explicitly selected harness.

| ID | Scenario and expected rendered result | Status |
|---|---|---|
| U1 | Owner types password and logs in; service overview separates failing /preview from passing /healthz, provider fixture label stays visible. | ✅ canonical browser1/2; independent first look |
| U2 | Context views work with keyboard and clicks; resources/logs/changes do not turn overview into a long report. Ask-from-sidebar returns to overview and focuses question. | ✅ context browser test; target/Ask focus assertions |
| U3 | Deterministic actual app investigation produces diagnosis, observed impact and next action. Copy/download handoff includes frozen cited evidence, unknowns and repo investigation/fix/tests; source text is readable and cannot trigger execution. | ✅ deterministic investigation, English export regression, copy/download equality and denied fallback |
| U4 | Actual historical CPU/RAM fixture series render separate applet charts, native times/units, invalid/future exclusions and visible gaps. Unknown/empty data shows no invented graph or zero. | ✅ actual CPU/RAM SVG/gaps/sample counts and worker unknown/no graph; parser18 behavior suite |
| U5 | Evidence opens readable facts/logs first; JSON is closed advanced audit, remains LTR/Latin when opened; Escape restores focus. | ✅ canonical RTL/raw/Escape + new readable evidence test; independent focus restoration |
| U6 | Start/stop watch, reload history, session expiry and sign-out clear private views/dialogs. Canonical regressions pass. | ✅ canonical watch/expiry/revoked-session/history assertions |
| U7 | Exact proposal, approve/execute guards, unknown/recheck history and recovered-vs-historical diagnosis remain intact on deterministic local states; no provider writes. | ✅ eight seeded display/guard states; login is the only POST; unchanged308 backend gates reused |
| U8 | At desktop and 390px: no horizontal overflow, readable chart and controls, no page errors; inspect screenshots. | ✅ five inspected screenshots; mobile no overflow/page errors; independent rendered pass |
| U9 | Setup recommendation form still accepts inputs, displays advice without pretending to provision anything. | ✅ independent actual form submit; affected authenticated/read-only setup API2 pass |

Missing-case review before execution: include tab state reset on target/session change, copied/downloaded content equality, stale/current generation handoff, unsupported units and partial resource sources, evidence paths versus fabricated repository paths. Negative fixtures remain explicitly labelled. Include authenticated empty list and no-endpoint worker, phone target switching/active clarity and clipboard-denied selectable/download fallback.

All nine rendered QA rows pass within the stated fixture/seeded scope. A separate authenticated truly empty inventory passed on a dedicated fixture; no selected service is invented and the next step is visible. Evidence and retained negative runs: [usability-r2.json](../../qa-evidence/usability-r2.json). No new cloud repair, genuine inference or sensitivity approval is claimed.

## Instance-label follow-up — planned before implementation

Actual live IDs are much longer than the original app-1 fixture. Show a friendly per-instance alias in each chart heading; CPU/RAM for the same ID share the alias, and refresh/order changes retain its mapping. Exact ID remains in a closed source disclosure and heading title. Do not combine values or change parsing/units/gaps/unknown handling.

| ID | Rendered assertion | Status |
|---|---|---|
| IL1 | Long real-shaped applet IDs do not appear as default heading text; CPU/RAM show the same friendly alias and remain separate charts. | ✅ 19 frontend behavior tests plus actual long-ID resource browser assertion; CPU/RAM remain two charts |
| IL2 | Exact long ID is available under closed source details and title; resource timestamps, units and gap lines stay intact. | ✅ actual closed provenance + title exact-ID assertion; gap/percent/MiB checks pass |
| IL3 | Phone chart headings fit without overflow; unknown/no-endpoint resource behavior remains unchanged. | ✅ 390px screenshot inspected; unknown/no-endpoint browser regression passes |

Validation scope: focused frontend behavior tests, production build and affected resource browser checks on an owned deterministic fixture; no backend change, model call, cloud write or main restart.
