# QA plan — read-only recovery recheck

Surface: isolated operator8685 with a temporary private DB and an explicitly seeded prior inconclusive attempt. Current provider and endpoint observations are real read-only reads of the two approved disposable apps; the test adapter refuses every provider write. Real clocks, five-second spacing and the unchanged verifier apply. This UI QA does not claim another actual deployment or replace root's original repair/recheck evidence.

| # | Scenario | Expected result | Status |
|---|----------|-----------------|--------|
| RR1 | Rendered owner login and seeded prior failure | Read-only recheck control appears for the exact eligible operation; previous failure visible | ✅ — [record](../../qa-evidence/recovery-recheck-ui.json) |
| RR2 | Click the recovery recheck | One accepted local observation action, awaiting-serving state and continued polling; no provider write | ✅ — [record](../../qa-evidence/recovery-recheck-ui.json) |
| RR3 | Duplicate request during active retry |409; same attempt token and one retry; no second observation job claimed | ✅ — [record](../../qa-evidence/recovery-recheck-ui.json) |
| RR4 | Complete unchanged verification | Actual expected build/request echoes, three rounds/five-second spacing, raw safe probe payloads and policy retained | ✅ — [record](../../qa-evidence/recovery-recheck-ui.json) |
| RR5 | Attempt history and retry removal | Both prior inconclusive and new result remain visible; retry control disappears | ✅ — [record](../../qa-evidence/recovery-recheck-ui.json) |
| RR6 | Mobile/readability and page errors |390px no horizontal overflow; clear read-only/awaiting/history labels; no page errors | ✅ — [record](../../qa-evidence/recovery-recheck-ui.json) |
| RR7 | Cleanup | Isolated server/browser closed, no active watch/job and no provider write | ✅ — [record](../../qa-evidence/recovery-recheck-ui.json) |
