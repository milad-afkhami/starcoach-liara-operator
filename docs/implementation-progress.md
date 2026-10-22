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

- Additional L1 red→green slow-stream budget regression:10-second wall budget checked between chunks, alongside5-second network-phase timeouts;27 tests pass. Live schema evidence remains pending. L2 begins next.

## L2 local demo and probe contracts

-53 tests pass: real HTTP dependency contract via test transport,502-versus200 liveness distinction, timeout reason, exact request/build propagation, registered origins, redirect/private-DNS refusal, pinned resolved-IP/TLS identity, fresh request IDs, bounded payload, exact artifact allowlist/hash and separate controller approval/replay/expiry/owner checks.
- Demo services use ordinary shipping_toman→delivery_toman incompatibility, opaque build IDs and correlated structured logs. No scenario label is returned to the investigator. Fault source and controller state are outside the operator/model tools. Semantic checkout remains cut.
- Healthy artifacts carry a generated build-id file separately from archive SHA-256; allowlisted packaging excludes .env/auth/VCS state. Configured dependency origin is packaged as an explicit nonsecret file. A changed archive cannot pass verification.
- Controller execution claims once even if its narrow provider writer fails. That writer must recheck before_release and reconcile ambiguous outcomes in L5; no live fault deployment is authorized or performed yet.
- Actual local HTTP QA passed: storefront /preview200 with real dependency, changed dependency source then /preview502 while /healthz remained200, changed opaque dependency build propagated, correlated log fields retained. Evidence: docs/qa-evidence/local-services.json. All QA service processes stopped. No Liara deployment/model diagnosis claim is made from this local fixture.

## L3 bounded monitoring

- Persistent15-minute watches, max2services/3HTTPchecks/180probes; provider refresh at most once/minute. Two endpoint failures open an incident without requiring a prior healthy baseline. Endpoint-less workers are normal. Runtime failure and observer401/403 are separate incident kinds; unknown metric units produce no guessed resource alert.
- Immutable owner-scoped evidence retains acquisition availability, source observation and provenance; incident observation sequence is separate from material generation. Same-failure polls preserve generation; changed release/fingerprint or sustained fresh recovery changes it.
- Red regressions caught a new probe after stop-during-provider-read, an older delayed probe overwriting newer health, and model completion overwriting newer observation sequence. All fixed;66tests and real local probe/watch acceptance pass. No SQLite write lock is held over network calls.
- Ruling: L3 fixture/local work proceeds before live L5 bootstrap because the explicit account/provisioning gate is pending, as allowed by the plan. L5 exact approval/intent primitives still precede any actual cloud setup; no circular bootstrap dependency or simulated-live claim.

## L5 primitives and L4 model boundary in progress

- Exact owner approvals bind a stored proposal digest, target/artifact/before-release/incident/policy and5-minute expiry. Atomic target claims prevent replay/concurrent writers. Upload/release intents persist before writes; ambiguous outcomes remain unknown, source IDs reconcile only unambiguously, and no generic POST retries exist.
- Red regressions caught initial app creation holding the target lock forever and a source-file change after hash validation. Creation now completes its setup operation; uploads use the exact hash-verified in-memory bytes (bounded5MB). This narrows the original Path interface to prevent an approved-archive time-of-check/time-of-use race.
- Verification requires provider/current/serving release identity plus3 fresh original-endpoint/build/request-echo successes5seconds apart within60seconds and12probe slots. Tests reject old/mixed instances, wrong build, replay, pre-change data, changed policy and READY with the symptom still failing. Full L5 live bridge/UI integration remains owed.
- Copied our isolated Codex adapter/model types and35tests from Torob commit19ff3cf into this independent repository; only temporary-directory/container labels changed to Liara. It retains the shared global100-start budget and mounts no Liara credential, operator DB or controller state. No running Torob server is required by this adapter.
- L4 interprets only immutable evidence available by cutoff, allows at most12 registered reads and2model calls/120seconds, validates support/contradiction IDs and rejects arbitrary operations. Observer authentication failure forces no_app_change; missing enrolled repair capability is disclosed. Raw evidence is redacted again at persistence, not merely trusted because a collector calls it redacted.
- Actual8-case synthetic Codex evaluation is running in scripts/evaluate_diagnosis.py, with rolling results/diagnosis.json and log /tmp/liara-actual-diagnosis.log. Ground truth stays in harness/fixtures/diagnostic-cases.json outside model requests. Do not claim final acceptance before all cases/results are inspected. No live Liara writes or API-key provisioning occurred.

## Actual Liara diagnosis evaluation

- All8 separately labelled synthetic cases met the expected cause-family/abstention outcome with genuine isolated Codex: schema regression, crash, timeout, distracting unrelated release, observer401 with passing endpoint, stale logs, unknown metric units and insufficient evidence. Eleven actual model calls; per-case wall time roughly10–22seconds. results/diagnosis.json owns exact output/provenance/timing. This is not a live Liara incident-success claim.
- Observer401 correctly returned no_app_change; stale/insufficient evidence abstained; no application writes exist in the investigator interface. No provider fallback or usage-ledger reset occurred. Current global model ledger includes both entries.
- L4 unit tests also cover invented IDs, arbitrary read/action names, stale generations, future evidence, source target mismatch, cancellation, redaction at persistence and structured source-read failure. Live service/UI integration and final review remain next.
