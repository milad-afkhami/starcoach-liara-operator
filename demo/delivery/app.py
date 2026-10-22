import os
from pathlib import Path
import re
import uuid
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def request_id(request):
    value = request.headers.get("x-request-id", "")
    return value if re.fullmatch(r"[A-Za-z0-9_-]{1,100}", value) else uuid.uuid4().hex


def create_app(*, build_id=None):
    build_file = Path(__file__).with_name("build-id")
    identity = build_id or (
        build_file.read_text().strip()
        if build_file.is_file()
        else os.environ.get("BUILD_ID", "local-delivery")
    )
    app = FastAPI()

    @app.get("/healthz")
    def health(request: Request):
        return JSONResponse(
            {"status": "ok", "build_id": identity, "request_id": request_id(request)},
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/quote")
    def quote(request: Request):
        return JSONResponse(
            {"shipping_toman": 10000, "build_id": identity, "request_id": request_id(request)},
            headers={"Cache-Control": "no-store"},
        )

    return app


app = create_app()
