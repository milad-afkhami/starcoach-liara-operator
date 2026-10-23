import json
import threading
import pytest
from liara_guard.investigator import Investigator
from liara_guard.model_types import ModelResult
from liara_guard.observer import MonitorStore, Observer
from liara_guard.types import Target, Evidence

TARGET = Target(team_id="team", app_name="demo", app_id="app")


def setup(tmp_path, output=None):
    now = [100.0]
    store = MonitorStore(tmp_path / "state.sqlite")
    observer = Observer(store, {"app": TARGET}, clock=lambda: now[0])
    incident = observer.begin_investigation("owner", TARGET, "Investigate the service")
    evidence = Evidence(
        id="fresh",
        target=TARGET,
        kind="logs",
        observed_at=99,
        available_at=100,
        quality="fresh",
        redacted_payload={"message": "upstream timed out"},
    )
    store.add_evidence("owner", incident["id"], evidence)

    class Model:
        def __init__(self):
            self.requests = []
            self.hook = None

        def generate(self, request, schema, cancel):
            self.requests.append(request)
            if self.hook:
                self.hook()
            value = output or {
                "action": "conclude",
                "outcome": "need_evidence",
                "cause_family": "dependency_timeout",
                "summary": "A recent upstream timeout needs a direct dependency check.",
                "evidence_ids": ["fresh"],
                "contradiction_ids": [],
                "unknowns": ["Dependency reachability"],
                "next_check": None,
            }
            return ModelResult(
                request_id=request.id,
                provider="codex_cli",
                model="test",
                cli_version="test",
                elapsed_ms=1,
                value=value,
            )

    model = Model()
    i = Investigator(store, model, {"app": TARGET}, clock=lambda: now[0])
    return store, observer, incident, model, i, now


def test_grounded_diagnosis_is_stored_without_app_write(tmp_path):
    s, o, incident, m, i, now = setup(tmp_path)
    value = i.investigate("owner", incident["id"], {})
    assert value["cause_family"] == "dependency_timeout" and value["evidence_ids"] == ["fresh"]
    assert s.incident("owner", incident["id"])["diagnosis"]["cause_family"] == "dependency_timeout"
    assert s.incident("owner", incident["id"])["action_allowed"] is False


@pytest.mark.parametrize(
    "override",
    [
        {"evidence_ids": ["invented"]},
        {"action": "restart"},
        {"next_check": "shell", "action": "read"},
        {"cause_family": "process_crash", "evidence_ids": []},
    ],
)
def test_unsupported_model_actions_or_evidence_fail_closed(tmp_path, override):
    output = {
        "action": "conclude",
        "outcome": "need_evidence",
        "cause_family": "dependency_timeout",
        "summary": "test",
        "evidence_ids": ["fresh"],
        "contradiction_ids": [],
        "unknowns": [],
        "next_check": None,
        **override,
    }
    s, o, incident, m, i, now = setup(tmp_path, output)
    result = i.investigate("owner", incident["id"], {})
    assert result["outcome"] == "unresolved" and result["error"] == "invalid_model_output"
    assert s.incident("owner", incident["id"])["action_allowed"] is False


def test_future_evidence_and_scenario_or_credentials_not_supplied(tmp_path):
    s, o, incident, m, i, now = setup(tmp_path)
    s.add_evidence(
        "owner",
        incident["id"],
        Evidence(
            id="future",
            target=TARGET,
            kind="logs",
            observed_at=101,
            available_at=101,
            quality="fresh",
            redacted_payload={"message": "future answer"},
        ),
    )
    i.investigate("owner", incident["id"], {})
    payload = str(m.requests[0].payload)
    assert "future answer" not in payload and m.requests[0].evidence_ids == ["fresh"]
    assert "harness/" not in payload and "LIARA_API_TOKEN" not in payload


