"""Two real local services plus a separate owner-approved fixture controller; no cloud writes."""

import json
import os
import signal
import socket
import subprocess
import sys
import tarfile
import threading
import time
import uuid
from pathlib import Path
import httpx
from controller import Controller
from liara_guard.artifacts import package_known_good
from liara_guard.types import Target

ROOT = Path(__file__).resolve().parents[1]


def main():
    for port in (8771, 8772):
        with socket.socket() as sock:
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                raise SystemExit(f"Port{port} already in use; no existing process will be stopped")
    private = ROOT / "data/local-controller"
    public = ROOT / "data/local-services"
    private.mkdir(parents=True, exist_ok=True)
    private.chmod(0o700)
    public.mkdir(parents=True, exist_ok=True)
    processes = {}
    metadata = {}
    stop = threading.Event()
    streams = []
    target = Target(team_id="local-fixture", app_name="delivery", app_id="local-dep")
    controller = Controller(
        private / "controller.sqlite", {"local-dep": target.model_dump(exclude={"origin"})}
    )

    def start(identifier, source, port, build):
        log = public / (identifier + ".log")
        log.touch(mode=0o600, exist_ok=True)
        env = {**os.environ, "BUILD_ID": build, "DEPENDENCY_ORIGIN": "http://127.0.0.1:8772"}
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app:app",
                "--app-dir",
                str(source),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-access-log",
            ],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        processes[identifier] = process

        def collect():
            with log.open("a") as output:
                for line in process.stdout:
                    output.write(json.dumps({"at": time.time(), "message": line.rstrip()}) + "\n")
                    output.flush()

        thread = threading.Thread(target=collect, daemon=True)
        thread.start()
        streams.append(thread)
        for _ in range(50):
            try:
                response = httpx.get(f"http://127.0.0.1:{port}/healthz", timeout=0.3)
                if response.status_code == 200 and response.json().get("build_id") == build:
                    break
            except (httpx.TransportError, ValueError):
                pass
            time.sleep(0.1)
        else:
            raise RuntimeError("Local service failed readiness")
        metadata[identifier] = {
            "release_id": "local-" + uuid.uuid4().hex,
            "build_id": build,
            "at": time.time(),
        }
        temporary = public / "releases.next"
        temporary.write_text(json.dumps(metadata))
        temporary.replace(public / "releases.json")

    def deploy(spec):
        if (
            spec["target"] != target.model_dump(exclude={"origin"})
            or spec["before_release"] != metadata["local-dep"]["release_id"]
        ):
            raise ValueError("Current local target/release changed")
        destination = private / ("release-" + uuid.uuid4().hex)
        destination.mkdir()
        with tarfile.open(spec["archive"]) as bundle:
            for name in ("app.py", "build-id"):
                member = bundle.getmember(name)
                if not member.isfile() or member.size > 100000:
                    raise ValueError("Invalid local source member")
                (destination / name).write_bytes(bundle.extractfile(member).read())
        build = (destination / "build-id").read_text().strip()
        processes["local-dep"].terminate()
        processes["local-dep"].wait(timeout=5)
        start("local-dep", destination, 8772, build)
        return {"release_id": metadata["local-dep"]["release_id"]}

    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop.set())
    try:
        start("local-dep", ROOT / "demo/delivery", 8772, uuid.uuid4().hex)
        start("local-store", ROOT / "demo/storefront", 8771, uuid.uuid4().hex)
        changed = private / "source"
        changed.mkdir(exist_ok=True)
        (changed / "app.py").write_text(
            (ROOT / "demo/delivery/app.py").read_text().replace('"shipping_toman"', '"delivery_toman"')
        )
        # Packaging alone is not baseline registration. This archive stays controller-only.
        manifest = package_known_good(
            changed, private / "variant.tar.gz", target, source_commit="local-controller-only"
        )
        (private / "variant.json").write_text(manifest.model_dump_json())
        print(
            json.dumps(
                {
                    "local_services": "ready",
                    "provider_metadata": "fixture",
                    "origins": ["http://127.0.0.1:8771", "http://127.0.0.1:8772"],
                }
            ),
            flush=True,
        )
        while not stop.wait(0.2):
            request = private / "approved-request.json"
            if not request.is_file():
                continue
            value = json.loads(request.read_text())
            request.unlink()
            try:
                receipt = controller.execute("local-demo-owner", value["id"], value["approval"], deploy)
            except Exception as exc:
                receipt = {"error": type(exc).__name__}
            (private / "receipt.json").write_text(json.dumps(receipt))
    finally:
        for process in processes.values():
            if process.poll() is None:
                process.terminate()
        for process in processes.values():
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for thread in streams:
            thread.join(timeout=1)


if __name__ == "__main__":
    main()
