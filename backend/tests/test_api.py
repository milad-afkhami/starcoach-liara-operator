import pytest
import threading
import time
from fastapi.testclient import TestClient
from liara_guard.api import create_app
from liara_guard.auth import hash_password
from liara_guard.runtime import FixtureProvider, local_config
from liara_guard.model_types import ModelResult

ORIGIN = "http://127.0.0.1:8661"
PASSWORD = "test-owner-password-long"


class Model:
    def generate(self, request, schema, cancel):
        ids = request.evidence_ids
        return ModelResult(
            request_id=request.id,
            provider="codex_cli",
            model="test",
            cli_version="test",
            elapsed_ms=1,
            value={
                "action": "conclude",
                "outcome": "unresolved",
                "cause_family": "unknown",
                "summary": "Evidence does not establish the cause.",
                "evidence_ids": ids[:1],
                "contradiction_ids": [],
                "unknowns": ["Provider fixture"],
                "next_check": None,
            },
        )


def app(tmp_path, **kw):
    return create_app(
        state_path=tmp_path / "state.sqlite",
        session_secret="s" * 32,
        password_hash=hash_password(PASSWORD),
        public_origin=ORIGIN,
        provider=FixtureProvider(tmp_path / "demo"),
        registry_config=local_config(),
        model=kw.pop("model", Model()),
        mode="fixture",
        **kw,
    )


def login(application):
    c = TestClient(application)
    c.headers["origin"] = ORIGIN
    assert c.post("/api/login", json={"password": PASSWORD}).status_code == 200
    return c


def test_auth_origin_validation_and_private_endpoints(tmp_path):
    a = app(tmp_path)
    c = TestClient(a)
    assert c.get("/healthz").status_code == 200
    assert c.get("/api/services").status_code == 401
    assert c.post("/api/login", json={"password": PASSWORD}).status_code == 403
    c.headers["origin"] = ORIGIN
    assert c.post("/api/login", json={"password": "wrong"}).status_code == 401
    response = c.post("/api/login", json={"password": PASSWORD})
    assert response.status_code == 200
    assert (
        "HttpOnly" in response.headers["set-cookie"] and "SameSite=strict" in response.headers["set-cookie"]
    )
    assert c.post("/api/watches", json={"target_ids": ["missing"]}).status_code == 404
    assert c.post("/api/watches", json={"target_ids": []}).status_code == 422
    assert c.get("/api/services/missing").status_code == 404
    assert c.post("/api/logout").status_code == 200
    assert c.get("/api/services").status_code == 401


def test_inventory_is_explicit_fixture_and_does_not_start_watch(tmp_path):
    c = login(app(tmp_path))
    value = c.get("/api/services").json()
    assert value["mode"] == "fixture" and len(value["services"]) == 2
    assert value["services"][0]["can_repair"] is False
    assert c.get("/api/state").json()["watches"] == []


def test_manual_investigation_is_async_without_baseline_and_owner_scoped(tmp_path):
    application = app(tmp_path)
    a = login(application)
    b = login(application)
    response = a.post("/api/services/local-store/investigate", json={"question": "What can be established?"})
    assert response.status_code == 202
    identifier = response.json()["id"]
    assert b.get("/api/incidents/" + identifier).status_code == 404
    for _ in range(60):
        value = a.get("/api/incidents/" + identifier).json()
        if value["incident"]["investigation_state"] in ("done", "failed"):
            break
        time.sleep(0.05)
    assert value["incident"]["watch_id"] is None
    assert value["incident"]["diagnosis"]["outcome"] == "unresolved"
    assert "owner" not in value["incident"]
    assert a.post(f"/api/incidents/{identifier}/proposal").status_code == 409


def test_watch_scope_stop_and_other_session_denial(tmp_path):
    application = app(tmp_path)
    a = login(application)
    b = login(application)
    w = a.post("/api/watches", json={"target_ids": ["local-store"]})
    assert w.status_code == 201
    identifier = w.json()["id"]
    assert b.post("/api/watches/" + identifier + "/stop").status_code == 404
    assert a.post("/api/watches/" + identifier + "/stop").status_code == 200
    assert a.get("/api/state").json()["watches"][0]["state"] == "stopped"


