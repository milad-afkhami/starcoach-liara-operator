"""Owner-only disposable-demo setup. No model or public API can call this workflow."""

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from .approvals import ApprovalError, Executor, OperationSpec, OperationStore
from .artifacts import ROOT, ArtifactManifest, package_known_good, verify_artifact
from .bootstrap import select_quote
from .contracts import ProbeRunner, RegisteredHttpCheck
from .observer import MonitorStore
from .operations_bridge import LiaraOperationProvider
from .runtime import Registry
from .verification import VerificationPolicy, verify_recovery

NAMES = {"storefront": "liara-watch-storefront-2026", "delivery": "liara-watch-delivery-2026"}


def write_private(path, value):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Symlink configuration refused")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".owner-")
    try:
        with os.fdopen(descriptor, "w") as out:
            json.dump(value, out, indent=2, ensure_ascii=False)
            out.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def register_baseline(config, manifest, operation, proof):
    target = manifest["target"]
    spec = operation["spec"]
    path = Path(manifest["path"])
    import hashlib

    if (
        operation["state"] != "ready"
        or spec["kind"] != "deploy_initial"
        or any(spec[k] != target[k] for k in ("team_id", "app_id", "app_name"))
        or spec["artifact_sha256"] != manifest["sha256"]
        or proof.get("state") != "recovered"
        or proof.get("submitted_release_id") != operation["release_id"]
        or len(set(proof.get("success_probe_ids", []))) < 3
        or path.is_symlink()
        or not path.is_file()
        or hashlib.sha256(path.read_bytes()).hexdigest() != manifest["sha256"]
    ):
        raise ApprovalError("Fresh exact baseline proof required")
    entry = config.get("enrolled", {}).get(target["app_id"], {})
    if entry.get("approved_sources", {}).get(manifest["sha256"]) != str(path):
        raise ApprovalError("Source not enrolled")
    entry.update(
        baseline_verified=True,
        baseline_release_id=operation["release_id"],
        baseline_build_id=manifest["build_id"],
        baseline_proof=proof,
        known_good={manifest["sha256"]: str(path)},
    )


