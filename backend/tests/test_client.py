import json
import httpx
import pytest
from liara_guard.client import LiaraClient, ProviderError, decode_logs
from liara_guard.types import Target

TEAM = "team-a"
TARGET = Target(team_id=TEAM, app_name="demo-shop", app_id="app-1")
NOW = 1792630800.0


def client(handler, **kw):
    return LiaraClient(
        "test-private-token",
        TEAM,
        transport=httpx.MockTransport(handler),
        clock=lambda: NOW,
        sleep=lambda _: None,
        **kw,
    )


def project(**kw):
    return {
        "_id": "app-1",
        "project_id": "demo-shop",
        "type": "docker",
        "status": "Unhealthy",
        "envs": [{"key": "PASSWORD", "value": "never-expose"}],
        **kw,
    }


def test_inventory_scopes_team_and_drops_environment_without_baseline():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json={"projects": [project()]})

    services = client(handler).list_services()
    assert len(services) == 1 and services[0].target == TARGET
    assert services[0].runtime_state == "Unhealthy" and services[0].target.origin is None
    assert "never-expose" not in services[0].model_dump_json()
    assert seen[0].url.params["teamID"] == TEAM
    assert seen[0].headers["authorization"] == "Bearer test-private-token"


def test_empty_team_is_empty_not_missing():
    assert client(lambda _: httpx.Response(200, json={"projects": []})).list_services() == []


@pytest.mark.parametrize(
    "status,code",
    [
        (401, "observer_auth"),
        (403, "observer_auth"),
        (404, "not_found"),
        (429, "rate_limited"),
        (500, "provider_error"),
    ],
)
def test_http_errors_are_typed_and_safe_reads_have_bounded_retry(status, code):
    seen = []
    c = client(lambda r: seen.append(r) or httpx.Response(status, json={"token": "should-not-escape"}))
    with pytest.raises(ProviderError) as error:
        c.list_services()
    assert error.value.code == code and "should-not-escape" not in str(error.value)
    assert len(seen) == (2 if status in (429, 500) else 1)


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        {"projects": None},
        {"projects": [{"_id": "missing-name"}]},
        {"projects": [project(teamID="other-team")]},
    ],
)
def test_malformed_or_wrong_team_inventory_is_not_accepted(payload):
    with pytest.raises(ProviderError):
        client(lambda _: httpx.Response(200, json=payload)).list_services()


def test_wrong_team_target_never_sends_request():
    seen = []
    c = client(lambda r: seen.append(r) or httpx.Response(200, json={}))
    with pytest.raises(ProviderError):
        c.get_project(TARGET.model_copy(update={"team_id": "other-team"}))
    assert seen == []


def test_provider_project_identity_mismatch_is_rejected():
    c = client(lambda _: httpx.Response(200, json={"project": project(_id="different-app")}))
    with pytest.raises(ProviderError) as error:
        c.get_project(TARGET)
    assert error.value.code == "target_mismatch"


def test_project_details_strip_secrets_and_preserve_actual_fields():
    c = client(lambda _: httpx.Response(200, json={"project": project(hourlyPrice=1040, scale=0)}))
    result = c.get_project(TARGET)
    assert result["hourlyPrice"] == 1040 and result["scale"] == 0
    assert "envs" not in result and "never-expose" not in json.dumps(result)


def test_oversized_response_is_bounded_and_not_reported_healthy():
    c = client(lambda _: httpx.Response(200, content=b"x" * 524289))
    with pytest.raises(ProviderError) as error:
        c.list_services()
    assert error.value.code == "response_too_large"


def test_redirect_does_not_forward_credentials():
    seen = []
    c = client(
        lambda r: (
            seen.append(str(r.url)) or httpx.Response(302, headers={"location": "https://evil.example/"})
        )
    )
    with pytest.raises(ProviderError):
        c.list_services()
    assert len(seen) == 1


def test_v2_logs_preserve_nanoseconds_release_and_redact_sensitive_text():
    payload = {
        "data": [
            {
                "metaData": {"releaseId": "r1"},
                "values": [
                    [
                        "1792630799123456789",
                        json.dumps({"_entry": "api_key=abc123 Bearer secret-token", "type": "stderr"}),
                    ]
                ],
            }
        ]
    }
    result = decode_logs(payload, "v2")
    assert result[0]["timestamp"] == "1792630799123456789" and result[0]["release_id"] == "r1"
    assert "abc123" not in result[0]["message"] and "secret-token" not in result[0]["message"]


def test_legacy_logs_decode_explicitly_and_reject_wrong_shape():
    payload = [{"datetime": "2026-10-22T00:59:59.123456Z", "type": "stderr", "message": "upstream failed"}]
    result = decode_logs(payload, "v1")
    assert result[0]["timestamp"] == payload[0]["datetime"] and result[0]["message"] == "upstream failed"
    with pytest.raises(ProviderError):
        decode_logs(payload, "v2")
    with pytest.raises(ProviderError):
        decode_logs({"data": []}, "v1")