def test_oversized_input_and_browser_secret_exposure_refused(tmp_path):
    c = login(app(tmp_path))
    assert (
        c.post(
            "/api/services/local-store/investigate",
            content=b"x" * 16385,
            headers={"content-type": "application/json"},
        ).status_code
        == 413
    )
    for url in ["/.env", "/data/state.sqlite", "/backend/liara_guard/api.py"]:
        assert c.get(url).status_code == 404
    text = c.get("/api/services").text
    assert "SESSION_SECRET" not in text and PASSWORD not in text


def test_actual_running_model_can_be_canceled_by_owner_only(tmp_path):
    entered = threading.Event()

    class Slow:
        def generate(self, request, schema, cancel):
            from liara_guard.model_types import ModelError

            entered.set()
            cancel.wait(3)
            raise ModelError("canceled")

    application = app(tmp_path, model=Slow())
    a = login(application)
    b = login(application)
    identifier = a.post("/api/services/local-store/investigate", json={"question": "Investigate"}).json()[
        "id"
    ]
    assert entered.wait(2)
    assert b.post(f"/api/incidents/{identifier}/cancel").status_code == 404
    assert a.post(f"/api/incidents/{identifier}/cancel").status_code == 200


def test_model_admission_is_one_per_owner_and_three_total(tmp_path):
    release = threading.Event()

    class Slow:
        def generate(self, request, schema, cancel):
            from liara_guard.model_types import ModelError

            release.wait(3)
            raise ModelError("canceled")

    application = app(tmp_path, model=Slow())
    clients = [login(application) for _ in range(4)]
    try:
        assert (
            clients[0].post("/api/services/local-store/investigate", json={"question": "First"}).status_code
            == 202
        )
        assert (
            clients[0]
            .post("/api/services/local-store/investigate", json={"question": "Duplicate"})
            .status_code
            == 409
        )
        for client in clients[1:3]:
            assert (
                client.post("/api/services/local-store/investigate", json={"question": "Queued"}).status_code
                == 202
            )
        assert (
            clients[3]
            .post("/api/services/local-store/investigate", json={"question": "Overflow"})
            .status_code
            == 429
        )
        assert len(clients[0].get("/api/state").json()["incidents"]) == 1
    finally:
        release.set()


def test_cancel_queued_job_is_immediate_and_restart_does_not_resume_watch(tmp_path):
    release = threading.Event()
    entered = threading.Event()

    class Slow:
        def generate(self, request, schema, cancel):
            from liara_guard.model_types import ModelError

            entered.set()
            release.wait(3)
            raise ModelError("canceled")

    application = app(tmp_path, model=Slow())
    a = login(application)
    b = login(application)
    try:
        a.post("/api/services/local-store/investigate", json={"question": "Running"})
        assert entered.wait(2)
        queued = b.post("/api/services/local-store/investigate", json={"question": "Queued"}).json()["id"]
        b.post("/api/incidents/" + queued + "/cancel")
        assert b.get("/api/incidents/" + queued).json()["incident"]["investigation_state"] == "canceled"
    finally:
        release.set()
    watch = a.post("/api/watches", json={"target_ids": ["local-store"]}).json()["id"]
    restarted = app(tmp_path)
    c = TestClient(restarted)
    c.cookies.update(a.cookies)
    c.headers["origin"] = ORIGIN
    assert next(w for w in c.get("/api/state").json()["watches"] if w["id"] == watch)["state"] == "stopped"


def test_material_release_refresh_invalidates_running_decision(tmp_path):
    import json

    release = threading.Event()
    entered = threading.Event()

    class Slow(Model):
        def generate(self, request, schema, cancel):
            entered.set()
            release.wait(3)
            return super().generate(request, schema, cancel)

    directory = tmp_path / "demo"
    directory.mkdir()
    metadata = directory / "releases.json"
    metadata.write_text(json.dumps({"local-store": {"release_id": "r1", "build_id": "b1", "at": 100}}))
    application = app(tmp_path, model=Slow())
    c = login(application)
    c.get("/api/services/local-store")
    try:
        identifier = c.post(
            "/api/services/local-store/investigate", json={"question": "Check current service"}
        ).json()["id"]
        assert entered.wait(2)
        metadata.write_text(json.dumps({"local-store": {"release_id": "r2", "build_id": "b2", "at": 101}}))
        c.get("/api/services/local-store")
        release.set()
        for _ in range(40):
            result = c.get("/api/incidents/" + identifier).json()["incident"]
            if result["investigation_state"] not in ("queued", "running"):
                break
            time.sleep(0.05)
        assert result["diagnosis"] is None
        assert (
            result["investigation_state"] == "failed" and result["investigation_error"] == "stale_generation"
        )
    finally:
        release.set()


