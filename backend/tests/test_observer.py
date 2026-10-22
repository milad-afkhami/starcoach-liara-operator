import pytest
from liara_guard.observer import MonitorStore, Observer
from liara_guard.contracts import RegisteredHttpCheck, ProbeResult
from liara_guard.types import Target, Evidence

TARGET = Target(team_id="team", app_name="shop", app_id="app", origin="https://shop.liara.run")
CHECK = RegisteredHttpCheck(id="preview", target_id="app", origin=TARGET.origin, path="/preview")


def setup(tmp_path):
    now = [100.0]
    store = MonitorStore(tmp_path / "state.sqlite")
    observer = Observer(store, {"app": TARGET}, clock=lambda: now[0])
    return store, observer, now


def result(now, status=502, reason="unexpected_status"):
    return ProbeResult(
        id=f"p{now}",
        target_id="app",
        check_id="preview",
        request_id=f"r{now}",
        observed_at=now,
        available_at=now,
        http_status=status,
        elapsed_ms=12,
        check_pass=status == 200,
        reason=reason,
        body_digest="abc",
        payload={"reason": "upstream_invalid"} if status != 200 else {},
    )


def test_two_failures_open_without_prior_healthy_baseline_and_repeated_polls_keep_generation(tmp_path):
    s, o, now = setup(tmp_path)
    w = o.start_watch("owner", ["app"], [CHECK])
    o.tick(w["id"], lambda c: result(now[0]))
    assert s.incidents("owner") == []
    now[0] = 115
    o.tick(w["id"], lambda c: result(now[0]))
    incident = s.incidents("owner")[0]
    assert incident["kind"] == "http_availability" and incident["generation"] == 1
    now[0] = 130
    o.tick(w["id"], lambda c: result(now[0]))
    current = s.incidents("owner")[0]
    assert (
        current["id"] == incident["id"]
        and current["generation"] == 1
        and current["observation_sequence"] == 2
    )


def test_stop_expiry_and_restart_never_resume_calls(tmp_path):
    s, o, now = setup(tmp_path)
    calls = []
    w = o.start_watch("owner", ["app"], [CHECK])
    o.stop_watch("owner", w["id"])
    o.tick(w["id"], lambda c: calls.append("call"))
    assert calls == []
    w = o.start_watch("owner", ["app"], [CHECK])
    now[0] = 1001
    o.tick(w["id"], lambda c: calls.append("call"))
    assert calls == []
    restarted = Observer(MonitorStore(tmp_path / "state.sqlite"), {"app": TARGET}, clock=lambda: now[0])
    restarted.tick(w["id"], lambda c: calls.append("call"))
    assert calls == []
    assert s.watch("owner", w["id"])["state"] == "expired"


def test_owner_limits_and_unknown_check_refused(tmp_path):
    s, o, now = setup(tmp_path)
    with pytest.raises(ValueError):
        o.start_watch("owner", ["app", "other", "third"], [])
    with pytest.raises(ValueError):
        o.start_watch("owner", ["missing"], [])
    with pytest.raises(ValueError):
        o.start_watch("owner", ["app"], [CHECK.model_copy(update={"origin": "https://evil.example"})])
    w = o.start_watch("owner", ["app"], [])
    with pytest.raises(KeyError):
        o.stop_watch("other", w["id"])
    assert o.tick(w["id"], lambda c: (_ for _ in ()).throw(AssertionError("worker has no endpoint"))) == []


def test_observer_failure_separate_from_http_health_and_zero_app_change(tmp_path):
    s, o, now = setup(tmp_path)
    w = o.start_watch("owner", ["app"], [CHECK])
    evidence = Evidence(
        id="e1",
        target=TARGET,
        kind="logs",
        observed_at=100,
        available_at=100,
        quality="unavailable",
        redacted_payload={"error": "observer_auth", "http_status": 401},
    )
    o.record_provider("owner", TARGET, evidence, watch_id=w["id"])
    o.tick(w["id"], lambda c: result(now[0], 200))
    incidents = s.incidents("owner")
    assert len(incidents) == 1 and incidents[0]["kind"] == "observer_access"
    assert incidents[0]["action_allowed"] is False