def test_logs_bound_window_lines_and_keep_empty_and_stale_distinct():
    seen = []
    payload = {
        "data": [
            {
                "metaData": {"releaseId": "r1"},
                "values": [
                    [str(int((NOW - 400) * 1e9) + i), json.dumps({"_entry": "old line", "type": "stdout"})]
                    for i in range(510)
                ],
            }
        ]
    }
    c = client(lambda r: seen.append(r) or httpx.Response(200, json=payload), log_version="v2")
    evidence = c.get_logs(TARGET, since=NOW - 3600)
    assert seen[0].url.params["start"] == str(int(NOW - 300))
    assert len(evidence.redacted_payload["lines"]) == 500 and evidence.coverage["truncated"]
    assert evidence.quality == "stale" and evidence.available_at == NOW
    empty = client(lambda _: httpx.Response(200, json={"data": []})).get_logs(TARGET, since=NOW - 300)
    assert empty.quality == "fresh" and empty.coverage["empty"]


def test_missing_metrics_and_unknown_units_never_become_zero_percent():
    c = client(lambda _: httpx.Response(200, json={"cpu": [[NOW, "0.3"]], "memory": [[NOW, "1000"]]}))
    value = c.get_metrics(TARGET)
    assert value.coverage["unit_verified"] is False
    assert value.redacted_payload["unit"] == "unverified"
    absent = client(lambda _: httpx.Response(404)).get_metrics(TARGET)
    assert absent.quality == "unavailable" and absent.redacted_payload["error"] == "not_found"


def test_recent_events_are_bounded_and_logs_capability_is_explicit():
    seen = []
    c = client(lambda r: seen.append(r) or httpx.Response(200, json={"events": []}))
    result = c.get_events(TARGET, start=NOW - 900, end=NOW + 1)
    assert result.redacted_payload["events"] == []
    assert float(seen[0].url.params["start"]) == NOW - 300
    assert float(seen[0].url.params["end"]) == NOW


def test_registered_name_cannot_be_reused_with_another_identity():
    seen = []
    c = client(lambda r: seen.append(r) or httpx.Response(200, json={"projects": [project()]}))
    c.list_services()
    with pytest.raises(ProviderError):
        c.get_logs(TARGET.model_copy(update={"app_id": "other"}), NOW - 10)
    assert len(seen) == 1


def test_log_error_and_future_timestamp_are_not_current_service_failure():
    error = client(lambda _: httpx.Response(401)).get_logs(TARGET, NOW - 30)
    assert error.quality == "unavailable" and error.redacted_payload["error"] == "observer_auth"
    payload = {
        "data": [
            {
                "metaData": {"releaseId": "r"},
                "values": [[str(int((NOW + 60) * 1e9)), json.dumps({"_entry": "future"})]],
            }
        ]
    }
    future = client(lambda _: httpx.Response(200, json=payload)).get_logs(TARGET, NOW - 30)
    assert future.quality == "invalid"


def test_release_and_applet_chronology_preserve_identity_not_environment():
    def handler(request):
        if request.url.path.endswith("/releases"):
            return httpx.Response(
                200,
                json={
                    "currentRelease": "r2",
                    "releases": [
                        {
                            "_id": "r2",
                            "state": "READY",
                            "createdAt": "2026-10-22T01:00:00Z",
                            "gitInfo": {"author": {"email": "private"}},
                        }
                    ],
                },
            )
        return httpx.Response(
            200,
            json={
                "applets": [
                    {
                        "id": "a",
                        "state": "Running",
                        "release": {"releaseID": "r2", "tag": "v2"},
                        "envs": {"PASSWORD": "private"},
                    }
                ]
            },
        )

    c = client(handler)
    release = c.get_releases(TARGET)
    applet = c.get_applets(TARGET)
    assert release.redacted_payload["currentRelease"] == "r2"
    assert applet.redacted_payload["applets"][0]["release"]["releaseID"] == "r2"
    assert "private" not in release.model_dump_json() + applet.model_dump_json()


def test_json_nonfinite_values_rejected_and_log_times_require_timezone():
    with pytest.raises(ProviderError):
        client(lambda _: httpx.Response(200, content=b'{"projects":[],"x":NaN}')).list_services()
    with pytest.raises(ProviderError):
        decode_logs([{"datetime": "2026-10-22T00:00:00", "type": "stdout", "message": "line"}], "v1")


def test_read_budget_bounds_a_slow_chunk_stream(monkeypatch):
    ticks = iter([0, 11, 12, 13])
    monkeypatch.setattr("liara_guard.client.time.monotonic", lambda: next(ticks, 13))

    class Slow(httpx.SyncByteStream):
        def __iter__(self):
            yield b'{"projects":[]}'

    c = client(lambda _: httpx.Response(200, stream=Slow()))
    with pytest.raises(ProviderError) as error:
        c.list_services()
    assert error.value.code == "read_budget_exceeded"
