# Configuration and API reference

[← Documentation](README.md) · [Architecture](architecture.md) · [Provider capability evidence](api-capabilities.md)

This page covers the **operator's own HTTP API and settings**. Liara's external API contracts and their acceptance qualifications are documented separately.

## Configuration

Prefer `scripts/init_operator.py` for initial private configuration. The example file is a reference of placeholders, not a safe substitute for generated password/signing values.

| Variable | Purpose | Notes |
|---|---|---|
| `PYTHONPATH` | Import root | `backend` |
| `LIARA_MODE` | `fixture` or `live` | Generator selects explicitly; application default is live |
| `PUBLIC_ORIGIN` | Exact browser origin | Local helper defaults to `http://127.0.0.1:8661` |
| `SESSION_SECRET` | Session-signing secret | Private generated value |
| `OPERATOR_PASSWORD_HASH` | Scrypt owner password hash | Generator writes the hash; private access file holds the password |
| `STATE_DB_PATH` | Persistent operator SQLite | Generator uses `data/operator.sqlite` |
| `LIARA_TEAM_ID` | Explicit provider team | Infrastructure team, not contest membership |
| `LIARA_API_TOKEN` | Account API credential | Trusted local operator only; never browser/model input |
| `LIARA_LOG_VERSION` | Explicit provider log adapter | Defaults to `v2`; no silent payload reinterpretation |
| `REGISTRY_PATH` | Checks, dependencies and repair registry | Live generator uses `data/live-setup/registry.json` |
| `CODEX_BINARY_PATH` | Static Codex executable | Supply together with authentication and image |
| `CODEX_AUTH_FILE` | Local model authentication | No Liara credentials in this mount |
| `CODEX_IMAGE` | Trusted pinned container image | [Recorded image](architecture.md#model-source-and-reproducible-image) |
| `MODEL_ID` | Model selection | Recorded build uses `gpt-6.1-sol` |

The provider token's actual native scope must be checked independently. Application team/target restrictions do not imply that Liara issued a resource-scoped token.

## Operator route map

The running local FastAPI app exposes `/docs` and `/openapi.json` for exact schemas. Authenticated operations still require an owner session; mutation requests require the exact configured Origin. The schema page is not an authentication bypass.

| Method | Route | Responsibility |
|---|---|---|
| GET | `/healthz` | Operator process liveness |
| POST | `/api/login`, `/api/logout` | Private owner session |
| GET | `/api/services` | Scoped provider inventory, configured checks and repair capability |
| GET | `/api/services/{identifier}` | Current service observations |
| POST | `/api/setup/recommendation` | Read-only requirement matching and initial deployment/domain guidance |
| POST | `/api/services/{identifier}/investigate` | Start a bounded investigation |
| GET | `/api/incidents/{identifier}` | Owned incident, evidence, capability and current fixed remediation checklist |
| POST | `/api/incidents/{identifier}/investigate` | Re-investigate a current incident |
| POST | `/api/incidents/{identifier}/cancel` | Cancel its current model work |
| POST | `/api/watches` | Start an explicitly scoped bounded watch |
| POST | `/api/watches/{identifier}/stop` | Stop periodic observation |
| GET | `/api/state` | Owner's watches/incidents/operations and server time |
| POST | `/api/incidents/{identifier}/proposal` | Prepare a supported enrolled repair candidate |
| POST | `/api/operations/{identifier}/approve` | Bind approval to its exact displayed digest |
| POST | `/api/operations/{identifier}/execute` | Fresh preflight and single-write execution |
| GET | `/api/operations/{identifier}` | Reconciliation/verification state and preserved attempt history |
| POST | `/api/operations/{identifier}/recheck-recovery` | One owner-triggered read-only recheck of the same submitted operation within its original deadline |

Identifiers are scoped to the signed-in owner and registry. Being able to list a service does not enroll mutation capability. Proposal requests are rejected unless live mode, enrolled repair support and a current supported diagnosis all agree.

## Runtime bounds

| Work | Bound |
|---|---|
| Periodic watch | 15 minutes; at most 2 services, 3 configured checks and 180 periodic probes |
| Provider refresh while watching | At most once per minute |
| Investigation | At most 12 registered reads, 2 model calls and 120 seconds including queue wait |
| Owner investigation admission | One active job per owner; at most 3 admitted globally |
| Model execution | One shared worker/lock; persistent rolling 24-hour start budget |
| Approval | Single-use, five-minute expiry, exact target/state/source/policy binding |
| Write reconciliation | Separately bounded, at most 10 minutes |
| Recovery verification | 3 fresh complete success rounds, at least 5 seconds apart, within 60 seconds / 12 probes |

The two product model adapters share a default 100-start rolling budget. It is not reset by a retry, browser session or documentation check. Unknown cleanup faults stop new model calls rather than hiding an orphaned container.

## Troubleshooting

| Symptom | Likely distinction to inspect | Next step |
|---|---|---|
| Cannot sign in | Wrong private access file or different generated environment | Use its matching password/configuration; do not overwrite the existing environment |
| Local service startup refuses a port | Another process is already listening | Inspect ownership; do not kill unrelated processes |
| AI unavailable | Adapter not fully configured or initialization failed | Verify all three Codex settings, Docker and local authentication |
| A configured AI call fails | Quota, timeout, validation or runtime fault | Read the bounded failure; inspect the runtime without resetting its ledger |
| `/healthz` passes but `/preview` fails | Process liveness differs from useful-endpoint health | Inspect the actual payload/log evidence and dependency |
| Provider evidence unavailable | Access/schema/network issue | Do not infer service failure or justify an app write |
| No repair button | Un-enrolled target, unsupported diagnosis or fixture mode | Continue read-only investigation; use exact owner setup for live capability |
| Proposal expires or becomes stale | Five-minute expiry or material service change | Refresh evidence and prepare a new exact supported proposal |
| Write outcome unknown | Upload/release response could not establish identity | Reconcile the existing operation; do not repeat POST blindly |
| Watch stops on restart | Deliberate interruption semantics | Start a fresh watch explicitly if desired |

## Source map

| Path | Responsibility |
|---|---|
| `backend/liara_guard/` | Provider adapter, observations, investigator, auth, approval/execution and verification |
| `frontend/src/` | Service notebook, evidence dialogs, investigation and operation views |
| `demo/` | Disposable storefront and delivery sources |
| `harness/` | Independent fixture/fault controller and diagnostic cases |
| `scripts/owner_setup.py` | Explicit create/package/baseline/enrollment workflow |
| `tests/`, `frontend/e2e/` | Domain/API/runtime and actual rendered regression checks |
| `results/`, `docs/qa-evidence/` | Recorded model/evaluation/browser/container outcomes |
| `data/` | Private runtime state and artifacts; not public source |

No kubeconfig, workplace infrastructure, private owner access file, provider token, model authentication or runtime database belongs in public source.
