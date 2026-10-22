# Independent local implementation review

Reviewed repository: `/home/milad/Desktop/projects/starcoach-liara-operator`. Base `fa7a9e1`; reviewed HEAD `d359e57fe709c0921296420ab0e65ea5c0658c99`. This is the single independent review requested for the complete local implementation, including the earlier adapter, probe, observation, model, approval and verification commits. Implementation, index, HEAD and QA ledgers were not edited.

Requirements inspected: the canonical Liara plan, original challenge source, local AGENTS.md/README.md, architecture, deployment, API capabilities, demo and implementation records. Product code inspected includes every backend module, demo service, owner/setup/controller CLI, local harness, model evaluation script and frontend behavior. Tests were inspected for the consequential boundaries below.

## Strengths

The product does support read-only existing-service investigation without a healthy baseline or HTTP endpoint. The provider adapter scopes requests and does not reuse read retries for writes. The executor freezes hash-verified source bytes, atomically claims a proposal and keeps ambiguous writes unresolved. Bootstrap requires its own creation ledger, and packaging does not itself enroll a known-good baseline. The model receives registered reads and evidence, while controller state and mutation authority remain outside its interface. Documentation consistently distinguishes local fixtures from actual Liara acceptance.

## Verification performed

- `uv run pytest -q -p no:cacheprovider`: **188 passed**, one dependency deprecation warning.
- `npm --prefix frontend test`: **3 passed**.
- `uv run ruff check --no-cache backend scripts harness demo`: **passed**.
- `frontend/node_modules/.bin/tsc --project frontend/tsconfig.json --noEmit`: **passed**.
- Executed isolated fake-clock/state reproductions in `/tmp/liara-review-repros.py`; they create only temporary state and perform no provider/network requests.
- Executed the actual frontend polling/preparation expressions extracted from the reviewed source in `/tmp/liara-review-ui-repros.mjs`. These are logic reproductions, not rendered-browser acceptance.
- Confirmed the tracked implementation diff remained clean and HEAD remained the reviewed commit. The independent rendered QA work is separate; its results are not claimed as my own execution.

Reproduce the Python findings with `uv run python /tmp/liara-review-repros.py` from the repository. Reproduce the frontend expression results with `node /tmp/liara-review-ui-repros.mjs`.

## Critical

None established.

## Important

### I1. Recovery can be certified outside the required time window or without five-second spacing between actual successes

Location: [verification.py:79](/home/milad/Desktop/projects/starcoach-liara-operator/backend/liara_guard/verification.py:79), [verification.py:114](/home/milad/Desktop/projects/starcoach-liara-operator/backend/liara_guard/verification.py:114), [verification.py:142](/home/milad/Desktop/projects/starcoach-liara-operator/backend/liara_guard/verification.py:142).

The delay is measured from a round's start, before its provider reads. A slow provider read in the first round can therefore place its successful HTTP probe immediately beside the next round's probe. Separately, the deadline is checked before a probe but not after it; the final result can finish after the 60-second limit and still enter the `streak == 3` success return. The freshness predicate permits this because it only compares `available_at` to the current clock, not the verification deadline.

Executed results: one run returned `recovered` with `observed_window=[100,161]`; its individual provider calls consumed nine or ten seconds and probes one or three seconds. Another returned `recovered` with actual successful probe observation times `[109,109,114]` and round-start times `[100,109,114]`. Both violate the stated recovery proof. This affects initial baseline registration as well as incident repair because both call this verifier.

Fix: gate success on the final completion time and acquisition times being inside the fixed window, and enforce minimum spacing on successful observations of each required check (or begin the next round only after a full interval following completion of the previous round). Add variable provider-latency and final-probe-crosses-deadline regressions.

### I2. Deployment reconciliation after restart depends on a browser loading inventory

Location: [api.py:130](/home/milad/Desktop/projects/starcoach-liara-operator/backend/liara_guard/api.py:130), [api.py:362](/home/milad/Desktop/projects/starcoach-liara-operator/backend/liara_guard/api.py:362), [operations_bridge.py:111](/home/milad/Desktop/projects/starcoach-liara-operator/backend/liara_guard/operations_bridge.py:111).