def test_unchanged_observations_do_not_invalidate_but_changed_release_does(tmp_path):
    s, o, incident, m, i, now = setup(tmp_path)
    m.hook = lambda: o.set_release("owner", "app", "r2")
    result = i.investigate("owner", incident["id"], {})
    assert result["error"] == "stale_generation" and s.incident("owner", incident["id"])["diagnosis"] is None


def test_observer_auth_failure_never_becomes_app_repair(tmp_path):
    output = {
        "action": "conclude",
        "outcome": "repair_candidate",
        "cause_family": "observer_access",
        "summary": "The API returned unauthorized.",
        "evidence_ids": ["auth"],
        "contradiction_ids": [],
        "unknowns": [],
        "next_check": None,
    }
    s, o, incident, m, i, now = setup(tmp_path, output)
    s.add_evidence(
        "owner",
        incident["id"],
        Evidence(
            id="auth",
            target=TARGET,
            kind="logs",
            observed_at=100,
            available_at=100,
            quality="unavailable",
            redacted_payload={"error": "observer_auth", "http_status": 401},
        ),
    )
    result = i.investigate("owner", incident["id"], {})
    assert result["outcome"] == "no_app_change" and result["cause_family"] == "observer_access"


def test_stale_only_evidence_and_unknown_units_force_abstention(tmp_path):
    output = {
        "action": "conclude",
        "outcome": "repair_candidate",
        "cause_family": "process_crash",
        "summary": "Old error.",
        "evidence_ids": ["stale"],
        "contradiction_ids": [],
        "unknowns": [],
        "next_check": None,
    }
    s, o, incident, m, i, now = setup(tmp_path, output)
    s.add_evidence(
        "owner",
        incident["id"],
        Evidence(
            id="stale",
            target=TARGET,
            kind="logs",
            observed_at=1,
            available_at=100,
            quality="stale",
            redacted_payload={"message": "old failure"},
        ),
    )
    result = i.investigate("owner", incident["id"], {})
    assert result["outcome"] == "unresolved"


def test_discriminating_read_then_conclusion_is_at_most_two_calls(tmp_path):
    s, o, incident, m, i, now = setup(tmp_path)

    def generate(request, schema, cancel):
        m.requests.append(request)
        value = {
            "action": "read" if len(m.requests) == 1 else "conclude",
            "outcome": "need_evidence",
            "cause_family": "dependency_timeout",
            "summary": "Direct check needed.",
            "evidence_ids": ["fresh"],
            "contradiction_ids": [],
            "unknowns": [],
            "next_check": "dependency" if len(m.requests) == 1 else None,
        }
        return ModelResult(
            request_id=request.id,
            provider="codex_cli",
            model="test",
            cli_version="test",
            elapsed_ms=1,
            value=value,
        )

    m.generate = generate
    reads = []

    def read():
        reads.append("read")
        return Evidence(
            id="probe",
            target=TARGET,
            kind="http_probe",
            observed_at=100,
            available_at=100,
            quality="fresh",
            redacted_payload={"http_status": 504},
        )

    result = i.investigate("owner", incident["id"], {"dependency": read})
    assert len(m.requests) == 2 and reads == ["read"] and result["read_operations"] == 1


def test_read_target_mismatch_is_not_persisted(tmp_path):
    s, o, incident, m, i, now = setup(tmp_path)
    wrong = Target(team_id="other", app_name="other", app_id="other")
    result = i.investigate(
        "owner",
        incident["id"],
        {
            "logs": lambda: Evidence(
                id="wrong",
                target=wrong,
                kind="logs",
                observed_at=100,
                available_at=100,
                quality="fresh",
                redacted_payload={},
            )
        },
        initial_reads=["logs"],
    )
    assert result["outcome"] == "unresolved"
    assert all(e["id"] != "wrong" for e in s.evidence("owner", incident["id"], cutoff=100))


def test_precanceled_investigation_never_calls_model(tmp_path):
    s, o, incident, m, i, now = setup(tmp_path)
    cancel = threading.Event()
    cancel.set()
    result = i.investigate("owner", incident["id"], {}, cancel=cancel)
    assert result["error"] == "canceled" and m.requests == []


