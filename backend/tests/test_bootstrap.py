import httpx
import pytest
from liara_guard.bootstrap import select_quote, quote_for
from liara_guard.client import LiaraClient
from liara_guard.approvals import OperationSpec


def catalogue():
    return {
        "projects": {
            "g2-small": {
                "available": True,
                "region": "iran",
                "RAM": {"amount": 0.5},
                "CPU": {"amount": 0.5},
                "volume": 5,
                "price": "659.7222222222",
            },
            "g2-medium": {
                "available": True,
                "region": "iran",
                "RAM": {"amount": 1},
                "CPU": {"amount": 1},
                "volume": 10,
                "price": "1000",
            },
        },
        "projectBundlePlans": {
            "g2-small": {"basic": {"available": True, "displayPrice": 275000}},
            "g2-medium": {"basic": {"available": True, "displayPrice": 400000}},
        },
    }


def test_selects_measured_minimum_with_explicit_bundle_and_tax():
    quote = select_quote(catalogue())
    assert quote["plan_id"] == "g2-small" and quote["bundle_plan_id"] == "basic"
    assert quote["hourly_price_toman"] == "1146" and quote["vat_rate"] == "0.10"
    assert quote["ram_gb"] == "0.5" and quote["disk_gb"] == 5


def test_unknown_or_unavailable_price_is_not_a_zero_cost_quote():
    data = catalogue()
    data["projects"]["g2-small"]["available"] = False
    assert select_quote(data)["plan_id"] == "g2-medium"
    with pytest.raises(ValueError):
        quote_for(data, "g2-small", "basic")
    data["projects"]["g2-medium"]["price"] = "NaN"
    with pytest.raises(ValueError):
        select_quote(data)


def test_scoped_plan_network_reads_drop_unrelated_profile_fields():
    requests = []

    def handler(request):
        requests.append(request)
        return (
            httpx.Response(200, json={"plans": catalogue(), "email": "never-return", "token": "private"})
            if request.url.path.endswith("/me")
            else httpx.Response(
                200, json={"networks": [{"_id": "net", "name": "contest", "secret": "never-return"}]}
            )
        )

    client = LiaraClient("token", "team", transport=httpx.MockTransport(handler))
    assert client.plan_catalogue() == catalogue()
    assert client.list_networks() == [{"id": "net", "name": "contest"}]
    assert all(r.url.params["teamID"] == "team" for r in requests)


def test_create_requires_explicit_feature_bundle_and_network():
    with pytest.raises(ValueError):
        OperationSpec(
            kind="create_app",
            team_id="team",
            app_name="demo",
            plan_id="g2-small",
            hourly_price_toman="1146",
            price_verified_at=100,
        )


def test_user_requirements_choose_a_matching_plan_without_claiming_load_capacity():
    assert select_quote(catalogue(), min_ram_gb='1', min_cpu='1', min_disk_gb=10)['plan_id'] == 'g2-medium'
    with pytest.raises(ValueError):
        select_quote(catalogue(), min_ram_gb='8', min_cpu='2', min_disk_gb=5)
