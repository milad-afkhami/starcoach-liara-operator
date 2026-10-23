"""Current account plan selection. Prices are explicit and never default to zero."""

from decimal import Decimal, InvalidOperation, ROUND_CEILING

# Final console review inspected 2026-10-22 includes this tax on both components.
VAT_RATE = Decimal("0.10")


def number(value):
    try:
        result = Decimal(str(value))
        if not result.is_finite() or result < 0:
            raise ValueError("Invalid nonnegative amount")
        return result
    except (InvalidOperation, TypeError) as exc:
        raise ValueError("Unknown amount") from exc


def quote_for(catalogue, plan_id, bundle_id):
    try:
        plan = catalogue["projects"][plan_id]
        bundle = catalogue["projectBundlePlans"][plan_id][bundle_id]
        if plan.get("available") is not True or bundle.get("available") is not True:
            raise ValueError("Unavailable plan or bundle")
        ram, cpu, disk = number(plan["RAM"]["amount"]), number(plan["CPU"]["amount"]), number(plan["volume"])
        if disk != disk.to_integral_value():
            raise ValueError("Unknown disk units")
        hourly = (number(plan["price"]) + number(bundle["displayPrice"]) / 720) * (1 + VAT_RATE)
        return {
            "plan_id": plan_id,
            "bundle_plan_id": bundle_id,
            "hourly_price_toman": str(hourly.to_integral_value(rounding=ROUND_CEILING)),
            "vat_rate": str(VAT_RATE),
            "ram_gb": str(ram),
            "cpu": str(cpu),
            "disk_gb": int(disk),
            "region": plan["region"],
        }
    except (KeyError, TypeError) as exc:
        raise ValueError("Incomplete plan catalogue") from exc


def select_quote(catalogue, *, min_ram_gb="0.5", min_cpu="0.5", min_disk_gb=5):
    ram_floor, cpu_floor, disk_floor = number(min_ram_gb), number(min_cpu), number(min_disk_gb)
    candidates = []
    for plan_id in catalogue.get("projects", {}):
        try:
            q = quote_for(catalogue, plan_id, "basic")
            if (
                q["region"] == "iran"
                and number(q["ram_gb"]) >= ram_floor
                and number(q["cpu"]) >= cpu_floor
                and q["disk_gb"] >= disk_floor
            ):
                candidates.append(q)
        except ValueError:
            continue
    if not candidates:
        raise ValueError("No verified available minimum plan")
    return min(candidates, key=lambda q: (int(q["hourly_price_toman"]), number(q["ram_gb"]), q["plan_id"]))