def test_manual_investigation_needs_no_watch_artifact_or_baseline(tmp_path):
    s, o, now = setup(tmp_path)
    i = o.begin_investigation("owner", TARGET, "Why does it fail?")
    assert i["watch_id"] is None and i["kind"] == "log_investigation"
    with pytest.raises(KeyError):
        s.incident("other", i["id"])


def test_release_change_and_three_fresh_successes_invalidate_previous_generation(tmp_path):
    s, o, now = setup(tmp_path)
    w = o.start_watch("owner", ["app"], [CHECK])
    for t in [100, 115]:
        now[0] = t
        o.tick(w["id"], lambda c: result(now[0]))
    i = s.incidents("owner")[0]
    o.set_release("owner", "app", "r2")
    assert s.incident("owner", i["id"])["generation"] == 2
    for t in [130, 145]:
        now[0] = t
        o.tick(w["id"], lambda c: result(now[0], 200))
    assert s.incident("owner", i["id"])["state"] == "open"
    now[0] = 160
    o.tick(w["id"], lambda c: result(now[0], 200))
    assert s.incident("owner", i["id"])["state"] == "recovered"
    assert s.incident("owner", i["id"])["generation"] == 3


def test_evidence_is_immutable_owner_scoped_and_frozen_by_availability(tmp_path):
    s, o, now = setup(tmp_path)
    i = o.begin_investigation("owner", TARGET, "issue")
    e = Evidence(
        id="e1",
        target=TARGET,
        kind="logs",
        observed_at=90,
        available_at=100,
        quality="fresh",
        redacted_payload={"message": "first"},
    )
    s.add_evidence("owner", i["id"], e)
    with pytest.raises(ValueError):
        s.add_evidence("owner", i["id"], e.model_copy(update={"redacted_payload": {"message": "changed"}}))
    assert s.evidence("owner", i["id"], cutoff=99) == []
    assert s.evidence("owner", i["id"], cutoff=100)[0]["redacted_payload"]["message"] == "first"
    with pytest.raises(KeyError):
        s.evidence("other", i["id"], cutoff=100)


def test_replayed_probe_and_same_tick_cannot_count_toward_failure_or_recovery(tmp_path):
    s, o, now = setup(tmp_path)
    w = o.start_watch("owner", ["app"], [CHECK])
    old = result(100)
    o.tick(w["id"], lambda c: old)
    assert o.tick(w["id"], lambda c: (_ for _ in ()).throw(AssertionError("same tick"))) == []
    now[0] = 115
    o.tick(w["id"], lambda c: old)
    assert s.incidents("owner") == []


def test_provider_refresh_once_per_minute_and_runtime_failure_without_http(tmp_path):
    s, o, now = setup(tmp_path)
    w = o.start_watch("owner", ["app"], [])
    calls = []

    def provider(target):
        calls.append(now[0])
        return [
            Evidence(
                id=f"runtime-{now[0]}",
                target=target,
                kind="applets",
                observed_at=now[0],
                available_at=now[0],
                quality="fresh",
                redacted_payload={"applets": [{"state": "Failed", "reason": "CrashLoop"}]},
            )
        ]

    for t in [100, 115, 130, 145, 160]:
        now[0] = t
        o.tick(w["id"], lambda _: None, provider=provider)
    assert calls == [100, 160]
    incidents = s.incidents("owner")
    assert len(incidents) == 1 and incidents[0]["kind"] == "runtime"
    assert incidents[0]["generation"] == 1


