"""Execute locally packaged images; this never closes live Liara acceptance."""

import json
from pathlib import Path
import socket
import subprocess
import time
import uuid
import httpx

ROOT = Path(__file__).resolve().parents[1]


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True, stderr=subprocess.STDOUT).strip()


def main():
    for port in (8775, 8776):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", port))
    manifests = json.loads((ROOT / "data/artifact-smoke/manifests.json").read_text())
    builds = {m["target"]["app_name"].removeprefix("artifact-"): m["build_id"] for m in manifests}
    names = []
    prefix = "liara-artifact-" + uuid.uuid4().hex[:10]

    def start(role, port):
        name = prefix + "-" + role
        docker(
            "run",
            "--detach",
            "--rm",
            "--name",
            name,
            "--network",
            "host",
            "--read-only",
            "--tmpfs",
            "/tmp:rw,nosuid,size=16m",
            "--cpus",
            "0.5",
            "--memory",
            "512m",
            "--pids-limit",
            "64",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--user",
            "1000:1000",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            "starcoach-liara-" + role + ":local",
            "uvicorn",
            "app:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
        )
        names.append(name)
        for _ in range(80):
            try:
                response = httpx.get(f"http://127.0.0.1:{port}/healthz", timeout=1, trust_env=False)
                if response.status_code == 200 and response.json()["build_id"] == builds[role]:
                    return name
            except (httpx.TransportError, ValueError):
                pass
            time.sleep(0.1)
        raise RuntimeError("Packaged image readiness failed")

    def probe(path="/preview", port=8775):
        identifier = uuid.uuid4().hex
        response = httpx.get(
            f"http://127.0.0.1:{port}" + path,
            headers={"X-Request-ID": identifier},
            timeout=3,
            trust_env=False,
        )
        body = response.json()
        assert body["request_id"] == identifier
        return {"http_status": response.status_code, "payload": body, "at": time.time()}

    result = {
        "mode": "actual_local_packaged_containers",
        "live_liara": False,
        "manifests": manifests,
        "checks": {},
    }
    try:
        delivery = start("delivery", 8776)
        store = start("storefront", 8775)
        good = probe()
        assert good["http_status"] == 200 and good["payload"]["dependency_build_id"] == builds["delivery"]
        assert good["payload"]["build_id"] == builds["storefront"]
        result["checks"]["healthy"] = good
        docker("stop", delivery)
        names.remove(delivery)
        variant = start("variant", 8776)
        bad = probe()
        health = probe("/healthz")
        dependency = probe("/quote", 8776)
        assert bad["http_status"] == 502 and bad["payload"]["reason"] == "upstream_invalid"
        assert health["http_status"] == 200 and dependency["payload"].get("delivery_toman") == 10000
        assert bad["payload"]["dependency_build_id"] == builds["variant"]
        result["checks"].update(failed_endpoint=bad, liveness=health, changed_dependency=dependency)
        docker("stop", variant)
        names.remove(variant)
        delivery = start("delivery", 8776)
        recovered = []
        for _ in range(3):
            value = probe()
            assert (
                value["http_status"] == 200 and value["payload"]["dependency_build_id"] == builds["delivery"]
            )
            recovered.append(value)
            if len(recovered) < 3:
                time.sleep(5)
        result["checks"]["fresh_restored_builds"] = recovered
        result["logs"] = docker("logs", store)[-4000:]
        assert "shipping_toman" in result["logs"] and "delivery_toman" in result["logs"]
        result["images"] = {
            r: json.loads(docker("image", "inspect", "starcoach-liara-" + r + ":local"))[0]["Id"]
            for r in ("delivery", "storefront", "variant")
        }
        result["stats"] = docker("stats", "--no-stream", "--format", "{{json .}}", store, delivery)
        result["passed"] = True
    finally:
        for name in names:
            subprocess.run(["docker", "stop", name], capture_output=True, text=True)
    output = ROOT / "docs/qa-evidence/packaged-containers.json"
    output.write_text(json.dumps(result, indent=2))
    print(json.dumps({"passed": True, "local_only": True, "evidence": str(output)}))


if __name__ == "__main__":
    main()
