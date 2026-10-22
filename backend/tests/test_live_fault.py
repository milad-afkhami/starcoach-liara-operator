"""The separate controller writer is never an investigator tool."""

import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest
from liara_guard.types import Evidence, Target

specmod = importlib.util.spec_from_file_location(
    "live_fault", Path(__file__).resolve().parents[2] / "harness/live_fault.py"
)
module = importlib.util.module_from_spec(specmod)
specmod.loader.exec_module(module)


def setup(tmp_path):
    archive = tmp_path / "variant.tar.gz"
    archive.write_bytes(b"variant")
    target = Target(team_id="team", app_name="liara-watch-delivery-2026", app_id="dep")
    source = {
        "target": target.model_dump(exclude={"origin"}),
        "archive": str(archive),
        "artifact_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "before_release": "r1",
        "expires_at": 1000,
    }
    writes = []
    client = SimpleNamespace(
        get_project=lambda t: {"_id": "dep"},
        get_releases=lambda t: Evidence(
            id="e",
            target=t,
            kind="releases",
            observed_at=100,
            available_at=100,
            quality="fresh",
            redacted_payload={"currentRelease": "r1"},
        ),
        upload_source=lambda s, b: writes.append(("upload", b)) or "source",
        create_release=lambda s, src: writes.append(("release", src)) or "r2",
    )
    return source, client, writes


def test_controller_stale_before_state_performs_zero_writes(tmp_path):
    source, client, writes = setup(tmp_path)
    source["before_release"] = "old"
    with pytest.raises(ValueError):
        module.deploy_once(client, source, tmp_path / "receipt.json", clock=lambda: 100)
    assert writes == []


def test_controller_freezes_exact_bytes_and_records_source_release(tmp_path):
    source, client, writes = setup(tmp_path)
    result = module.deploy_once(client, source, tmp_path / "receipt.json", clock=lambda: 100)
    assert result["state"] == "pending" and result["release_id"] == "r2"
    assert writes == [("upload", b"variant"), ("release", "source")]


def test_ambiguous_controller_write_records_unknown_and_does_not_retry(tmp_path):
    from liara_guard.approvals import AmbiguousWrite

    source, client, writes = setup(tmp_path)

    def upload(s, b):
        writes.append(("upload", b))
        raise AmbiguousWrite("unknown")

    client.upload_source = upload
    result = module.deploy_once(client, source, tmp_path / "receipt.json", clock=lambda: 100)
    assert result["state"] == "unknown" and len(writes) == 1
