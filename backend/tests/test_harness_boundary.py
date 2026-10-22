from pathlib import Path
import importlib.util
import tarfile
import pytest
from liara_guard.artifacts import package_known_good, verify_artifact
from liara_guard.types import Target

ROOT = Path(__file__).parents[2]
TARGET = Target(team_id="t", app_name="demo-shop", app_id="app1")


def test_artifact_is_exact_allowlist_with_opaque_identity(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").write_text("app=1\n")
    (source / ".env").write_text("secret")
    (source / "auth.json").write_text("private")
    manifest = package_known_good(source, tmp_path / "good.tar.gz", TARGET, source_commit="commit1")
    assert verify_artifact(manifest)
    with tarfile.open(manifest.path) as bundle:
        assert set(bundle.getnames()) == {"app.py", "build-id", "Dockerfile", "requirements.lock"}
        assert bundle.extractfile("build-id").read().decode().strip() == manifest.build_id
    Path(manifest.path).write_bytes(b"changed")
    assert not verify_artifact(manifest)


def test_artifact_refuses_symlinked_sources_and_unsafe_dependency(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "app.py").symlink_to(ROOT / "demo/storefront/app.py")
    with pytest.raises(ValueError):
        package_known_good(source, tmp_path / "out.tar.gz", TARGET, source_commit="x")


def controller():
    spec = importlib.util.spec_from_file_location("isolated_controller", ROOT / "harness/controller.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_independent_injection_requires_owner_exact_approval_and_never_enters_registry(tmp_path):
    mod = controller()
    calls = []
    target = {"team_id": "t", "app_name": "demo-shop", "app_id": "app1"}
    archive = tmp_path / "fault.tar.gz"
    archive.write_bytes(b"independent fault source")
    c = mod.Controller(tmp_path / "controller.sqlite", {"app1": target}, clock=lambda: 100)
    spec = c.propose("owner", "deploy_fault", target, archive, before_release="r1")
    with pytest.raises(ValueError):
        c.execute("owner", spec["id"], "wrong", lambda *_: calls.append("write"))
    assert calls == []
    approval = c.approve("owner", spec["id"], spec["artifact_sha256"])
    assert (
        c.execute("owner", spec["id"], approval, lambda *_: calls.append("write") or {"release_id": "r2"})[
            "release_id"
        ]
        == "r2"
    )
    with pytest.raises(ValueError):
        c.execute("owner", spec["id"], approval, lambda *_: calls.append("write"))
    assert calls == ["write"]
    assert not (tmp_path / "operator.sqlite").exists()


def test_injection_denies_expired_wrong_owner_changed_artifact_and_unenrolled_target(tmp_path):
    mod = controller()
    now = [100]
    target = {"team_id": "t", "app_name": "demo-shop", "app_id": "app1"}
    archive = tmp_path / "fault.tar.gz"
    archive.write_bytes(b"x")
    c = mod.Controller(tmp_path / "controller.sqlite", {"app1": target}, clock=lambda: now[0])
    calls = []
    with pytest.raises(ValueError):
        c.propose("owner", "deploy_fault", {**target, "app_name": "production"}, archive, before_release="r1")
    spec = c.propose("owner", "deploy_fault", target, archive, before_release="r1")
    with pytest.raises(ValueError):
        c.approve("other", spec["id"], spec["artifact_sha256"])
    approval = c.approve("owner", spec["id"], spec["artifact_sha256"])
    archive.write_bytes(b"y")
    with pytest.raises(ValueError):
        c.execute("owner", spec["id"], approval, lambda *_: calls.append("write"))
    archive.write_bytes(b"x")
    now[0] = 401
    with pytest.raises(ValueError):
        c.execute("owner", spec["id"], approval, lambda *_: calls.append("write"))
    assert calls == []
