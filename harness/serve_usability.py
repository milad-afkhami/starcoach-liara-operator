"""Owned deterministic UI QA; no cloud writer, no genuine model adapter."""

import sys
import time
import secrets
import json
import threading
import os
import tempfile
import socket
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from liara_guard.api import create_app
from liara_guard.auth import hash_password
from liara_guard.runtime import FixtureProvider, local_config
from liara_guard.model_types import ModelResult
from liara_guard.metrics import normalize_history
from liara_guard.types import Target, ServiceSummary

ROOT = Path(os.environ.get("LIARA_UI_QA_DIR") or tempfile.mkdtemp(prefix="liara-ui-qa-"))
PORT = int(os.environ.get("LIARA_UI_QA_PORT", "8692"))
STORE_PORT = int(os.environ.get("LIARA_UI_QA_STORE_PORT", "8787"))
DEP_PORT = int(os.environ.get("LIARA_UI_QA_DEP_PORT", "8788"))


class Provider(FixtureProvider):
    def list_services(self):
        return [
            ServiceSummary(
                target=Target(
                    team_id=self.team_id, app_id=identifier, app_name=name, origin=f"http://127.0.0.1:{port}"
                ),
                platform="python",
                runtime_state="Running",
                observed_at=time.time(),
            )
            for identifier, name, port in [
                ("local-store", "storefront", STORE_PORT),
                ("local-dep", "delivery", DEP_PORT),
                ("worker", "background-worker", DEP_PORT),
            ]
        ]

    def get_metrics_history(self, target):
        if target.app_id == "worker":
            return self._evidence(
                target, "metrics_history", {"historical_only": True, "unit": "unverified"}, "unavailable"
            )
        now = time.time()
        rows = [
            [now - 280, 0.05],
            [now - 260, 0.07],
            [now - 240, 0.11],
            [now - 220, "NaN"],
            [now - 200, 0.16],
            [now - 180, 0.08],
            [now - 80, 0.13],
            [now - 60, 0.1],
            [now + 20, 0.99],
        ]
        sources = {
            "cpu": {"result": [{"applet": "app-1", "values": rows}]},
            "memory": {
                "result": [
                    {
                        "applet": "app-1",
                        "values": [[at, 104857600 + index * 1048576] for index, (at, _) in enumerate(rows)],
                    }
                ]
            },
        }
        payload, coverage, quality, observed = normalize_history(sources, now)
        evidence = self._evidence(target, "metrics_history", payload, quality, observed)
        evidence.coverage.update(coverage)
        return evidence

    def get_metrics(self, target):
        return self._evidence(target, "metrics", {"error": "future_summary", "unit": "unverified"}, "invalid")

    def get_logs(self, target, since):
        return self._evidence(
            target,
            "logs",
            {
                "lines": [
                    {
                        "timestamp": time.time() - 2,
                        "message": "upstream response missing shipping_toman; received delivery_toman",
                    }
                ]
            },
        )


class Model:
    def generate(self, request, schema, cancel):
        time.sleep(0.2)
        ids = [e["id"] for e in request.payload["evidence"] if e["kind"] == "http_probe"]
        return ModelResult(
            request_id=request.id,
            provider="deterministic_ui_fixture",
            model="fixture-no-inference",
            cli_version="fixture",
            elapsed_ms=1,
            value={
                "action": "conclude",
                "outcome": "need_evidence",
                "cause_family": "dependency_schema",
                "summary": "درخواست پیش‌نمایش با خطای 502 روبه‌رو شده، اما برنامه هنوز روشن است. پاسخ سرویس وابسته با فیلد مورد انتظار هماهنگ نیست؛ میزان اثر روی کاربران مشخص نیست. قدم بعدی بررسی فیلدهای پاسخ در سورس و اجرای تست همان درخواست است.",
                "evidence_ids": ids[:2],
                "contradiction_ids": [],
                "unknowns": [
                    "فایل مسئول خطا و زمان شروع مشکل مشخص نیست.",
                    "برای انتخاب پلن بزرگ‌تر دادهٔ کافی نداریم.",
                ],
                "next_check": None,
            },
        )


services = FastAPI()


@services.get("/healthz")
def health(request: Request):
    return {"build_id": "qa-build", "request_id": request.headers.get("x-request-id")}


@services.get("/preview")
def preview(request: Request):
    return JSONResponse(
        {
            "build_id": "qa-build",
            "request_id": request.headers.get("x-request-id"),
            "reason": "upstream_shape",
            "expected": "shipping_toman",
            "received": "delivery_toman",
        },
        status_code=502,
    )


@services.get("/quote")
def quote(request: Request):
    return {
        "build_id": "qa-build",
        "request_id": request.headers.get("x-request-id"),
        "delivery_toman": 10000,
    }


if __name__ == "__main__":
    ROOT.mkdir(parents=True, exist_ok=True)
    if (ROOT / "operator.sqlite").exists() or (ROOT / "access.json").exists():
        raise SystemExit("Refusing to overwrite existing UI QA state")
    for port in [PORT, STORE_PORT, DEP_PORT]:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", port))
    for port in [STORE_PORT, DEP_PORT]:
        threading.Thread(
            target=lambda p=port: uvicorn.run(services, host="127.0.0.1", port=p, log_level="error"),
            daemon=True,
        ).start()
    password = secrets.token_urlsafe(24)
    access = ROOT / "access.json"
    access.write_text(json.dumps({"url": f"http://127.0.0.1:{PORT}", "password": password}))
    access.chmod(0o600)
    config = local_config()
    for check in config["http_checks"]:
        check["origin"] = check["origin"].replace(":8771", f":{STORE_PORT}").replace(":8772", f":{DEP_PORT}")
    application = create_app(
        state_path=ROOT / "operator.sqlite",
        session_secret=secrets.token_urlsafe(48),
        password_hash=hash_password(password),
        public_origin=f"http://127.0.0.1:{PORT}",
        provider=Provider(ROOT),
        registry_config=config,
        model=Model(),
        mode="fixture",
    )
    print(
        "Deterministic fixture only; no model calls or cloud writes. Private login: " + str(access.resolve()),
        flush=True,
    )
    uvicorn.run(application, host="127.0.0.1", port=PORT, log_level="warning")
