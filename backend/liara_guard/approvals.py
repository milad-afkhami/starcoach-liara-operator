"""Exact, expiring owner approvals and durable write intents. No blind mutation retries."""

import hashlib
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from pydantic import Field, model_validator
from .types import Record


class ApprovalError(ValueError):
    pass


class AmbiguousWrite(RuntimeError):
    pass


class RejectedWrite(RuntimeError):
    pass


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


class OperationSpec(Record):
    kind: Literal["create_app", "deploy_initial", "redeploy_known_good"]
    team_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    app_name: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{0,62}$")
    app_id: str | None = None
    artifact_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    platform: Literal["docker"] = "docker"
    port: int = Field(default=8000, ge=1, le=65535)
    plan_id: str | None = None
    bundle_plan_id: str | None = None
    network_id: str | None = None
    hourly_price_toman: str | None = Field(default=None, pattern=r"^[0-9]+$")
    price_verified_at: float | None = None
    before_release_id: str | None = None
    incident_id: str | None = None
    incident_generation: int | None = Field(default=None, ge=1)
    failure_fingerprint: str | None = None
    verification_policy_hash: str | None = None

    @model_validator(mode="after")
    def complete(self):
        if self.kind == "create_app":
            if (
                self.app_id
                or self.artifact_sha256
                or not self.plan_id
                or not self.bundle_plan_id
                or not self.network_id
                or self.hourly_price_toman is None
                or self.price_verified_at is None
            ):
                raise ValueError("Exact current plan/price and new name required")
        elif not self.app_id or not self.artifact_sha256:
            raise ValueError("Registered target/artifact required")
        if self.kind == "redeploy_known_good" and any(
            v is None
            for v in [
                self.before_release_id,
                self.incident_id,
                self.incident_generation,
                self.failure_fingerprint,
                self.verification_policy_hash,
            ]
        ):
            raise ValueError("Exact incident/before-state/policy required")
        return self


class OperationStore:
    def __init__(self, path, *, clock=time.time):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.clock = clock
        with self.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS operations(id TEXT PRIMARY KEY,owner TEXT,target TEXT,state TEXT,data TEXT)"
            )
            for row in db.execute(
                "SELECT id,data FROM operations WHERE state IN ('checking','uploading','creating_release','creating_app')"
            ).fetchall():
                value = json.loads(row["data"])
                value["state"] = "unknown" if row["data"] else "failed"
                value["error"] = "interrupted_intent"
                db.execute(
                    "UPDATE operations SET state='unknown',data=? WHERE id=?", (encode(value), row["id"])
                )
            for row in db.execute("SELECT id,data FROM operations WHERE state='verifying'").fetchall():
                value = json.loads(row["data"])
                value.update(
                    state="failed",
                    error="verification_interrupted",
                    verification={
                        "state": "inconclusive",
                        "reason": "verification_interrupted",
                        "probe_ids": [],
                    },
                )
                db.execute(
                    "UPDATE operations SET state='failed',data=? WHERE id=?", (encode(value), row["id"])
                )
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def propose(self, owner, spec):
        spec = OperationSpec.model_validate(spec.model_dump())
        now = self.clock()
        if spec.kind == "create_app" and not now - 300 <= spec.price_verified_at <= now:
            raise ApprovalError("Current quote required")
        value = {
            "id": uuid.uuid4().hex,
            "owner": owner,
            "spec": spec.model_dump(),
            "digest": hashlib.sha256(encode(spec.model_dump()).encode()).hexdigest(),
            "created_at": now,
            "expires_at": min(now + 300, spec.price_verified_at + 300)
            if spec.kind == "create_app"
            else now + 300,
            "state": "proposed",
            "approved_at": None,
            "source_id": None,
            "release_id": None,
            "submitted_at": None,
            "reconcile_until": None,
            "last_reconciled": None,
            "error": None,
        }
        with self.connect() as db:
            db.execute(
                "INSERT INTO operations VALUES(?,?,?,?,?)",
                (value["id"], owner, f"{spec.team_id}:{spec.app_name}", "proposed", encode(value)),
            )
        return value

    def get(self, owner, identifier):
        with self.connect() as db:
            row = db.execute(
                "SELECT data FROM operations WHERE id=? AND owner=?", (identifier, owner)
            ).fetchone()
        if not row:
            raise ApprovalError("Operation unavailable")
        return json.loads(row[0])

    def approve(self, owner, identifier, digest):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT data FROM operations WHERE id=? AND owner=?", (identifier, owner)
            ).fetchone()
            if not row:
                raise ApprovalError("Operation unavailable")
            value = json.loads(row[0])
            if (
                value["state"] != "proposed"
                or value["expires_at"] <= self.clock()
                or value["digest"] != digest
            ):
                raise ApprovalError("Exact unexpired proposal required")
            value.update(state="approved", approved_at=self.clock())
            db.execute(
                "UPDATE operations SET state='approved',data=? WHERE id=?", (encode(value), identifier)
            )
        return value

    def claim(self, owner, identifier):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT * FROM operations WHERE id=? AND owner=?", (identifier, owner)
            ).fetchone()
            if not row:
                raise ApprovalError("Operation unavailable")
            value = json.loads(row["data"])
            if value["state"] != "approved" or value["expires_at"] <= self.clock():
                raise ApprovalError("Unexpired unused approval required")
            if db.execute(
                "SELECT 1 FROM operations WHERE target=? AND id!=? AND state IN ('checking','uploading','creating_release','creating_app','pending','ready','verifying','unknown')",
                (row["target"], identifier),
            ).fetchone():
                raise ApprovalError("Target has unresolved operation")
            value["state"] = "checking"
            db.execute(
                "UPDATE operations SET state='checking',data=? WHERE id=?", (encode(value), identifier)
            )
        return value

    def update(self, value, **changes):
        value = {**value, **changes}
        with self.connect() as db:
            db.execute(
                "UPDATE operations SET state=?,data=? WHERE id=? AND owner=?",
                (value["state"], encode(value), value["id"], value["owner"]),
            )
        return value


