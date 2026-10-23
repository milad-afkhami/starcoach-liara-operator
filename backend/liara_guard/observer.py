"""Persistent bounded watch and immutable evidence. Network calls never hold DB transactions."""

import hashlib
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from .contracts import RegisteredHttpCheck
from .redaction import redact
from .types import Evidence


def encode(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def invalidate_diagnosis(value, reason="stale_generation"):
    if value.get("diagnosis") is not None:
        value["superseded_diagnosis"] = value["diagnosis"]
    value["diagnosis"] = None
    value["investigation_state"] = "stale"
    value["investigation_error"] = reason


class MonitorStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS watches(id TEXT PRIMARY KEY,owner TEXT,state TEXT,ends REAL,next_tick REAL,data TEXT);
            CREATE TABLE IF NOT EXISTS incidents(id TEXT PRIMARY KEY,owner TEXT,scope TEXT,state TEXT,data TEXT);
            CREATE UNIQUE INDEX IF NOT EXISTS open_incident ON incidents(owner,scope) WHERE state='open';
            CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY,owner TEXT,data TEXT);
            CREATE TABLE IF NOT EXISTS incident_evidence(incident TEXT,evidence TEXT,PRIMARY KEY(incident,evidence));
            CREATE TABLE IF NOT EXISTS probe_ids(watch TEXT,request_id TEXT,PRIMARY KEY(watch,request_id));
            CREATE TABLE IF NOT EXISTS release_state(owner TEXT,target TEXT,release TEXT,PRIMARY KEY(owner,target));
            CREATE TABLE IF NOT EXISTS investigation_rejections(owner TEXT,incident TEXT,run TEXT,call INTEGER,data TEXT,UNIQUE(owner,incident,run,call));
            """)
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

    def watch(self, owner, identifier):
        with self.connect() as db:
            row = db.execute(
                "SELECT data,state FROM watches WHERE id=? AND owner=?", (identifier, owner)
            ).fetchone()
        if not row:
            raise KeyError("watch_not_found")
        value = json.loads(row["data"])
        value["state"] = row["state"]
        return value

    def incident(self, owner, identifier):
        with self.connect() as db:
            row = db.execute(
                "SELECT data FROM incidents WHERE id=? AND owner=?", (identifier, owner)
            ).fetchone()
        if not row:
            raise KeyError("incident_not_found")
        return json.loads(row["data"])

    def incidents(self, owner):
        with self.connect() as db:
            return [
                json.loads(r[0])
                for r in db.execute(
                    "SELECT data FROM incidents WHERE owner=? ORDER BY rowid DESC LIMIT 100", (owner,)
                )
            ]

    def record_rejected_draft(self, owner, incident_id, record):
        self.incident(owner, incident_id)
        safe = redact(record)
        encoded = encode(safe)
        if len(encoded.encode("utf-8")) > 8192:
            raise ValueError("Rejected diagnostic exceeds byte bound")
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO investigation_rejections VALUES(?,?,?,?,?)",
                       (owner, incident_id, safe["run_id"], safe["call"], encoded))
            db.execute("DELETE FROM investigation_rejections WHERE owner=? AND incident=? AND rowid NOT IN (SELECT rowid FROM investigation_rejections WHERE owner=? AND incident=? ORDER BY rowid DESC LIMIT 8)",
                       (owner, incident_id, owner, incident_id))

    def rejected_drafts(self, owner, incident_id):
        self.incident(owner, incident_id)
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute(
                "SELECT data FROM investigation_rejections WHERE owner=? AND incident=? ORDER BY rowid DESC LIMIT 8",
                (owner, incident_id))]

    def save_incident(self, value, expected_generation=None):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT data FROM incidents WHERE id=? AND owner=?", (value["id"], value["owner"])
            ).fetchone()
            if not row:
                raise KeyError("incident_not_found")
            if expected_generation is not None and json.loads(row[0])["generation"] != expected_generation:
                raise ValueError("stale_generation")
            current = json.loads(row[0])
            # A diagnosis can span unchanged polls; retain their newer sequence/state.
            for field in (
                "diagnosis",
                "investigation_state",
                "investigation_run_id",
                "investigation_error",
                "investigation_progress",
                "proposal",
                "execution",
                "verification",
                "repair_pending",
                "repair_operation_id",
            ):
                if field in value:
                    current[field] = value[field]
            db.execute("UPDATE incidents SET data=? WHERE id=?", (encode(current), value["id"]))

    def finish_investigation_error(self, owner, identifier, run_id, state, error):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT data FROM incidents WHERE id=? AND owner=?", (identifier, owner)
            ).fetchone()
            if not row:
                raise KeyError("incident_not_found")
            value = json.loads(row[0])
            if (run_id is not None and value.get("investigation_run_id") == run_id) or (
                run_id is None and value.get("investigation_state") in ("idle", "queued")
            ):
                value.update(investigation_state=state, investigation_error=error)
                db.execute("UPDATE incidents SET data=? WHERE id=?", (encode(value), identifier))

    def ensure_incident(
        self, owner, target, kind, scope, now, *, watch_id=None, fingerprint=None, question=None
    ):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute(
                "SELECT data FROM incidents WHERE owner=? AND scope=? AND state='open'", (owner, scope)
            ).fetchone()
            if old:
                value = json.loads(old[0])
                value["observation_sequence"] += 1
                if fingerprint and value["failure_fingerprint"] != fingerprint:
                    value["generation"] += 1
                    invalidate_diagnosis(value)
                    value["failure_fingerprint"] = fingerprint
            else:
                value = {
                    "id": uuid.uuid4().hex,
                    "owner": owner,
                    "target": target.model_dump(),
                    "kind": kind,
                    "watch_id": watch_id,
                    "generation": 1,
                    "observation_sequence": 1,
                    "opened_at": now,
                    "state": "open",
                    "failure_fingerprint": fingerprint,
                    "question": redact(question or ""),
                    "action_allowed": False,
                    "investigation_state": "idle",
                    "diagnosis": None,
                }
                db.execute(
                    "INSERT INTO incidents VALUES(?,?,?,?,?)",
                    (value["id"], owner, scope, "open", encode(value)),
                )
            db.execute("UPDATE incidents SET data=? WHERE id=?", (encode(value), value["id"]))
        return value

    def add_evidence(self, owner, incident_id, evidence, *, related_targets=()):
        incident = self.incident(owner, incident_id)
        allowed_ids = {
            incident["target"]["app_id"],
            *(target.app_id for target in related_targets if target.team_id == incident["target"]["team_id"]),
        }
        if (
            evidence.target.app_id not in allowed_ids
            or evidence.target.team_id != incident["target"]["team_id"]
        ):
            raise ValueError("Evidence target mismatch")
        safe_evidence = evidence.model_copy(update={"redacted_payload": redact(evidence.redacted_payload)})
        payload = encode(safe_evidence.model_dump())
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT owner,data FROM evidence WHERE id=?", (evidence.id,)).fetchone()
            if old and (old["owner"] != owner or old["data"] != payload):
                raise ValueError("Immutable evidence conflict")
            db.execute("INSERT OR IGNORE INTO evidence VALUES(?,?,?)", (evidence.id, owner, payload))
            db.execute("INSERT OR IGNORE INTO incident_evidence VALUES(?,?)", (incident_id, evidence.id))

    def evidence(self, owner, incident_id, *, cutoff):
        self.incident(owner, incident_id)
        with self.connect() as db:
            values = [
                json.loads(r[0])
                for r in db.execute(
                    "SELECT e.data FROM evidence e JOIN incident_evidence i ON i.evidence=e.id WHERE i.incident=? AND e.owner=? ORDER BY e.rowid",
                    (incident_id, owner),
                )
            ]
        projected = [v for v in values if v["available_at"] <= cutoff][-100:]
        for value in projected:
            original = value["quality"]
            if value["observed_at"] > cutoff + 5 or value["observed_at"] > value["available_at"] + 5:
                value["quality"] = "invalid"
            elif original == "fresh" and cutoff - value["observed_at"] > 300:
                value["quality"] = "stale"
            if value["quality"] != original:
                value["coverage"] = {
                    **value.get("coverage", {}),
                    "quality_at_collection": original,
                    "freshness_as_of": cutoff,
                }
        return projected


class Observer:
    def __init__(self, store, targets, *, clock=time.time):
        self.store, self.targets, self.clock = store, targets, clock

    def start_watch(self, owner, target_ids, checks):
        if (
            not 1 <= len(target_ids) <= 2
            or len(set(target_ids)) != len(target_ids)
            or any(t not in self.targets for t in target_ids)
            or len(checks) > 3
        ):
            raise ValueError("Watch scope exceeds limit")
        registered = []
        for check in checks:
            check = RegisteredHttpCheck.model_validate(check.model_dump())
            if check.target_id not in target_ids or self.targets[check.target_id].origin != check.origin:
                raise ValueError("Unregistered watch check")
            registered.append(check.model_dump())
        if len({c["id"] for c in registered}) != len(registered):
            raise ValueError("Duplicate check id")
        now = self.clock()
        value = {
            "id": uuid.uuid4().hex,
            "owner": owner,
            "targets": target_ids,
            "checks": registered,
            "started_at": now,
            "ends_at": now + 900,
            "state": "active",
            "samples": {},
            "probe_count": 0,
        }
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute(
                "SELECT 1 FROM watches WHERE owner=? AND state='active' AND ends>?", (owner, now)
            ).fetchone():
                raise ValueError("Watch already active")
            db.execute(
                "INSERT INTO watches VALUES(?,?,?,?,?,?)",
                (value["id"], owner, "active", now + 900, now, encode(value)),
            )
        return value

    def stop_watch(self, owner, identifier):
        self.store.watch(owner, identifier)
        with self.store.connect() as db:
            db.execute("UPDATE watches SET state='stopped' WHERE id=? AND owner=?", (identifier, owner))

    def tick(self, identifier, probe, *, provider=None):
        now = self.clock()
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM watches WHERE id=?", (identifier,)).fetchone()
            if not row or row["state"] != "active":
                return []
            if row["ends"] <= now:
                db.execute("UPDATE watches SET state='expired' WHERE id=?", (identifier,))
                return []
            if row["next_tick"] > now:
                return []
            db.execute("UPDATE watches SET next_tick=? WHERE id=?", (now + 15, identifier))
            watch = json.loads(row["data"])
        changes = []
        if provider and now >= watch.get("provider_due", now):
            with self.store.connect() as db:
                watch["provider_due"] = now + 60
                db.execute("UPDATE watches SET data=? WHERE id=?", (encode(watch), identifier))
            for target_id in watch["targets"]:
                current = self.store.watch(watch["owner"], identifier)
                if current["state"] != "active" or self.clock() >= current["ends_at"]:
                    break
                observations = provider(self.targets[target_id])
                current = self.store.watch(watch["owner"], identifier)
                if current["state"] != "active" or self.clock() >= current["ends_at"]:
                    break
                for evidence in observations:
                    incident = self.record_provider(
                        watch["owner"], self.targets[target_id], evidence, watch_id=identifier
                    )
                    if incident:
                        changes.append(incident)
        for raw in watch["checks"]:
            current = self.store.watch(watch["owner"], identifier)
            if current["state"] != "active" or self.clock() >= current["ends_at"]:
                break
            check = RegisteredHttpCheck.model_validate(raw)
            result = probe(check)  # No SQLite lock across network I/O.
            with self.store.connect() as db:
                db.execute("BEGIN IMMEDIATE")
                current = db.execute(
                    "SELECT state,ends,data FROM watches WHERE id=?", (identifier,)
                ).fetchone()
                if current["state"] != "active" or current["ends"] <= self.clock():
                    break
                watch = json.loads(current["data"])
                if watch["probe_count"] >= 180:
                    break
                if result.target_id != check.target_id or result.check_id != check.id:
                    raise ValueError("Probe target mismatch")
                try:
                    db.execute("INSERT INTO probe_ids VALUES(?,?)", (identifier, result.request_id))
                except sqlite3.IntegrityError:
                    continue
                if (
                    result.available_at > self.clock() + 5
                    or result.observed_at < now
                    or result.available_at < result.observed_at
                ):
                    continue
                sample = watch["samples"].get(check.id, {"failures": 0, "passes": 0})
                if result.observed_at <= sample.get("last", {}).get("observed_at", float("-inf")):
                    continue
                sample["failures"] = sample["failures"] + 1 if result.check_pass is False else 0
                sample["passes"] = sample["passes"] + 1 if result.check_pass is True else 0
                sample["last"] = result.model_dump()
                watch["samples"][check.id] = sample
                watch["probe_count"] += 1
                db.execute("UPDATE watches SET data=? WHERE id=?", (encode(watch), identifier))
            scope = f"http:{check.target_id}:{check.id}"
            if sample["failures"] >= 2:
                fingerprint = hashlib.sha256(
                    encode(
                        {
                            "check": raw,
                            "status": result.http_status,
                            "reason": result.reason,
                            "body_reason": result.payload.get("reason"),
                        }
                    ).encode()
                ).hexdigest()
                incident = self.store.ensure_incident(
                    watch["owner"],
                    self.targets[check.target_id],
                    "http_availability",
                    scope,
                    self.clock(),
                    watch_id=identifier,
                    fingerprint=fingerprint,
                )
                evidence = Evidence(
                    id=result.id,
                    target=self.targets[check.target_id],
                    kind="http_probe",
                    observed_at=result.observed_at,
                    available_at=result.available_at,
                    quality="fresh",
                    redacted_payload=result.model_dump(),
                    coverage={"failure_count": sample["failures"], "vantage": "operator"},
                )
                self.store.add_evidence(watch["owner"], incident["id"], evidence)
                changes.append(incident)
            elif sample["passes"] >= 3:
                with self.store.connect() as db:
                    db.execute("BEGIN IMMEDIATE")
                    row = db.execute(
                        "SELECT data FROM incidents WHERE owner=? AND scope=? AND state='open'",
                        (watch["owner"], scope),
                    ).fetchone()
                    if row:
                        value = json.loads(row[0])
                        if value.get("repair_pending"):
                            continue
                        value["generation"] += 1
                        invalidate_diagnosis(value)
                        value["state"] = "recovered"
                        value["recovered_at"] = self.clock()
                        db.execute(
                            "UPDATE incidents SET state='recovered',data=? WHERE id=?",
                            (encode(value), value["id"]),
                        )
                        changes.append(value)
        return changes

    def begin_investigation(self, owner, target, question):
        if self.targets.get(target.app_id) != target:
            raise ValueError("Unregistered target")
        return self.store.ensure_incident(
            owner, target, "log_investigation", "manual:" + uuid.uuid4().hex, self.clock(), question=question
        )

    def set_release(self, owner, target_id, release):
        if target_id not in self.targets:
            raise ValueError("Unregistered target")
        with self.store.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT release FROM release_state WHERE owner=? AND target=?", (owner, target_id)
            ).fetchone()
            if row and row[0] == release:
                return
            db.execute(
                "INSERT INTO release_state VALUES(?,?,?) ON CONFLICT(owner,target) DO UPDATE SET release=excluded.release",
                (owner, target_id, release),
            )
            for row in db.execute(
                "SELECT data FROM incidents WHERE owner=? AND state='open'", (owner,)
            ).fetchall():
                value = json.loads(row[0])
                if value["target"]["app_id"] == target_id:
                    value["generation"] += 1
                    invalidate_diagnosis(value)
                    value["current_release_id"] = release
                    db.execute("UPDATE incidents SET data=? WHERE id=?", (encode(value), value["id"]))

    def record_provider(self, owner, target, evidence, *, watch_id=None):
        if self.targets.get(target.app_id) != target or evidence.target != target:
            raise ValueError("Unregistered evidence target")
        if evidence.quality == "unavailable" and evidence.redacted_payload.get("error") == "observer_auth":
            incident = self.store.ensure_incident(
                owner,
                target,
                "observer_access",
                f"observer:{target.app_id}",
                self.clock(),
                watch_id=watch_id,
                fingerprint="observer_auth",
            )
            self.store.add_evidence(owner, incident["id"], evidence)
            return incident
        if evidence.quality == "fresh" and evidence.kind == "applets":
            states = [str(a.get("state", "unknown")) for a in evidence.redacted_payload.get("applets", [])]
            failures = sorted(
                state.lower()
                for state in states
                if state.lower() in {"failed", "unhealthy", "crashloopbackoff", "error"}
            )
            if failures:
                incident = self.store.ensure_incident(
                    owner,
                    target,
                    "runtime",
                    f"runtime:{target.app_id}",
                    self.clock(),
                    watch_id=watch_id,
                    fingerprint=encode(failures),
                )
                self.store.add_evidence(owner, incident["id"], evidence)
                return incident
        if evidence.quality == "fresh" and evidence.kind == "releases":
            current = evidence.redacted_payload.get("currentRelease")
            if isinstance(current, str):
                self.set_release(owner, target.app_id, current)
        return None
