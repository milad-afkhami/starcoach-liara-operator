"""Independent owner-approved demo fault. Never imported by the operator or model."""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from controller import Controller
from liara_guard.approvals import OperationSpec, RejectedWrite
from liara_guard.artifacts import ROOT, package_known_good
from liara_guard.client import LiaraClient
from liara_guard.owner_setup import Setup, NAMES, write_private
from liara_guard.types import Target


def deploy_once(client, proposal, receipt_path, *, clock=time.time):
    target = Target.model_validate(proposal["target"])
    if target.app_name != NAMES["delivery"] or clock() >= proposal["expires_at"]:
        raise ValueError("Wrong/expired fault target")
    path = Path(proposal["archive"])
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("Invalid fault archive")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != proposal["artifact_sha256"]:
        raise ValueError("Fault source changed")
    client.get_project(target)
    releases = client.get_releases(target)
    if (
        releases.quality != "fresh"
        or releases.redacted_payload.get("currentRelease") != proposal["before_release"]
    ):
        raise ValueError("Current release changed")
    if clock() >= proposal["expires_at"]:
        raise ValueError("Fault approval expired")
    spec = OperationSpec(
        kind="deploy_initial",
        team_id=target.team_id,
        app_id=target.app_id,
        app_name=target.app_name,
        artifact_sha256=proposal["artifact_sha256"],
        before_release_id=proposal["before_release"],
    )
    receipt = {
        "state": "uploading",
        "submitted_at": clock(),
        "reconcile_until": clock() + 600,
        "source_id": None,
        "release_id": None,
        "target": proposal["target"],
        "artifact_sha256": proposal["artifact_sha256"],
        "last_reconciled": None,
    }
    write_private(receipt_path, receipt)
    try:
        receipt["source_id"] = client.upload_source(spec, content)
        receipt["state"] = "creating_release"
        write_private(receipt_path, receipt)
        if clock() >= proposal["expires_at"]:
            receipt["state"] = "failed"
            receipt["reason"] = "approval_expired_before_release"
        else:
            receipt["release_id"] = client.create_release(spec, receipt["source_id"])
            receipt["state"] = "pending"
    except RejectedWrite:
        receipt["state"] = "failed"
        receipt["reason"] = "provider_rejected"
    except Exception:
        receipt["state"] = "unknown"
        receipt["reason"] = "ambiguous_write"
    write_private(receipt_path, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["propose", "approve-execute", "status"])
    parser.add_argument("--id")
    parser.add_argument("--sha256")
    parser.add_argument("--setup-directory", default="data/live-setup")
    args = parser.parse_args()
    if not os.environ.get("LIARA_API_TOKEN") or not os.environ.get("LIARA_TEAM_ID"):
        parser.exit(2, "Owner-provisioned credentials required; no cloud action performed.\n")
    client = LiaraClient(os.environ["LIARA_API_TOKEN"], os.environ["LIARA_TEAM_ID"])
    private = ROOT / "data/live-controller"
    private.mkdir(parents=True, exist_ok=True)
    private.chmod(0o700)
    try:
        setup = Setup(client, args.setup_directory)
        target = setup.target(NAMES["delivery"])
        if not setup.config.get("enrolled", {}).get(target.app_id, {}).get("baseline_verified"):
            raise ValueError("Actual baseline required")
        controller = Controller(
            private / "controller.sqlite", {target.app_id: target.model_dump(exclude={"origin"})}
        )
        if args.action == "propose":
            receipt_path = private / "receipt.json"
            if receipt_path.exists() and json.loads(receipt_path.read_text()).get("state") in (
                "uploading",
                "creating_release",
                "unknown",
                "pending",
            ):
                raise ValueError("Unresolved prior fault intent; reconcile it first")
            changed = private / "source"
            changed.mkdir(exist_ok=True)
            source = (ROOT / "demo/delivery/app.py").read_text()
            if source.count('"shipping_toman"') != 1:
                raise ValueError("Source contract changed")
            (changed / "app.py").write_text(source.replace('"shipping_toman"', '"delivery_toman"'))
            # This deliberately incompatible archive NEVER enters enrolled/known_good.
            manifest = package_known_good(
                changed, private / "variant.tar.gz", target, source_commit="independent-controller-variant"
            )
            write_private(private / "variant.manifest.json", manifest.model_dump())
            releases = client.get_releases(target)
            if releases.quality != "fresh":
                raise ValueError("Current release unavailable")
            result = controller.propose(
                "live-demo-owner",
                "deploy_fault",
                target.model_dump(exclude={"origin"}),
                manifest.path,
                before_release=releases.redacted_payload.get("currentRelease"),
            )
            result.pop("archive", None)
        elif args.action == "approve-execute":
            if not args.id or not args.sha256:
                parser.error("Exact --id and --sha256 required")
            token = controller.approve("live-demo-owner", args.id, args.sha256)
            result = controller.execute(
                "live-demo-owner", args.id, token, lambda p: deploy_once(client, p, private / "receipt.json")
            )
        else:
            result = json.loads((private / "receipt.json").read_text())
            if result["state"] in ("uploading", "creating_release"):
                result["state"] = "unknown"
            now = time.time()
            if (
                result["state"] in ("unknown", "pending")
                and now <= result["reconcile_until"]
                and (result.get("last_reconciled") is None or now - result["last_reconciled"] >= 10)
            ):
                result["last_reconciled"] = now
                evidence = client.get_releases(target)
                rows = evidence.redacted_payload.get("releases", []) if evidence.quality == "fresh" else []
                matches = (
                    [r for r in rows if r.get("sourceID") == result["source_id"]]
                    if result["source_id"]
                    else []
                )
                if not result["release_id"] and len(matches) == 1:
                    result["release_id"] = matches[0]["_id"]
                    result["state"] = "pending"
                found = next((r for r in rows if r.get("_id") == result["release_id"]), {})
                if found.get("state") in ("FAILED", "UNHEALTHY"):
                    result["state"] = "failed"
                if (
                    found.get("state") == "READY"
                    and evidence.redacted_payload.get("currentRelease") == result["release_id"]
                ):
                    result["state"] = "ready"
            write_private(private / "receipt.json", result)
        print(json.dumps(result, indent=2))
    except (ValueError, KeyError, OSError):
        parser.exit(2, "Fault setup rejected or state unavailable; inspect private ledger. No blind retry.\n")
    finally:
        client.close()


if __name__ == "__main__":
    main()
