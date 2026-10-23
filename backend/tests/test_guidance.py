from liara_guard.guidance import remediation_guidance


def incident(cause='dependency_schema'):
    return {'target': {'app_id': 'store', 'app_name': 'storefront'}, 'generation': 3,
            'investigation_state': 'done', 'diagnosis': {'generation': 3, 'cause_family': cause,
                'outcome': 'need_evidence', 'evidence_ids': ['failed', 'logs'], 'cutoff': 100}}


def evidence():
    return [
        {'id': 'failed', 'kind': 'http_probe', 'target': {'app_id': 'store', 'app_name': 'storefront'},
         'available_at': 99, 'quality': 'fresh', 'redacted_payload': {'check_id': 'preview', 'path': '/preview',
             'http_status': 502, 'check_pass': False}},
        {'id': 'logs', 'kind': 'logs', 'target': {'app_id': 'dep', 'app_name': 'delivery'},
         'available_at': 100, 'quality': 'fresh', 'redacted_payload': {'lines': []}},
        {'id': 'future', 'kind': 'logs', 'target': {'app_id': 'store', 'app_name': 'storefront'},
         'available_at': 101, 'quality': 'fresh', 'redacted_payload': {'message': 'future answer'}},
    ]


def test_unenrolled_service_gets_actionable_manual_steps_with_exact_original_recheck():
    result = remediation_guidance(incident(), evidence(), can_repair=False)
    assert result['mode'] == 'owner_checklist'
    assert result['automatic_changes'] is False
    assert len(result['steps']) >= 3
    assert result['steps'][-1]['check_ids'] == ['preview']
    assert '502' in result['steps'][-1]['detail']
    assert result['steps'][0]['evidence_ids'] == ['failed', 'logs']
    assert all(step['actor'] in ('owner', 'assistant') for step in result['steps'])
    assert 'future' not in str(result) and 'future answer' not in str(result)
    assert all('command' not in step and 'url' not in step for step in result['steps'])


def test_stale_or_unfinished_diagnosis_never_gets_current_remediation():
    value = incident()
    value['generation'] = 4
    assert remediation_guidance(value, evidence(), can_repair=False) is None
    value = incident()
    value['investigation_state'] = 'running'
    assert remediation_guidance(value, evidence(), can_repair=False) is None


def test_observer_auth_guidance_never_recommends_application_restart_or_plan_change():
    result = remediation_guidance(incident('observer_access'), evidence(), can_repair=False)
    assert result['mode'] == 'restore_observation'
    text = ' '.join(step['detail'] for step in result['steps'])
    assert 'دسترسی' in text
    assert 'ری‌استارت' not in text and 'افزایش منابع' not in text
    assert result['automatic_changes'] is False


def test_unknown_cause_guidance_requires_evidence_instead_of_inventing_a_fix():
    value = incident('unknown')
    value['diagnosis']['evidence_ids'] = []
    result = remediation_guidance(value, [], can_repair=False)
    assert result['mode'] == 'gather_evidence'
    assert all(step['evidence_ids'] == [] for step in result['steps'])
    assert result['steps'][-1]['check_ids'] == []


def test_registered_repair_guidance_retains_separate_exact_approval():
    value = incident()
    value['diagnosis']['outcome'] = 'repair_candidate'
    result = remediation_guidance(value, evidence(), can_repair=True)
    assert result['mode'] == 'review_proposal'
    assert result['automatic_changes'] is False
    assert 'تأیید' in result['limitation']
