# Persian customer interface QA

App: http://127.0.0.1:8661. This phase changes visible UI and owes rendered QA. API schemas, target IDs and JSON evidence stay unchanged. Local mode is labelled honestly.

| ID | Scenario | Steps and expected result | Status |
|---|---|---|---|
| FA1 | Persian login | Open signed out; Persian title and editable password; login reaches Persian inventory | ✅ frontend/e2e/operator.spec.ts, rendered browser regressions |
| FA2 | RTL layout | Inspect document language/direction; service navigation at right; Persian font loaded | ✅ frontend/e2e/operator.spec.ts, rendered browser regressions |
| FA3 | Actual evidence | Open storefront; see real HTTP 200 liveness and HTTP 502 symptom, technical paths remain LTR | ✅ frontend/e2e/operator.spec.ts, rendered browser regressions |
| FA4 | Evidence dialog | Open Persian evidence action; JSON stays LTR/Latin; Escape closes the modal | ✅ frontend/e2e/operator.spec.ts, rendered browser regressions |
| FA5 | Watch lifecycle | Start and stop watch using Persian labels; rendered state and countdown update | ✅ frontend/e2e/operator.spec.ts, rendered browser regressions |
| FA6 | Mobile | At 390px width, login/service/evidence remain usable without horizontal overflow | ✅ frontend/e2e/operator.spec.ts, rendered browser regressions |
| FA7 | Session isolation | Expire own session with dialog open; Persian login replaces private state; relogin does not restore old dialog | ✅ frontend/e2e/operator.spec.ts, rendered browser regressions |
| FA9 | Durable owner history | New valid login sees the same active watch; stop it, logout, relogin and recover the same stopped record; revoked session remains 401 | ✅ red on old backend; green after combined restart, exact stopped-watch ID restored and revoked cookie returned 401 |
| FA10 | Mobile assistant access | At 390px select service; visible «پرسیدن از دستیار» focuses and scrolls to question after detail is ready | ✅ rendered regression; initial race reproduced and corrected |
| FA11 | Readable absolute timestamps | At 390px evidence card and dialog show Persian calendar date plus Tehran time; metadata computed font is at least 11px; no overflow | ✅ actual rendered evidence card/dialog regression |
| FA8 | Real Persian investigation | Submit Persian question; fresh model result renders Persian explanation and preserves technical field identifiers | ✅ actual 2-call Codex diagnosis, 27.2s + 19.2s; Persian summary/unknowns; exact saved result survived relogin |

Automated regression scenarios live in frontend/e2e/operator.spec.ts. Unit tests cover Persian uncertainty/error labels while preserving identifiers. Raw source JSON, actual app names, platform identifiers, hashes and HTTP codes deliberately remain machine-readable.

Evidence: scratchpad `liara-persian-desktop.png` and `liara-persian-mobile.png`; frontend/test-results/results.json contains the rendered run. The first new digit/RTL test found a test setup assumption (the first evidence row was preview 502, not health 200); it now explicitly selects preview evidence and verifies untouched Latin 502 in the LTR JSON. FA8 completed via actual new model result and final rendered reread. The first run caught an English deterministic server caveat; the backend now emits Persian for new runs and the frontend localizes only that exact legacy system string for historical records. Raw model output and evidence are not rewritten.

Final rendered suite: 10/10 passed. Unit suite: 9/9 passed. TypeScript/Vite production build passed. Final evidence: scratchpad `liara-persian-model-result.json` and `liara-persian-model-result.png`; zero browser page errors, zero active watches/investigations at cleanup. Model diagnosis was not simulated; it cited the actual local dependency mismatch. Cloud-provider acceptance remains a separate unverified scope.

Second blind-judge follow-up: `need_evidence` and its legacy normalized `need evidence` label now render «نیاز به شواهد بیشتر». The label lookup normalizes only a known translation match, so arbitrary identifiers such as `shipping_toman` remain unchanged. `when()` uses the Persian calendar and explicit Asia/Tehran timezone for both epoch-seconds and ISO inputs, with a UTC-midnight rollover regression. Mobile evidence metadata is at least 11px with the regular muted foreground. No further model inference was used.
