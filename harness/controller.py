"""Owner-only fault controller. Never import/register this in the operator or model tools."""

import hashlib
import hmac
import json
import secrets
import sqlite3
import time
import uuid
from pathlib import Path


class Controller:
    def __init__(self, path, targets, *, clock=time.time):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.targets = targets
        self.clock = clock
        with sqlite3.connect(self.path) as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS injections(id TEXT PRIMARY KEY,owner TEXT,data TEXT,approval TEXT,claimed INTEGER)"
            )
        self.path.chmod(0o600)

    def propose(self, owner, operation, target, archive=None, *, before_release=None):
        if self.targets.get(target.get("app_id")) != target or operation not in (
            "deploy_fault",
            "break_observer",
        ):
            raise ValueError("Unenrolled target or operation")
        if operation == "deploy_fault" and (not archive or not before_release or Path(archive).is_symlink()):
            raise ValueError("Exact artifact/current release required")
        digest = hashlib.file_digest(Path(archive).open("rb"), "sha256").hexdigest() if archive else None
        spec = {
            "id": uuid.uuid4().hex,
            "target": target,
            "operation": operation,
            "archive": str(Path(archive).resolve()) if archive else None,
            "artifact_sha256": digest,
            "before_release": before_release,
            "expires_at": self.clock() + 300,
        }
        with sqlite3.connect(self.path) as db:
            db.execute("INSERT INTO injections VALUES(?,?,?,NULL,0)", (spec["id"], owner, json.dumps(spec)))
        return spec

    def _load(self, db, owner, identifier):
        row = db.execute(
            "SELECT data,approval,claimed FROM injections WHERE id=? AND owner=?", (identifier, owner)
        ).fetchone()
        if not row:
            raise ValueError("Unknown owner/proposal")
        spec = json.loads(row[0])
        if spec["expires_at"] <= self.clock() or row[2]:
            raise ValueError("Expired/used injection")
        return spec, row[1]

    def approve(self, owner, identifier, exact_digest):
        with sqlite3.connect(self.path) as db:
            spec, _ = self._load(db, owner, identifier)
            if exact_digest != spec["artifact_sha256"]:
                raise ValueError("Artifact mismatch")
            approval = secrets.token_urlsafe(32)
            db.execute(
                "UPDATE injections SET approval=? WHERE id=?",
                (hashlib.sha256(approval.encode()).hexdigest(), identifier),
            )
            return approval

    def execute(self, owner, identifier, approval, writer):
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            spec, expected = self._load(db, owner, identifier)
            if not expected or not hmac.compare_digest(
                expected, hashlib.sha256(approval.encode()).hexdigest()
            ):
                raise ValueError("Exact approval required")
            if self.targets.get(spec["target"]["app_id"]) != spec["target"]:
                raise ValueError("Target changed")
            if spec["archive"]:
                path = Path(spec["archive"])
                if (
                    path.is_symlink()
                    or hashlib.file_digest(path.open("rb"), "sha256").hexdigest() != spec["artifact_sha256"]
                ):
                    raise ValueError("Artifact changed")
            db.execute("UPDATE injections SET claimed=1 WHERE id=?", (identifier,))
        # The narrow provider writer must recheck before_release and reconcile unknown outcomes.
        # Claim persists even on timeout; calling execute again never repeats a write.
        return writer(spec)
