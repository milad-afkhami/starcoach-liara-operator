"""Generate private local operator configuration without printing credentials."""

import argparse
import os
from pathlib import Path
import secrets
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from liara_guard.auth import hash_password
from liara_guard.owner_setup import write_private


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["fixture", "live"], required=True)
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--access-file", required=True)
    parser.add_argument("--team")
    parser.add_argument("--codex-binary")
    parser.add_argument("--codex-auth-file")
    parser.add_argument("--codex-image")
    args = parser.parse_args()
    envpath, access = Path(args.env_file), Path(args.access_file)
    if envpath.exists() or envpath.is_symlink() or access.exists() or access.is_symlink():
        parser.error("Refusing to overwrite existing configuration/access file")
    model = [args.codex_binary, args.codex_auth_file, args.codex_image]
    if any(model) and not all(model):
        parser.error("All three Codex paths/image are required together")
    if args.mode == "live" and not args.team:
        parser.error("Explicit --team required in live mode")
    password = secrets.token_urlsafe(24)
    values = {
        "PYTHONPATH": "backend",
        "LIARA_MODE": args.mode,
        "LIARA_TEAM_ID": args.team or "local-fixture",
        "STATE_DB_PATH": "data/operator.sqlite",
        "PUBLIC_ORIGIN": "http://127.0.0.1:8661",
        "SESSION_SECRET": secrets.token_urlsafe(48),
        "OPERATOR_PASSWORD_HASH": hash_password(password),
    }
    if args.mode == "live":
        values["REGISTRY_PATH"] = "data/live-setup/registry.json"
    if all(model):
        values.update(
            CODEX_BINARY_PATH=args.codex_binary,
            CODEX_AUTH_FILE=args.codex_auth_file,
            CODEX_IMAGE=args.codex_image,
        )
    for value in values.values():
        if "\n" in value or "\r" in value or "'" in value:
            parser.error("Invalid configuration value")
    write_private(access, {"url": values["PUBLIC_ORIGIN"], "password": password})
    envpath.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(envpath, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as out:
        for key, value in values.items():
            out.write(f"{key}='{value}'\n")
    print("Private environment: " + str(envpath.resolve()))
    print("Private owner access: " + str(access.resolve()))
    print("No Liara credential was created or copied. No cloud resource was changed.")


if __name__ == "__main__":
    main()
