import hashlib
import json
from types import SimpleNamespace
import pytest
from liara_guard.owner_setup import Setup, write_private
from liara_guard.approvals import ApprovalError
from liara_guard.types import Target, ServiceSummary


def test_setup_rejects_non_demo_names_without_writes(tmp_path):
    setup = Setup(SimpleNamespace(team_id="team"), tmp_path)
    with pytest.raises(ValueError):
        setup.propose_create("production", "network")
    with pytest.raises(ValueError):
        setup.package("production")


def test_existing_app_is_not_implicitly_enrolled_for_initial_deployment(tmp_path):
    target = Target(team_id="team", app_name="liara-watch-delivery-2026", app_id="dep")
    client = SimpleNamespace(
        team_id="team",
        list_services=lambda: [
            ServiceSummary(target=target, platform="docker", runtime_state="running", observed_at=100)
        ],
    )
    setup = Setup(client, tmp_path)
    with pytest.raises(ApprovalError):
        setup.package(target.app_name)


def test_private_configuration_is_atomic_and_symlink_refused(tmp_path):
    path = tmp_path / "registry.json"
    write_private(path, {"x": 1})
    assert json.loads(path.read_text()) == {"x": 1} and path.stat().st_mode & 0o777 == 0o600
    secret = tmp_path / "other"
    secret.write_text("untouched")
    path.unlink()
    path.symlink_to(secret)
    with pytest.raises(ValueError):
        write_private(path, {"x": 2})
    assert secret.read_text() == "untouched"


def test_baseline_registration_requires_real_success_and_exact_artifact(tmp_path):
    from liara_guard.owner_setup import register_baseline

    target = Target(team_id="team", app_name="liara-watch-delivery-2026", app_id="dep")
    archive = tmp_path / "source.tar.gz"
    archive.write_bytes(b"approved")
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest = {"path": str(archive), "sha256": digest, "build_id": "build", "target": target.model_dump()}
    cfg = {
        "enrolled": {
            "dep": {
                "team_id": "team",
                "app_name": target.app_name,
                "approved_sources": {digest: str(archive)},
            }
        }
    }
    operation = {
        "state": "ready",
        "release_id": "r1",
        "spec": {
            "kind": "deploy_initial",
            "app_id": "dep",
            "team_id": "team",
            "app_name": target.app_name,
            "artifact_sha256": digest,
        },
    }
    bad = {"state": "inconclusive"}
    with pytest.raises(ApprovalError):
        register_baseline(cfg, manifest, operation, bad)
    assert "baseline_verified" not in cfg["enrolled"]["dep"]
    good = {"state": "recovered", "submitted_release_id": "r1", "success_probe_ids": ["a", "b", "c"]}
    register_baseline(cfg, manifest, operation, good)
    assert cfg["enrolled"]["dep"]["baseline_verified"] is True
    assert cfg["enrolled"]["dep"]["known_good"] == {digest: str(archive)}
    archive.write_bytes(b"changed")
    with pytest.raises(ApprovalError):
        register_baseline(cfg, manifest, operation, good)
