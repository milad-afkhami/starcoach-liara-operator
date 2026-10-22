# Getting started

[← Documentation](README.md) · [Next: user guide →](user-guide.md)

This path starts a **local fixture-provider environment with real HTTP services**. It does not create a Liara API key, cloud app, network or paid resource.

## Prerequisites

| Requirement | Purpose |
|---|---|
| Python 3.12 and uv | Locked backend/runtime dependencies |
| Node 24 and npm | Frontend build and behavior tests |
| Docker and local Codex authentication | Optional genuine isolated model calls |
| Chrome | Optional actual browser regressions |
| Free ports 8661, 8771 and 8772 | Operator, storefront and delivery |

Commands run from the repository root. Do not start another copy over existing processes/state.

## 1. Install and build

```bash
uv sync --locked
npm --prefix frontend ci
npm --prefix frontend run build
```

## 2. Generate private owner access

For a fresh checkout without an existing `.env` or access file:

```bash
uv run python scripts/init_operator.py --mode fixture --access-file /tmp/liara-local-access.json
```

The generator creates private configuration and an owner password file, refuses overwrite, and prints paths instead of passwords. Read the password privately before logging in; keep that file out of screen recordings and Git. The generated environment selects fixture mode explicitly.

<details>
<summary><strong>Enable Codex when generating a new environment</strong></summary>

Supply all three model options together. Replace the two filesystem placeholders with the local static CLI executable and its existing model authentication file:

```bash
uv run python scripts/init_operator.py --mode fixture --access-file /tmp/liara-local-access.json \
  --codex-binary /absolute/path/to/static/codex \
  --codex-auth-file /absolute/path/to/codex/auth.json \
  --codex-image public.ecr.aws/docker/library/python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70
```

Choose this command **instead of**, not after, the basic generator. For an existing private environment, deliberately configure the same three `CODEX_*` settings without regenerating credentials or overwriting state. The recorded model is `gpt-6.1-sol`; installed CLI calls use `codex exec`, not `-p` as a prompt flag. [Model boundary](architecture.md#model-source-and-reproducible-image).

</details>

## 3. Start the real local services

In terminal A:

```bash
PYTHONPATH=backend uv run python harness/serve_local.py
```

This starts storefront at `http://127.0.0.1:8771` and delivery at `http://127.0.0.1:8772`. Both begin with healthy source. The supervisor refuses occupied ports rather than killing an existing process. Keep the terminal running.

## 4. Start the operator

In terminal B:

```bash
uv run --env-file .env python scripts/dev_server.py
```

Open **http://127.0.0.1:8661**, enter the privately generated owner password and click **Sign in**. Choose storefront in the sidebar. A fresh healthy setup shows passing `/preview` and `/healthz` checks. The running rehearsal environment may already contain an explicitly introduced local fault; inspect its observations rather than assuming a fresh state.

Without model configuration, observation still works and the interface discloses AI unavailability. With configuration, **AI configured** means the adapter is configured; an actual request can still fail due to credentials, Docker, quota or output validation.

## 5. Introduce the optional local rehearsal fault

This intentionally changes only the disposable local delivery fixture. It is separate owner-controlled setup, not an investigator tool or a cloud operation.

```bash
PYTHONPATH=backend uv run python harness/control_local.py propose
```

Inspect the exact target, before-release, proposal ID and archive hash. If you intend to introduce that displayed fault, approve those exact values:

```bash
PYTHONPATH=backend uv run python harness/control_local.py approve --id <proposal-id> --sha256 <displayed-archive-sha256>
```

The separate supervisor performs the approved deployment and records its receipt under `data/local-controller/`. Refresh storefront observations: `/preview` should fail with 502 while `/healthz` remains 200. Use the [user guide](user-guide.md) to investigate. This does not enroll a cloud repair capability.

To return these owned local fixtures to their initial healthy source, stop their supervisor with <kbd>Ctrl</kbd> + <kbd>C</kbd> and start it again after its child processes exit. Do not delete the operator database or shared model budget. Refresh observations and re-investigate after a material service change.

## Verification

```bash
uv run pytest -q
uv run ruff check backend scripts harness demo
npm --prefix frontend test
npm --prefix frontend run build
```

For the actual browser suite, run the operator and services in the documented failing-dependency state, then set `LIARA_TEST_ACCESS_FILE` to the private access file:

```bash
LIARA_TEST_ACCESS_FILE=/tmp/liara-local-access.json npm --prefix frontend run test:e2e
```

An optional genuine model evaluation is:

```bash
PYTHONPATH=backend uv run --env-file .env python scripts/evaluate_diagnosis.py
```

It consumes the persistent shared model budget. [Evaluation](evaluation.md) explains its synthetic-case scope and separate runtime-image evidence.

## Move to actual Liara integration

Use a separate live environment and the exact owner workflow in [deployment.md](deployment.md). Existing services remain read-only until an independently verified repair capability exists. A catalogue of provider APIs, a local fixture or a packaged image is not live acceptance.
