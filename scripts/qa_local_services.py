"""Actual local HTTP dependency regression; controller ground truth never enters model inputs."""

import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
import httpx
from liara_guard.contracts import ProbeRunner, RegisteredHttpCheck
from liara_guard.types import Target

ROOT = Path(__file__).resolve().parents[1]


def wait(url):
    for _ in range(50):
        try:
            if httpx.get(url, timeout=0.5).status_code == 200:
                return
        except httpx.TransportError:
            pass
        time.sleep(0.1)
    raise RuntimeError("Demo failed to start")


def main():
    processes = []
    with tempfile.TemporaryDirectory(prefix="liara-demo-qa-") as scratch:
        logs = Path(scratch) / "service.log"
        with logs.open("w") as output:

            def start(directory, port, identity):
                env = {**os.environ, "BUILD_ID": identity, "DEPENDENCY_ORIGIN": "http://127.0.0.1:8772"}
                p = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "app:app",
                        "--app-dir",
                        str(directory),
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(port),
                        "--no-access-log",
                    ],
                    env=env,
                    stdout=output,
                    stderr=output,
                )
                processes.append(p)
                wait(f"http://127.0.0.1:{port}/healthz")
                return p

            good_id = uuid.uuid4().hex
            store_id = uuid.uuid4().hex
            changed_id = uuid.uuid4().hex
            try:
                delivery = start(ROOT / "demo/delivery", 8772, good_id)
                start(ROOT / "demo/storefront", 8771, store_id)
                target = Target(
                    team_id="local-fixture",
                    app_name="local-storefront",
                    app_id="local-app",
                    origin="http://127.0.0.1:8771",
                )
                runner = ProbeRunner({"local-app": target}, allow_loopback=True)
                check = RegisteredHttpCheck(
                    id="preview",
                    target_id="local-app",
                    origin=target.origin,
                    path="/preview",
                    require_request_echo=True,
                )
                healthy = runner.run(check)
                assert healthy.check_pass and healthy.payload["dependency_build_id"] == good_id
                delivery.terminate()
                delivery.wait(timeout=5)
                altered = Path(scratch) / "changed"
                altered.mkdir()
                source = (ROOT / "demo/delivery/app.py").read_text()
                assert '"shipping_toman"' in source
                (altered / "app.py").write_text(source.replace('"shipping_toman"', '"delivery_toman"'))
                start(altered, 8772, changed_id)
                broken = runner.run(check)
                assert broken.http_status == 502 and not broken.check_pass
                assert broken.payload["dependency_build_id"] == changed_id
                live = httpx.get("http://127.0.0.1:8771/healthz").json()
                assert live["status"] == "ok"
                dependency = httpx.get("http://127.0.0.1:8772/quote").json()
                assert "delivery_toman" in dependency and "shipping_toman" not in dependency
                output.flush()
                from liara_guard.observer import MonitorStore, Observer

                clock = [time.time()]
                monitor = MonitorStore(Path(scratch) / "watch.sqlite")
                observer = Observer(monitor, {"local-app": target}, clock=lambda: clock[0])
                watch = observer.start_watch("local-owner", ["local-app"], [check])
                watched_runner = ProbeRunner(
                    {"local-app": target}, allow_loopback=True, clock=lambda: clock[0]
                )
                observer.tick(watch["id"], watched_runner.run)
                assert monitor.incidents("local-owner") == []
                clock[0] += 15
                observer.tick(watch["id"], watched_runner.run)
                incident = monitor.incidents("local-owner")[0]
                assert incident["kind"] == "http_availability" and incident["generation"] == 1
                clock[0] += 15
                observer.tick(watch["id"], watched_runner.run)
                updated = monitor.incident("local-owner", incident["id"])
                assert updated["generation"] == 1 and updated["observation_sequence"] == 2
                observer.stop_watch("local-owner", watch["id"])
                assert (
                    observer.tick(
                        watch["id"],
                        lambda _: (_ for _ in ()).throw(AssertionError("Stopped watch called probe")),
                    )
                    == []
                )
                record = {
                    "scope": "Real local HTTP, deliberately controlled dependency source change; not Liara deployment.",
                    "healthy": healthy.model_dump(),
                    "broken": broken.model_dump(),
                    "liveness": live,
                    "dependency_observation": dependency,
                    "structured_log_contains_evidence": all(
                        x in logs.read_text()
                        for x in ["upstream_invalid", "shipping_toman", "delivery_toman"]
                    ),
                    "ground_truth_not_supplied_to_model": True,
                    "model_called": False,
                    "watch": {
                        "actual_http": True,
                        "clock": "injected15second steps",
                        "incident_kind": incident["kind"],
                        "stable_generation": updated["generation"],
                        "observation_sequence": updated["observation_sequence"],
                        "stop_verified": True,
                    },
                }
                assert record["structured_log_contains_evidence"]
            finally:
                for p in processes:
                    if p.poll() is None:
                        p.terminate()
                for p in processes:
                    try:
                        p.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        p.kill()
                        p.wait()
        destination = ROOT / "docs/qa-evidence/local-services.json"
        destination.write_text(json.dumps(record, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "healthy": healthy.http_status,
                    "after_change": broken.http_status,
                    "liveness": live["status"],
                    "actual_dependency_build_propagated": True,
                    "cleanup": "all own servers stopped",
                }
            )
        )


if __name__ == "__main__":
    main()
