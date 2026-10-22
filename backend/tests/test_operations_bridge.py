"""Consequential boundary checks; provider fakes never close the live QA ledger."""

import json
from types import SimpleNamespace
import httpx
import pytest
from liara_guard.approvals import OperationSpec, ApprovalError, AmbiguousWrite, RejectedWrite
from liara_guard.client import LiaraClient
from liara_guard.operations_bridge import LiaraOperationProvider
from test_bootstrap import catalogue


def create_spec():
    return OperationSpec(
        kind="create_app",
        team_id="team",
        app_name="liara-watch-delivery-2026",
        plan_id="g2-small",
        bundle_plan_id="basic",
        network_id="net",
        hourly_price_toman="1146",
        price_verified_at=100,
    )


def test_creation_sends_exact_network_bundle_platform_and_scope():
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            return httpx.Response(201, json={})
        return httpx.Response(
            200, json={"project": {"_id": "dep", "project_id": "liara-watch-delivery-2026", "teamID": "team"}}
        )

    client = LiaraClient("private", "team", transport=httpx.MockTransport(handler))
    assert client.create_project(create_spec()) == "dep"
    assert len(calls) == 2 and json.loads(calls[0].content) == {
        "name": "liara-watch-delivery-2026",
        "planID": "g2-small",
        "bundlePlanID": "basic",
        "network": "net",
        "platform": "docker",
        "readOnlyRootFilesystem": False,
    }
    assert all(r.url.params["teamID"] == "team" for r in calls)


@pytest.mark.parametrize("status", [302, 500, 502])
def test_ambiguous_provider_write_is_never_retried(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(status, json={})

    client = LiaraClient("private", "team", transport=httpx.MockTransport(handler))
    with pytest.raises(AmbiguousWrite):
        client.create_project(create_spec())
    assert len(calls) == 1


def test_rejected_provider_write_never_reads_or_retries():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(403, json={"private": "ignored"})

    client = LiaraClient("private", "team", transport=httpx.MockTransport(handler))
    with pytest.raises(RejectedWrite):
        client.create_project(create_spec())
    assert len(calls) == 1


def test_create_preflight_refreshes_quote_and_network_membership():
    def handler(request):
        if request.url.path.endswith("/me"):
            return httpx.Response(200, json={"plans": catalogue()})
        if request.url.path.endswith("/networks"):
            return httpx.Response(200, json={"networks": [{"_id": "net", "name": "demo"}]})
        return httpx.Response(404, json={})

    client = LiaraClient("private", "team", transport=httpx.MockTransport(handler))
    bridge = LiaraOperationProvider(client, SimpleNamespace(team_id="team"), None, None, "owner")
    assert bridge.inspect(create_spec()) == {
        "exists": False,
        "plan_id": "g2-small",
        "bundle_plan_id": "basic",
        "network_id": "net",
        "hourly_price_toman": "1146",
    }
    with pytest.raises(ApprovalError):
        bridge.inspect(create_spec().model_copy(update={"network_id": "wrong"}))


def test_bootstrap_runner_registers_exact_demo_origin(tmp_path):
    from liara_guard.owner_setup import Setup
    from liara_guard.types import Target, ServiceSummary
    from liara_guard.contracts import RegisteredHttpCheck

    target = Target(team_id="team", app_name="liara-watch-delivery-2026", app_id="dep")
    setup = Setup(SimpleNamespace(team_id="team"), tmp_path)
    setup.registry.refresh(
        [ServiceSummary(target=target, platform="docker", runtime_state="running", observed_at=100)]
    )
    check = RegisteredHttpCheck(
        id="q", target_id="dep", origin="https://liara-watch-delivery-2026.liara.run", path="/quote"
    )
    runner = setup.runner_for([check])
    assert runner.targets["dep"].origin == check.origin
    with pytest.raises(ApprovalError):
        setup.runner_for([check.model_copy(update={"origin": "https://other.example"})])


def test_repair_requires_completed_diagnosis_of_this_exact_generation():
    from liara_guard.operations_bridge import current_repair_candidate

    value = {
        "generation": 2,
        "state": "open",
        "investigation_state": "done",
        "diagnosis": {"generation": 1, "outcome": "repair_candidate"},
    }
    assert not current_repair_candidate(value)
    value["diagnosis"]["generation"] = 2
    assert current_repair_candidate(value)
    value["investigation_state"] = "running"
    assert not current_repair_candidate(value)