def test_missing_local_model_does_not_disable_readonly_monitoring(tmp_path, monkeypatch):
    monkeypatch.setenv("CODEX_BINARY_PATH", "/no/such/codex")
    monkeypatch.setenv("CODEX_AUTH_FILE", "/no/such/auth")
    monkeypatch.setenv("CODEX_IMAGE", "test")
    c = login(app(tmp_path, model=None))
    assert c.get("/api/services").json()["model_available"] is False


def test_existing_watch_incident_investigation_preserves_record_and_question(tmp_path):
    application = app(tmp_path)
    c = login(application)
    c.get("/api/services")
    owner = c.cookies.get("liara_owner").split(".")[0]
    target = application.state.registry.resolve("local-store")
    incident = application.state.monitor.ensure_incident(
        owner,
        target,
        "http_availability",
        "watch-scope",
        time.time(),
        watch_id="watch-1",
        fingerprint="same-failure",
    )
    response = c.post(
        "/api/incidents/" + incident["id"] + "/investigate",
        json={"question": "Explain this specific endpoint alert."},
    )
    assert response.status_code == 202 and response.json()["id"] == incident["id"]
    value = c.get("/api/incidents/" + incident["id"]).json()["incident"]
    assert value["question"] == "Explain this specific endpoint alert." and value["watch_id"] == "watch-1"
    assert len(c.get("/api/state").json()["incidents"]) == 1


def test_restart_reconciles_submitted_deployment_without_browser_inventory_load(tmp_path):
    from liara_guard.approvals import OperationSpec
    from liara_guard.types import Evidence

    class Pending(FixtureProvider):
        def __init__(self):
            super().__init__(tmp_path / "demo", clock=lambda: 100)
            self.status_reads = 0

        def get_releases(self, target):
            self.status_reads += 1
            return Evidence(
                id="r",
                target=target,
                kind="releases",
                observed_at=100,
                available_at=100,
                quality="fresh",
                redacted_payload={
                    "currentRelease": "r2",
                    "releases": [{"_id": "r2", "state": "BUILDING", "sourceID": "s1"}],
                },
            )

    provider = Pending()
    application = create_app(
        state_path=tmp_path / "restart.sqlite",
        session_secret="s" * 32,
        password_hash=hash_password(PASSWORD),
        public_origin=ORIGIN,
        provider=provider,
        registry_config={},
        model=Model(),
        mode="live",
        clock=lambda: 100,
    )
    store = application.state.operations
    op = store.propose(
        "owner",
        OperationSpec(
            kind="redeploy_known_good",
            team_id="local-fixture",
            app_name="delivery",
            app_id="local-dep",
            artifact_sha256="a" * 64,
            before_release_id="r1",
            incident_id="i",
            incident_generation=1,
            failure_fingerprint="f",
            verification_policy_hash="p",
        ),
    )
    store.update(op, state="pending", release_id="r2", source_id="s1", submitted_at=90, reconcile_until=690)
    assert application.state.registry.targets == {}
    application.state.tick()
    assert provider.status_reads == 1 and "local-dep" in application.state.registry.targets


