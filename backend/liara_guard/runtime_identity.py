"""Fail-closed identity for network runtimes, reconstructed from bounded lifecycle history."""
from datetime import datetime
import time


class IncompleteHistory(ValueError):
    pass


def network_runtime_identity(project, known_releases, read_events, *, now, monotonic=time.monotonic):
    coverage = {'complete_interval': False, 'event_count': 0, 'requests': 0,
                'derived': True, 'uncertainty': 'event-derived identity; fresh original build probes remain required'}
    result = {'serving_release_ids': [], 'identity_source': 'network_lifecycle_events',
              'observed_at': now, 'coverage': coverage}

    def reject(reason):
        coverage['reason'] = reason
        return result

    if not isinstance(project.get('network'), dict) or not project['network'].get('_id'):
        return reject('network_runtime_not_confirmed')
    if not isinstance(project.get('created_at'), str):
        return reject('missing_creation_anchor')
    try:
        created = datetime.fromisoformat(project['created_at'].replace('Z', '+00:00'))
        if created.tzinfo is None or not 0 <= now-created.timestamp() <= 86400:
            return reject('invalid_creation_anchor')
    except ValueError:
        return reject('invalid_creation_anchor')
    if type(project.get('scale')) is not int or not 1 <= project['scale'] <= 10:
        return reject('invalid_scale')
    start, end = int(created.timestamp())-1, int(now)+1
    coverage.update(creation_anchor=created.timestamp(), history_start=start, history_end=end,
                    max_requests=12, max_events=200, max_history_seconds=86400)
    deadline = monotonic()+10
    all_events = {}
    largest_page = 0

    def fetch(left, right):
        if coverage['requests'] >= 12 or monotonic() >= deadline:
            raise IncompleteHistory('history_budget_exceeded')
        coverage['requests'] += 1
        body = read_events(left, right)
        if monotonic() >= deadline:
            raise IncompleteHistory('history_budget_exceeded')
        if (not isinstance(body, dict) or not isinstance(body.get('data'), list)
                or set(body)-{'data','truncated','has_more','hasMore','next'}
                or any(body.get(key) for key in ('truncated', 'has_more', 'hasMore', 'next'))):
            raise IncompleteHistory('history_completeness_unavailable')
        rows = body['data']
        if len(rows) > 200:
            raise IncompleteHistory('history_truncated')
        previous = None
        for event in rows:
            if (not isinstance(event, dict)
                    or not all(isinstance(event.get(key), str) and event[key] for key in ('id','action','time','release'))
                    or any(len(event[key]) > 200 for key in ('id','release'))
                    or not event['time'].isdigit()):
                raise IncompleteHistory('malformed_history')
            at = int(event['time'])
            if not left <= at < right or at > now+5:
                raise IncompleteHistory('history_interval_not_honored')
            if previous is not None and at > previous:
                raise IncompleteHistory('history_order_unknown')
            previous = at
        return rows

    def add(rows):
        for row in rows:
            key = (row['id'], row['time'], row['action'], row['release'])
            all_events[key] = row
        if len(all_events) > 200:
            raise IncompleteHistory('history_truncated')
        coverage['event_count'] = len(all_events)

    try:
        while end >= start:
            rows = fetch(start, end)
            if not rows:
                coverage['empty_older_interval'] = True
                break
            largest_page = max(largest_page, len(rows))
            add(rows)
            boundary = min(int(row['time']) for row in rows)
            # Console-supported pagination uses end timestamps. A separate exact-second
            # read must fit below an already observed page size, otherwise a same-second
            # server page limit could hide another container and identity stays unknown.
            bucket = fetch(boundary, boundary+1)
            if not bucket or len(bucket) >= largest_page:
                raise IncompleteHistory('boundary_completeness_unknown')
            if not {key for key in all_events if int(key[1]) == boundary}.issubset(
                    {(row['id'],row['time'],row['action'],row['release']) for row in bucket}):
                raise IncompleteHistory('history_changed_during_read')
            add(bucket)
            end = boundary
        else:
            coverage['empty_older_interval'] = True
        if not all_events:
            raise IncompleteHistory('missing_history')
        containers = {}
        for event in sorted(all_events.values(), key=lambda row: int(row['time'])):
            key, action, release, at = event['id'], event['action'], event['release'], int(event['time'])
            previous = containers.get(key)
            if previous is None:
                if action != 'create':
                    raise IncompleteHistory('missing_container_creation')
                containers[key] = {'state': 'created', 'release': release, 'at': at}
                continue
            if release != previous['release'] or at < previous['at']:
                raise IncompleteHistory('ambiguous_container_history')
            if at == previous['at']:
                # Terminal actions commute: kill/die/destroy in one provider second
                # all establish inactivity. Create/start or restart ties remain unknown.
                if previous['state'] in ('stopped','destroyed') and action in ('stop','die','kill','oom','destroy'):
                    previous['state'] = 'destroyed' if action == 'destroy' or previous['state'] == 'destroyed' else 'stopped'
                    continue
                raise IncompleteHistory('ambiguous_container_history')
            if action == 'start':
                if previous['state'] not in ('created','stopped'):
                    raise IncompleteHistory('impossible_container_history')
                state = 'running'
            elif action in ('stop','die','kill','oom'):
                if previous['state'] == 'destroyed':
                    raise IncompleteHistory('impossible_container_history')
                state = 'stopped'
            elif action == 'destroy':
                state = 'destroyed'
            elif action == 'restart':
                state = 'restarting'
            elif action == 'exec_die' or action.startswith('exec_start'):
                state = previous['state']
            else:
                raise IncompleteHistory('unknown_lifecycle_action')
            containers[key] = {'state': state, 'release': release, 'at': at}
        if any(value['state'] in ('created','restarting') for value in containers.values()):
            raise IncompleteHistory('container_transition_incomplete')
        active = [value for value in containers.values() if value['state'] == 'running']
        if len(active) != project['scale']:
            raise IncompleteHistory('active_count_mismatch')
        if any(value['release'] not in known_releases for value in active):
            raise IncompleteHistory('active_release_unknown')
        result['serving_release_ids'] = [value['release'] for value in active]
        coverage.update(complete_interval=True, reason='complete_lifecycle_history',
                        active_count=len(active), container_count=len(containers),
                        boundary_check='exact-second bucket below observed page-size lower bound')
        return result
    except IncompleteHistory as exc:
        return reject(str(exc))
    except Exception:
        return reject('history_read_unavailable')
