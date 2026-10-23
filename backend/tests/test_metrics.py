import httpx
import pytest
from liara_guard.client import LiaraClient
from liara_guard.types import Target

NOW = 1792714000.0
TARGET = Target(team_id='team', app_name='demo', app_id='app')


def metrics(payload):
    client = LiaraClient('private-token', 'team', clock=lambda: NOW,
                         transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload)))
    return client.get_metrics(TARGET)


def test_verified_summary_contract_preserves_per_applet_units_sample_times_and_no_capacity_claim():
    result = metrics({'cpuUsage': [{'applet': 'a1', 'value': [NOW - 10, '0.125']}],
                      'memoryUsage': [{'applet': 'a1', 'value': [NOW - 12, '67108864']}], 'disksUsage': []})
    assert result.coverage['unit_verified'] is True
    assert result.coverage['threshold_evaluated'] is False
    assert result.observed_at == NOW - 12
    values = result.redacted_payload['measurements']
    assert values[0] == {'metric': 'cpu', 'applet': 'a1', 'value': 12.5, 'unit': 'percent', 'observed_at': NOW - 10}
    assert values[1]['value'] == 67108864 and values[1]['unit'] == 'bytes'
    assert result.redacted_payload['capacity_assessment'] == 'not_established'
    assert result.redacted_payload['unit_source']['sha256'] == 'd3e0d8646a7dde8e13f42b22fb659b1bb135531d069b0b0c2024a57ed983f5ec'


@pytest.mark.parametrize('stamp,quality', [(NOW-301, 'stale'), (NOW+60, 'invalid')])
def test_metric_acquisition_time_cannot_make_stale_or_future_samples_current(stamp, quality):
    result = metrics({'cpuUsage': [{'applet': 'a', 'value': [stamp, '0.9']}], 'memoryUsage': []})
    assert result.quality == quality
    assert result.observed_at == stamp


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-1', None, True])
def test_malformed_recognized_metrics_never_become_measured_percentages(value):
    result = metrics({'cpuUsage': [{'applet': 'a', 'value': [NOW, value]}], 'memoryUsage': []})
    assert result.quality == 'unavailable'
    assert result.redacted_payload['error'] == 'invalid_metrics_schema'


def test_empty_metrics_are_unavailable_and_partial_snapshot_never_defaults_to_zero():
    result = metrics({'cpuUsage': [], 'memoryUsage': []})
    assert result.quality == 'unavailable' and result.redacted_payload['error'] == 'metrics_empty'
    partial = metrics({'cpuUsage': [], 'memoryUsage': [{'applet': 'a', 'value': [NOW, '1000']}]})
    assert [item['metric'] for item in partial.redacted_payload['measurements']] == ['memory']
    assert partial.coverage['missing_metrics'] == ['cpu']


def test_unknown_metric_shape_stays_unverified_instead_of_guessing_units():
    result = metrics({'cpu': [[NOW, '0.3']], 'memory': [[NOW, '1000']]})
    assert result.coverage['unit_verified'] is False
    assert result.redacted_payload['unit'] == 'unverified'
    assert 'measurements' not in result.redacted_payload


def test_original_provider_values_are_retained_alongside_normalized_metrics():
    payload = {'cpuUsage': [{'applet': 'a', 'value': [NOW, '0.123456789']}], 'memoryUsage': []}
    assert metrics(payload).redacted_payload['provider_data'] == payload


def test_history_reads_documented_since_only_and_selects_native_past_per_applet():
    calls = []
    raw = {'end': NOW+20, 'result': [
        {'applet': 'old', 'values': [[NOW-30, '0.2'], [NOW+1, '9'], [NOW-301, '8'], [NOW-2, 'NaN']]},
        {'applet': 'new', 'values': [[NOW, '0.125'], [NOW-50, '0.3']]},
    ]}
    def respond(request):
        calls.append(request)
        return httpx.Response(200, json=raw)
    client = LiaraClient('private-token', 'team', clock=lambda: NOW, transport=httpx.MockTransport(respond))
    result = client.get_metrics_history(TARGET)
    assert [call.url.path for call in calls] == ['/v1/projects/demo/metrics/cpu', '/v1/projects/demo/metrics/memory']
    assert all(dict(call.url.params) == {'since': str(int(NOW-300)), 'teamID': 'team'} for call in calls)
    assert result.kind == 'metrics_history' and result.quality == 'fresh'
    assert result.redacted_payload['provider_data'] == {'cpu': raw, 'memory': raw}
    samples = result.redacted_payload['measurements']
    assert len(samples) == 4  # Each applet remains separate; no replica sum.
    assert samples[0] == {'metric': 'cpu', 'applet': 'old', 'value': 20, 'unit': 'percent', 'observed_at': NOW-30, 'age_seconds': 30}
    assert samples[1]['observed_at'] == NOW and samples[1]['value'] == 12.5
    assert result.coverage['excluded_future'] == 2
    assert result.coverage['excluded_stale'] == 2
    assert result.coverage['excluded_invalid'] == 2
    assert result.redacted_payload['historical_only'] is True
    assert result.redacted_payload['capacity_assessment'] == 'not_established'


@pytest.mark.parametrize('point,eligible,counter', [
    ([NOW, '0'], True, None), ([NOW-300, '0.1'], True, None),
    ([NOW+.001, '0.1'], False, 'excluded_future'), ([NOW-300.001, '0.1'], False, 'excluded_stale'),
    ([True, '0.1'], False, 'excluded_invalid'), ([NOW, '-1'], False, 'excluded_invalid'),
    ([NOW, 'Infinity'], False, 'excluded_invalid'), ([NOW, True], False, 'excluded_invalid'),
    ([NOW], False, 'excluded_invalid'),
])
def test_historical_eligibility_has_strict_native_timestamp_boundary(point, eligible, counter):
    client = LiaraClient('private-token', 'team', clock=lambda: NOW, transport=httpx.MockTransport(
        lambda _: httpx.Response(200, json={'end': NOW+200, 'result': [{'applet': 'a', 'values': [point]}]})))
    result = client.get_metrics_history(TARGET)
    assert bool(result.redacted_payload['measurements']) is eligible
    assert result.quality == ('fresh' if eligible else 'unavailable')
    if counter:
        assert result.coverage[counter] == 2


def test_history_partial_failure_and_unknown_shape_are_explicit_not_zero_or_summary_repair():
    def respond(request):
        return httpx.Response(403) if request.url.path.endswith('/cpu') else httpx.Response(200, json={'unexpected': []})
    client = LiaraClient('private-token', 'team', clock=lambda: NOW, transport=httpx.MockTransport(respond))
    result = client.get_metrics_history(TARGET)
    assert result.quality == 'unavailable' and result.redacted_payload['measurements'] == []
    assert result.coverage['source_errors'] == {'cpu': 'observer_auth', 'memory': 'invalid_metrics_history_schema'}
