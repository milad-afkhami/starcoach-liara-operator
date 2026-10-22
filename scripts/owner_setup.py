"""Run with uv --env-file; credentials are read only from private environment."""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from liara_guard.client import LiaraClient, ProviderError
from liara_guard.owner_setup import Setup, NAMES
from liara_guard.approvals import ApprovalError
from liara_guard.bootstrap import select_quote


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=[
            "inspect",
            "propose-create",
            "package",
            "propose-initial",
            "approve-execute",
            "status",
            "baseline",
            "enable-repair",
        ],
    )
    parser.add_argument("--directory", default="data/live-setup")
    parser.add_argument("--app", choices=list(NAMES.values()))
    parser.add_argument("--network")
    parser.add_argument("--id")
    parser.add_argument("--digest")
    args = parser.parse_args()
    if not os.environ.get("LIARA_API_TOKEN") or not os.environ.get("LIARA_TEAM_ID"):
        parser.exit(
            2,
            "Owner-provisioned LIARA_API_TOKEN and LIARA_TEAM_ID are required; no cloud action performed.\n",
        )
    client = LiaraClient(os.environ["LIARA_API_TOKEN"], os.environ["LIARA_TEAM_ID"])
    try:
        setup = Setup(client, args.directory)
        if args.action == "inspect":
            result = {
                "team_id": client.team_id,
                "quote": select_quote(client.plan_catalogue()),
                "networks": client.list_networks(),
                "services": [s.model_dump() for s in client.list_services()],
            }
        elif args.action == "propose-create":
            if not args.app or not args.network:
                parser.error("Exact --app and --network required")
            result = setup.propose_create(args.app, args.network)
        elif args.action in ("package", "propose-initial"):
            if not args.app:
                parser.error("--app required")
            result = setup.package(args.app) if args.action == "package" else setup.propose_initial(args.app)
        elif args.action == "approve-execute":
            if not args.id or not args.digest:
                parser.error("Exact --id and displayed --digest required; no blanket approval")
            result = setup.execute(args.id, args.digest)
        elif args.action in ("status", "baseline"):
            if not args.id:
                parser.error("--id required")
            result = setup.status(args.id) if args.action == "status" else setup.baseline(args.id)
        else:
            result = setup.enable_repair()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ApprovalError, ProviderError, ValueError, FileNotFoundError):
        parser.exit(
            2,
            "Setup rejected or evidence unavailable. Check exact target, current quote, artifact and local ledger; no blind retry.\n",
        )
    finally:
        client.close()


if __name__ == "__main__":
    main()