Registry construction leaves `targets` empty. The background operation loop calls the bridge directly, whereas only API resolution/inventory reads call `refresh()`. After a restart, an existing pending/unknown deployment consequently fails at `registry.resolve()` before any provider status request. `Executor.reconcile()` absorbs that exception and retains the operation, eventually expiring its reconciliation allowance. A submitted write is meant to continue bounded reconciliation independently of a watch or an open browser.

Executed result: a seeded pending deployment plus a freshly constructed application and `app.state.tick()` produced `registered_targets=[]`, `provider_status_reads=0`, `operation_state=pending`. Loading provider inventory into the registry and advancing ten seconds made the next tick perform the status read. No live provider was used. A persisted `ready` operation is also vulnerable to starting verification with this empty registry.

Fix: obtain and validate the necessary inventory/target identities as part of operation recovery/background reconciliation. Treat unavailable inventory as a retryable observation gap within the existing deadline; do not consume a verification attempt merely because no browser has populated the registry.

### I3. Completed diagnoses remain actionable after material service changes

Location: [observer.py:387](/home/milad/Desktop/projects/starcoach-liara-operator/backend/liara_guard/observer.py:387), [observer.py:127](/home/milad/Desktop/projects/starcoach-liara-operator/backend/liara_guard/observer.py:127), [api.py:608](/home/milad/Desktop/projects/starcoach-liara-operator/backend/liara_guard/api.py:608).

Material release/fingerprint changes advance the incident generation but leave a completed diagnosis and its `done` state intact. Diagnosis records do not store the generation they establish. The proposal endpoint accepts any retained `repair_candidate`, then binds a new proposal to the current generation; it even updates a changed failure fingerprint itself without requiring a new diagnosis. Thus the stale-generation protection covers in-flight model completion and old proposals, but not a completed conclusion used to mint a fresh proposal. The UI continues to label it an evidence-based finding.

Executed result: finishing an investigation, then calling `set_release()` changed generation from 1 to 2 while leaving `investigation_state=done` and the diagnosis byte-for-byte unchanged. The proposal acceptance path is established by the cited code; it does not compare a diagnosis generation. Execution still has its separate fresh discriminator guard, so this finding is not a claim that every stale diagnosis necessarily causes an incorrect write.

Fix: record the decision generation and mark historical diagnoses stale when material state changes. Preserve their evidence/history, but prevent the UI and proposal endpoint from treating them as a current supported recommendation. Require a current diagnosis before minting a proposal; a changed symptom during preparation should invalidate it rather than silently upgrade its generation.

### I4. Evidence labeled fresh at acquisition remains valid current support indefinitely

Location: [investigator.py:125](/home/milad/Desktop/projects/starcoach-liara-operator/backend/liara_guard/investigator.py:125), [investigator.py:174](/home/milad/Desktop/projects/starcoach-liara-operator/backend/liara_guard/investigator.py:174).

The evidence cutoff excludes future acquisitions, but no age calculation downgrades old evidence. The current-support guard only tests the persisted `quality == 'fresh'` label. Reinvestigating an open incident can therefore reuse old evidence as fresh support even after its observation window has elapsed, including when current reads are unavailable. Immutable acquisition records should remain immutable, but decision-time freshness cannot be copied unchanged from the original acquisition.

Executed result: a log observed at 99 and acquired at 100, marked fresh then, remained `fresh` at cutoff 1000 and was accepted as support for `dependency_timeout`. The stale-only regression tests only evidence already labeled stale; it does not test fresh evidence aging into stale evidence.

Fix: create a derived freshness view for each decision cutoff, with source-appropriate age bounds, and require currently valid supporting observations for current-state conclusions or repair candidates. Keep older records available as explicitly historical chronology rather than current proof. Test reinvestigation after elapsed time with newly unavailable reads.

### I5. The UI stops observing an ambiguous deployment while the backend is still reconciling it

Location: [App.tsx:35](/home/milad/Desktop/projects/starcoach-liara-operator/frontend/src/App.tsx:35).

The polling condition includes pending/ready/verifying operations but excludes `unknown`. If a release POST times out after acceptance, execution returns unknown and backend reconciliation continues. When there is no active watch or model job—an explicitly supported manual-investigation flow—the frontend stops `/api/state` polling and never shows the later known release, verification progress or recovery unless the user separately refreshes/reloads. Stopping or expiring a watch produces the same gap.

