import pytest
from liara_guard.runtime_identity import network_runtime_identity

NOW = 1000
PROJECT = {'_id': 'app', 'created_at': '1970-01-01T00:10:00Z', 'network': {'_id': 'net'}, 'scale': 1}


def row(container, action, at, release='r2'):
    return {'id': container, 'action': action, 'status': action, 'time': str(at), 'release': release, 'tag': 'v2'}


def read_history(history, limit=20):
    def read(start, end):
        return {'data': sorted([item for item in history if start <= int(item['time']) < end],
                               key=lambda item: int(item['time']), reverse=True)[:limit]}
    return read


def identity(history, **overrides):
    return network_runtime_identity(overrides.pop('project', PROJECT), overrides.pop('known_releases', {'r1','r2'}),
                                    overrides.pop('reader', read_history(history)), now=NOW, **overrides)


def test_complete_network_lifecycle_proves_actual_event_release_not_current_release_substitution():
    result = identity([row('c', 'create', 610), row('c', 'start', 612)])
    assert result['serving_release_ids'] == ['r2']
    assert result['identity_source'] == 'network_lifecycle_events'
    assert result['coverage']['complete_interval'] is True
    assert result['coverage']['history_start'] <= 600 and NOW <= result['coverage']['history_end'] <= NOW+1
    assert result['coverage']['event_count'] == 2


@pytest.mark.parametrize('changes,reason', [
    ({'created_at': None}, 'missing_creation_anchor'),
    ({'created_at': '1970-01-02T00:00:00Z'}, 'invalid_creation_anchor'),
    ({'network': None}, 'network_runtime_not_confirmed'),
    ({'scale': 2}, 'active_count_mismatch'),
])
def test_missing_or_invalid_anchor_network_and_scale_fail_closed(changes, reason):
    result = identity([row('c','create',610),row('c','start',612)], project={**PROJECT,**changes})
    assert result['serving_release_ids'] == []
    assert result['coverage']['reason'] == reason


@pytest.mark.parametrize('history', [
    [row('c','start',612)],
    [row('c','create',610),row('c','unknown_action',612)],
    [row('c','create',610),row('c','start',610)],
    [row('c','create',610),row('c','start',NOW+60)],
    [row('c','create',610,'r2'),row('c','start',612,'unrecognized')],
    [row('c','create',610),row('c','start',612),row('c','destroy',620),row('c','start',630)],
])
def test_incomplete_ambiguous_unknown_future_or_impossible_history_never_proves_serving(history):
    assert identity(history)['serving_release_ids'] == []


def test_old_and_mixed_running_release_ids_are_retained_for_existing_verifier_to_reject():
    old = [row('old','create',610,'r1'),row('old','start',612,'r1')]
    assert identity(old)['serving_release_ids'] == ['r1']
    mixed = identity(old+[row('new','create',620),row('new','start',622)], project={**PROJECT,'scale':2})
    assert set(mixed['serving_release_ids']) == {'r1','r2'}


@pytest.mark.parametrize('terminal', ['stop','die','destroy','kill','oom'])
def test_stopped_old_instances_are_excluded_only_after_observed_terminal_event(terminal):
    history = [row('old','create',610,'r1'),row('old','start',612,'r1'),row('old',terminal,620,'r1'),
               row('new','create',630),row('new','start',632)]
    assert identity(history)['serving_release_ids'] == ['r2']


def test_backfill_handles_supported_bounded_pages_without_losing_boundary_events():
    history = [row('old','create',610,'r1'),row('old','start',612,'r1'),row('old','stop',620,'r1'),
               row('new','create',630),row('new','start',632)]
    result = identity(history,reader=read_history(history,limit=2))
    assert result['serving_release_ids'] == ['r2']
    assert result['coverage']['event_count'] == 5


def test_unsupported_pagination_or_explicit_truncation_cannot_prove_complete_interval():
    history = [row('c','create',610),row('c','start',612)]
    def ignores_interval(start,end):
        return {'data': list(reversed(history))}
    assert identity(history,reader=ignores_interval)['serving_release_ids'] == []
    def truncated(start,end):
        return {'data': [], 'truncated': True}
    assert identity([],reader=truncated)['serving_release_ids'] == []


def test_provider_ordering_or_boundary_second_overflow_fails_closed():
    def unordered(start,end):
        return {'data': [row('c','create',610),row('c','start',612)]}
    assert identity([],reader=unordered)['serving_release_ids'] == []
    crowded = [row('a','create',610),row('b','create',610),row('a','start',612),row('b','start',612)]
    assert identity(crowded,reader=read_history(crowded,limit=2),project={**PROJECT,'scale':2})['serving_release_ids'] == []


def test_same_second_terminal_events_do_not_hide_a_stopped_old_instance():
    history = [row('old','create',610,'r1'),row('old','start',612,'r1'),
               row('old','kill',620,'r1'),row('old','die',620,'r1'),row('old','destroy',620,'r1'),
               row('new','create',630),row('new','start',632)]
    assert identity(history)['serving_release_ids'] == ['r2']


def test_complete_pagination_cannot_supply_an_instance_without_its_creation_event():
    history = [row('old','create',610,'r1'),row('old','start',612,'r1'),row('old','stop',614,'r1'),
               row('unanchored','start',622)]
    result = identity(history)
    assert result['serving_release_ids'] == []
    assert result['coverage']['reason'] == 'missing_container_creation'


def test_history_network_and_request_budgets_fail_closed_without_unbounded_reads():
    history = []
    for n in range(8):
        history += [row(str(n),'create',610+n*10),row(str(n),'start',612+n*10),row(str(n),'stop',614+n*10)]
    result = identity(history,reader=read_history(history,limit=2))
    assert result['serving_release_ids'] == []
    assert result['coverage']['reason'] == 'history_budget_exceeded'
    assert result['coverage']['requests'] == 12
    ticks=iter([0,0,11])
    result = identity([row('c','create',610),row('c','start',612)],monotonic=lambda:next(ticks,11))
    assert result['serving_release_ids'] == []
    assert result['coverage']['reason'] == 'history_budget_exceeded'