def test_source_read_failure_is_structured_and_no_raw_secret_enters_model(tmp_path):
    s, o, incident, m, i, now = setup(tmp_path)
    s.add_evidence(
        "owner",
        incident["id"],
        Evidence(
            id="secret",
            target=TARGET,
            kind="logs",
            observed_at=100,
            available_at=100,
            quality="fresh",
            redacted_payload={"message": "api_key=should-not-leak"},
        ),
    )
    i.investigate("owner", incident["id"], {})
    assert "should-not-leak" not in str(m.requests[-1].payload)

    def broken():
        raise OSError("private provider details")

    result = i.investigate("owner", incident["id"], {"logs": broken}, initial_reads=["logs"])
    assert result["error"] == "evidence_read_failed"


def test_generation_race_during_final_save_leaves_explicit_failed_state(tmp_path):
    s, o, incident, m, i, now = setup(tmp_path)
    original = s.save_incident

    def racing(value, expected_generation=None):
        if value.get("diagnosis"):
            o.set_release("owner", "app", "new-release")
        return original(value, expected_generation)

    s.save_incident = racing
    result = i.investigate("owner", incident["id"], {})
    assert result["error"] == "stale_generation"
    assert s.incident("owner", incident["id"])["investigation_state"] == "failed"


def test_old_originally_fresh_evidence_cannot_support_reinvestigation(tmp_path):
    s, o, incident, m, i, now = setup(tmp_path)
    now[0] = 1000
    result = i.investigate("owner", incident["id"], {})
    assert m.requests[0].payload["evidence"][0]["quality"] == "stale"
    assert result["outcome"] == "unresolved" and result["error"] == "invalid_model_output"


def test_diagnosis_requests_persian_prose_without_translating_schema_identifiers(tmp_path):
    s, o, incident, model, investigator, now = setup(tmp_path)
    investigator.investigate('owner', incident['id'], {})
    request = model.requests[0]
    assert request.payload['response_language'] == 'fa-IR'
    assert 'Persian' in request.payload['instructions']
    assert 'Use concise English' not in request.payload['instructions']
    assert request.schema_id == 'liara-diagnosis'


def test_large_log_excerpt_keeps_newest_structured_lines_and_immutable_storage(tmp_path):
    store, _, incident, model, investigator, _ = setup(tmp_path)
    lines = [
        {"timestamp": str((38 + n) * 1_000_000_000), "release_id": "release-current",
         "type": "stdout", "message": f"older request {n}: " + "x" * 350}
        for n in range(61)
    ]
    newest = {"timestamp": "99000000000", "release_id": "release-current",
              "type": "stderr", "message": "GET /latest-request 504 upstream timeout"}
    lines.append(newest)
    payload = {"lines": lines, "schema": "v2"}
    store.add_evidence(
        "owner", incident["id"],
        Evidence(id="large-logs", target=TARGET, kind="logs", observed_at=99,
                 available_at=100, quality="fresh", redacted_payload=payload),
    )

    investigator.investigate("owner", incident["id"], {})

    projected = next(e for e in model.requests[0].payload["evidence"] if e["id"] == "large-logs")
    excerpt = projected["redacted_payload"]
    assert excerpt.get("lines", [])[-1:] == [newest]
    assert excerpt["schema"] == "v2"
    assert excerpt["truncated_for_model"] is True
    assert 0 < excerpt["omitted_line_count"] == len(lines) - len(excerpt["lines"])
    assert len(json.dumps(excerpt, ensure_ascii=False).encode()) <= 4096
    stored = next(e for e in store.evidence("owner", incident["id"], cutoff=100)
                  if e["id"] == "large-logs")
    assert stored["redacted_payload"] == payload


