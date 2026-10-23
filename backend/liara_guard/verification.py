"""Provider acceptance, serving identity and fresh symptom recovery are separate proofs."""

import hashlib
import json
import time
from pydantic import Field, model_validator
from .types import Record
from .contracts import RegisteredHttpCheck


class VerificationPolicy(Record):
    id: str
    checks: list[RegisteredHttpCheck] = Field(min_length=1, max_length=3)
    expected_build_fields: dict[str, dict[str, str]]
    expected_release_ids: dict[str, str]
    changed_target_id: str

    @model_validator(mode="after")
    def bound(self):
        if self.expected_release_ids.get(self.changed_target_id) != "$submitted":
            raise ValueError("Changed target must bind submitted release")
        if any(
            not c.require_request_echo
            or c.id not in self.expected_build_fields
            or "build_id" not in self.expected_build_fields[c.id]
            for c in self.checks
        ):
            raise ValueError("Fresh serving build proof required for every check")
        if len({c.id for c in self.checks}) != len(self.checks):
            raise ValueError("Duplicate check id")
        return self

    def digest(self):
        return hashlib.sha256(
            json.dumps(self.model_dump(), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()


def serving_readiness(policy, release_id, provider_status, *, clock=time.time, deadline):
    result = {"state": "waiting", "reason": "serving_identity_pending", "provider_identity": []}
    for target, expected in policy.expected_release_ids.items():
        if clock() >= deadline:
            return {**result, "state": "expired", "reason": "reconciliation_expired"}
        try:
            state = provider_status(target)
        except Exception:
            return result
        result["provider_identity"].append({"target_id": target, **state})
        if clock() >= deadline:
            return {**result, "state": "expired", "reason": "reconciliation_expired"}
        required = release_id if expected == "$submitted" else expected
        serving = state.get("serving_release_ids", [])
        if state.get("state") != "READY" or state.get("current_release_id") != required or not serving or set(serving) != {required}:
            return result
    return {**result, "state": "ready", "reason": "serving_identity_ready"}


def verify_recovery(
    policy,
    release_id,
    provider_status,
    probe,
    *,
    clock=time.time,
    sleep=time.sleep,
    current_policy_hash=None,
    cancel=None,
    deadline_utc=None,
):
    start = clock()
    deadline = min(start + 60, deadline_utc) if deadline_utc is not None else start + 60
    seen = set()
    probe_ids = []
    probe_results = []
    success_ids = []
    provider_identity = []
    round_times = []
    streak = 0
    count = 0
    last_round = None
    had_symptom_failure = False
    current_policy_hash = current_policy_hash or policy.digest

    def finish(state, reason):
        return {
            "state": state,
            "reason": reason,
            "probe_ids": probe_ids,
            "probe_results": probe_results,
            "verification_policy": policy.model_dump(),
            "success_probe_ids": success_ids,
            "round_times": round_times,
            "observed_window": [start, clock()],
            "policy_hash": policy.digest(),
            "submitted_release_id": release_id,
            "provider_identity": provider_identity,
        }

    while clock() <= deadline and count + len(policy.checks) <= 12:
        if cancel is not None and cancel.is_set():
            return finish("inconclusive", "canceled")
        if current_policy_hash() != policy.digest():
            return finish("inconclusive", "policy_changed")
        if last_round is not None:
            delay = max(0, 5 - (clock() - last_round))
            if clock() + delay > deadline:
                break
            sleep(delay)
        if clock() > deadline:
            break
        last_round = clock()
        round_times.append(last_round)
        provider_ok = True
        for target, expected in policy.expected_release_ids.items():
            required = release_id if expected == "$submitted" else expected
            try:
                state = provider_status(target)
                if clock() > deadline:
                    return finish("inconclusive", "verification_deadline")
                provider_identity.append({
                    "target_id": target, "checked_at": clock(),
                    "identity_source": state.get("identity_source"),
                    "coverage": state.get("identity_coverage", {}),
                    "current_release_id": state.get("current_release_id"),
                    "serving_release_ids": state.get("serving_release_ids", []),
                })
            except Exception:
                provider_ok = False
                break
            serving = state.get("serving_release_ids", [])
            if (
                state.get("state") != "READY"
                or state.get("current_release_id") != required
                or not serving
                or set(serving) != {required}
            ):
                provider_ok = False
                break
        round_ok = provider_ok
        # Bound attempts even when provider/serving identity never becomes trustworthy.
        if not provider_ok:
            count += len(policy.checks)
        else:
            for check in policy.checks:
                if clock() > deadline:
                    return finish("inconclusive", "verification_deadline")
                try:
                    result = probe(check)
                    probe_results.append(result.model_dump())
                    if clock() > deadline:
                        return finish("inconclusive", "verification_deadline")
                except Exception:
                    round_ok = False
                    count += 1
                    continue
                count += 1
                probe_ids.append(result.id)
                fresh = (
                    result.request_id not in seen
                    and result.observed_at >= start
                    and result.available_at >= result.observed_at
                    and result.available_at <= clock() + 1
                    and result.target_id == check.target_id
                    and result.check_id == check.id
                    and result.payload.get("request_id") == result.request_id
                )
                seen.add(result.request_id)
                matching = all(
                    result.payload.get(field) == value
                    for field, value in policy.expected_build_fields[check.id].items()
                )
                if result.check_pass is False:
                    had_symptom_failure = True
                if not fresh or result.check_pass is not True or not matching:
                    round_ok = False
                else:
                    success_ids.append(result.id)
        last_round = clock()
        if current_policy_hash() != policy.digest():
            return finish("inconclusive", "policy_changed")
        streak = streak + 1 if round_ok else 0
        if streak == 3:
            return finish("recovered", "original_checks_and_serving_build_verified")
    return finish(
        "failed" if had_symptom_failure else "inconclusive",
        "original_symptom_persists" if had_symptom_failure else "insufficient_fresh_identity_proof",
    )


def bind_verification(operation, incident, policy, result):
    """The approved operation may change release generation; its policy/association may not change."""
    if policy.digest() != operation["spec"]["verification_policy_hash"]:
        return {**result, "state": "inconclusive", "reason": "approved_policy_changed"}
    if incident.get("repair_operation_id") != operation["id"]:
        return {**result, "state": "inconclusive", "reason": "incident_operation_changed"}
    return result
