from pathlib import Path
import hashlib
import pytest
from liara_guard.approvals import OperationStore, Executor, OperationSpec, ApprovalError, AmbiguousWrite


def setup(tmp_path):
    now = [100.0]
    archive = tmp_path / "good.tar.gz"
    archive.write_bytes(b"known-good")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    store = OperationStore(tmp_path / "operations.sqlite", clock=lambda: now[0])
    spec = OperationSpec(
        kind="redeploy_known_good",
        team_id="team",
        app_name="demo",
        app_id="app",
        artifact_sha256=digest,
        before_release_id="r1",
        incident_id="i",
        incident_generation=1,
        failure_fingerprint="failure",
        verification_policy_hash="policy",
    )
    op = store.propose("owner", spec)

    class Provider:
        def __init__(self):
            self.writes = []
            self.releases = []
            self.current = "r1"
            self.upload_error = False
            self.release_error = False

        def upload_source(self, spec, path):
            self.writes.append("upload")
            if self.upload_error:
                raise AmbiguousWrite("upload_unknown")
            return "source-1"

        def create_release(self, spec, source):
            self.writes.append("release")
            if self.release_error:
                raise AmbiguousWrite("release_unknown")
            return "r2"

        def create_project(self, spec):
            self.writes.append("create")
            return "new-app"

        def inspect(self, spec):
            return {
                "release_id": self.current,
                "exists": True,
                "app_id": "app",
                "incident_generation": 1,
                "failure_fingerprint": "failure",
                "verification_policy_hash": "policy",
                "discriminating_condition": True,
            }

        def release_candidates(self, spec, source):
            return self.releases

    provider = Provider()
    ex = Executor(
        store,
        provider,
        {"app": {"team_id": "team", "app_name": "demo", "known_good": {digest: str(archive)}}},
        clock=lambda: now[0],
    )
    return store, ex, provider, op, now, archive


def approve(s, op):
    return s.approve("owner", op["id"], op["digest"])


def test_exact_approval_one_write_sequence_and_replay_refusal(tmp_path):
    s, e, p, op, now, a = setup(tmp_path)
    with pytest.raises(ApprovalError):
        e.execute("owner", op["id"])
    assert p.writes == []
    approve(s, op)
    result = e.execute("owner", op["id"])
    assert result["state"] == "pending" and result["release_id"] == "r2" and p.writes == ["upload", "release"]
    with pytest.raises(ApprovalError):
        e.execute("owner", op["id"])
    assert p.writes == ["upload", "release"]


@pytest.mark.parametrize(
    "case",
    [
        "owner",
        "digest",
        "expiry",
        "release",
        "generation",
        "fingerprint",
        "policy",
        "condition",
        "archive",
        "target",
    ],
)
def test_rejected_or_stale_conditions_produce_zero_writes(tmp_path, case):
    s, e, p, op, now, a = setup(tmp_path)
    if case == "owner":
        with pytest.raises(ApprovalError):
            s.approve("other", op["id"], op["digest"])
        return
    if case == "digest":
        with pytest.raises(ApprovalError):
            s.approve("owner", op["id"], "different")
        return
    approve(s, op)
    if case == "expiry":
        now[0] = 401
    elif case == "release":
        p.current = "r3"
    elif case == "archive":
        a.write_bytes(b"changed")
    elif case == "target":
        e.enrolled["app"]["app_name"] = "other"
    else:
        original = p.inspect
        field = {
            "generation": "incident_generation",
            "fingerprint": "failure_fingerprint",
            "policy": "verification_policy_hash",
            "condition": "discriminating_condition",
        }[case]
        p.inspect = lambda spec: {**original(spec), field: False if case == "condition" else "different"}
    with pytest.raises(ApprovalError):
        e.execute("owner", op["id"])
    assert p.writes == []


def test_ambiguous_upload_never_creates_release_or_blindly_retries(tmp_path):
    s, e, p, op, now, a = setup(tmp_path)
    p.upload_error = True
    approve(s, op)
    result = e.execute("owner", op["id"])
    assert result["state"] == "unknown" and p.writes == ["upload"]
    assert e.reconcile("owner", op["id"])["state"] == "unknown"
    with pytest.raises(ApprovalError):
        e.execute("owner", op["id"])
    assert p.writes == ["upload"]


