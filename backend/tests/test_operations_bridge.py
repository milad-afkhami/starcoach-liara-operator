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


@pytest.mark.parametrize('actual_release', ['r1', 'r2'])
def test_network_runtime_compatibility_preserves_actual_serving_release_and_scope(actual_release):
    from liara_guard.types import Target
    from test_runtime_identity import read_history, row
    target = Target(team_id='team', app_id='app', app_name='demo')
    requests = []
    history = read_history([row('container','create',610,actual_release),row('container','start',612,actual_release)])

    def handler(request):
        requests.append(request)
        if request.url.path.endswith('/applets'):
            return httpx.Response(500, json={'error':'Internal Server Error'})
        if request.url.path.endswith('/releases'):
            return httpx.Response(200,json={'currentRelease':'r2','releases':[{'_id':'r1','state':'READY'},{'_id':'r2','state':'READY'}]})
        if request.url.path.endswith('/events'):
            return httpx.Response(200,json=history(int(request.url.params['start']),int(request.url.params['end'])))
        return httpx.Response(200,json={'project':{'_id':'app','project_id':'demo','teamID':'team','scale':1,
            'network':{'_id':'net'},'created_at':'1970-01-01T00:10:00Z'}})

    client = LiaraClient('private-token','team',clock=lambda:1000,sleep=lambda _:None,transport=httpx.MockTransport(handler))
    bridge = LiaraOperationProvider(client,SimpleNamespace(resolve=lambda identifier:target),None,None,'owner')
    result = bridge.status_for_policy('app')
    assert result['state'] == 'READY' and result['current_release_id'] == 'r2'
    assert result['serving_release_ids'] == [actual_release]
    assert result['identity_source'] == 'network_lifecycle_events'
    assert result['identity_coverage']['complete_interval'] is True
    assert all(request.method == 'GET' and request.url.params['teamID']=='team' for request in requests)


def test_incomplete_network_history_never_uses_ready_current_release_as_serving_identity():
    from liara_guard.types import Target, Evidence
    target = Target(team_id='team',app_id='app',app_name='demo')
    def evidence(kind,quality,payload):
        return Evidence(id=kind,target=target,kind=kind,observed_at=1000,available_at=1000,
                        quality=quality,redacted_payload=payload)
    client = SimpleNamespace(get_releases=lambda target:evidence('releases','fresh',{'currentRelease':'r2','releases':[{'_id':'r2','state':'READY'}]}),
        get_applets=lambda target:evidence('applets','unavailable',{'error':'provider_error','http_status':500}),
        get_runtime_identity=lambda target,known:{'serving_release_ids':['r2'],'identity_source':'network_lifecycle_events','coverage':{'complete_interval':False,'reason':'history_truncated'}})
    result = LiaraOperationProvider(client,SimpleNamespace(resolve=lambda identifier:target),None,None,'owner').status_for_policy('app')
    assert result['state'] == 'unknown' and result.get('serving_release_ids',[]) == []