@pytest.mark.parametrize("text", ["ژ" * 3900, "😀" * 3900, '\\"' * 1900], ids=["persian", "emoji", "escaped"])
def test_oversized_log_message_is_explicitly_truncated_with_utf8_byte_bound(tmp_path, text):
    store, _, incident, model, investigator, _ = setup(tmp_path)
    payload = {"lines": [{"timestamp": 99, "message": "start " + text + " end"}]}
    store.add_evidence(
        "owner", incident["id"],
        Evidence(id="long-message", target=TARGET, kind="logs", observed_at=99,
                 available_at=100, quality="fresh", redacted_payload=payload),
    )
    investigator.investigate("owner", incident["id"], {})
    excerpt = next(e["redacted_payload"] for e in model.requests[0].payload["evidence"]
                   if e["id"] == "long-message")
    assert len(json.dumps(excerpt, ensure_ascii=False).encode()) <= 4096
    assert excerpt.get("lines", [{}])[-1]["timestamp"] == 99
    line = excerpt["lines"][-1]
    assert line["truncated_for_model"] is True
    assert line["message"].startswith("start ") and line["message"].endswith(" end")
    assert "�" not in line["message"]


def test_large_log_excerpt_excludes_future_evidence_and_respects_total_budget(tmp_path):
    store, _, incident, model, investigator, _ = setup(tmp_path)
    for n in range(12):
        store.add_evidence(
            "owner", incident["id"],
            Evidence(id=f"logs-{n}", target=TARGET, kind="logs", observed_at=99,
                     available_at=100, quality="fresh",
                     redacted_payload={"lines": [{"timestamp": 99, "message": "ژ" * 3900}]}),
        )
    store.add_evidence(
        "owner", incident["id"],
        Evidence(id="future-large", target=TARGET, kind="logs", observed_at=101,
                 available_at=101, quality="fresh",
                 redacted_payload={"lines": [{"timestamp": 101, "message": "future marker " * 300}]}),
    )
    investigator.investigate("owner", incident["id"], {})
    request = model.requests[0]
    encoded = json.dumps(request.payload["evidence"], ensure_ascii=False).encode()
    assert len(encoded) <= 36000
    assert "future-large" not in request.evidence_ids and b"future marker" not in encoded
    assert "logs-0" in request.evidence_ids


def test_deterministic_failure_and_repair_caveat_are_in_persian(tmp_path):
    _, _, incident, _, investigator, _ = setup(tmp_path)
    cancel = threading.Event()
    cancel.set()
    failed = investigator.investigate("owner", incident["id"], {}, cancel=cancel)
    assert any("\u0600" <= char <= "\u06ff" for char in failed["summary"])
    output = {
        "action": "conclude", "outcome": "repair_candidate", "cause_family": "dependency_timeout",
        "summary": "بررسی وابستگی لازم است.", "evidence_ids": ["fresh"], "contradiction_ids": [],
        "unknowns": [], "next_check": None,
    }
    _, _, incident, _, investigator, _ = setup(tmp_path, output)
    result = investigator.investigate("owner", incident["id"], {})
    assert result["outcome"] == "need_evidence"
    assert any("\u0600" <= char <= "\u06ff" for char in result["unknowns"][-1])


def test_investigation_reports_actual_collection_model_and_completion_stages(tmp_path):
    store, _, incident, model, investigator, _ = setup(tmp_path)
    seen = []

    def reader():
        seen.append(store.incident('owner', incident['id'])['investigation_progress'])
        return Evidence(id='new-log', target=TARGET, kind='logs', observed_at=99,
                        available_at=100, quality='fresh', redacted_payload={'lines': []})

    model.hook = lambda: seen.append(store.incident('owner', incident['id'])['investigation_progress'])
    investigator.investigate('owner', incident['id'], {'logs': reader}, initial_reads=['logs'])
    assert seen[0]['stage'] == 'collecting' and seen[0]['read_name'] == 'logs'
    assert seen[0]['reads_completed'] == 0
    assert seen[1]['stage'] == 'analyzing' and seen[1]['reads_completed'] == 1
    assert seen[1]['model_call'] == 1
    assert store.incident('owner', incident['id'])['investigation_progress']['stage'] == 'done'


