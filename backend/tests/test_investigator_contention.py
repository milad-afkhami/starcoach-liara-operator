"""Contention uses the real gate/client boundary; the runner marks actual starts."""
import json
import time
from pathlib import Path

from liara_guard.codex_cli import CodexCliClient
from liara_guard.investigator import Investigator
from liara_guard.observer import MonitorStore, Observer
from liara_guard.types import Target


class ControlledCancel:
    def __init__(self, clock, on_wait=None):
        self.clock, self.on_wait = clock, on_wait
        self.canceled = False
        self.waits = []

    def is_set(self):
        return self.canceled

    def wait(self, duration):
        self.waits.append(duration)
        self.clock[0] += duration
        if self.on_wait:
            self.on_wait(self)
        return self.canceled


def setup(tmp_path, *, runner_exit=0):
    clock = [time.time()]
    target = Target(team_id='team', app_id='app', app_name='demo')
    store = MonitorStore(tmp_path/'state.sqlite')
    incident = Observer(store, {'app': target}, clock=lambda: clock[0]).begin_investigation('owner', target, 'Investigate')
    binary, auth = tmp_path/'binary', tmp_path/'auth.json'
    binary.touch()
    auth.write_text('{}')
    started = []

    def runner(spec, cancel):
        started.append(spec)
        spec.output.write_text(json.dumps({'action': 'conclude', 'outcome': 'unresolved', 'cause_family': 'unknown',
            'summary': 'Insufficient evidence.', 'evidence_ids': [], 'contradiction_ids': [], 'unknowns': [], 'next_check': None}))
        return runner_exit

    client = CodexCliClient(binary=binary, auth_file=auth, image='test-only', gate_dir=tmp_path/'gate', runner=runner)
    attempts = []

    class RecordingModel:
        def generate(self, request, schema, cancel):
            attempts.append(request)
            return client.generate(request, schema, cancel)

    investigator = Investigator(store, RecordingModel(), {'app': target}, clock=lambda: clock[0])
    return investigator, incident, client, started, attempts, clock


def charged(client):
    ledger = Path(client.gate.root)/'starts.json'
    return json.loads(ledger.read_text()) if ledger.exists() else []


def test_contention_release_reuses_original_request_and_starts_exactly_once(tmp_path):
    investigator, incident, client, started, attempts, clock = setup(tmp_path)
    reservation = client.gate.reserve()
    reservation.__enter__()
    cancel = ControlledCancel(clock, lambda _: reservation.__exit__(None, None, None))
    initial_deadline = clock[0]+1
    result = investigator.investigate('owner', incident['id'], {}, cancel=cancel, deadline_utc=initial_deadline)
    assert 'error' not in result
    assert len(attempts) == 2 and attempts[0] is attempts[1]
    assert attempts[0].deadline_utc == initial_deadline
    assert len(cancel.waits) == 1
    assert len(started) == len(charged(client)) == 1
    assert len(result['model_calls']) == 1


def test_persistent_contention_expires_at_original_absolute_deadline_without_start(tmp_path):
    investigator, incident, client, started, attempts, clock = setup(tmp_path)
    deadline = clock[0]+.25
    cancel = ControlledCancel(clock)
    with client.gate.reserve():
        result = investigator.investigate('owner', incident['id'], {}, cancel=cancel, deadline_utc=deadline)
    assert result['error'] == 'expired'
    assert clock[0] == deadline
    assert len(attempts) >= 2
    assert all(request is attempts[0] and request.deadline_utc == deadline for request in attempts)
    assert started == [] and charged(client) == []


def test_cancellation_during_contention_stops_without_another_attempt_or_start(tmp_path):
    investigator, incident, client, started, attempts, clock = setup(tmp_path)
    cancel = ControlledCancel(clock, lambda event: setattr(event, 'canceled', True))
    with client.gate.reserve():
        result = investigator.investigate('owner', incident['id'], {}, cancel=cancel)
    assert result['error'] == 'canceled'
    assert len(attempts) == 1 and len(cancel.waits) == 1
    assert started == [] and charged(client) == []


def test_nonbusy_failure_after_start_is_never_retried_or_charged_twice(tmp_path):
    investigator, incident, client, started, attempts, clock = setup(tmp_path, runner_exit=1)
    cancel = ControlledCancel(clock)
    result = investigator.investigate('owner', incident['id'], {}, cancel=cancel)
    assert result['error'] == 'provider_failed'
    assert len(attempts) == len(started) == len(charged(client)) == 1
    assert cancel.waits == []


def test_replaced_investigation_during_contention_never_starts_or_overwrites_replacement(tmp_path):
    investigator, incident, client, started, attempts, clock = setup(tmp_path)

    def replace(_):
        current = investigator.store.incident('owner', incident['id'])
        current['investigation_run_id'] = 'replacement-run'
        investigator.store.save_incident(current, current['generation'])

    cancel = ControlledCancel(clock, replace)
    with client.gate.reserve():
        result = investigator.investigate('owner', incident['id'], {}, cancel=cancel)
    assert result['error'] == 'stale_generation'
    assert investigator.store.incident('owner', incident['id'])['investigation_run_id'] == 'replacement-run'
    assert len(attempts) == 1 and started == [] and charged(client) == []
