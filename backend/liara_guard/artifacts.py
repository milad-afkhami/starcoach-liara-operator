"""Exact source bundles, separate opaque serving identity and archive digest."""

import hashlib
import io
import os
import tarfile
import uuid
from pathlib import Path
from pydantic import Field
from .types import Record, Target
from .contracts import unsafe_origin

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = """FROM public.ecr.aws/docker/library/python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock
COPY app.py build-id ./
COPY config/ ./config/
EXPOSE 8000
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000","--no-access-log"]
"""


class ArtifactManifest(Record):
    path: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    build_id: str
    target: Target
    platform: str = "docker"
    port: int = 8000
    source_commit: str
    source_sha256: str


def package_known_good(source_dir, destination, target, *, source_commit, dependency_origin=None):
    source = Path(source_dir) / "app.py"
    if source.is_symlink() or not source.is_file():
        raise ValueError("Regular allowlisted source required")
    if dependency_origin is not None and unsafe_origin(dependency_origin, allow_loopback=True):
        raise ValueError("Invalid declared dependency")
    identity = uuid.uuid4().hex
    source_bytes = source.read_bytes()
    files = {
        "app.py": source_bytes,
        "build-id": (identity + "\n").encode(),
        "Dockerfile": DOCKERFILE.replace(
            "COPY config/ ./config/\n", "" if dependency_origin is None else "COPY config/ ./config/\n"
        ).encode(),
        "requirements.lock": (ROOT / "requirements.lock").read_bytes(),
    }
    if dependency_origin is not None:
        files["config/dependency-origin"] = (dependency_origin + "\n").encode()
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("wb") as output:
        os.chmod(destination, 0o600)
        with tarfile.open(fileobj=output, mode="w:gz") as archive:
            for name, data in files.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                info.mode = 0o644
                archive.addfile(info, io.BytesIO(data))
    return ArtifactManifest(
        path=str(destination.resolve()),
        sha256=hashlib.file_digest(destination.open("rb"), "sha256").hexdigest(),
        build_id=identity,
        target=target,
        source_commit=source_commit,
        source_sha256=hashlib.sha256(source_bytes).hexdigest(),
    )


def verify_artifact(manifest):
    path = Path(manifest.path)
    return (
        not path.is_symlink()
        and path.is_file()
        and hashlib.file_digest(path.open("rb"), "sha256").hexdigest() == manifest.sha256
    )
