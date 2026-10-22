import pytest
from liara_guard.runtime import Registry, FixtureProvider
from liara_guard.types import Target, ServiceSummary


def service():
    return ServiceSummary(
        target=Target(team_id="team", app_name="existing", app_id="app"),
        platform="docker",
        runtime_state="Unhealthy",
        observed_at=100,
    )


def test_existing_failing_or_endpointless_service_needs_no_artifact():
    r = Registry("team", {})
    r.refresh([service()])
    assert r.resolve("app").origin is None and r.checks_for("app") == []
    assert r.can_repair("app") is False


def test_registry_binds_check_and_dependency_to_real_scoped_identity():
    cfg = {
        "http_checks": [
            {"id": "health", "target_id": "app", "origin": "https://existing.liara.run", "path": "/healthz"}
        ]
    }
    r = Registry("team", cfg)
    r.refresh([service()])
    assert r.resolve("app").origin == "https://existing.liara.run"
    with pytest.raises(ValueError):
        r.refresh(
            [
                service().model_copy(
                    update={"target": Target(team_id="other", app_name="existing", app_id="app")}
                )
            ]
        )
    with pytest.raises(KeyError):
        r.resolve("missing")


def test_registry_rejects_public_private_url_and_unknown_dependencies():
    with pytest.raises(ValueError):
        Registry(
            "team",
            {"http_checks": [{"id": "x", "target_id": "app", "origin": "https://127.0.0.1", "path": "/"}]},
        )
    r = Registry("team", {"dependencies": {"app": ["missing"]}})
    with pytest.raises(ValueError):
        r.refresh([service()])


def test_fixture_provider_is_explicit_and_does_not_invent_resources(tmp_path):
    p = FixtureProvider(tmp_path)
    services = p.list_services()
    assert len(services) == 2
    metric = p.get_metrics(services[0].target)
    assert metric.quality == "unavailable" and metric.coverage["provider_fixture"] is True
    logs = p.get_logs(services[0].target, 0)
    assert logs.quality == "unavailable"
