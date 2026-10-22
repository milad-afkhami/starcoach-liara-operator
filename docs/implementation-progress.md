# Implementation progress and rulings

User authorized Torob first, then Liara after completion or a confirmed blocker. Torob local code is in final independent review; actual hosted deployment has the plan’s concrete paid-provisioning approval gate. Liara implementation begins while those checks finish. No cloud key/app/disk or publication has been created.

- Ruling: an independent previously absent sibling repository on build/liara supplies workspace isolation without a nested worktree.
- Ruling: optional semantic checkout stays cut. Core demo is a real502 on a configured endpoint while liveness stays200; monitoring existing services has no artifact/baseline prerequisite.
- Preflight: L1 produces scoped Target/Evidence for L3/L4; L2 produces actual probes/known-good manifests for early L5 bootstrap; L5 setup precedes L3 live target checks, repair comes after L4; L4 uses a small isolated copy of our proven Codex adapter and shared global quota. No dependency on the Torob server or Wallex.
- Cloud creation/deployment, API-key provisioning and final public submission gates remain distinct from local implementation. Finish independent work without false live-integration claims.

## L1 adapter progress

- RED missing adapter, then26 passing scenarios cover exact team query/auth, environment exclusion, empty/already-failing inventory, wrong identity,401/403/404/429/500, bounded retry/response size, redirect refusal, v1/v2 log precision, truncation/staleness/future data, missing metrics and preserved release/applet identity. Red regression caught permissive JSON NaN and naive timestamps; both now reject.
- Public PaaS spec and pinned current CLI were inspected directly. Authenticated log/metrics/release acceptance remains pending; do not call fixtures sponsor integration. No UI surface in this phase, QA N/A; later L6 owns the real user flow.
- Ruling: metric values may be shown as raw provider evidence with unit_unverified; no inferred CPU percentages or zero-default health. This trades convenient charts for truthful diagnosis until actual units are verified.