class Executor:
    def __init__(self, store, provider, enrolled, *, clock=time.time, allowed_new_names=()):
        self.store, self.provider, self.enrolled, self.clock = store, provider, enrolled, clock
        self.allowed_new_names = set(allowed_new_names)

    def execute(self, owner, identifier):
        value = self.store.claim(owner, identifier)
        spec = OperationSpec.model_validate(value["spec"])
        try:
            if spec.kind == "create_app":
                if spec.app_name not in self.allowed_new_names:
                    raise ApprovalError("New name not enrolled")
            else:
                enrollment = self.enrolled.get(spec.app_id, {})
                if enrollment.get("team_id") != spec.team_id or enrollment.get("app_name") != spec.app_name:
                    raise ApprovalError("Target changed")
                sources = enrollment.get(
                    "known_good" if spec.kind == "redeploy_known_good" else "approved_sources", {}
                )
                path = Path(sources.get(spec.artifact_sha256, ""))
                if path.is_symlink() or not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
                    raise ApprovalError("Artifact changed/not enrolled")
                content = path.read_bytes()
                if hashlib.sha256(content).hexdigest() != spec.artifact_sha256:
                    raise ApprovalError("Artifact changed/not enrolled")
            before = self.provider.inspect(spec)
            if spec.kind == "create_app":
                if (
                    before.get("exists")
                    or before.get("plan_id") != spec.plan_id
                    or before.get("bundle_plan_id") != spec.bundle_plan_id
                    or before.get("network_id") != spec.network_id
                    or str(before.get("hourly_price_toman")) != spec.hourly_price_toman
                ):
                    raise ApprovalError("Name collision or quote changed/unverified")
            else:
                if before.get("app_id") != spec.app_id or before.get("release_id") != spec.before_release_id:
                    raise ApprovalError("Before-state changed")
                if spec.kind == "redeploy_known_good":
                    for key in ["incident_generation", "failure_fingerprint", "verification_policy_hash"]:
                        if before.get(key) != getattr(spec, key):
                            raise ApprovalError("Incident/policy changed")
                    if before.get("discriminating_condition") is not True:
                        raise ApprovalError("Current discriminating evidence required")
            if value["expires_at"] <= self.clock():
                raise ApprovalError("Approval expired during checking")
        except Exception as exc:
            self.store.update(value, state="failed", error="preflight_rejected")
            if isinstance(exc, ApprovalError):
                raise
            raise ApprovalError("Preflight unavailable") from exc
        try:
            now = self.clock()
            value = self.store.update(
                value,
                state="creating_app" if spec.kind == "create_app" else "uploading",
                submitted_at=now,
                reconcile_until=now + 600,
            )
            if spec.kind == "create_app":
                app_id = self.provider.create_project(spec)
                return self.store.update(value, state="completed", created_app_id=app_id)
            source = self.provider.upload_source(spec, content)
            if not isinstance(source, str) or not source:
                raise AmbiguousWrite("source_identity_unknown")
            value = self.store.update(value, source_id=source)
            if self.clock() >= value["expires_at"]:
                return self.store.update(value, state="failed", error="approval_expired_before_release")
            value = self.store.update(value, state="creating_release")
            release = self.provider.create_release(spec, source)
            if not isinstance(release, str) or not release:
                raise AmbiguousWrite("release_identity_unknown")
            return self.store.update(value, state="pending", release_id=release)
        except RejectedWrite:
            return self.store.update(value, state="failed", error="provider_rejected")
        except Exception:
            return self.store.update(value, state="unknown", error="ambiguous_write")

    def reconcile(self, owner, identifier):
        value = self.store.get(owner, identifier)
        if value["state"] not in ("unknown", "pending"):
            return value
        now = self.clock()
        if value["reconcile_until"] is None or now > value["reconcile_until"]:
            return self.store.update(value, state="unknown", error="reconciliation_expired")
        if value["last_reconciled"] is not None and now - value["last_reconciled"] < 10:
            return value
        value = self.store.update(value, last_reconciled=now)
        if not value["source_id"]:
            return value
        spec = OperationSpec.model_validate(value["spec"])
        try:
            if not value["release_id"]:
                matches = self.provider.release_candidates(spec, value["source_id"])
                matches = [
                    r
                    for r in matches
                    if r.get("source_id") == value["source_id"] and isinstance(r.get("id"), str)
                ]
                if len(matches) == 1:
                    value = self.store.update(value, state="pending", release_id=matches[0]["id"], error=None)
            elif hasattr(self.provider, "release_status"):
                status = self.provider.release_status(spec, value["release_id"])
                if status.get("state") in ("FAILED", "UNHEALTHY"):
                    value = self.store.update(value, state="failed", error="release_failed")
                elif (
                    status.get("state") == "READY" and status.get("current_release_id") == value["release_id"]
                ):
                    value = self.store.update(value, state="ready", error=None)
        except Exception:
            return value
        return value
