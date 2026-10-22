# QA plan — local service-monitoring interface

Use the actual compiled UI, authenticated FastAPI app, two actual local HTTP services, real isolated Codex and persistent SQLite. Fixture provider metadata must remain explicitly labelled. No mocked response can close a rendered-flow row. Setup HTTP calls may independently confirm state, not replace the UI action. An independent reviewer must add missed promises before execution.

|ID|Scenario|Expected result|Status|
|---|---|---|---|
|LUI1|Fresh login, type wrong then correct password|Inputs accept typing; wrong password is rejected; correct login enters service overview; no credentials in page/network response|✅ operator-ui.json rows.LUI1|
|LUI2|Reload and logout|Session persists on reload; logout removes access and private data from view|✅ operator-ui.json rows.LUI2|
|LUI3|Service overview without baseline/artifact|Two configured fixture services visible; clear mode/team; no watch starts implicitly|✅ operator-ui.json rows.LUI3|
|LUI4|Select already-broken service|Real /healthz200 and /preview502 remain distinct; no healthy-baseline prerequisite|✅ operator-ui.json rows.LUI4|
|LUI5|Evidence/source detail|Read logs/release/resource coverage and timestamps; unknown metrics never show0%/healthy; fixture status remains visible|✅ operator-ui.json rows.LUI5|
|LUI6|Real manual investigation|Type question, start actual Codex, visible progress, supported cause or explicit uncertainty; no app mutation|✅ operator-ui.json rows.LUI6|
|LUI7|Discriminating read and citations|Actual configured dependency evidence available; every cited ID opens the matching source; no scenario answer key|✅ operator-ui.json rows.LUI7|
|LUI8|Running cancellation|Owner cancels actual model call; canceled/failed state is honest; controls recover and no late conclusion overwrites new work|✅ operator-ui.json rows.LUI8|
|LUI9|Watch start and stop|Explicit15-minute scope, real probes, one incident per failing check, stop prevents new periodic traffic|✅ operator-ui.json rows.LUI9|
|LUI10|Observe while investigation runs|Same-failure observations can advance without invalidating the model; material changes invalidate stale decisions|✅ operator-ui.json rows.LUI10|
|LUI11|Provider-access gap|Explicitly injected isolated401/fixture replay is labelled; independently passing HTTP stays passing and no repair CTA appears|✅ operator-ui.json rows.LUI11|
|LUI12|No HTTP configuration|Endpoint-less service is unknown/not configured, never down merely for lacking a URL|✅ operator-ui.json rows.LUI12|
|LUI13|Independent sessions|No cross-owner incident/watch/approval disclosure; one session stop/cancel cannot change another|✅ operator-ui.json rows.LUI13|
|LUI14|Model unavailable|Monitoring/manual evidence remain usable; AI failure is shown without fabricated diagnosis|✅ operator-ui.json rows.LUI14|
|LUI15|Recoverable API failure|Injected transport failure shows feedback, releases loading state, allows real retry|✅ operator-ui.json rows.LUI15|
|LUI16|Question validation, repeated actions/admission limits|Blank/oversized questions get usable feedback; no duplicate investigation; one owner active and bounded global queue; cancel queued work works|✅ operator-ui.json rows.LUI16|
|LUI17|Restart|Old watches/model calls do not restart silently; persisted incident/evidence remains readable|✅ operator-ui.json rows.LUI17|
|LUI18|Unenrolled repair|Existing service remains investigable but no misleading executable repair control; crafted request rejected|✅ operator-ui.json rows.LUI18|
|LUI19|Keyboard/dialogs|Visible focus, Enter/Tab usability, evidence dialog Escape and focus return; no underlying-page focus leakage|✅ operator-ui.json rows.LUI19|
|LUI20|390×844 layout|Core login→service→investigate/evidence/watch flow usable with no horizontal overflow|✅ operator-ui.json rows.LUI20|
|LUI21|Empty team or unavailable connection|Useful explicit state, no invented services; recovery refresh works|✅ operator-ui.json rows.LUI21|
|LUI22|Console/network and source boundary|No uncaught app errors; no secrets/static state paths; only intended local/provider/model traffic|✅ operator-ui.json rows.LUI22|
|LUI23|Stale response and authentication races|Hold real detail/initial investigation responses while switching service or signing out; late data cannot restore private content or overwrite the newer selection, and controls recover after login|✅ operator-ui.json rows.LUI23|
|LUI24|Filter and recent-record navigation|Type a service name, try a no-match filter, clear it, then reopen a recent investigation; correct service/evidence is shown and active watch state remains attached to its service|✅ operator-ui.json rows.LUI24|
|LUI25|Copy evidence and denied clipboard|Copy the rendered bounded evidence, then inject clipboard denial; copied text matches the shown source and selectable fallback/feedback remains inside the evidence dialog|✅ operator-ui.json rows.LUI25|
|LUI26|Watch expiry transition|Observe an owned local watch at its deadline; countdown reaches zero, state becomes expired, Start becomes available, no new periodic probes are admitted; any accelerated fixture deadline is explicitly labelled|✅ operator-ui.json rows.LUI26|
|LUI27|Expired-session private-modal reset|Invalidate only the owned local session while its evidence dialog is open; real401 clears all private UI, and a fresh login cannot remount old evidence or selections|✅ operator-ui.json rows.LUI27|
|LUI28|Completed diagnosis invalidation|Complete a genuine investigation, change only labelled simulated release metadata, refresh; prior conclusion is not presented as current, original evidence remains readable, and fixture bytes are restored|✅ operator-ui.json rows.LUI28|
|LUI29|Bounded unknown-operation polling|Seed an owned explicit fixture operation in unknown state without a provider write; UI polls while reconciliation window is open then stops at the bound. Expired unexecuted proposal can be replaced when supported|✅ operator-ui.json rows.LUI29|

