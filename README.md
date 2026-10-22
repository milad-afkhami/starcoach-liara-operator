# Service Watch — Liara monitoring assistant

Service Watch helps a Liara customer inspect an existing service, investigate a failure from cited evidence, and approve a narrowly enrolled repair. A service can be investigated immediately even when it is already broken, has no healthy baseline, or has no HTTP endpoint.

The core demonstration separates process liveness from a customer-facing failure: a storefront responds200 on `/healthz` while `/preview` returns502 after a genuine dependency response mismatch. The assistant can inspect the dependency’s bounded response, logs and release chronology. A recent deployment is supporting evidence, not automatic proof of cause.

## Current evidence

The local operator and two real local HTTP services are implemented. Provider metadata in local mode is explicitly simulated. Genuine Codex diagnosis has been evaluated on eight synthetic cases; precise outcomes and timings are in [results/diagnosis.json](results/diagnosis.json). Independent browser results are in [the local QA ledger](docs/insured-vibe-coding/test-plans/operator-ui.md). Actual Liara account/API/deployment/repair acceptance remains pending in [the live QA ledger](docs/insured-vibe-coding/test-plans/live-liara.md). No local result establishes live sponsor integration.

## Run locally

Requires Python3.12, uv, Node/npm, and Docker for isolated model calls. Install locked dependencies with `uv sync --locked` and `npm --prefix frontend ci`, then build with `npm --prefix frontend run build`.

Generate a new private environment with `uv run python scripts/init_operator.py --mode fixture --access-file /tmp/liara-local-access.json`. This refuses existing files and prints paths rather than credentials. The owner password is in that private access file. Start real fixture services with `PYTHONPATH=backend uv run python harness/serve_local.py`, then start the operator with `uv run --env-file .env python scripts/dev_server.py`. Open http://127.0.0.1:8661. Monitoring works without model configuration; the UI discloses that diagnosis is unavailable.

To enable the intended local Codex worker, supply the three explicit options shown in `scripts/init_operator.py --help`: static executable, local Codex authentication file, and the pinned official runtime image documented in docs/architecture.md. The child container only receives that executable, read-only model authentication, and a unique scratch directory; Liara credentials, operator state, controller state and the Docker socket are absent. This workflow uses `codex exec` with a schema and bounded result file; in the inspected CLI, `-p` is a profile option. Never export personal Codex authentication into a public cloud deployment.

Use the separate fixture controller to propose an incompatible dependency with `PYTHONPATH=backend uv run python harness/control_local.py propose`, then inspect its exact target/archive hash and approve it using the command’s `--id` and `--sha256` options. Fault setup is separate from the investigator and has no web endpoint. It is labelled test setup, not an organic production incident. [Live setup and approvals](docs/deployment.md) cover the actual provider workflow.

## Verify

Run `uv run pytest -q`, `uv run ruff check backend scripts harness demo`, `npm --prefix frontend test`, and `npm --prefix frontend run build`. With the local services in the documented failing-dependency state and the private operator running, set `LIARA_TEST_ACCESS_FILE` to the generated access file and run `npm --prefix frontend run test:e2e`. Browser tests use actual HTTP services and authenticated application routes; deliberate transport faults are labelled regression setup.

For a new actual model evaluation, run `PYTHONPATH=backend uv run --env-file .env python scripts/evaluate_diagnosis.py`. This consumes the same persistent model quota as UI use and the separate Torob entry; it never resets that budget. Synthetic fixture truth stays outside model requests. Existing result files do not prove another provider/model would produce the same results.

## Product boundaries

Watches are explicitly started, last15 minutes, and observe at most two services/three configured endpoints/180 periodic probes. Provider reads refresh at most once per minute. Investigations allow at most12 registered evidence reads and two model calls within120 seconds including queue wait. One model worker and persistent global limits bound use. Cancellation, restart, expiry and material service changes have explicit terminal states.

Existing services remain read-only unless the owner has independently enrolled the exact target, verified source/build and recovery policy. Repairs use a new known-good source deployment; no provider-native rollback endpoint is invented. An exact single-use five-minute approval binds target, source hash, before release, incident generation and verification policy. Ambiguous writes are reconciled rather than blindly retried. Provider readiness alone does not establish recovery: three fresh original-symptom/build checks and serving-release identity are required.

No environment replacement, automatic restart/resizing, arbitrary shell/URL execution, continuous24-hour monitoring, workplace Kubernetes access or outbound alerts are implemented. Metric units/limits remain unverified and are shown truthfully. Source details: [API capabilities](docs/api-capabilities.md), [architecture](docs/architecture.md), [demo sequence](docs/demo.md), and [evaluation](docs/evaluation.md), [current build state](docs/insured-vibe-coding/kanban.md), and [submission evidence](submission.md).
