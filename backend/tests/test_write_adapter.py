import httpx
import pytest
from liara_guard.client import LiaraClient
from liara_guard.approvals import OperationSpec, AmbiguousWrite, RejectedWrite


def spec(**extra):
    return OperationSpec(
        kind="deploy_initial",
        team_id="team",
        app_name="demo",
        app_id="app",
        artifact_sha256="a" * 64,
        **extra,
    )


def test_source_and_release_use_exact_scoped_contract_and_do_not_retry():
    requests = []

    def handle(r):
        requests.append(r)
        return httpx.Response(
            200, json={"sourceID": "s"} if r.url.path.endswith("/sources") else {"releaseID": "r"}
        )

    c = LiaraClient("token", "team", transport=httpx.MockTransport(handle))
    assert c.upload_source(spec(), b"approved archive") == "s"
    assert c.create_release(spec(), "s") == "r"
    assert all(r.url.params["teamID"] == "team" for r in requests)
    assert requests[0].url.path == "/v2/projects/demo/sources" and b"approved archive" in requests[0].read()
    assert requests[1].content == b'{"sourceID":"s","port":8000,"type":"docker"}'


@pytest.mark.parametrize(
    "status,kind",
    [
        (400, RejectedWrite),
        (401, RejectedWrite),
        (409, RejectedWrite),
        (500, AmbiguousWrite),
        (302, AmbiguousWrite),
    ],
)
def test_write_errors_never_use_generic_read_retry(status, kind):
    calls = []
    c = LiaraClient(
        "token", "team", transport=httpx.MockTransport(lambda r: calls.append(r) or httpx.Response(status))
    )
    with pytest.raises(kind):
        c.create_release(spec(), "s")
    assert len(calls) == 1


def test_write_timeout_and_missing_returned_identity_are_unknown():
    calls = []

    def timeout(r):
        calls.append(r)
        raise httpx.ReadTimeout("unknown", request=r)

    c = LiaraClient("token", "team", transport=httpx.MockTransport(timeout))
    with pytest.raises(AmbiguousWrite):
        c.upload_source(spec(), b"archive")
    assert len(calls) == 1
    c = LiaraClient("token", "team", transport=httpx.MockTransport(lambda _: httpx.Response(200, json={})))
    with pytest.raises(AmbiguousWrite):
        c.create_release(spec(), "s")


def test_mismatched_team_or_unbounded_source_never_writes():
    calls = []
    c = LiaraClient("token", "team", transport=httpx.MockTransport(lambda r: calls.append(r)))
    with pytest.raises(ValueError):
        c.upload_source(spec().model_copy(update={"team_id": "other"}), b"archive")
    with pytest.raises(ValueError):
        c.upload_source(spec(), b"x" * (5 * 1024 * 1024 + 1))
    assert calls == []