Executed frontend-expression result with an authenticated user, completed investigation and no watch: pending→polling true; unknown→polling false; ready→polling true. The real `useEffect` exits on the false condition. This is a static/logic reproduction, not a claimed browser run of live deployment.

Fix: keep polling unknown submitted operations through their bounded reconciliation deadline and expose the terminal follow-up state when the deadline expires. Include no-watch and watch-expiry ambiguous-write UI regressions.

### I6. An expired session's open evidence dialog is restored into the next session

Location: [App.tsx:25](/home/milad/Desktop/projects/starcoach-liara-operator/frontend/src/App.tsx:25), [App.tsx:38](/home/milad/Desktop/projects/starcoach-liara-operator/frontend/src/App.tsx:38), [App.tsx:80](/home/milad/Desktop/projects/starcoach-liara-operator/frontend/src/App.tsx:80).

`evidence` is retained in the root App component. Handling 401 clears the login flag, service list and main state but does not clear that evidence. The login-page return temporarily unmounts the dialog; it does not reset the parent state. Signing in again sets `logged=true`, so the old evidence dialog remounts immediately without any request authorized under the new owner session. Explicit logout also omits this state cleanup. This breaks the intended session partition even though the backend properly rejects cross-session evidence reads.

Reproduction from state flow: open an incident evidence dialog during a watch, let the next state request receive a real expired-session 401, then sign in to obtain a new owner session without reloading the document. The previous dialog is rendered from its retained object. This finding is based on direct React state-flow inspection; an independent rendered reproduction was not executed in this review.

Fix: use one session-reset path for logout and authentication failure that clears every private view/modal and invalidates pending request epochs. Add a rendered expiry-with-open-modal → new-login regression, including a delayed old-session response.

## Minor

### M1. Expired proposals have no direct preparation path in the UI

Location: [App.tsx:57](/home/milad/Desktop/projects/starcoach-liara-operator/frontend/src/App.tsx:57), [App.tsx:75](/home/milad/Desktop/projects/starcoach-liara-operator/frontend/src/App.tsx:75).

Expiry disables approval/execution, but `mayPrepare` remains false for a proposed/approved operation whose generation has not changed. The user must rerun the model investigation merely to change generation before preparing a replacement. The extracted expression returns false for an expired proposed operation. Include expiry in replacement eligibility and explain that the old approval cannot be used; the backend must still construct a new exact proposal.

## Declined to judge

- Actual Liara account authentication, response schemas, network provisioning, catalogue prices and source/release acceptance: credentials/resources are unavailable and LIVE1–LIVE5 explicitly remain blocked. Fixtures are not treated as sponsor integration, and their lack is not itself a code defect.
- Actual cloud build/deployment and three fresh public serving checks: require those blocked resources. The newly added `scripts/qa_artifacts.py` and its container evidence postdate this review pin and are owned by the parent execution task.
- A new real Codex evaluation or model credential inspection: not necessary to establish the code findings; existing eight-case results are synthetic and correctly labeled. I inspected the adapter/evaluation boundaries without reading authentication files or spending model quota.
- Independent rendered QA verdict, browser aesthetics and the newly running delayed-response/logout cases: the designated QA agent owns execution and evidence. Frontend findings here are explicitly identified as source/logic findings where applicable.
- Protection from a hostile local OS user rewriting approved registry/SQLite/source configuration: those files are the trusted owner boundary in this local single-owner MVP; no untrusted-host protection was promised.
- Semantic checkout, arbitrary repairs, multi-user production identity, hosted operator, automatic topology discovery, persistent 24-hour monitoring and outbound alerts: deliberately outside the approved MVP.
- Public repository/video/submission acceptance: delivery work remains separate and no completed submission was claimed.

## Assessment

**Ready to merge as a completed local implementation: no; fix the Important findings first.** The core separation of evidence, authority and mutation is sound, and the existing tests pass, but the recovery proof and restart/state handling do not yet meet the documented guarantees. This verdict does not convert any blocked live gate into a pass or require pretending those gates can be tested locally.