class Setup:
    def __init__(self, client, directory, *, clock=time.time):
        self.client, self.directory, self.clock = client, Path(directory), clock
        self.directory.mkdir(parents=True, exist_ok=True)
        self.owner = "demo-bootstrap-owner"
        self.config_path = self.directory / "registry.json"
        self.config = json.loads(self.config_path.read_text()) if self.config_path.is_file() else {}
        if self.config.get("team_id", client.team_id) != client.team_id:
            raise ApprovalError("Setup team changed")
        self.config["team_id"] = client.team_id
        self.operations = OperationStore(self.directory / "setup.sqlite", clock=clock)
        self.registry = Registry(client.team_id, self.config)

    def name(self, name):
        if name not in NAMES.values():
            raise ValueError("Only the two disposable demo names are permitted")
        return name

    def refresh(self):
        self.registry.refresh(self.client.list_services())

    def target(self, name):
        self.name(name)
        self.refresh()
        found = next((t for t in self.registry.targets.values() if t.app_name == name), None)
        if found is None:
            raise ApprovalError("Create the approved demo app first")
        with self.operations.connect() as db:
            rows = [
                json.loads(row[0])
                for row in db.execute("SELECT data FROM operations WHERE state='completed'")
            ]
        if not any(
            row["spec"]["kind"] == "create_app"
            and row["spec"]["app_name"] == name
            and row.get("created_app_id") == found.app_id
            for row in rows
        ):
            raise ApprovalError("Existing app was not created by this setup ledger")
        return found

    def bridge(self):
        return LiaraOperationProvider(
            self.client,
            self.registry,
            MonitorStore(self.directory / "setup-observations.sqlite"),
            ProbeRunner(self.registry.targets),
            self.owner,
        )

    def propose_create(self, name, network):
        self.name(name)
        quote = select_quote(self.client.plan_catalogue())
        if network not in {n["id"] for n in self.client.list_networks()}:
            raise ApprovalError("Explicit existing network required")
        return self.operations.propose(
            self.owner,
            OperationSpec(
                kind="create_app",
                team_id=self.client.team_id,
                app_name=name,
                plan_id=quote["plan_id"],
                bundle_plan_id=quote["bundle_plan_id"],
                network_id=network,
                hourly_price_toman=quote["hourly_price_toman"],
                price_verified_at=self.clock(),
            ),
        )

    def package(self, name):
        target = self.target(name)
        role = next(role for role, app in NAMES.items() if app == name)
        dependency = "https://" + NAMES["delivery"] + ".liara.run" if role == "storefront" else None
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        # Refuse to label an uncommitted app source as a committed artifact.
        dirty = subprocess.check_output(
            [
                "git",
                "status",
                "--porcelain",
                "--",
                f"demo/{role}/app.py",
                "requirements.lock",
                "backend/liara_guard/artifacts.py",
            ],
            cwd=ROOT,
            text=True,
        )
        if dirty:
            raise ApprovalError("Commit the allowlisted source and packager before packaging")
        if self.config.get("enrolled", {}).get(target.app_id, {}).get("baseline_verified"):
            raise ApprovalError("Baseline already registered; do not overwrite it")
        manifest = package_known_good(
            ROOT / "demo" / role,
            self.directory / f"{role}.tar.gz",
            target,
            source_commit=commit,
            dependency_origin=dependency,
        )
        write_private(self.directory / f"{role}.manifest.json", manifest.model_dump())
        entry = self.config.setdefault("enrolled", {}).setdefault(
            target.app_id, {"team_id": target.team_id, "app_name": target.app_name}
        )
        if entry.get("baseline_verified"):
            raise ApprovalError("Baseline already registered; do not overwrite it")
        entry["approved_sources"] = {manifest.sha256: manifest.path}
        write_private(self.config_path, self.config)
        return manifest.model_dump()

    def manifest(self, name):
        self.name(name)
        role = next(role for role, app in NAMES.items() if app == name)
        manifest = ArtifactManifest.model_validate_json(
            (self.directory / f"{role}.manifest.json").read_text()
        )
        if manifest.target != self.target(name) or not verify_artifact(manifest):
            raise ApprovalError("Artifact or target changed")
        return manifest

    def propose_initial(self, name):
        manifest = self.manifest(name)
        releases = self.client.get_releases(manifest.target)
        if releases.quality != "fresh" or releases.redacted_payload.get("currentRelease") is not None:
            raise ApprovalError("Initial deployment requires a verified never-deployed target")
        return self.operations.propose(
            self.owner,
            OperationSpec(
                kind="deploy_initial",
                team_id=manifest.target.team_id,
                app_name=name,
                app_id=manifest.target.app_id,
                artifact_sha256=manifest.sha256,
            ),
        )

    def execute(self, identifier, digest):
        op = self.operations.get(self.owner, identifier)
        self.name(op["spec"]["app_name"])
        self.refresh()
        self.operations.approve(self.owner, identifier, digest)
        return Executor(
            self.operations,
            self.bridge(),
            self.registry.enrolled,
            clock=self.clock,
            allowed_new_names=NAMES.values(),
        ).execute(self.owner, identifier)

    def status(self, identifier):
        self.refresh()
        return Executor(
            self.operations,
            self.bridge(),
            self.registry.enrolled,
            clock=self.clock,
            allowed_new_names=NAMES.values(),
        ).reconcile(self.owner, identifier)

    def runner_for(self, checks):
        targets = dict(self.registry.targets)
        for check in checks:
            target = self.registry.resolve(check.target_id)
            if check.origin != "https://" + self.name(target.app_name) + ".liara.run":
                raise ApprovalError("Unexpected demo origin")
            targets[target.app_id] = target.model_copy(update={"origin": check.origin})
        return ProbeRunner(targets)

    def baseline(self, identifier):
        operation = self.status(identifier)
        if operation["state"] != "ready" or operation["spec"]["kind"] != "deploy_initial":
            raise ApprovalError("Wait for exact initial release readiness")
        manifest = self.manifest(operation["spec"]["app_name"])
        target = manifest.target
        role = next(role for role, name in NAMES.items() if name == target.app_name)
        check = RegisteredHttpCheck(
            id=role + "-baseline",
            target_id=target.app_id,
            origin="https://" + target.app_name + ".liara.run",
            path="/quote" if role == "delivery" else "/preview",
            require_request_echo=True,
        )
        policy = VerificationPolicy(
            id=role + "-initial",
            checks=[check],
            changed_target_id=target.app_id,
            expected_release_ids={target.app_id: "$submitted"},
            expected_build_fields={check.id: {"build_id": manifest.build_id}},
        )
        proof = verify_recovery(
            policy,
            operation["release_id"],
            self.bridge().status_for_policy,
            self.runner_for(policy.checks).run,
        )
        register_baseline(self.config, manifest.model_dump(), operation, proof)
        write_private(self.config_path, self.config)
        self.operations.update(operation, state="completed", verification=proof)
        return proof

    def enable_repair(self):
        store, dep = self.target(NAMES["storefront"]), self.target(NAMES["delivery"])
        a, b = (
            self.config.get("enrolled", {}).get(store.app_id, {}),
            self.config.get("enrolled", {}).get(dep.app_id, {}),
        )
        if not a.get("baseline_verified") or not b.get("baseline_verified"):
            raise ApprovalError("Both actual baselines must pass first")
        preview = RegisteredHttpCheck(
            id="store-preview",
            target_id=store.app_id,
            origin="https://" + store.app_name + ".liara.run",
            path="/preview",
            require_request_echo=True,
        )
        quote = RegisteredHttpCheck(
            id="dep-quote",
            target_id=dep.app_id,
            origin="https://" + dep.app_name + ".liara.run",
            path="/quote",
            require_request_echo=True,
        )
        health = RegisteredHttpCheck(
            id="store-health",
            target_id=store.app_id,
            origin=preview.origin,
            path="/healthz",
            require_request_echo=True,
        )
        # A fresh observation must still identify both registered builds and releases.
        policy = VerificationPolicy(
            id="dependency-recovery",
            checks=[preview, quote],
            changed_target_id=dep.app_id,
            expected_release_ids={store.app_id: a["baseline_release_id"], dep.app_id: "$submitted"},
            expected_build_fields={
                preview.id: {
                    "build_id": a["baseline_build_id"],
                    "dependency_build_id": b["baseline_build_id"],
                },
                quote.id: {"build_id": b["baseline_build_id"]},
            },
        )
        proof = verify_recovery(
            policy,
            b["baseline_release_id"],
            self.bridge().status_for_policy,
            self.runner_for(policy.checks).run,
        )
        if proof["state"] != "recovered":
            raise ApprovalError("Both current baselines must still match")
        self.config.update(
            http_checks=[c.model_dump() for c in [preview, health, quote]],
            dependencies={store.app_id: [dep.app_id]},
            repair_targets={store.app_id: dep.app_id},
            verification_policies={store.app_id: policy.model_dump()},
            repair_discriminators={
                store.app_id: {"check_id": quote.id, "required_integer_field": "shipping_toman"}
            },
        )
        write_private(self.config_path, self.config)
        return {"registered": True, "policy_sha256": policy.digest(), "proof": proof}
