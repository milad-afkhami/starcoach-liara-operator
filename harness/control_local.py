"""Separate local fixture approval command. No operator/model endpoint invokes this."""

import argparse
import json
from pathlib import Path
from controller import Controller

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["propose", "approve"])
    parser.add_argument("--id")
    parser.add_argument("--sha256")
    args = parser.parse_args()
    private = ROOT / "data/local-controller"
    target = {"team_id": "local-fixture", "app_name": "delivery", "app_id": "local-dep"}
    controller = Controller(private / "controller.sqlite", {"local-dep": target})
    if args.action == "propose":
        current = json.loads((ROOT / "data/local-services/releases.json").read_text())["local-dep"][
            "release_id"
        ]
        value = controller.propose(
            "local-demo-owner", "deploy_fault", target, private / "variant.tar.gz", before_release=current
        )
        print(json.dumps({k: v for k, v in value.items() if k != "archive"}))
    else:
        if not args.id or not args.sha256:
            raise SystemExit("Approve requires the exact proposal ID and displayed archive SHA256")
        token = controller.approve("local-demo-owner", args.id, args.sha256)
        request = private / "approved-request.json"
        request.write_text(json.dumps({"id": args.id, "approval": token}))
        request.chmod(0o600)
        print("Exact local fixture deployment approved; inspect receipt.json for the outcome.")


if __name__ == "__main__":
    main()