def test_provider_stale_runtime_data_cannot_open_service_failure(tmp_path):
    s, o, now = setup(tmp_path)
    evidence = Evidence(
        id="old",
        target=TARGET,
        kind="applets",
        observed_at=0,
        available_at=100,
        quality="stale",
        redacted_payload={"applets": [{"state": "Failed"}]},
    )
    assert o.record_provider("owner", TARGET, evidence) is None
    assert s.incidents("owner") == []


def test_stop_during_provider_collection_prevents_new_http_probe(tmp_path):
    s, o, now = setup(tmp_path)
    w = o.start_watch("owner", ["app"], [CHECK])
    calls = []

    def provider(_):
        o.stop_watch("owner", w["id"])
        return []

    o.tick(w["id"], lambda _: calls.append("http"), provider=provider)
    assert calls == []


def test_late_old_probe_cannot_overwrite_newer_health(tmp_path):
    import threading

    s, o, now = setup(tmp_path)
    w = o.start_watch("owner", ["app"], [CHECK])
    entered = threading.Event()
    release = threading.Event()

    def slow(_):
        entered.set()
        release.wait(2)
        return result(100)

    thread = threading.Thread(target=lambda: o.tick(w["id"], slow))
    thread.start()
    assert entered.wait(2)
    now[0] = 115
    o.tick(w["id"], lambda _: result(115, 200))
    release.set()
    thread.join(3)
    sample = s.watch("owner", w["id"])["samples"]["preview"]
    assert sample["last"]["observed_at"] == 115 and sample["failures"] == 0


def test_diagnosis_save_preserves_new_observations_with_same_generation(tmp_path):
    s, o, now = setup(tmp_path)
    old = s.ensure_incident("owner", TARGET, "http_availability", "scope", 100, fingerprint="same")
    s.ensure_incident("owner", TARGET, "http_availability", "scope", 115, fingerprint="same")
    old["diagnosis"] = {"outcome": "need_evidence", "cutoff": 100}
    s.save_incident(old, expected_generation=1)
    current = s.incident("owner", old["id"])
    assert current["observation_sequence"] == 2 and current["diagnosis"]["cutoff"] == 100
    s.ensure_incident("owner", TARGET, "http_availability", "scope", 130, fingerprint="changed")
    with pytest.raises(ValueError):
        s.save_incident(old, expected_generation=1)


@pytest.mark.parametrize("change", ["release", "fingerprint"])
def test_completed_diagnosis_is_invalidated_when_actionable_state_changes(tmp_path, change):
    s, o, now = setup(tmp_path)
    incident = s.ensure_incident("owner", TARGET, "http_availability", "scope", 100, fingerprint="old")
    incident.update(
        diagnosis={"outcome": "repair_candidate", "summary": "old conclusion"}, investigation_state="done"
    )
    s.save_incident(incident, incident["generation"])
    if change == "release":
        o.set_release("owner", "app", "new-release")
    else:
        s.ensure_incident("owner", TARGET, "http_availability", "scope", 115, fingerprint="different")
    current = s.incident("owner", incident["id"])
    assert current["generation"] > incident["generation"]
    assert current["diagnosis"] is None and current["investigation_state"] == "stale"


def test_evidence_freshness_ages_in_projection_without_rewriting_original(tmp_path):
    import json

    s, o, now = setup(tmp_path)
    incident = o.begin_investigation("owner", TARGET, "Investigate")
    s.add_evidence(
        "owner",
        incident["id"],
        Evidence(
            id="old",
            target=TARGET,
            kind="logs",
            observed_at=100,
            available_at=100,
            quality="fresh",
            redacted_payload={"message": "old crash"},
        ),
    )
    assert s.evidence("owner", incident["id"], cutoff=100)[0]["quality"] == "fresh"
    assert s.evidence("owner", incident["id"], cutoff=1000)[0]["quality"] == "stale"
    with s.connect() as db:
        assert (
            json.loads(db.execute("SELECT data FROM evidence WHERE id='old'").fetchone()[0])["quality"]
            == "fresh"
        )
