"""Documented Liara reads with explicit team scope; no generic write retry path."""

import json
import time
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation
import httpx
from .redaction import redact
from .types import Evidence, ServiceSummary, Target


class ProviderError(Exception):
    def __init__(self, code, status=None):
        self.code, self.status = code, status
        super().__init__(code)


def decode_logs(payload, version):
    lines = []
    try:
        if version == "v1":
            if not isinstance(payload, list):
                raise ValueError()
            for item in payload:
                if not all(isinstance(item.get(k), str) for k in ("datetime", "type", "message")):
                    raise ValueError()
                lines.append(
                    {
                        "timestamp": item["datetime"],
                        "release_id": None,
                        "type": item["type"],
                        "message": redact(item["message"]),
                    }
                )
        elif version == "v2":
            if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
                raise ValueError()
            for group in payload["data"]:
                release = group["metaData"]["releaseId"]
                if not isinstance(release, str) or not isinstance(group["values"], list):
                    raise ValueError()
                for pair in group["values"]:
                    if (
                        not isinstance(pair, list)
                        or len(pair) != 2
                        or not all(isinstance(v, str) for v in pair)
                    ):
                        raise ValueError()
                    stamp, text = pair
                    if not stamp.isdigit():
                        raise ValueError()
                    entry = json.loads(text)
                    if not isinstance(entry, dict) or not isinstance(entry.get("_entry"), str):
                        raise ValueError()
                    lines.append(
                        {
                            "timestamp": stamp,
                            "release_id": release,
                            "type": str(entry.get("type", "unknown")),
                            "message": redact(entry["_entry"]),
                        }
                    )
        else:
            raise ValueError()
    except (KeyError, TypeError, ValueError) as exc:
        raise ProviderError("invalid_log_schema") from exc
    return sorted(lines, key=lambda line: timestamp(line["timestamp"]))


def timestamp(value):
    try:
        if value.isdigit():
            return float(Decimal(value) / Decimal(1_000_000_000))
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("Timezone required")
        return parsed.timestamp()
    except (AttributeError, ValueError, InvalidOperation) as exc:
        raise ProviderError("invalid_timestamp") from exc


