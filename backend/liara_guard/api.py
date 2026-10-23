import asyncio
import contextlib
import json
import os
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from .auth import AuthStore
from .approvals import ApprovalError, Executor, OperationSpec, OperationStore
from .client import LiaraClient, ProviderError
from .contracts import ProbeRunner, ProbeResult
from .investigator import Investigator
from .guidance import remediation_guidance
from .setup_advice import setup_recommendation
from .model_types import ModelError
from .observer import MonitorStore, Observer, encode, invalidate_diagnosis
from .operations_bridge import LiaraOperationProvider, failure_fingerprint, current_repair_candidate
from .runtime import Registry, FixtureProvider, local_config
from .redaction import redact
from .types import Evidence, Record
from .verification import verify_recovery, bind_verification, serving_readiness


class Login(Record):
    password: str = Field(min_length=1, max_length=1024)


class Question(Record):
    question: str = Field(default="Investigate this service.", min_length=1, max_length=1500)


class WatchInput(Record):
    target_ids: list[str] = Field(min_length=1, max_length=2)


class ApprovalInput(Record):
    digest: str = Field(min_length=64, max_length=64)


class SetupRequirements(Record):
    workload: Literal["web", "worker", "static"] = "web"
    ram_gb: float = Field(default=0.5, ge=0.25, le=128)
    cpu_cores: float = Field(default=0.5, ge=0.1, le=64)
    disk_gb: int = Field(default=5, ge=1, le=1024)


class LimitedRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request):
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 16384:
                    raise HTTPException(413, "request_too_large")
            request._body = bytes(body)
            return await original(request)

        return handler


class UnavailableModel:
    def generate(self, *args, **kwargs):
        raise ModelError("runtime_unavailable")