Separate actual-Liara acceptance is required below; local fixture rows never close it.

Independent pre-execution review added LUI23–LUI26 and extended LUI16. These protect distinct promises that successful investigation alone cannot establish. Expiry checks must exercise the production UI and scheduler; a controlled own-watch deadline may shorten waiting only if documented, and it does not claim a measured fifteen-minute wall-clock run. Native browser-chrome Tab traversal is acceptable if background app controls stay inert and focus returns to the dialog.

LUI26 initial actual run: a fresh owned watch was started through rendered controls and its normal900-second scope verified. Only that watch’s stored deadline was shortened to eight seconds ahead as explicitly authorized local setup; the production clock/API/scheduler were unchanged. The backend reached expired while the UI remained active at00:00 with no Start action. Screenshot/evidence are local fixture acceptance only; LIVE1–LIVE5 remain untouched. Other rows were unrun at that checkpoint; the final local result below supersedes that status.

Focused runtime retest after the discovered create/cancel race: enter the real acknowledged-container-create path, cancel through the rendered pending-request control, then verify no named/labeled container survives after a settling interval and no runtime fault latch remains. A genuine normal call on the new pinned image must also complete and clean up. The initial orphan lifecycle evidence remains recorded; a manual removal is not accepted as an adapter fix. These checks share the persistent global start ledger without resets.

Final local result: **29/29 rendered UI rows pass**, with assertion-specific evidence in `docs/qa-evidence/operator-ui.json` and `liara-*.png`. Failed initial expiry, selected-incident wiring, same-target loading, configured-observation error, and cancellation-cleanup attempts remain recorded alongside retests. Expiry setup, provider-access/empty-inventory fixtures, simulated release changes, and seeded operation state are explicitly labelled; none is represented as a real Liara provider write.

The genuine independence investigation completed while Torob’s server and worker were stopped. Actual model provenance and registered dependency citations were verified. The global start ledger advanced from50 to68: 17 QA-attributable charged runtime starts, including cancellations, plus one parent generic image proof. The quota was never reset.

Final cleanup review discovered an orphaned CREATED container after cancellation during Docker launch. Its lifecycle and absent fault latch were preserved before removing only that confirmed QA container. The shared adapter was fixed to acknowledge create before cancellable start. The focused real retest recorded create→destroy without a start event or orphan, followed by a normal genuine call on the pinned public Python image that completed and cleaned up. No runtime fault latch or model container remains.

The added session-expiry row used a real401 with the evidence dialog open and confirmed that fresh login clears modal, question, filter and old private state. Completed conclusions now become stale after material simulated release changes. The seeded unknown-operation row recorded a final canonical read after its reconciliation deadline, then bounded polling stopped. Expired approval is disabled with a replacement explanation; actual replacement is not applicable on the unenrolled local fixture and is not claimed as tested.

**LIVE1–LIVE5 remain blocked and unchanged.** Actual scoped Liara reads, owner-approved provisioning/fault injection, deployment approval/execution, and provider/build recovery proof are still required. All local variant servers were stopped; seeded operation state was deleted and simulated release bytes restored. Browser/context cleanup is recorded in the JSON; main8661 and real local fixture services8771/8772 remain with the parent.
