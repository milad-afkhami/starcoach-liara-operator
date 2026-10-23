"""Strict normalization of the summary contract used by Liara's public console."""
from decimal import Decimal, InvalidOperation
import math

UNIT_SOURCE = {
    'url': 'https://console.liara.ir/static/js/main.25f709b7.js',
    'sha256': 'd3e0d8646a7dde8e13f42b22fb659b1bb135531d069b0b0c2024a57ed983f5ec',
    'inspected_at': '2026-10-22',
    'cpu_denominator': 'provider_reported_ratio',
}


def nonnegative(value):
    if type(value) not in (int, float, str):
        raise ValueError('invalid_metrics_schema')
    try:
        number = Decimal(str(value))
        if not number.is_finite() or number < 0 or not math.isfinite(float(number)):
            raise ValueError('invalid_metrics_schema')
        return number
    except InvalidOperation as exc:
        raise ValueError('invalid_metrics_schema') from exc


def normalize_summary(payload, now):
    # Field names alone do not establish a unit. Unknown schemas stay raw/unverified.
    if not any(field in payload for field in ('cpuUsage', 'memoryUsage')):
        return None
    measurements = []
    sample_times = []
    missing = []
    truncated = False
    for field, metric, unit, multiplier in [('cpuUsage', 'cpu', 'percent', 100), ('memoryUsage', 'memory', 'bytes', 1)]:
        rows = payload.get(field, [])
        if not isinstance(rows, list):
            raise ValueError('invalid_metrics_schema')
        if not rows:
            missing.append(metric)
        for index, row in enumerate(rows):
            if (not isinstance(row, dict) or not isinstance(row.get('applet'), str)
                    or not row['applet'] or len(row['applet']) > 200
                    or not isinstance(row.get('value'), list) or len(row['value']) != 2):
                raise ValueError('invalid_metrics_schema')
            observed = float(nonnegative(row['value'][0]))
            value = float(nonnegative(row['value'][1]) * multiplier)
            if not math.isfinite(value):
                raise ValueError('invalid_metrics_schema')
            sample_times.append(observed)
            if index < 100:
                measurements.append({'metric': metric, 'applet': row['applet'], 'value': value,
                                     'unit': unit, 'observed_at': observed})
            else:
                truncated = True
    if not sample_times:
        raise ValueError('metrics_empty')
    oldest, newest = min(sample_times), max(sample_times)
    quality = 'invalid' if newest > now + 5 else 'stale' if now - oldest > 300 else 'fresh'
    return (
        {'unit': 'verified', 'measurements': measurements, 'unit_source': UNIT_SOURCE,
         'provider_data': payload, 'capacity_assessment': 'not_established', 'snapshot_only': True},
        {'unit_verified': True, 'threshold_evaluated': False, 'missing_metrics': missing,
         'truncated': truncated, 'sample_count': len(sample_times)},
        quality, newest if quality == 'invalid' else oldest,
    )


def normalize_history(sources, cutoff, source_errors=None):
    """Native past observations only; a range response never repairs summary clock quality."""
    selected = {}
    counts = {name: 0 for name in ('excluded_future', 'excluded_stale', 'excluded_invalid', 'eligible_points')}
    errors = dict(source_errors or {})
    for metric, payload in sources.items():
        if not isinstance(payload, dict) or not isinstance(payload.get('result'), list):
            errors[metric] = 'invalid_metrics_history_schema'
            continue
        for series in payload['result']:
            if (not isinstance(series, dict) or not isinstance(series.get('applet'), str)
                    or not 1 <= len(series['applet']) <= 200 or not isinstance(series.get('values'), list)):
                counts['excluded_invalid'] += 1
                continue
            for point in series['values']:
                try:
                    if not isinstance(point, list) or len(point) != 2:
                        raise ValueError('invalid_metrics_history_point')
                    stamp = float(nonnegative(point[0]))
                    value = float(nonnegative(point[1]) * (100 if metric == 'cpu' else 1))
                    if not math.isfinite(value):
                        raise ValueError('invalid_metrics_history_point')
                except (ValueError, OverflowError):
                    counts['excluded_invalid'] += 1
                    continue
                if stamp > cutoff:
                    counts['excluded_future'] += 1
                    continue
                if cutoff-stamp > 300:
                    counts['excluded_stale'] += 1
                    continue
                counts['eligible_points'] += 1
                key = (metric, series['applet'])
                if key not in selected or stamp > selected[key]['observed_at']:
                    selected[key] = {'metric': metric, 'applet': series['applet'], 'value': value,
                                     'unit': 'percent' if metric == 'cpu' else 'bytes',
                                     'observed_at': stamp, 'age_seconds': cutoff-stamp}
    measurements = list(selected.values())[:100]
    coverage = {**counts, 'unit_verified': True, 'threshold_evaluated': False, 'source_errors': errors,
                'truncated': len(selected) > 100, 'selected_count': len(measurements),
                'missing_metrics': [metric for metric in ('cpu', 'memory') if not any(m['metric'] == metric for m in measurements)]}
    payload = {'unit': 'verified', 'historical_only': True, 'cutoff': cutoff, 'window_start': cutoff-300,
               'measurements': measurements, 'provider_data': sources, 'unit_source': UNIT_SOURCE,
               'source': '/v1/projects/{app}/metrics/{cpu,memory}?since=window_start',
               'capacity_assessment': 'not_established',
               'clock_uncertainty': 'Past relative to observer cutoff only; summary/provider/observer clock agreement is not established.'}
    return payload, coverage, 'fresh' if measurements else 'unavailable', min((m['observed_at'] for m in measurements), default=cutoff)