def create_app(
    *,
    state_path=None,
    session_secret=None,
    password_hash=None,
    public_origin=None,
    provider=None,
    registry_config=None,
    model=None,
    mode=None,
    clock=time.time,
    frontend_dist=None,
):
    state_path = Path(state_path or os.environ.get("STATE_DB_PATH", "data/operator.sqlite"))
    origin = (public_origin or os.environ.get("PUBLIC_ORIGIN", "http://127.0.0.1:8661")).rstrip("/")
    parsed = urlsplit(origin)
    if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.path:
        raise ValueError("Exact public origin required")
    if parsed.scheme == "http" and parsed.hostname not in ("127.0.0.1", "localhost"):
        raise ValueError("Nonloopback operator requires HTTPS")
    mode = mode or os.environ.get("LIARA_MODE", "live")
    if mode not in ("live", "fixture"):
        raise ValueError("Explicit live/fixture mode required")
    auth = AuthStore(
        state_path,
        session_secret or os.environ.get("SESSION_SECRET", ""),
        password_hash or os.environ.get("OPERATOR_PASSWORD_HASH", ""),
        clock=clock,
    )
    monitor = MonitorStore(state_path)
    # Restart never silently resumes old observation or model activity.
    with monitor.connect() as db:
        for row in db.execute("SELECT id,data,ends FROM watches WHERE state='active'").fetchall():
            value = json.loads(row["data"])
            value["stop_reason"] = "server_restarted"
            state = "expired" if row["ends"] <= clock() else "stopped"
            db.execute("UPDATE watches SET state=?,data=? WHERE id=?", (state, encode(value), row["id"]))
        for row in db.execute("SELECT id,data FROM incidents").fetchall():
            value = json.loads(row["data"])
            if value.get("investigation_state") in ("queued", "running"):
                value.update(investigation_state="failed", investigation_error="server_restarted")
                db.execute("UPDATE incidents SET data=? WHERE id=?", (encode(value), row["id"]))
    operations = OperationStore(state_path, clock=clock)
    if provider is None:
        if mode == "fixture":
            provider = FixtureProvider(Path("data/local-services"), clock=clock)
        elif os.environ.get("LIARA_API_TOKEN"):
            provider = LiaraClient(
                os.environ["LIARA_API_TOKEN"],
                os.environ["LIARA_TEAM_ID"],
                clock=clock,
                log_version=os.environ.get("LIARA_LOG_VERSION", "v2"),
            )
    if registry_config is None:
        if mode == "fixture":
            registry_config = local_config()
        else:
            config_path = Path(os.environ.get("REGISTRY_PATH", "data/registry.json"))
            registry_config = json.loads(config_path.read_text()) if config_path.is_file() else {}
    team = provider.team_id if provider else os.environ.get("LIARA_TEAM_ID", "unconfigured")
    registry = Registry(team, registry_config, allow_loopback=mode == "fixture")
    if model is None:
        if all(os.environ.get(k) for k in ("CODEX_BINARY_PATH", "CODEX_AUTH_FILE", "CODEX_IMAGE")):
            from .codex_cli import CodexCliClient

            try:
                if not Path(os.environ["CODEX_AUTH_FILE"]).is_file():
                    raise ValueError("Missing local model authentication")
                model = CodexCliClient(
                    binary=Path(os.environ["CODEX_BINARY_PATH"]),
                    auth_file=Path(os.environ["CODEX_AUTH_FILE"]),
                    image=os.environ["CODEX_IMAGE"],
                    gate_dir=Path(f"/tmp/starcoach-codex-{os.getuid()}"),
                    model=os.environ.get("MODEL_ID", "gpt-6.1-sol"),
                )
            except (OSError, ValueError, ModelError, subprocess.SubprocessError):
                model = UnavailableModel()
        else:
            model = UnavailableModel()
    pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="liara-operator")
    model_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="liara-model")
    jobs = {}
    lock = threading.RLock()
    verifying = set()
    last_recovery_inventory = [float("-inf")]
    probes = ProbeRunner(registry.targets, allow_loopback=mode == "fixture", clock=clock)
    observer = Observer(monitor, registry.targets, clock=clock)

    def refresh():
        if provider is None:
            raise HTTPException(503, "provider_not_configured")
        registry.refresh(provider.list_services())

    def resolve(identifier):
        if identifier not in registry.targets:
            refresh()
        return registry.resolve(identifier)

    def evidence_read(target, name):
        try:
            if name == "project":
                return Evidence(
                    id=uuid.uuid4().hex,
                    target=target,
                    kind=name,
                    observed_at=clock(),
                    available_at=clock(),
                    quality="fresh",
                    redacted_payload=provider.get_project(target),
                    coverage={"provider_fixture": mode == "fixture"},
                )
            if name == "logs":
                return provider.get_logs(target, clock() - 300)
            if name == "events":
                return provider.get_events(target, clock() - 300, clock())
            return getattr(provider, "get_" + name)(target)
        except ProviderError as exc:
            return Evidence(
                id=uuid.uuid4().hex,
                target=target,
                kind=name,
                observed_at=clock(),
                available_at=clock(),
                quality="unavailable",
                redacted_payload={"error": exc.code, "http_status": exc.status},
                coverage={"observed_service_health": False, "provider_fixture": mode == "fixture"},
            )

    def probe_evidence(check):
        value = probes.run(check)
        return Evidence(
            id=value.id,
            target=registry.resolve(check.target_id),
            kind="http_probe",
            observed_at=value.observed_at,
            available_at=value.available_at,
            quality="fresh" if value.http_status is not None or value.reason == "timeout" else "unavailable",
            redacted_payload=value.model_dump(),
            coverage={"configured_endpoint": True, "local_fixture_target": mode == "fixture"},
        )

    def readers_for(target):
        reads = {
            name: (lambda name=name: evidence_read(target, name))
            for name in ["project", "applets", "releases", "logs", "metrics", "metrics_history", "events"]
        }
        for check in registry.checks_for(target.app_id):
            reads["http:" + check.id] = lambda check=check: probe_evidence(check)
        for dep in registry.dependencies.get(target.app_id, []):
            for check in registry.checks_for(dep):
                reads["dependency:" + check.id] = lambda check=check: probe_evidence(check)
        return reads

    def initial_reads(target):
        return [
            "project",
            "applets",
            "releases",
            *["http:" + c.id for c in registry.checks_for(target.app_id)],
            "logs",
            "metrics",
            "metrics_history",
        ]

    def provider_snapshot(target):
        if provider is None:
            return []
        return [evidence_read(target, name) for name in ["applets", "releases"]]

    def investigator():
        return Investigator(
            monitor,
            model,
            registry.targets,
            clock=clock,
            dependencies=registry.dependencies,
            repair_capabilities=[i for i in registry.targets if registry.can_repair(i)],
            diagnostic_secrets=(getattr(provider, "token", None), session_secret or os.environ.get("SESSION_SECRET", ""),
                                password_hash or os.environ.get("OPERATOR_PASSWORD_HASH", "")),
        )

    def public_incident(value):
        return {k: v for k, v in value.items() if k != "owner"}

    def public_operation(value):
        return {k: v for k, v in value.items() if k != "owner"}

    def capacity(owner):
        for identifier in [key for key, job in jobs.items() if job["future"].done()]:
            jobs.pop(identifier, None)
        if any(job["owner"] == owner for job in jobs.values()):
            raise HTTPException(409, "investigation_in_progress")
        if len(jobs) >= 3:
            raise HTTPException(429, "investigation_queue_full")

    def start_investigation(owner, incident):
        with lock:
            capacity(owner)
            cancel = threading.Event()
            target = resolve(incident["target"]["app_id"])
            incident.update(investigation_state="queued", diagnosis=None, investigation_error=None,
                            investigation_progress={"stage": "queued", "reads_completed": 0})
            monitor.save_incident(incident, incident["generation"])
            future = model_pool.submit(
                investigator().investigate,
                owner,
                incident["id"],
                readers_for(target),
                initial_reads=initial_reads(target),
                cancel=cancel,
                deadline_utc=clock() + 120,
            )
            jobs[incident["id"]] = {"cancel": cancel, "future": future, "owner": owner}
        return {"id": incident["id"], "state": "queued"}

    def executor(owner):
        if mode != "live" or provider is None:
            raise HTTPException(409, "live_provider_required_for_deployment")
        bridge = LiaraOperationProvider(provider, registry, monitor, probes, owner)
        return Executor(
            operations,
            bridge,
            registry.enrolled,
            clock=clock,
            allowed_new_names=registry.config.get("allowed_new_names", []),
        ), bridge

    def verify_operation(value, bridge):
        try:
            spec = OperationSpec.model_validate(value["spec"])
            incident = monitor.incident(value["owner"], spec.incident_id)
            policy = registry.policies[incident["target"]["app_id"]]
            result = bind_verification(
                value, incident, policy, {"state": "pending", "reason": "not_started", "probe_ids": []}
            )
            if result["state"] != "inconclusive":
                value = operations.transition_verification(value, state="verifying")
                result = verify_recovery(
                    policy,
                    value["release_id"],
                    bridge.status_for_policy,
                    probes.run,
                    clock=clock,
                    current_policy_hash=lambda: registry.policies[incident["target"]["app_id"]].digest(),
                    deadline_utc=value["reconcile_until"],
                )
            operations.finish_verification(value, result, publish_incident=True,
                policy_hash=registry.policies[incident["target"]["app_id"]].digest())
        except ApprovalError:
            # A stale worker cannot publish to either record or finalize the newer attempt.
            pass
        except Exception:
            try:
                operations.finish_verification(value, {"state": "inconclusive", "reason": "verification_unavailable", "probe_ids": []},
                    publish_incident=True,
                    policy_hash=registry.policies[incident["target"]["app_id"]].digest() if "incident" in locals() else None)
            except ApprovalError:
                pass
        finally:
            with lock:
                verifying.discard(value["id"])

    def tick_all():
        with monitor.connect() as db:
            watches = [r[0] for r in db.execute("SELECT id FROM watches WHERE state='active'")]
        for identifier in watches:
            try:
                observer.tick(identifier, probes.run, provider=provider_snapshot)
            except Exception:
                with monitor.connect() as db:
                    db.execute("UPDATE watches SET state='observer_unavailable' WHERE id=?", (identifier,))
        if mode == "live":
            with operations.connect() as db:
                pending = [
                    json.loads(r[0])
                    for r in db.execute(
                        "SELECT data FROM operations WHERE state IN ('pending','unknown','ready','awaiting_serving')"
                    )
                ]
            recoverable = []
            for value in pending:
                if value["spec"]["kind"] != "redeploy_known_good":
                    continue
                if value.get("reconcile_until") is None or clock() > value["reconcile_until"]:
                    if value["state"] == "awaiting_serving":
                        try:
                            operations.finish_verification(value, {"state": "inconclusive", "reason": "reconciliation_expired", "probe_ids": []})
                        except ApprovalError:
                            pass
                        continue
                    if value.get("error") != "reconciliation_expired":
                        operations.update(value, state="unknown", error="reconciliation_expired")
                    continue
                recoverable.append(value)
            pending = recoverable
            if pending and clock() - last_recovery_inventory[0] >= 10:
                last_recovery_inventory[0] = clock()
                try:
                    refresh()
                except (HTTPException, ProviderError, ValueError):
                    return  # Observation gap; retry within existing operation deadlines, no writes.
            if any(value["spec"].get("app_id") not in registry.targets for value in pending):
                return  # Never fail verification just because inventory recovery is still unavailable.
            for value in pending:
                try:
                    if value["spec"]["kind"] != "redeploy_known_good":
                        continue
                    ex, bridge = executor(value["owner"])
                    updated = ex.reconcile(value["owner"], value["id"])
                    if updated["state"] in ("ready", "awaiting_serving"):
                        with lock:
                            if updated["id"] in verifying:
                                continue
                            if clock()-updated.get("last_serving_checked", float("-inf")) < 10:
                                continue
                            incident = monitor.incident(updated["owner"], updated["spec"]["incident_id"])
                            policy = registry.policies[incident["target"]["app_id"]]
                            binding = bind_verification(updated, incident, policy, {"state": "pending"})
                            if updated.get("recovery_rechecks_used") and incident["generation"] != updated.get("recovery_recheck_generation"):
                                binding = {"state": "inconclusive"}
                            if binding["state"] == "inconclusive":
                                operations.finish_verification(updated, {"state": "inconclusive", "reason": "operation_binding_changed", "probe_ids": []})
                                continue
                            updated = operations.transition_verification(updated, state="awaiting_serving", last_serving_checked=clock())
                        readiness = serving_readiness(policy, updated["release_id"], bridge.status_for_policy,
                                                      clock=clock, deadline=updated["reconcile_until"])
                        latest_incident = monitor.incident(updated["owner"], updated["spec"]["incident_id"])
                        if (policy.digest() != updated["spec"]["verification_policy_hash"]
                                or latest_incident.get("repair_operation_id") != updated["id"]
                                or (updated.get("recovery_rechecks_used") and latest_incident["generation"] != updated.get("recovery_recheck_generation"))):
                            readiness = {"state": "expired", "reason": "operation_binding_changed"}
                        updated = operations.transition_verification(updated, serving_readiness=readiness)
                        if readiness["state"] == "expired":
                            operations.finish_verification(updated, {"state": "inconclusive", "reason": readiness["reason"], "probe_ids": []})
                        elif readiness["state"] == "ready":
                            with lock:
                                if updated["id"] in verifying:
                                    continue
                                verifying.add(updated["id"])
                                updated = operations.transition_verification(updated, state="verifying", verification_attempt_id=updated.get("verification_attempt_id") or uuid.uuid4().hex)
                                pool.submit(verify_operation, updated, bridge)
                except ApprovalError:
                    continue  # A stale readiness observation cannot replace a newer attempt.

    @asynccontextmanager
    async def lifespan(app):
        stop = asyncio.Event()

        async def watch_loop():
            while not stop.is_set():
                await asyncio.to_thread(tick_all)
                try:
                    await asyncio.wait_for(stop.wait(), 1)
                except asyncio.TimeoutError:
                    pass

        task = asyncio.create_task(watch_loop())
        yield
        stop.set()
        for job in list(jobs.values()):
            job["cancel"].set()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        pool.shutdown(wait=False, cancel_futures=True)
        model_pool.shutdown(wait=False, cancel_futures=True)
        if provider is not None:
            provider.close()

    app = FastAPI(lifespan=lifespan)
    app.router.route_class = LimitedRoute
    app.state.monitor = monitor
    app.state.operations = operations
    app.state.registry = registry
    app.state.tick = tick_all
    app.state.observer = observer
    app.state.jobs = jobs
    app.state.pool = pool

    @app.middleware("http")
    async def boundaries(request, call_next):
        if (
            request.url.path.startswith("/api/")
            and request.method in ("POST", "PATCH", "DELETE")
            and request.headers.get("origin") != origin
        ):
            return JSONResponse({"detail": "origin_not_allowed"}, status_code=403)
        response = await call_next(request)
        if request.url.path.startswith("/api/"):
            response.headers["cache-control"] = "no-store"
        response.headers["x-content-type-options"] = "nosniff"
        response.headers["referrer-policy"] = "no-referrer"
        return response

    @app.exception_handler(ProviderError)
    async def provider_error(request, exc):
        return JSONResponse({"detail": exc.code}, status_code=503)

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        return JSONResponse({"detail": "not_found"}, status_code=404)

    @app.exception_handler(ApprovalError)
    async def approval_error(request, exc):
        return JSONResponse({"detail": "approval_rejected"}, status_code=409)

    def owner(request: Request):
        try:
            return auth.resolve(request.cookies.get("liara_owner"))
        except ValueError:
            raise HTTPException(401, "unauthenticated")

    Owner = Annotated[str, Depends(owner)]

    @app.get("/healthz")
    def health():
        return {"status": "ok"}

    @app.post("/api/login")
    def login(body: Login, request: Request, response: Response):
        try:
            cookie, _ = auth.login(body.password, request.client.host if request.client else "unknown")
        except ValueError as exc:
            raise HTTPException(429 if str(exc) == "rate_limited" else 401, str(exc))
        response.set_cookie(
            "liara_owner",
            cookie,
            httponly=True,
            samesite="strict",
            secure=parsed.scheme == "https",
            max_age=86400,
        )
        return {"authenticated": True}

    @app.post("/api/logout")
    def logout(request: Request, response: Response, _: Owner):
        auth.logout(request.cookies.get("liara_owner"))
        response.delete_cookie("liara_owner")
        return {"authenticated": False}

    @app.get("/api/services")
    def services(_: Owner):
        refresh()
        return {
            "mode": mode,
            "team_id": team,
            "model_available": not isinstance(model, UnavailableModel),
            "services": [
                {
                    **s.model_dump(),
                    "checks": [c.model_dump() for c in registry.checks_for(i)],
                    "can_repair": registry.can_repair(i),
                }
                for i, s in registry.services.items()
            ],
        }

    @app.post("/api/setup/recommendation")
    def recommend_setup(body: SetupRequirements, _: Owner):
        return setup_recommendation(provider, body.model_dump(), checked_at=clock(), mode=mode)

    @app.get("/api/services/{identifier}")
    def detail(identifier: str, owner: Owner):
        target = resolve(identifier)
        evidence = []
        for name in ["project", "applets", "releases", "metrics", "metrics_history"]:
            try:
                item = evidence_read(target, name)
                evidence.append(item.model_dump())
                if name == "releases" and item.quality == "fresh":
                    current = item.redacted_payload.get("currentRelease")
                    if isinstance(current, str):
                        observer.set_release(owner, identifier, current)
            except ProviderError as exc:
                evidence.append(
                    {
                        "id": uuid.uuid4().hex,
                        "kind": name,
                        "quality": "unavailable",
                        "observed_at": clock(),
                        "available_at": clock(),
                        "redacted_payload": {"error": exc.code},
                    }
                )
        for check in registry.checks_for(identifier):
            evidence.append(probe_evidence(check).model_dump())
        return {
            "service": registry.services[identifier].model_dump(),
            "mode": mode,
            "evidence": evidence,
            "can_repair": registry.can_repair(identifier),
        }

    @app.post("/api/services/{identifier}/investigate", status_code=202)
    def investigate_service(identifier: str, body: Question, owner: Owner):
        target = resolve(identifier)
        with lock:
            capacity(owner)
            incident = observer.begin_investigation(owner, target, body.question)
            return start_investigation(owner, incident)

    @app.get("/api/incidents/{identifier}")
    def incident(identifier: str, owner: Owner):
        value = monitor.incident(owner, identifier)
        evidence = monitor.evidence(owner, identifier, cutoff=clock())
        can_repair = registry.can_repair(value["target"]["app_id"])
        return {
            "incident": public_incident(value),
            "evidence": evidence,
            "can_repair": can_repair,
            "guidance": remediation_guidance(value, evidence, can_repair=can_repair),
        }

    @app.post("/api/incidents/{identifier}/investigate", status_code=202)
    def reinvestigate(identifier: str, owner: Owner, body: Question = Question()):
        with lock:
            capacity(owner)
            with monitor.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                row = db.execute(
                    "SELECT data FROM incidents WHERE id=? AND owner=?", (identifier, owner)
                ).fetchone()
                if not row:
                    raise KeyError("incident_not_found")
                value = json.loads(row[0])
                if value["state"] != "open":
                    raise HTTPException(409, "incident_not_open")
                # Explicit reconsideration supersedes prior unexecuted decisions.
                value["generation"] += 1
                value["question"] = redact(body.question)
                db.execute("UPDATE incidents SET data=? WHERE id=?", (encode(value), identifier))
            return start_investigation(owner, value)

    @app.get("/api/incidents/{identifier}/rejected-drafts")
    def rejected_drafts(identifier: str, owner: Owner):
        return {"rejected_not_a_diagnosis": True, "diagnostics": monitor.rejected_drafts(owner, identifier)}

    @app.post("/api/incidents/{identifier}/cancel")
    def cancel_investigation(identifier: str, owner: Owner):
        monitor.incident(owner, identifier)
        with lock:
            if identifier in jobs:
                job = jobs[identifier]
                job["cancel"].set()
                if job["future"].cancel():
                    value = monitor.incident(owner, identifier)
                    value.update(investigation_state="canceled", investigation_error="canceled")
                    monitor.save_incident(value, value["generation"])
                    return {"state": "canceled"}
        return {"state": "cancel_requested"}

    @app.post("/api/watches", status_code=201)
    def watch(body: WatchInput, owner: Owner):
        for identifier in body.target_ids:
            resolve(identifier)
        checks = [c for identifier in body.target_ids for c in registry.checks_for(identifier)]
        try:
            value = observer.start_watch(owner, body.target_ids, checks)
        except ValueError:
            raise HTTPException(409, "watch_scope_or_state_conflict")
        return {k: v for k, v in value.items() if k != "owner"}

    @app.post("/api/watches/{identifier}/stop")
    def stop_watch(identifier: str, owner: Owner):
        observer.stop_watch(owner, identifier)
        return {"state": "stopped"}

    @app.get("/api/state")
    def state(owner: Owner):
        with monitor.connect() as db:
            rows = db.execute(
                "SELECT id FROM watches WHERE owner=? ORDER BY rowid DESC LIMIT 10", (owner,)
            ).fetchall()
        watches = [{k: v for k, v in monitor.watch(owner, r[0]).items() if k != "owner"} for r in rows]
        with operations.connect() as db:
            ops = [
                public_operation(json.loads(r[0]))
                for r in db.execute(
                    "SELECT data FROM operations WHERE owner=? ORDER BY rowid DESC LIMIT 20", (owner,)
                )
            ]
        return {
            "watches": watches,
            "incidents": [public_incident(v) for v in monitor.incidents(owner)],
            "operations": ops,
            "now": clock(),
        }

    @app.post("/api/incidents/{identifier}/proposal", status_code=201)
    def propose(identifier: str, owner: Owner):
        incident = monitor.incident(owner, identifier)
        root = incident["target"]["app_id"]
        if not registry.can_repair(root) or mode != "live" or not current_repair_candidate(incident):
            raise HTTPException(409, "repair_not_enrolled_or_supported")
        policy = registry.policies[root]
        actor = registry.resolve(policy.changed_target_id)
        entry = registry.enrolled[actor.app_id]
        artifact = next(iter(entry["known_good"]))
        symptom = probes.run(policy.checks[0])
        if symptom.check_pass is not False:
            raise HTTPException(409, "original_failure_not_current")
        fingerprint = failure_fingerprint(policy.checks[0], symptom)
        # Bind a manual diagnosis to its frozen observed symptom, rather than promote an old cause.
        recorded = [
            e
            for e in monitor.evidence(owner, identifier, cutoff=incident["diagnosis"]["cutoff"])
            if e["kind"] == "http_probe"
            and e["target"]["app_id"] == root
            and e["redacted_payload"].get("check_id") == policy.checks[0].id
        ]
        diagnosed_fingerprint = incident.get("failure_fingerprint")
        if diagnosed_fingerprint is None and recorded:
            diagnosed_fingerprint = failure_fingerprint(
                policy.checks[0], ProbeResult.model_validate(recorded[-1]["redacted_payload"])
            )
        stale = diagnosed_fingerprint != fingerprint
        with monitor.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT data FROM incidents WHERE id=? AND owner=?", (identifier, owner)
            ).fetchone()
            latest = json.loads(row[0])
            if latest["generation"] != incident["generation"] or not current_repair_candidate(latest):
                raise HTTPException(409, "diagnosis_changed_reinvestigate")
            incident = latest
            if stale:
                incident["generation"] += 1
                invalidate_diagnosis(incident)
            incident["failure_fingerprint"] = fingerprint
            db.execute("UPDATE incidents SET data=? WHERE id=?", (encode(incident), identifier))
        if stale:
            raise HTTPException(409, "failure_changed_reinvestigate")
        releases = provider.get_releases(actor)
        if releases.quality != "fresh" or not releases.redacted_payload.get("currentRelease"):
            raise HTTPException(409, "current_release_unavailable")
        spec = OperationSpec(
            kind="redeploy_known_good",
            team_id=actor.team_id,
            app_name=actor.app_name,
            app_id=actor.app_id,
            artifact_sha256=artifact,
            before_release_id=releases.redacted_payload["currentRelease"],
            incident_id=identifier,
            incident_generation=incident["generation"],
            failure_fingerprint=fingerprint,
            verification_policy_hash=policy.digest(),
        )
        return public_operation(operations.propose(owner, spec))

    @app.post("/api/operations/{identifier}/approve")
    def approve(identifier: str, body: ApprovalInput, owner: Owner):
        return public_operation(operations.approve(owner, identifier, body.digest))

    @app.post("/api/operations/{identifier}/execute")
    def execute(identifier: str, owner: Owner):
        ex, _bridge = executor(owner)
        value = ex.execute(owner, identifier)
        if value["state"] in ("pending", "unknown") and value["spec"]["incident_id"]:
            incident = monitor.incident(owner, value["spec"]["incident_id"])
            incident["repair_pending"] = True
            incident["repair_operation_id"] = value["id"]
            monitor.save_incident(incident, incident["generation"])
        return public_operation(value)

    @app.get("/api/operations/{identifier}")
    def operation(identifier: str, owner: Owner):
        return public_operation(operations.get(owner, identifier))

    @app.post("/api/operations/{identifier}/recheck-recovery", status_code=202)
    def recheck_recovery(identifier: str, owner: Owner):
        if mode != "live" or provider is None:
            raise HTTPException(409, "live_provider_required_for_deployment")
        value = operations.get(owner, identifier)
        incident = monitor.incident(owner, value["spec"]["incident_id"])
        policy = registry.policies.get(incident["target"]["app_id"])
        if (policy is None or incident["state"] != "open" or incident.get("repair_operation_id") != identifier
                or policy.changed_target_id != value["spec"]["app_id"]):
            raise HTTPException(409, "recovery_recheck_unavailable")
        target = resolve(value["spec"]["app_id"])
        if target.team_id != value["spec"]["team_id"] or target.app_name != value["spec"]["app_name"]:
            raise HTTPException(409, "recovery_recheck_unavailable")
        return public_operation(operations.claim_recovery_recheck(owner, identifier,
            incident_generation=incident["generation"], policy_hash=policy.digest()))

    root = Path(__file__).resolve().parents[2]
    dist = Path(frontend_dist) if frontend_dist else root / "frontend/dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app