def test_ambiguous_release_reconciles_only_unique_source_identity(tmp_path):
    s, e, p, op, now, a = setup(tmp_path)
    p.release_error = True
    approve(s, op)
    assert e.execute("owner", op["id"])["state"] == "unknown"
    p.releases = [{"id": "r2", "source_id": "source-1"}, {"id": "r3", "source_id": "source-1"}]
    assert e.reconcile("owner", op["id"])["state"] == "unknown"
    p.releases = [{"id": "r2", "source_id": "source-1"}]
    now[0] += 10
    resolved = e.reconcile("owner", op["id"])
    assert resolved["state"] == "pending" and resolved["release_id"] == "r2"
    assert p.writes == ["upload", "release"]


def test_unknown_intent_blocks_another_writer_and_restart_never_replays(tmp_path):
    s, e, p, op, now, a = setup(tmp_path)
    p.upload_error = True
    approve(s, op)
    e.execute("owner", op["id"])
    next_op = s.propose("owner", OperationSpec.model_validate(op["spec"]))
    approve(s, next_op)
    with pytest.raises(ApprovalError):
        e.execute("owner", next_op["id"])
    restarted = OperationStore(tmp_path / "operations.sqlite", clock=lambda: now[0])
    assert restarted.get("owner", op["id"])["state"] == "unknown" and p.writes == ["upload"]


def test_reconciliation_stops_after_ten_minutes_without_new_writes(tmp_path):
    s, e, p, op, now, a = setup(tmp_path)
    p.release_error = True
    approve(s, op)
    e.execute("owner", op["id"])
    now[0] = 701
    assert e.reconcile("owner", op["id"])["state"] == "unknown"
    assert p.writes == ["upload", "release"]


def test_bootstrap_create_collision_and_exact_price_bound(tmp_path):
    s, e, p, op, now, a = setup(tmp_path)
    with pytest.raises(ValueError):
        OperationSpec(kind="create_app", team_id="team", app_name="fresh")
    spec = OperationSpec(
        kind="create_app",
        team_id="team",
        app_name="fresh",
        plan_id="earth",
        bundle_plan_id="basic",
        network_id="net",
        hourly_price_toman="1040",
        price_verified_at=100,
    )
    create = s.propose("owner", spec)
    approve(s, create)
    e.allowed_new_names = {"fresh"}
    with pytest.raises(ApprovalError):
        e.execute("owner", create["id"])
    assert p.writes == []


def test_created_app_does_not_lock_out_its_initial_deployment(tmp_path):
    s, e, p, op, now, a = setup(tmp_path)
    e.allowed_new_names = {"fresh"}
    p.inspect = lambda spec: {
        "exists": False,
        "plan_id": "earth",
        "bundle_plan_id": "basic",
        "network_id": "net",
        "hourly_price_toman": "1040",
    }
    spec = OperationSpec(
        kind="create_app",
        team_id="team",
        app_name="fresh",
        plan_id="earth",
        bundle_plan_id="basic",
        network_id="net",
        hourly_price_toman="1040",
        price_verified_at=100,
    )
    create = s.propose("owner", spec)
    approve(s, create)
    result = e.execute("owner", create["id"])
    assert result["state"] == "completed" and result["created_app_id"] == "new-app"
    initial = s.propose(
        "owner",
        OperationSpec(
            kind="deploy_initial",
            team_id="team",
            app_name="fresh",
            app_id="new-app",
            artifact_sha256=op["spec"]["artifact_sha256"],
        ),
    )
    approve(s, initial)
    assert s.claim("owner", initial["id"])["state"] == "checking"


def test_upload_uses_approved_bytes_even_if_source_changes_during_before_read(tmp_path):
    s, e, p, op, now, a = setup(tmp_path)
    approve(s, op)
    original = p.inspect
    sent = []

    def inspect(spec):
        a.write_bytes(b"changed-after-check")
        return original(spec)

    p.inspect = inspect

    def upload(spec, content):
        sent.append(content if isinstance(content, bytes) else Path(content).read_bytes())
        return "source-1"

    p.upload_source = upload
    e.execute("owner", op["id"])
    assert sent == [b"known-good"]


def test_restart_of_verification_is_inconclusive_not_an_unbounded_new_window(tmp_path):
    s, e, p, op, now, a = setup(tmp_path)
    s.update(op, state="verifying")
    restarted = OperationStore(tmp_path / "operations.sqlite", clock=lambda: now[0])
    result = restarted.get("owner", op["id"])
    assert result["state"] == "failed" and result["error"] == "verification_interrupted"
