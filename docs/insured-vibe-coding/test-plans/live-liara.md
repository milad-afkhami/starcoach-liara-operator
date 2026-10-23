# QA plan — actual Liara integration and repair

Actual acceptance completed23October on the two exact disposable targets using a private account token and explicit team/target enforcement. Each row below owns its observed scope; the deliberately isolated credential-loss case is labelled separately. Source-only and fixture checks are not substituted for provider evidence.

|ID|Scenario|Expected result|Status|
|---|---|---|---|
|LIVE1|Actual scoped inventory/log/release/metrics reads|Correct team/targets, validated real schemas, truthful units and coverage|✅ Actual inventory/log/schema/history inputs; live-runtime-inputs.json, live-log-query.json and historical-metrics-live.json. Unsupported applets/future summary stay unknown.|
|LIVE2|Exact bootstrap and baseline registration|Current quote/name/artifact approved; actual initial release and fresh build checks; no existing app overwritten|✅ Exact scoped setup and both real baseline/build checks; actual scope in deployment.md and private setup ledger.|
|LIVE3|Independent approved fault injection|Actual configured endpoint502 with liveness200; no controller answer key in model inputs|✅ Independent approved incompatible source; actual502/liveness200 and genuine cited diagnosis in live-ready-diagnosis.json.|
|LIVE4|UI diagnosis→precise approval→actual redeployment|Supported evidence, exact single-use approval and source/release identity; expired approval is disabled and a fresh exact replacement can be prepared on an enrolled target; ambiguous write not retried|✅ Final-source exact UI approval, real5-minute expiry/API409, fresh replacement and one deployment: live-expiry-repair.json.|
|LIVE5|Fresh original-symptom/build verification and negative observer case|Three fresh successes/new serving identity; failed proof remains open; observer-only failure makes zero app writes|✅ Final fresh serving/build/original symptom3-round proof in live-expiry-repair.json; controlled actual401/no-change/zero-write-attempt case in live-observer-*.json.|

The whole entry cannot be declared done while these gates remain open. Local implementation may be reviewed and packaged without claiming live integration.

## Current actual observer-access acceptance

Run an isolated production operator on8762 with its own state, the actual registered cloud targets and genuine local Codex. Fetch inventory with the real observer authorization, then deliberately replace only this isolated client authorization with an invalid value. All subsequent provider401 responses must remain observation failures, while actual public endpoints stay200. Ask a genuine investigation, require no-app-change outcome and no repair proposal; the instrumented provider rejects/counts any attempted write. Record real HTTP statuses, diagnosis/citations, UI rendering and zero write attempts. This controlled credential-loss setup does not claim the account token was revoked or a spontaneous outage occurred. Restore by closing this isolated process; do not modify the real operator or any cloud application.
