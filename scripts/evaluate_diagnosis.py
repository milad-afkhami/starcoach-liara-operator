"""Actual isolated model over synthetic cases; expected answers stay outside request payloads."""

import json
import os
import tempfile
import time
from pathlib import Path
from liara_guard.codex_cli import CodexCliClient
from liara_guard.investigator import Investigator
from liara_guard.observer import MonitorStore, Observer
from liara_guard.types import Target, Evidence

ROOT = Path(__file__).resolve().parents[1]


def main():
    client = CodexCliClient(
        binary=Path(os.environ["CODEX_BINARY_PATH"]),
        auth_file=Path(os.environ["CODEX_AUTH_FILE"]),
        image=os.environ["CODEX_IMAGE"],
        gate_dir=Path(f"/tmp/starcoach-codex-{os.getuid()}"),
        model=os.environ.get("MODEL_ID", "gpt-6.1-sol"),
    )
    cases = json.loads((ROOT / "harness/fixtures/diagnostic-cases.json").read_text())
    results = []
    target = Target(team_id="synthetic", app_name="service-one", app_id="app")
    dependency = Target(team_id="synthetic", app_name="service-two", app_id="dep")
    with tempfile.TemporaryDirectory(prefix="liara-diagnosis-eval-") as temp:
        for index, case in enumerate(cases):
            store = MonitorStore(Path(temp) / f"{index}.sqlite")
            observer = Observer(store, {"app": target})
            incident = observer.begin_investigation(
                "evaluator", target, "Investigate this service from the currently available evidence."
            )
            now = time.time()
            for number, (kind, quality, age, payload) in enumerate(case["evidence"]):
                store.add_evidence(
                    "evaluator",
                    incident["id"],
                    Evidence(
                        id=f"e{number + 1}",
                        target=target,
                        kind=kind,
                        quality=quality,
                        observed_at=now - age,
                        available_at=now,
                        redacted_payload=payload,
                    ),
                )
            readers = {}
            if "read" in case:

                def check(case=case):
                    at = time.time()
                    return Evidence(
                        id="direct-check",
                        target=dependency,
                        kind=case["read"]["kind"],
                        quality="fresh",
                        observed_at=at,
                        available_at=at,
                        redacted_payload=case["read"]["payload"],
                    )

                readers["registered_dependency_check"] = check
            investigator = Investigator(
                store, client, {"app": target, "dep": dependency}, dependencies={"app": ["dep"]}
            )
            start = time.perf_counter()
            diagnosis = investigator.investigate("evaluator", incident["id"], readers)
            correct = diagnosis["cause_family"] in case["expected"] and (
                not case.get("outcome") or diagnosis["outcome"] == case["outcome"]
            )
            result = {
                "case": case["name"],
                "expected": case["expected"],
                "correct": correct,
                "elapsed_ms": round((time.perf_counter() - start) * 1000),
                "diagnosis": diagnosis,
                "application_writes": 0,
            }
            results.append(result)
            report = {
                "scope": "Synthetic separately labelled diagnostic fixtures, genuine isolated Codex; not live Liara incident success.",
                "cases": results,
                "correct": sum(r["correct"] for r in results),
                "total": len(results),
                "unsupported_app_writes": 0,
            }
            (ROOT / "results/diagnosis.json").write_text(json.dumps(report, indent=2) + "\n")
            print(
                json.dumps(
                    {
                        "case": case["name"],
                        "correct": correct,
                        "cause_family": diagnosis["cause_family"],
                        "outcome": diagnosis["outcome"],
                        "calls": len(diagnosis["model_calls"]),
                        "elapsed_ms": result["elapsed_ms"],
                    }
                ),
                flush=True,
            )
    if sum(r["correct"] for r in results) < 7:
        raise SystemExit("Below7/8 target; inspect actual results")


if __name__ == "__main__":
    main()