@pytest.mark.parametrize("case", ["current", "stale", "probe_race", "symptom_change"])
def test_proposal_cannot_promote_historical_diagnosis_to_new_state(tmp_path, monkeypatch, case):
    from liara_guard.contracts import ProbeRunner, ProbeResult
    from liara_guard.types import Evidence
    from liara_guard.verification import VerificationPolicy
    from liara_guard.observer import encode

    check = {
        "id": "preview",
        "target_id": "local-store",
        "origin": "https://store.liara.run",
        "path": "/preview",
        "require_request_echo": True,
    }
    policy = VerificationPolicy(
        id="p",
        checks=[check],
        changed_target_id="local-dep",
        expected_release_ids={"local-dep": "$submitted"},
        expected_build_fields={"preview": {"build_id": "store"}},
    )
    cfg = {
        "http_checks": [check],
        "repair_targets": {"local-store": "local-dep"},
        "verification_policies": {"local-store": policy.model_dump()},
        "enrolled": {
            "local-dep": {
                "team_id": "local-fixture",
                "app_name": "delivery",
                "baseline_verified": True,
                "known_good": {"a" * 64: str(tmp_path / "good")},
            }
        },
    }

    class Provider(FixtureProvider):
        def get_releases(self, target):
            return self._evidence(target, "releases", {"currentRelease": "r1", "releases": []})

    application = create_app(
        state_path=tmp_path / "proposal.sqlite",
        session_secret="s" * 32,
        password_hash=hash_password(PASSWORD),
        public_origin=ORIGIN,
        provider=Provider(tmp_path / "demo", clock=lambda: 100),
        registry_config=cfg,
        model=Model(),
        mode="live",
        clock=lambda: 100,
    )
    c = login(application)
    c.get("/api/services")
    owner = c.cookies.get("liara_owner").split(".")[0]
    target = application.state.registry.resolve("local-store")
    store = application.state.monitor
    incident = store.ensure_incident(owner, target, "log_investigation", "manual", 100)
    incident.update(
        diagnosis={"generation": 1, "outcome": "repair_candidate", "cutoff": 100}, investigation_state="done"
    )
    store.save_incident(incident, 1)
    old = ProbeResult(
        id="observed",
        target_id="local-store",
        check_id="preview",
        request_id="original",
        observed_at=100,
        available_at=100,
        http_status=502,
        elapsed_ms=1,
        check_pass=False,
        reason="unexpected_status",
        body_digest="digest",
        payload={"reason": "upstream_invalid"},
    )
    store.add_evidence(
        owner,
        incident["id"],
        Evidence(
            id="observed",
            target=target,
            kind="http_probe",
            observed_at=100,
            available_at=100,
            quality="fresh",
            redacted_payload=old.model_dump(),
        ),
    )

    def change_generation():
        with store.connect() as db:
            current = store.incident(owner, incident["id"])
            current["generation"] += 1
            db.execute("UPDATE incidents SET data=? WHERE id=?", (encode(current), incident["id"]))

    if case == "stale":
        change_generation()

    def probe(self, c):
        if case == "probe_race":
            change_generation()
        return (
            old.model_copy(
                update={"id": "new", "request_id": "new", "http_status": 504, "payload": {"reason": "new"}}
            )
            if case == "symptom_change"
            else old
        )

    monkeypatch.setattr(ProbeRunner, "run", probe)
    response = c.post("/api/incidents/" + incident["id"] + "/proposal")
    assert response.status_code == (201 if case == "current" else 409)
    with application.state.operations.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM operations").fetchone()[0] == (1 if case == "current" else 0)
    if case == "symptom_change":
        assert store.incident(owner, incident["id"])["diagnosis"] is None


def test_unavailable_recovery_inventory_cannot_fail_verification_or_extend_deadline(tmp_path):
    from liara_guard.approvals import OperationSpec
    from liara_guard.client import ProviderError

    now = [100.0]

    class Unavailable(FixtureProvider):
        def list_services(self):
            raise ProviderError("observer_auth", 401)

    application = create_app(
        state_path=tmp_path / "no-inventory.sqlite",
        session_secret="s" * 32,
        password_hash=hash_password(PASSWORD),
        public_origin=ORIGIN,
        provider=Unavailable(tmp_path / "demo"),
        registry_config={},
        model=Model(),
        mode="live",
        clock=lambda: now[0],
    )
    store = application.state.operations
    op = store.propose(
        "owner",
        OperationSpec(
            kind="redeploy_known_good",
            team_id="local-fixture",
            app_name="delivery",
            app_id="local-dep",
            artifact_sha256="a" * 64,
            before_release_id="r1",
            incident_id="i",
            incident_generation=1,
            failure_fingerprint="f",
            verification_policy_hash="p",
        ),
    )
    store.update(op, state="ready", release_id="r2", source_id="s1", submitted_at=90, reconcile_until=690)
    application.state.tick()
    now[0] += 1
    application.state.tick()
    assert store.get("owner", op["id"])["state"] == "ready"
    now[0] = 691
    application.state.tick()
    result = store.get("owner", op["id"])
    assert result["state"] == "unknown" and result["error"] == "reconciliation_expired"
