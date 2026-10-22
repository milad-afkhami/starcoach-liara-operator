import importlib.util
from pathlib import Path
import httpx
import pytest
from fastapi.testclient import TestClient
from liara_guard.contracts import RegisteredHttpCheck, ProbeRunner, unsafe_origin
from liara_guard.types import Target

ROOT = Path(__file__).parents[2]


def load_app(name):
    spec = importlib.util.spec_from_file_location("demo_" + name, ROOT / "demo" / name / "app.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_real_dependency_contract_and_request_build_propagation():
    seen = []

    def upstream(request):
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "shipping_toman": 10000,
                "build_id": "opaque-dep",
                "request_id": request.headers["x-request-id"],
            },
        )

    app = load_app("storefront").create_app(
        build_id="opaque-store",
        dependency_origin="http://127.0.0.1:8772",
        transport=httpx.MockTransport(upstream),
    )
    with TestClient(app) as c:
        r = c.get("/preview", headers={"x-request-id": "request-001"})
        assert r.status_code == 200 and r.json()["dependency_build_id"] == "opaque-dep"
        assert r.json()["build_id"] == "opaque-store" and r.json()["request_id"] == "request-001"
        assert seen[0].url.path == "/quote" and seen[0].headers["x-request-id"] == "request-001"
        assert r.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(
    "payload",
    [
        {"delivery_toman": 10000},
        {"shipping_toman": "10000"},
        {"shipping_toman": True},
        {"shipping_toman": -1},
        {"shipping_toman": 10000, "request_id": "old"},
    ],
)
def test_schema_regression_is502_while_liveness_stays200(payload):
    def upstream(request):
        return httpx.Response(
            200, json={"build_id": "opaque-dep", "request_id": request.headers["x-request-id"], **payload}
        )

    app = load_app("storefront").create_app(
        build_id="opaque-store",
        dependency_origin="http://127.0.0.1:8772",
        transport=httpx.MockTransport(upstream),
    )
    with TestClient(app) as c:
        r = c.get("/preview")
        assert r.status_code == 502
        assert r.json()["reason"] == "upstream_invalid"
        assert c.get("/healthz").status_code == 200
        assert "scenario" not in r.text and "fault" not in r.text


def test_dependency_timeout_is_a_distinct_observed_reason():
    def upstream(request):
        raise httpx.ReadTimeout("slow", request=request)

    app = load_app("storefront").create_app(
        build_id="opaque", dependency_origin="http://127.0.0.1:8772", transport=httpx.MockTransport(upstream)
    )
    with TestClient(app) as c:
        assert c.get("/preview").json()["reason"] == "upstream_timeout"


def test_delivery_endpoint_has_opaque_identity_and_actual_key():
    app = load_app("delivery").create_app(build_id="dep-v1")
    with TestClient(app) as c:
        data = c.get("/quote", headers={"x-request-id": "request-001"}).json()
        assert data == {"shipping_toman": 10000, "build_id": "dep-v1", "request_id": "request-001"}
        assert c.get("/healthz").json()["build_id"] == "dep-v1"


def target(origin="https://demo-shop.liara.run"):
    return Target(team_id="team", app_name="demo-shop", app_id="app", origin=origin)


def check(**kw):
    return RegisteredHttpCheck(
        id="preview", target_id="app", origin="https://demo-shop.liara.run", path="/preview", **kw
    )


@pytest.mark.parametrize(
    "origin",
    [
        "http://public.example",
        "https://u:p@public.example",
        "https://127.0.0.1",
        "https://169.254.169.254",
        "https://[::1]",
        "https://public.example/path",
        "https://public.example?token=x",
    ],
)
def test_unregistered_or_unsafe_origin_is_rejected(origin):
    assert unsafe_origin(origin, allow_loopback=False)


