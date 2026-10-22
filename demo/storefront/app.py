import json
import os
from pathlib import Path
import re
import uuid
from contextlib import asynccontextmanager
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def create_app(*, build_id=None, dependency_origin=None, transport=None):
    build_file = Path(__file__).with_name("build-id")
    identity = build_id or (
        build_file.read_text().strip()
        if build_file.is_file()
        else os.environ.get("BUILD_ID", "local-storefront")
    )
    config = Path(__file__).parent / "config" / "dependency-origin"
    origin = (
        dependency_origin
        or (
            config.read_text().strip()
            if config.is_file()
            else os.environ.get("DEPENDENCY_ORIGIN", "http://127.0.0.1:8772")
        )
    ).rstrip("/")

    @asynccontextmanager
    async def lifespan(app):
        # Source/runtime configuration owns this fixed URL; no request/model URL is accepted.
        with httpx.Client(
            base_url=origin, transport=transport, timeout=2, follow_redirects=False, trust_env=False
        ) as client:
            app.state.dependency = client
            yield

    app = FastAPI(lifespan=lifespan)

    def rid(request):
        value = request.headers.get("x-request-id", "")
        return value if re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value) else uuid.uuid4().hex

    def response(payload, code=200):
        return JSONResponse(payload, status_code=code, headers={"Cache-Control": "no-store"})

    @app.get("/healthz")
    def health(request: Request):
        return response({"status": "ok", "build_id": identity, "request_id": rid(request)})

    @app.get("/preview")
    def preview(request: Request):
        request_id = rid(request)
        dependency_build = None
        keys = []
        try:
            with app.state.dependency.stream(
                "GET", "/quote", headers={"X-Request-ID": request_id, "Cache-Control": "no-cache"}
            ) as upstream:
                if upstream.status_code != 200:
                    raise ValueError()
                raw = bytearray()
                for chunk in upstream.iter_bytes():
                    raw.extend(chunk)
                    if len(raw) > 4096:
                        raise ValueError()
                payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError()
            keys = sorted(str(k)[:50] for k in payload)[:20]
            dependency_build = payload.get("build_id")
            value = payload.get("shipping_toman")
            if (
                type(value) is not int
                or value < 0
                or not isinstance(dependency_build, str)
                or payload.get("request_id") != request_id
            ):
                raise ValueError()
            return response(
                {
                    "status": "ready",
                    "shipping_toman": value,
                    "build_id": identity,
                    "dependency_build_id": dependency_build,
                    "request_id": request_id,
                }
            )
        except httpx.TimeoutException:
            reason = "upstream_timeout"
        except httpx.TransportError:
            reason = "upstream_network"
        except (ValueError, UnicodeError):
            reason = "upstream_invalid"
        print(
            json.dumps(
                {
                    "event": "upstream_error",
                    "reason": reason,
                    "request_id": request_id,
                    "build_id": identity,
                    "dependency_build_id": dependency_build,
                    "expected_field": "shipping_toman",
                    "observed_fields": keys,
                }
            ),
            flush=True,
        )
        return response(
            {
                "status": "unavailable",
                "reason": reason,
                "build_id": identity,
                "dependency_build_id": dependency_build,
                "request_id": request_id,
            },
            502,
        )

    return app


app = create_app()
