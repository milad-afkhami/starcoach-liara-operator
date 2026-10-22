"""Narrow live Liara binding. Existing unregistered services remain read-only."""

import hashlib
import json
from .approvals import ApprovalError
from .bootstrap import quote_for
from .client import ProviderError


def failure_fingerprint(check, result):
    value = {
        "check": check.model_dump(),
        "status": result.http_status,
        "reason": result.reason,
        "body_reason": result.payload.get("reason"),
    }
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


class LiaraOperationProvider:
    def __init__(self, client, registry, monitor, probes, owner):
        self.client, self.registry, self.monitor, self.probes, self.owner = (
            client,
            registry,
            monitor,
            probes,
            owner,
        )

    def inspect(self, spec):
        if spec.team_id != self.registry.team_id:
            raise ApprovalError("Wrong team")
        if spec.kind == "create_app":
            try:
                self.client._read(f"/v1/projects/{spec.app_name}")
                exists = True
            except ProviderError as exc:
                if exc.code != "not_found":
                    raise
                exists = False
            quote = quote_for(self.client.plan_catalogue(), spec.plan_id, spec.bundle_plan_id)
            if spec.network_id not in {n["id"] for n in self.client.list_networks()}:
                raise ApprovalError("Approved network unavailable")
            return {
                "exists": exists,
                "plan_id": spec.plan_id,
                "bundle_plan_id": spec.bundle_plan_id,
                "network_id": spec.network_id,
                "hourly_price_toman": quote.get("hourly_price_toman"),
            }
        target = self.registry.resolve(spec.app_id)
        project = self.client.get_project(target)
        releases = self.client.get_releases(target)
        if releases.quality != "fresh":
            raise ApprovalError("Release evidence unavailable")
        result = {
            "exists": True,
            "app_id": project["_id"],
            "release_id": releases.redacted_payload.get("currentRelease"),
        }
        if spec.kind == "redeploy_known_good":
            incident = self.monitor.incident(self.owner, spec.incident_id)
            root = incident["target"]["app_id"]
            policy = self.registry.policies.get(root)
            if not policy or not self.registry.can_repair(root) or policy.changed_target_id != target.app_id:
                raise ApprovalError("Repair capability unavailable")
            symptom = self.probes.run(policy.checks[0])
            discriminator = self.registry.config.get("repair_discriminators", {}).get(root, {})
            check = self.registry.checks.get(discriminator.get("check_id"))
            supported = False
            if check and check.target_id == target.app_id:
                probe = self.probes.run(check)
                field = discriminator.get("required_integer_field")
                supported = bool(
                    probe.check_pass is True
                    and field
                    and (type(probe.payload.get(field)) is not int or probe.payload[field] < 0)
                )
            result.update(
                incident_generation=incident["generation"],
                failure_fingerprint=failure_fingerprint(policy.checks[0], symptom),
                verification_policy_hash=policy.digest(),
                discriminating_condition=symptom.check_pass is False
                and supported
                and incident["state"] == "open",
            )
        return result

    def upload_source(self, spec, content):
        return self.client.upload_source(spec, content)

    def create_release(self, spec, source):
        return self.client.create_release(spec, source)

    def create_project(self, spec):
        return self.client.create_project(spec)

    def release_candidates(self, spec, source):
        evidence = self.client.get_releases(self.registry.resolve(spec.app_id))
        if evidence.quality != "fresh":
            return []
        return [
            {"id": r.get("_id"), "source_id": r.get("sourceID")}
            for r in evidence.redacted_payload.get("releases", [])
            if r.get("sourceID") == source
        ]

    def release_status(self, spec, release_id):
        evidence = self.client.get_releases(self.registry.resolve(spec.app_id))
        if evidence.quality != "fresh":
            return {"state": "unknown"}
        row = next(
            (r for r in evidence.redacted_payload.get("releases", []) if r.get("_id") == release_id), {}
        )
        return {
            "state": row.get("state", "unknown"),
            "current_release_id": evidence.redacted_payload.get("currentRelease"),
        }

    def status_for_policy(self, target_id):
        target = self.registry.resolve(target_id)
        releases = self.client.get_releases(target)
        applets = self.client.get_applets(target)
        if releases.quality != "fresh" or applets.quality != "fresh":
            return {"state": "unknown"}
        current = releases.redacted_payload.get("currentRelease")
        row = next((r for r in releases.redacted_payload.get("releases", []) if r.get("_id") == current), {})
        active = [
            a
            for a in applets.redacted_payload.get("applets", [])
            if str(a.get("state", "")).lower() == "running"
        ]
        ids = [a.get("release", {}).get("releaseID") for a in active]
        return {
            "state": row.get("state", "unknown"),
            "current_release_id": current,
            "serving_release_ids": ids,
        }
