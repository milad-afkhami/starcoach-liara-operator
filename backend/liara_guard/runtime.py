"""Owner-configured service scope and an explicitly labelled local provider fixture."""

import json
import time
import uuid
from pathlib import Path
from .client import ProviderError
from .contracts import RegisteredHttpCheck, unsafe_origin
from .redaction import redact
from .types import Target, ServiceSummary, Evidence
from .verification import VerificationPolicy


class Registry:
    def __init__(self, team_id, config, *, allow_loopback=False):
        self.team_id, self.config = team_id, config
        self.targets = {}
        self.services = {}
        self.checks = {}
        self.dependencies = config.get("dependencies", {})
        self.enrolled = config.get("enrolled", {})
        self.policies = {}
        for row in config.get("http_checks", []):
            check = RegisteredHttpCheck.model_validate(row)
            if unsafe_origin(check.origin, allow_loopback) or check.id in self.checks:
                raise ValueError("Invalid/duplicate configured check")
            self.checks[check.id] = check
        for key, value in config.get("verification_policies", {}).items():
            self.policies[key] = VerificationPolicy.model_validate(value)

    def refresh(self, services):
        targets = {}
        summaries = {}
        for service in services:
            if service.target.team_id != self.team_id or service.target.app_id in targets:
                raise ValueError("Wrong/duplicate provider identity")
            target = service.target
            checks = [c for c in self.checks.values() if c.target_id == target.app_id]
            if checks:
                origins = {c.origin for c in checks}
                if len(origins) != 1:
                    raise ValueError("Conflicting service origins")
                target = target.model_copy(update={"origin": next(iter(origins))})
            targets[target.app_id] = target
            summaries[target.app_id] = service.model_copy(update={"target": target})
        for target, dependencies in self.dependencies.items():
            if target not in targets or any(d not in targets for d in dependencies):
                raise ValueError("Unregistered dependency")
        self.targets.clear()
        self.targets.update(targets)
        self.services = summaries

    def resolve(self, identifier):
        if identifier not in self.targets:
            raise KeyError("service_not_found")
        return self.targets[identifier]

    def checks_for(self, identifier):
        return [c for c in self.checks.values() if c.target_id == identifier]

    def can_repair(self, identifier):
        actor = self.config.get("repair_targets", {}).get(identifier)
        entry = self.enrolled.get(actor, {})
        return bool(
            actor in self.targets
            and entry.get("baseline_verified") is True
            and entry.get("known_good")
            and identifier in self.policies
        )


class FixtureProvider:
    """Read-only source of local metadata. It cannot provision or mutate any Liara app."""

    mode = "fixture"
    team_id = "local-fixture"

    def __init__(self, directory, *, clock=time.time):
        self.directory = Path(directory)
        self.clock = clock

    def list_services(self):
        return [
            ServiceSummary(
                target=Target(team_id=self.team_id, app_name=name, app_id=identifier),
                platform="docker",
                runtime_state="Fixture metadata",
                observed_at=self.clock(),
                capabilities={"provider_fixture": True},
            )
            for identifier, name in [("local-store", "storefront"), ("local-dep", "delivery")]
        ]

    def _meta(self, target):
        if target.team_id != self.team_id or target.app_id not in ("local-store", "local-dep"):
            raise ProviderError("target_mismatch")
        try:
            return json.loads((self.directory / "releases.json").read_text()).get(target.app_id, {})
        except (OSError, ValueError):
            return {}

    def _evidence(self, target, kind, payload, quality="fresh", observed=None):
        return Evidence(
            id=uuid.uuid4().hex,
            target=target,
            kind=kind,
            observed_at=self.clock() if observed is None else observed,
            available_at=self.clock(),
            quality=quality,
            redacted_payload=redact(payload),
            coverage={"provider_fixture": True},
        )

    def get_project(self, target):
        meta = self._meta(target)
        return {
            "_id": target.app_id,
            "project_id": target.app_name,
            "type": "docker",
            "status": "Local metadata",
            "isDeployed": bool(meta),
            "provider_fixture": True,
        }

    def get_applets(self, target):
        meta = self._meta(target)
        return self._evidence(
            target,
            "applets",
            {
                "applets": [
                    {"id": "local-process", "state": "Running", "release": {"releaseID": meta["release_id"]}}
                ]
                if meta
                else []
            },
        )

    def get_releases(self, target):
        meta = self._meta(target)
        return self._evidence(
            target,
            "releases",
            {
                "currentRelease": meta.get("release_id"),
                "releases": [
                    {
                        "_id": meta["release_id"],
                        "state": "READY",
                        "createdAt": meta.get("at"),
                        "build_id": meta.get("build_id"),
                    }
                ]
                if meta
                else [],
            },
        )

    def get_events(self, target, start, end):
        return self._evidence(target, "events", {"events": []})

    def get_metrics(self, target):
        return self._evidence(
            target,
            "metrics",
            {"error": "fixture_has_no_provider_metrics", "unit": "unverified"},
            "unavailable",
        )

    def get_logs(self, target, since):
        self._meta(target)
        path = self.directory / (target.app_id + ".log")
        try:
            with path.open("rb") as source:
                source.seek(0, 2)
                size = source.tell()
                source.seek(max(0, size - 524288))
                data = source.read()
            lines = []
            for raw in data.splitlines():
                try:
                    value = json.loads(raw)
                except ValueError:
                    continue
                if value.get("at", 0) >= max(since, self.clock() - 300):
                    lines.append({"timestamp": value["at"], "message": redact(value.get("message", ""))})
            latest = max((r["timestamp"] for r in lines), default=self.clock())
            result = self._evidence(target, "logs", {"lines": lines[-500:]}, observed=latest)
            result.coverage.update(
                {
                    "empty": not lines,
                    "truncated": size > 524288 or len(lines) > 500,
                    "actual_local_stdout": True,
                }
            )
            return result
        except OSError:
            return self._evidence(target, "logs", {"error": "local_logs_unavailable"}, "unavailable")

    def close(self):
        pass


def local_config():
    return {
        "http_checks": [
            {
                "id": "store-preview",
                "target_id": "local-store",
                "origin": "http://127.0.0.1:8771",
                "path": "/preview",
                "require_request_echo": True,
            },
            {
                "id": "store-health",
                "target_id": "local-store",
                "origin": "http://127.0.0.1:8771",
                "path": "/healthz",
                "require_request_echo": True,
            },
            {
                "id": "dep-quote",
                "target_id": "local-dep",
                "origin": "http://127.0.0.1:8772",
                "path": "/quote",
                "require_request_echo": True,
            },
        ],
        "dependencies": {"local-store": ["local-dep"]},
    }
