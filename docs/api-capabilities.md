# Liara capability evidence

Public contracts were checked22October2026 against [official API introduction](https://docs.liara.ir/references/api/about/), [PaaS OpenAPI](https://developers.liara.ir/spec/paas.yaml), and official CLI commit14ec35f79d703a09a5e3abbb22ba59239cdde80d. This establishes documented interfaces, not authenticated live schema acceptance.

The adapter scopes every request to explicit `teamID`, uses Bearer authentication, checks name/ID against discovered targets, and strips environment/author/node data. Existing failing and endpoint-less services require no baseline, semantic contract or deployment artifact. Unknown HTTP coverage is not failure. API401/403 means observer access failed; it does not mean the application failed.

Read routes: `/v1/projects`, `/v1/projects/{name}`, `/applets`, `/releases?page=1&count=10`, `/events?start=...&end=...`, `/metrics/summary`. Log schemas are deliberately separate: public v1 arrays with datetime/type/message, and current CLI v2 data groups with metaData.releaseId and nanosecond/string pairs. The configurable version defaults to the current CLI route but remains unverified against this account until real apps/key exist. No fallback silently reinterprets a payload.

Reads are limited to512KiB, five-second per-network-phase timeouts and one bounded retry for transient failures. Logs ask for a five-minute window and retain at most500 lines, with truncation/empty/stale/future-data quality. Raw metric units remain unverified; no percentages or resource-exhaustion claims are derived from names alone. Safe returned data is redacted before persistence/model use. These limits do not establish full log coverage or production observability.

Writes are not part of this initial adapter phase. Planned setup and repair require separate exact approvals and no generic POST retry. Native rollback, Kubernetes/tracing access, environment replacement and automatic topology discovery are not claimed.

Live gate: an owner-provisioned API key and explicitly approved disposable target deployments are still absent. The user's signed-in console was read-only checked during Torob preparation; no key was extracted/created. All current adapter evidence is deterministic fixture testing; real Liara integration stays pending.
