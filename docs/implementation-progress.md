# Implementation progress and rulings

User authorized Torob first, then Liara after completion or a confirmed blocker. Torob local code and its final review fix pass are verified; actual hosted deployment has the plan’s concrete paid-provisioning approval gate. Liara implementation begins while those checks finish. No cloud key/app/disk or publication has been created.

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

## L6 local API/interface acceptance in progress

- Authenticated API now supports existing-service inventory/detail, asynchronous investigation/cancel, evidence, bounded watch and precise operation proposal/approval/execute/status. One model job per owner, at most3 admitted globally, one model worker, queue time included in120seconds. Queued cancellation is immediate. Read-only monitoring survives missing model configuration.
- Red regressions caught duplicate owner admission, delayed queued cancellation, automatic watch resumption on restart, fresh-login false expiry text, and stale decision completion after a changed release. Run IDs and atomic terminal-state handling prevent old jobs from overwriting newer decisions or remaining forever running.
- Verification is bound to the exact approved policy and operation association. The approved new release may legitimately advance generation; a different operation/policy may not inherit the success claim. A restart during verification is recorded inconclusive, not granted a fresh unbounded window. Actual sponsor verification remains pending.
- Built Service Watch frontend;2core rendered flows passed with real local endpoints. Parent inspected desktop/mobile screenshots: no horizontal overflow or page errors. Source/provider fixture status is persistent, and502 is distinct from200 process liveness.
- Independent QA expanded the written local list to26rows. Initial LUI26 proved backend expiry stopped traffic while UI stranded at00:00; frontend now polls until server reports final watch state. LUI11/12/14/21 passed using explicitly labelled isolated production-app configurations, not claimed live Liara responses. Full main QA/retest still underway.
- The local two-service supervisor is harness/serve_local.py, with separate owner-only controller state. An exact SHA-bound local test approval via harness/control_local.py deployed the incompatible dependency; its source/answer key is absent from operator/model inputs. Actual local /preview502 and /healthz200 are the current review fixture. No cloud resource was changed.
- Local review login was generated outside Git at /tmp/codex-scratchpad-01a15365-1037-78b2-a19e-e47bb7574a9c/liara-local-access.json; do not copy its password into documentation, commands, results or browser captures.

## L6 browser regressions and live setup preparation

- Independent actual browser QA found same-target reselection invalidating an in-flight detail read without starting its replacement, leaving refresh disabled. A held real response reproduced the failure; selection now preserves that request for the same target. A second regression proved configured checks must remain known when observation transport fails. Both actual browser regressions now pass after the fixes; independent full retest continues.
- Owner setup now binds app creation to an explicit feature bundle and existing private network, in addition to the plan/name/team/current quote. Current official CLI/account contracts supply bundlePlanID and network; account pricing uses base hourly plus monthly basic bundle divided by720, with inspected10% VAT. Final console review showed1146toman/hour per Earth/basic app on22October; the live account catalogue is reread before any write. No cloud operation occurred.
- scripts/owner_setup.py prepares exact expiring proposals for only the two disposable demo names. New apps must be proven created by its own setup ledger before source enrollment; initial source deployment cannot overwrite an existing release. Three fresh provider/serving/build/original-endpoint checks are required before known-good registration; both registered baselines are checked again before enabling the dependency repair policy. No packaged file is assumed healthy merely from its name. Authenticated live acceptance remains blocked by the missing approved key/targets.

## Local packaging and delivery evidence

- Full backend suite188passed; frontend presentation3passed, TypeScript/Vite build passed, and5actual browser regression flows passed at checkpoint d359e57. The known upstream Starlette/httpx TestClient deprecation warning does not affect these observed assertions.
- Actual allowlisted source archives built with hashed dependencies and pinned Python image, then ran as private nonroot512MiB/0.5CPUcontainers. Healthy200→independent incompatible dependency502 with liveness200→three restored expected-build200checks passed. Correlated logs contained expected/observed field names. Exact source/image/build identities and request results are in docs/qa-evidence/packaged-containers.json; these are local container tests, not Liara API acceptance.
- Owner configuration CLI was exercised in a fresh temporary directory:0600private files, no printed password, overwrite refusal, and explicit missing-live-credential refusal. Actual provider create/deploy/baseline/repair remain blocked pending their concrete approvals.
- Fresh whole-local-code review is running on d359e57. Independent rendered UI QA continues; active-call/watch restart and material-invalidation retests passed. Do not promote unfinished rows or live gates to Done.