def test_probe_pins_approved_destination_retains_sanitized_payload():
    seen = []
    runner = ProbeRunner(
        {"app": target()},
        resolver=lambda *_: ["93.184.216.34"],
        transport=httpx.MockTransport(
            lambda r: (
                seen.append(r)
                or httpx.Response(200, json={"build_id": "dep-v1", "shipping_toman": 10000, "token": "never"})
            )
        ),
    )
    result = runner.run(check(), request_id="unique-1")
    assert result.check_pass is True and result.http_status == 200
    assert result.payload["shipping_toman"] == 10000 and result.payload["token"] == "[redacted]"
    assert seen[0].headers["x-request-id"] == "unique-1"
    assert result.request_id == "unique-1" and result.body_digest


def test_duplicate_request_id_never_counts_as_fresh_probe():
    runner = ProbeRunner(
        {"app": target()},
        resolver=lambda *_: ["93.184.216.34"],
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={})),
    )
    runner.run(check(), request_id="same")
    with pytest.raises(ValueError):
        runner.run(check(), request_id="same")


def test_private_dns_and_redirect_never_follow_unregistered_destination():
    seen = []
    transport = httpx.MockTransport(
        lambda r: seen.append(r) or httpx.Response(302, headers={"location": "http://169.254.169.254"})
    )
    denied = ProbeRunner({"app": target()}, resolver=lambda *_: ["10.0.0.1"], transport=transport).run(
        check(), request_id="p1"
    )
    assert denied.check_pass is None and denied.reason == "unsafe_destination" and seen == []
    redirected = ProbeRunner(
        {"app": target()}, resolver=lambda *_: ["93.184.216.34"], transport=transport
    ).run(check(), request_id="p2")
    assert redirected.check_pass is False and redirected.http_status == 302 and len(seen) == 1


def test_probe_target_path_and_fixture_loopback_must_be_explicit():
    with pytest.raises(ValueError):
        RegisteredHttpCheck(
            id="p", target_id="app", origin="https://demo-shop.liara.run", path="//evil.example"
        )
    with pytest.raises(ValueError):
        ProbeRunner({"app": target()}, transport=httpx.MockTransport(lambda _: httpx.Response(200))).run(
            check().model_copy(update={"origin": "https://other.liara.run"}), request_id="x"
        )
    local = target("http://127.0.0.1:8772")
    c = check().model_copy(update={"origin": local.origin})
    r = ProbeRunner(
        {"app": local},
        allow_loopback=True,
        resolver=lambda *_: ["127.0.0.1"],
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={})),
    ).run(c, request_id="local")
    assert r.check_pass is True


def test_probe_body_is_bounded_and_network_timeout_is_not_zero_latency():
    r = ProbeRunner(
        {"app": target()},
        resolver=lambda *_: ["93.184.216.34"],
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"x" * 4097)),
    ).run(check(), request_id="large")
    assert r.check_pass is None and r.reason == "response_too_large"

    def timeout(request):
        raise httpx.ReadTimeout("timeout", request=request)

    r = ProbeRunner(
        {"app": target()}, resolver=lambda *_: ["93.184.216.34"], transport=httpx.MockTransport(timeout)
    ).run(check(), request_id="timeout")
    assert r.http_status is None and r.check_pass is False and r.reason == "timeout"


def test_real_transport_connects_to_resolved_ip_with_original_tls_identity(monkeypatch):
    from liara_guard.contracts import PinnedTransport

    captured = []

    class Inner:
        def handle_request(self, request):
            captured.append(request)
            return httpx.Response(200)

        def close(self):
            pass

    monkeypatch.setattr(httpx, "HTTPTransport", lambda **_: Inner())
    t = PinnedTransport("93.184.216.34", "demo-shop.liara.run", 443, "https")
    t.handle_request(httpx.Request("GET", "https://demo-shop.liara.run/preview"))
    assert captured[0].url.host == "93.184.216.34"
    assert captured[0].headers["host"] == "demo-shop.liara.run"
    assert captured[0].extensions["sni_hostname"] == b"demo-shop.liara.run"


def test_required_echo_rejects_cached_response_even_when_http200():
    runner = ProbeRunner(
        {"app": target()},
        resolver=lambda *_: ["93.184.216.34"],
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={"request_id": "old"})),
    )
    result = runner.run(check(require_request_echo=True), request_id="fresh")
    assert result.check_pass is False and result.reason == "request_id_mismatch"