def test_rejected_draft_records_controlled_guard_reason_without_promoting_or_leaking_secrets(tmp_path):
    output={'action':'conclude','outcome':'repair_candidate','cause_family':'dependency_schema','summary':'private-value token=another-secret',
            'evidence_ids':[],'contradiction_ids':[],'unknowns':[],'next_check':None}
    store,_,incident,model,investigator,_=setup(tmp_path,output)
    investigator.diagnostic_secrets=('private-value',)
    result=investigator.investigate('owner',incident['id'],{})
    assert result['error']=='invalid_model_output' and result['outcome']=='unresolved'
    assert store.incident('owner',incident['id'])['diagnosis'] is None
    records=store.rejected_drafts('owner',incident['id'])
    assert records[0]['reason']=='missing_support'
    assert records[0]['rejected_not_a_diagnosis'] is True
    assert 'private-value' not in json.dumps(records) and 'another-secret' not in json.dumps(records)
    assert model.requests[0].payload.get('rejected_drafts') is None


def test_second_call_read_none_is_rejected_by_executable_contract(tmp_path):
    store,_,incident,model,investigator,_=setup(tmp_path)
    def generate(request,schema,cancel):
        model.requests.append(request)
        return ModelResult(request_id=request.id,provider='test',model='test',cli_version='test',elapsed_ms=1,
            value={'action':'read','outcome':'need_evidence','cause_family':'unknown','summary':'Another check requested',
                   'evidence_ids':[],'contradiction_ids':[],'unknowns':[],
                   'next_check':'logs' if len(model.requests)==1 else None})
    model.generate=generate
    def reader():
        return Evidence(id='new',target=TARGET,kind='logs',observed_at=99,available_at=100,quality='fresh',redacted_payload={})
    result=investigator.investigate('owner',incident['id'],{'logs':reader})
    assert result['error']=='invalid_model_output'
    record=store.rejected_drafts('owner',incident['id'])[0]
    assert record['call']==2 and record['reason']=='schema_violation'
    assert record['draft']['action']=='read' and record['draft']['next_check'] is None
    assert record['allowed_next_checks']==[]


def test_rejected_diagnostic_is_byte_bounded_and_not_part_of_future_model_evidence(tmp_path):
    output={'action':'conclude','outcome':'repair_candidate','cause_family':'unknown','summary':'ژ'*15000,
            'evidence_ids':[],'contradiction_ids':[],'unknowns':['😀'*5000]*8,'next_check':None}
    store,_,incident,model,investigator,_=setup(tmp_path,output)
    investigator.investigate('owner',incident['id'],{})
    record=store.rejected_drafts('owner',incident['id'])[0]
    assert record['reason']=='schema_violation'
    assert len(json.dumps(record,ensure_ascii=False).encode())<=8192
    assert record['draft']['truncated_for_diagnostic'] is True
    assert all(item['kind']!='rejected_draft' for item in store.evidence('owner',incident['id'],cutoff=100))


def test_rejected_diagnostic_redacts_known_credentials_even_in_untrusted_field_names(tmp_path):
    output={'action':'conclude','outcome':'unresolved','cause_family':'unknown','summary':'diagnostic',
            'evidence_ids':[],'contradiction_ids':[],'unknowns':[],'next_check':None,'private-credential-key':'value'}
    store,_,incident,model,investigator,_=setup(tmp_path,output)
    investigator.diagnostic_secrets=('private-credential-key',)
    investigator.investigate('owner',incident['id'],{})
    assert 'private-credential-key' not in json.dumps(store.rejected_drafts('owner',incident['id']))


