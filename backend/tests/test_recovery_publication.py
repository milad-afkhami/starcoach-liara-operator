"""Exercise the production worker publication boundary, not a copied verifier."""
import inspect
import pytest
from types import SimpleNamespace
from liara_guard import api as api_module
from liara_guard.approvals import OperationSpec, ApprovalError
from liara_guard.contracts import RegisteredHttpCheck
from liara_guard.verification import VerificationPolicy
from test_api import app, login, durable_owner


@pytest.mark.parametrize('replace_at',['completion','entry'])
def test_stale_attempt_completion_cannot_publish_incident_or_clobber_current_attempt(tmp_path, monkeypatch, replace_at):
    application=app(tmp_path,clock=lambda:100)
    caller=login(application)
    caller.get('/api/services')
    owner=durable_owner(application,caller)
    check=RegisteredHttpCheck(id='preview',target_id='local-store',origin='https://store.liara.run',path='/preview',require_request_echo=True)
    policy=VerificationPolicy(id='p',checks=[check],expected_build_fields={'preview':{'build_id':'store'}},expected_release_ids={'local-dep':'$submitted'},changed_target_id='local-dep')
    application.state.registry.policies['local-store']=policy
    incident=application.state.monitor.ensure_incident(owner,application.state.registry.resolve('local-store'),'http_availability','manual',100)
    op=application.state.operations.propose(owner,OperationSpec(kind='redeploy_known_good',team_id='local-fixture',app_name='delivery',app_id='local-dep',
        artifact_sha256='a'*64,before_release_id='r1',incident_id=incident['id'],incident_generation=1,failure_fingerprint='f',verification_policy_hash=policy.digest()))
    original={'state':'inconclusive','reason':'original','probe_ids':['old']}
    value=application.state.operations.update(op,state='verifying',release_id='r2',source_id='source',approved_at=80,submitted_at=90,reconcile_until=700,
        verification=original,verification_attempts=[{'attempt':1,'result':original}],verification_attempt_id='old-attempt',recovery_rechecks_used=1,
        recovery_recheck_generation=1,recovery_recheck_release_id='r2')
    incident.update(repair_operation_id=op['id'],repair_pending=True)
    application.state.monitor.save_incident(incident,1)

    calls=[]
    def stale_return(*args,**kwargs):
        calls.append('verifier')
        current=application.state.operations.get(owner,op['id'])
        application.state.operations.update(current,state='awaiting_serving',verification_attempt_id='replacement-attempt',replacement_marker='protected')
        return {'state':'recovered','reason':'verified','probe_ids':['a','b','c'],'policy_hash':policy.digest(),'submitted_release_id':'r2'}

    monkeypatch.setattr(api_module,'verify_recovery',stale_return)
    worker=inspect.getclosurevars(application.state.tick).nonlocals['verify_operation']
    if replace_at=='entry':
        application.state.operations.update(value,state='awaiting_serving',verification_attempt_id='replacement-attempt',replacement_marker='protected')
    try:
        worker(value,SimpleNamespace(status_for_policy=lambda target:{}))
    except ApprovalError:
        pass
    current_incident=application.state.monitor.incident(owner,incident['id'])
    current_op=application.state.operations.get(owner,op['id'])
    assert current_incident['state']=='open' and current_incident['generation']==1
    assert 'verification' not in current_incident
    assert current_op['state']=='awaiting_serving' and current_op['verification_attempt_id']=='replacement-attempt'
    assert current_op['verification_attempts']==[{'attempt':1,'result':original}]

    assert current_op.get('replacement_marker')=='protected'
    assert calls==([] if replace_at=='entry' else ['verifier'])