class LiaraClient:
    def __init__(
        self, token, team_id, *, transport=None, clock=time.time, sleep=time.sleep, log_version="v2"
    ):
        if not token or not team_id:
            raise ValueError("Liara token and explicit team are required")
        self.team_id = Target(team_id=team_id, app_name="scope", app_id="scope").team_id
        if log_version not in ("v1", "v2"):
            raise ValueError("Explicit log version required")
        self.token, self.clock, self.sleep, self.log_version = token, clock, sleep, log_version
        self.http = httpx.Client(
            base_url="https://api.liara.ir",
            headers={"Authorization": "Bearer " + token},
            transport=transport,
            timeout=5,
            follow_redirects=False,
        )
        self.known = {}

    def close(self):
        self.http.close()

    def _read(self, path, params=None):
        parameters = {**(params or {}), "teamID": self.team_id}
        deadline = time.monotonic() + 10
        for attempt in range(2):
            try:
                with self.http.stream("GET", path, params=parameters) as response:
                    status = response.status_code
                    if status in (429, 500, 502, 503, 504) and attempt == 0:
                        self.sleep(0.2)
                        continue
                    if status != 200:
                        code = (
                            "observer_auth"
                            if status in (401, 403)
                            else "not_found"
                            if status == 404
                            else "rate_limited"
                            if status == 429
                            else "provider_error"
                        )
                        raise ProviderError(code, status)
                    data = bytearray()
                    for chunk in response.iter_bytes():
                        if time.monotonic() > deadline:
                            raise ProviderError("read_budget_exceeded")
                        data.extend(chunk)
                        if len(data) > 524288:
                            raise ProviderError("response_too_large")
                    try:
                        return json.loads(
                            data, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value))
                        )
                    except (ValueError, UnicodeError) as exc:
                        raise ProviderError("invalid_json") from exc
            except httpx.TransportError as exc:
                if attempt == 0:
                    self.sleep(0.2)
                    continue
                raise ProviderError("observer_network") from exc
        raise ProviderError("provider_error")

    def plan_catalogue(self):
        payload = self._read("/v1/me")
        plans = payload.get("plans") if isinstance(payload, dict) else None
        if not isinstance(plans, dict) or not all(
            isinstance(plans.get(k), dict) for k in ("projects", "projectBundlePlans")
        ):
            raise ProviderError("invalid_plan_catalogue")
        return {k: plans[k] for k in ("projects", "projectBundlePlans")}

    def list_networks(self):
        payload = self._read("/v1/networks")
        rows = payload.get("networks") if isinstance(payload, dict) else None
        if not isinstance(rows, list) or any(
            not isinstance(r, dict) or not isinstance(r.get("_id"), str) or not isinstance(r.get("name"), str)
            for r in rows
        ):
            raise ProviderError("invalid_networks")
        return [{"id": r["_id"], "name": r["name"]} for r in rows]

    def _target(self, target):
        # Revalidate even model_copy/test-created values before composing a path.
        try:
            target = Target.model_validate(target.model_dump())
        except ValueError as exc:
            raise ProviderError("target_mismatch") from exc
        if target.team_id != self.team_id or (
            target.app_name in self.known and self.known[target.app_name] != target.app_id
        ):
            raise ProviderError("target_mismatch")
        return target

    def _project(self, p):
        if not isinstance(p, dict) or p.get("teamID", self.team_id) != self.team_id:
            raise ProviderError("target_mismatch")
        try:
            if not isinstance(p["_id"], str) or not isinstance(p["project_id"], str):
                raise ValueError()
            t = Target(team_id=self.team_id, app_name=p["project_id"], app_id=p["_id"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ProviderError("invalid_project") from exc
        return t

    def list_services(self):
        payload = self._read("/v1/projects")
        if not isinstance(payload, dict) or not isinstance(payload.get("projects"), list):
            raise ProviderError("invalid_inventory")
        services = []
        for p in payload["projects"][:200]:
            target = self._project(p)
            services.append(
                ServiceSummary(
                    target=target,
                    platform=str(p.get("type", "unknown")),
                    runtime_state=str(p.get("status", "unknown")),
                    observed_at=self.clock(),
                    capabilities={
                        "provider_reads": True,
                        "http_check_configured": False,
                        "log_schema": self.log_version,
                        "live_schema_verified": False,
                    },
                )
            )
        self.known = {s.target.app_name: s.target.app_id for s in services}
        return services

    def get_project(self, target):
        target = self._target(target)
        payload = self._read(f"/v1/projects/{target.app_name}")
        if not isinstance(payload, dict) or not isinstance(payload.get("project"), dict):
            raise ProviderError("invalid_project")
        p = payload["project"]
        found = self._project(p)
        if found.app_id != target.app_id or found.app_name != target.app_name:
            raise ProviderError("target_mismatch")
        self.known[target.app_name] = target.app_id
        return {
            k: redact(p[k], (self.token,))
            for k in (
                "_id",
                "project_id",
                "type",
                "status",
                "scale",
                "planID",
                "hourlyPrice",
                "isDeployed",
                "created_at",
            )
            if k in p
        }

    def _evidence(self, target, kind, payload, quality="fresh", coverage=None, observed_at=None):
        return Evidence(
            id=uuid.uuid4().hex,
            target=target,
            kind=kind,
            observed_at=self.clock() if observed_at is None else observed_at,
            available_at=self.clock(),
            quality=quality,
            redacted_payload=redact(payload, (self.token,)),
            coverage=coverage or {},
        )

    def _failure(self, target, kind, exc):
        return self._evidence(
            target,
            kind,
            {"error": exc.code, "http_status": exc.status},
            quality="unavailable",
            coverage={"observed_service_health": False},
        )

    def get_logs(self, target, since):
        target = self._target(target)
        now = self.clock()
        params = (
            {"start": int(max(since, now - 300)), "direction": "forward", "last_lines": 500}
            if self.log_version == "v2"
            else {"since": int(max(since, now - 300))}
        )
        try:
            lines = decode_logs(
                self._read(f"/{self.log_version}/projects/{target.app_name}/logs", params), self.log_version
            )
            truncated = len(lines) > 500
            lines = lines[-500:]
            latest = max((timestamp(x["timestamp"]) for x in lines), default=now)
            quality = "invalid" if latest > now + 5 else "stale" if latest < now - 300 else "fresh"
            return self._evidence(
                target,
                "logs",
                {"lines": lines, "schema": self.log_version},
                quality,
                {"truncated": truncated, "empty": not lines, "window_start": max(since, now - 300)},
                observed_at=latest,
            )
        except ProviderError as exc:
            return self._failure(target, "logs", exc)

    def get_metrics(self, target):
        target = self._target(target)
        try:
            payload = self._read(f"/v1/projects/{target.app_name}/metrics/summary")
            if not isinstance(payload, dict) or not payload:
                raise ProviderError("metrics_unavailable")
            return self._evidence(
                target,
                "metrics",
                {"unit": "unverified", "provider_data": payload},
                coverage={"unit_verified": False, "threshold_evaluated": False},
            )
        except ProviderError as exc:
            return self._failure(target, "metrics", exc)

    def get_events(self, target, start, end):
        target = self._target(target)
        now = self.clock()
        return self._collection(target, "events", {"start": max(now - 300, start), "end": min(now, end)})

    def get_applets(self, target):
        return self._collection(self._target(target), "applets")

    def get_releases(self, target):
        return self._collection(self._target(target), "releases", {"page": 1, "count": 10})

    def _collection(self, target, kind, params=None):
        try:
            payload = self._read(f"/v1/projects/{target.app_name}/{kind}", params)
            if not isinstance(payload, dict) or not isinstance(payload.get(kind), list):
                raise ProviderError("invalid_" + kind)
            # Only diagnostic fields, never provider environment/node/author data.
            fields = {
                "_id",
                "id",
                "name",
                "state",
                "status",
                "reason",
                "message",
                "timestamp",
                "createdAt",
                "finishedAt",
                "releaseId",
                "releaseID",
                "sourceID",
                "release",
                "tag",
                "type",
            }
            rows = []
            for row in payload[kind][:100]:
                if not isinstance(row, dict):
                    raise ProviderError("invalid_" + kind)
                rows.append({k: redact(v, (self.token,)) for k, v in row.items() if k in fields})
            safe = {kind: rows}
            if kind == "releases":
                safe["currentRelease"] = redact(payload.get("currentRelease"), (self.token,))
            return self._evidence(
                target, kind, safe, coverage={"truncated": len(payload[kind]) > 100, "empty": not rows}
            )
        except ProviderError as exc:
            return self._failure(target, kind, exc)

    def _write(self, spec, path, **kwargs):
        from .approvals import OperationSpec, AmbiguousWrite, RejectedWrite

        spec = OperationSpec.model_validate(spec.model_dump())
        if spec.team_id != self.team_id:
            raise ValueError("Wrong team")
        try:
            with self.http.stream("POST", path, params={"teamID": self.team_id}, **kwargs) as response:
                if response.status_code in (400, 401, 403, 404, 409, 422, 429):
                    raise RejectedWrite("provider_rejected")
                if not 200 <= response.status_code < 300:
                    raise AmbiguousWrite("provider_outcome_unknown")
                raw = bytearray()
                deadline = time.monotonic() + 10
                for chunk in response.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 524288 or time.monotonic() > deadline:
                        raise AmbiguousWrite("response_unavailable")
                if not raw:
                    return {}
                try:
                    value = json.loads(
                        raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value))
                    )
                except (ValueError, UnicodeError) as exc:
                    raise AmbiguousWrite("invalid_response") from exc
                if not isinstance(value, dict):
                    raise AmbiguousWrite("invalid_response")
                return value
        except httpx.TransportError as exc:
            raise AmbiguousWrite("transport_outcome_unknown") from exc

    def upload_source(self, spec, content):
        from .approvals import AmbiguousWrite

        if not isinstance(content, bytes) or not 0 < len(content) <= 5 * 1024 * 1024:
            raise ValueError("Bounded approved source bytes required")
        data = self._write(
            spec,
            f"/v2/projects/{spec.app_name}/sources",
            files={"file": ("source.tar.gz", content, "application/gzip")},
        )
        if not isinstance(data.get("sourceID"), str) or not data["sourceID"]:
            raise AmbiguousWrite("source_identity_unknown")
        return data["sourceID"]

    def create_release(self, spec, source_id):
        from .approvals import AmbiguousWrite

        if not isinstance(source_id, str) or not source_id or len(source_id) > 200:
            raise ValueError("Known source identity required")
        data = self._write(
            spec,
            f"/v2/projects/{spec.app_name}/releases",
            json={"sourceID": source_id, "port": spec.port, "type": spec.platform},
        )
        if not isinstance(data.get("releaseID"), str) or not data["releaseID"]:
            raise AmbiguousWrite("release_identity_unknown")
        return data["releaseID"]

    def create_project(self, spec):
        from .approvals import AmbiguousWrite

        if spec.kind != "create_app":
            raise ValueError("Bootstrap create spec required")
        self._write(
            spec,
            "/v1/projects",
            json={
                "name": spec.app_name,
                "planID": spec.plan_id,
                "bundlePlanID": spec.bundle_plan_id,
                "network": spec.network_id,
                "platform": spec.platform,
                "readOnlyRootFilesystem": False,
            },
        )
        try:
            target = self._project(self._read(f"/v1/projects/{spec.app_name}")["project"])
            if target.app_name != spec.app_name:
                raise ValueError("Identity mismatch")
        except (ProviderError, KeyError, ValueError) as exc:
            raise AmbiguousWrite("created_identity_unknown") from exc
        return target.app_id
