import pytest
from liara_guard.verification import VerificationPolicy, verify_recovery
from liara_guard.contracts import RegisteredHttpCheck, ProbeResult


def policy():
    check = RegisteredHttpCheck(
        id="preview",
        target_id="store",
        origin="https://store.liara.run",
        path="/preview",
        require_request_echo=True,
    )
    return VerificationPolicy(
        id="policy",
        checks=[check],
        expected_build_fields={"preview": {"build_id": "store-build", "dependency_build_id": "good-dep"}},
        expected_release_ids={"store": "r-store", "dep": "$submitted"},
        changed_target_id="dep",
    )


def setup(status=200, payload=None):
    now = [100.0]
    calls = []

    def provider(target):
        return {
            "state": "READY",
            "current_release_id": "r2" if target == "dep" else "r-store",
            "serving_release_ids": ["r2" if target == "dep" else "r-store"],
        }

    def probe(check):
        calls.append(now[0])
        identifier = f"p{len(calls)}"
        return ProbeResult(
            id=identifier,
            target_id="store",
            check_id="preview",
            request_id=identifier,
            observed_at=now[0],
            available_at=now[0],
            http_status=status,
            elapsed_ms=10,
            check_pass=status == 200,
            reason="pass" if status == 200 else "unexpected_status",
            body_digest="x",
            payload=payload
            if payload is not None
            else {"build_id": "store-build", "dependency_build_id": "good-dep", "request_id": identifier},
        )

    return now, calls, provider, probe


def test_three_fresh_successes_five_seconds_apart_and_serving_release_required():
    now, calls, provider, probe = setup()
    result = verify_recovery(
        policy(), "r2", provider, probe, clock=lambda: now[0], sleep=lambda n: now.__setitem__(0, now[0] + n)
    )
    assert result["state"] == "recovered" and calls == [100, 105, 110] and len(result["probe_ids"]) == 3


def test_provider_ready_with_original_endpoint_broken_is_failed():
    now, calls, provider, probe = setup(502)
    result = verify_recovery(
        policy(), "r2", provider, probe, clock=lambda: now[0], sleep=lambda n: now.__setitem__(0, now[0] + n)
    )
    assert result["state"] == "failed" and len(calls) <= 12 and now[0] <= 160


@pytest.mark.parametrize(
    "case", ["old_instance", "mixed_rollout", "wrong_build", "replayed", "pre_change", "policy_changed"]
)
def test_inconclusive_or_stale_proof_never_claims_recovery(case):
    now, calls, provider, probe = setup()
    original_provider = provider
    original_probe = probe
    if case == "old_instance":

        def provider(target):
            return {**original_provider(target), "current_release_id": "old"}

    if case == "mixed_rollout":

        def provider(target):
            return {**original_provider(target), "serving_release_ids": ["old", "r2"]}

    if case == "wrong_build":

        def probe(check):
            return original_probe(check).model_copy(
                update={"payload": {"build_id": "store-build", "dependency_build_id": "old-dep"}}
            )

    if case == "replayed":

        def probe(check):
            return original_probe(check).model_copy(update={"id": "same", "request_id": "same"})

    if case == "pre_change":

        def probe(check):
            return original_probe(check).model_copy(update={"observed_at": 99})

    current_hash = (lambda: "changed") if case == "policy_changed" else (lambda: policy().digest())
    result = verify_recovery(
        policy(),
        "r2",
        provider,
        probe,
        clock=lambda: now[0],
        sleep=lambda n: now.__setitem__(0, now[0] + n),
        current_policy_hash=current_hash,
    )
    assert result["state"] != "recovered"


def test_one_pass_then_failure_resets_success_streak():
    now, calls, provider, probe = setup()
    original = probe

    def intermittent(check):
        result = original(check)
        return (
            result.model_copy(update={"check_pass": False, "http_status": 502}) if len(calls) == 2 else result
        )

    result = verify_recovery(
        policy(),
        "r2",
        provider,
        intermittent,
        clock=lambda: now[0],
        sleep=lambda n: now.__setitem__(0, now[0] + n),
    )
    assert result["state"] == "recovered" and calls == [100, 105, 110, 115, 120]


def test_approved_policy_and_operation_stay_bound_across_expected_release_change():
    from liara_guard.verification import bind_verification

    p = policy()
    op = {"id": "op", "spec": {"verification_policy_hash": p.digest(), "incident_generation": 1}}
    incident = {"generation": 2, "repair_operation_id": "op"}
    result = {"state": "recovered", "reason": "verified", "probe_ids": ["p1", "p2", "p3"]}
    assert bind_verification(op, incident, p, result)["state"] == "recovered"
    changed = p.model_copy(update={"id": "changed-policy"})
    assert bind_verification(op, incident, changed, result)["state"] == "inconclusive"
    assert (
        bind_verification(op, {**incident, "repair_operation_id": "new-op"}, p, result)["state"]
        == "inconclusive"
    )


def test_last_success_after_deadline_never_counts_as_recovered():
    now, calls, provider, probe = setup()
    original = probe

    def late(check):
        result = original(check)
        if len(calls) == 3:
            now[0] = 161
        return result.model_copy(update={"available_at": now[0]})

    result = verify_recovery(
        policy(), "r2", provider, late, clock=lambda: now[0], sleep=lambda n: now.__setitem__(0, now[0] + n)
    )
    assert result["state"] == "inconclusive" and result["reason"] == "verification_deadline"


def test_success_spacing_is_measured_after_reads_not_before_slow_provider():
    now, calls, provider, probe = setup()
    original = provider
    first = [True]

    def slow(target):
        if first[0]:
            now[0] += 9
            first[0] = False
        return original(target)

    result = verify_recovery(
        policy(), "r2", slow, probe, clock=lambda: now[0], sleep=lambda n: now.__setitem__(0, now[0] + n)
    )
    assert result["state"] == "recovered" and calls == [109, 114, 119]
