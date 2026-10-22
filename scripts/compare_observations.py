"""Compare restricted observation baselines with existing actual synthetic diagnoses."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    fixtures = json.loads((ROOT / "harness/fixtures/diagnostic-cases.json").read_text())
    actual = json.loads((ROOT / "results/diagnosis.json").read_text())
    by_name = {case["case"]: case for case in actual["cases"]}
    assert len(by_name) == len(fixtures) == 8
    rows = []
    for case in fixtures:
        http = [
            payload
            for kind, quality, age, payload in case["evidence"]
            if kind == "http_probe" and quality == "fresh" and age <= 300
        ]
        releases = [
            payload
            for kind, quality, age, payload in case["evidence"]
            if kind == "releases" and quality == "fresh" and age <= 300
        ]
        statuses = [p.get("http_status") for p in http]
        http_state = (
            "failed"
            if any(isinstance(s, int) and s >= 400 for s in statuses)
            else "passing"
            if statuses and all(s == 200 for s in statuses)
            else "unknown"
        )
        result = by_name[case["name"]]
        rows.append(
            {
                "case": case["name"],
                "http_only": {
                    "state": http_state,
                    "statuses": statuses,
                    "causal_conclusion": "not_established",
                },
                "latest_release_only": {
                    "fresh_release_payload_present": bool(releases),
                    "causal_conclusion": "not_established",
                },
                "observed_model": {
                    "cause_family": result["diagnosis"]["cause_family"],
                    "outcome": result["diagnosis"]["outcome"],
                    "expected_case_outcome": result["correct"],
                    "elapsed_ms": result["elapsed_ms"],
                },
            }
        )
    report = {
        "scope": "Restricted observation baselines on the same eight synthetic cases. These are intentionally small non-diagnostic baselines, not production SRE competitors. Model outputs are the existing actual recorded run; no new inference.",
        "comparison_limits": "HTTP state answers endpoint availability from supplied observations; release metadata answers whether a change is visible. Neither alone establishes cause. Cause accuracy is therefore not scored against these different-output baselines. No production savings or live Liara success is measured.",
        "cases": rows,
        "model_correct": sum(r["observed_model"]["expected_case_outcome"] for r in rows),
        "total": len(rows),
    }
    output = ROOT / "results/observation-baselines.json"
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {"rows": len(rows), "observed_model_correct": report["model_correct"], "output": str(output)}
        )
    )


if __name__ == "__main__":
    main()