def test_rejected_draft_retention_is_bounded_owner_scoped_and_keeps_first_record_for_call(tmp_path):
    store,_,incident,model,investigator,_=setup(tmp_path)
    for index in range(12):
        store.record_rejected_draft('owner',incident['id'],{'run_id':str(index),'call':1,'draft':{'summary':str(index)}})
    rows=store.rejected_drafts('owner',incident['id'])
    assert len(rows)==8 and rows[0]['run_id']=='11' and rows[-1]['run_id']=='4'
    store.record_rejected_draft('owner',incident['id'],{'run_id':'11','call':1,'draft':{'summary':'replacement'}})
    assert store.rejected_drafts('owner',incident['id'])[0]['draft']['summary']=='11'
    with pytest.raises(KeyError):
        store.rejected_drafts('other',incident['id'])


def test_historical_model_projection_excludes_raw_future_rejected_series_but_preserves_audit(tmp_path):
    s, o, incident, m, i, now = setup(tmp_path)
    payload = {'historical_only': True, 'cutoff': 100, 'unit': 'verified',
               'measurements': [{'metric': 'cpu', 'applet': 'a', 'value': 12.5, 'unit': 'percent', 'observed_at': 99, 'age_seconds': 1}],
               'provider_data': {'cpu': {'end': 900, 'result': [{'values': [[900, 'rejected-future-marker'], [99, '0.125']]}]}},
               'capacity_assessment': 'not_established', 'unit_source': {'cpu_denominator': 'provider_reported_ratio'}}
    s.add_evidence('owner', incident['id'], Evidence(id='history', target=TARGET, kind='metrics_history', observed_at=99,
                   available_at=100, quality='fresh', redacted_payload=payload, coverage={'excluded_future': 1}))
    i.investigate('owner', incident['id'], {})
    projected = next(e for e in m.requests[0].payload['evidence'] if e['id'] == 'history')
    assert 'provider_data' not in projected['redacted_payload']
    assert 'rejected-future-marker' not in json.dumps(m.requests[0].payload)
    assert projected['redacted_payload']['measurements'] == payload['measurements']
    assert projected['coverage']['excluded_future'] == 1
    assert next(e for e in s.evidence('owner', incident['id'], cutoff=100) if e['id'] == 'history')['redacted_payload'] == payload


def test_final_call_advertises_only_executable_actions_and_zero_remaining_reads(tmp_path):
    from jsonschema import Draft202012Validator
    s, _, incident, model, investigator, _ = setup(tmp_path)
    contracts=[]
    def generate(request, contract, cancel):
        model.requests.append(request)
        contracts.append(contract)
        final = len(model.requests)==2
        value={'action':'conclude' if final else 'read','outcome':'unresolved','cause_family':'unknown',
               'summary':'شواهد کافی نیست؛ علت نامشخص است.','evidence_ids':[],'contradiction_ids':[],
               'unknowns':['بررسی بیشتر لازم است.'],'next_check':None if final else 'logs'}
        if final:
            assert request.payload['available_reads']==[]
            assert request.payload['remaining_read_budget']==0
            assert contract['properties']['action']['enum']==['conclude']
            assert not Draft202012Validator(contract).is_valid({**value,'action':'read'})
        else:
            assert request.payload['available_reads']==['logs']
            assert request.payload['remaining_read_budget']==12
        return ModelResult(request_id=request.id,provider='test',model='test',cli_version='test',elapsed_ms=1,value=value)
    model.generate=generate
    result=investigator.investigate('owner',incident['id'],{'logs':lambda: Evidence(id='new-log',target=TARGET,kind='logs',
                                   observed_at=99,available_at=100,quality='fresh',redacted_payload={})})
    assert result['outcome']=='unresolved' and len(contracts)==2


def test_exhausted_initial_read_budget_disallows_read_even_on_first_call(tmp_path):
    s, _, incident, model, investigator, _=setup(tmp_path)
    investigator.investigate('owner',incident['id'],{'logs':lambda: Evidence(id='same-log',target=TARGET,kind='logs',
                            observed_at=99,available_at=100,quality='fresh',redacted_payload={})}, initial_reads=['logs']*12)
    assert model.requests[0].payload['available_reads']==[]
    assert model.requests[0].payload['remaining_read_budget']==0
