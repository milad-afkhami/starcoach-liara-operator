"""Deterministic owner-local presentation cases; never a model or provider write."""

import hashlib
import json
import hmac
import time
from liara_guard.approvals import OperationSpec
from liara_guard.types import Evidence


def seed_cases(application, provider, session_secret):
    owner = hmac.new(
        session_secret.encode(), b"liara-service-watch:instance-owner:v1", hashlib.sha256
    ).hexdigest()
    application.state.registry.refresh(provider.list_services())
    target = application.state.registry.resolve("local-store")
    monitor, observer, operations = (
        application.state.monitor,
        application.state.observer,
        application.state.operations,
    )
    now = time.time()
    long_summary = (
        "درخواست بررسی‌شده پاسخ موفق داشته است و از همین پاسخ نمی‌توان سالم بودن تمام قابلیت‌های برنامه را نتیجه گرفت. "
        "اطلاعات وضعیت پردازش از لیارا با خطای 500 دریافت شده است؛ بنابراین وضعیت پردازش و کافی بودن ظرفیت همچنان نامعلوم است و هیچ تغییر برنامه‌ای پیشنهاد نشده است. "
        "قدم بعدی این است که دریافت وضعیت پردازش از لیارا دوباره بررسی شود و اگر خطا ادامه داشت، همان خطای دریافت داده پیگیری شود."
    )
    for index, case in enumerate(["repair", "need", "stale", "recovered", "submitted", "nochange"]):
        case_target = application.state.registry.resolve("local-dep") if case == "nochange" else target
        incident = observer.begin_investigation(owner, case_target, "UI CASE: " + case)
        stamp = now - (6 - index) * 5
        failed = case in ("repair", "stale", "recovered", "submitted")
        evidence = Evidence(
            id="ui-" + case,
            target=case_target,
            kind="http_probe",
            quality="fresh",
            observed_at=stamp,
            available_at=stamp,
            redacted_payload={
                "check_id": "dep-quote" if case == "nochange" else "store-preview",
                "http_status": 502 if failed else 200,
                "check_pass": not failed,
                "reason": "unexpected_status" if failed else "pass",
                "elapsed_ms": 20,
            },
        )
        monitor.add_evidence(owner, incident["id"], evidence)
        incident = monitor.incident(owner, incident["id"])
        outcome = (
            "repair_candidate"
            if case in ("repair", "stale", "recovered")
            else "no_app_change"
            if case == "nochange"
            else "need_evidence"
        )
        incident.update(
            opened_at=stamp,
            investigation_state="done",
            diagnosis={
                "generation": incident["generation"],
                "outcome": outcome,
                "cause_family": "dependency_schema" if failed else "unknown",
                "summary": long_summary
                if case == "nochange"
                else "این یک نتیجهٔ آزمایشی ثبت‌شده است. شواهد و ابهام‌های همین بررسی باید بازبینی شوند. هیچ عملیات واقعی اجرا نشده است.",
                "evidence_ids": [evidence.id],
                "contradiction_ids": [],
                "unknowns": ["سورس پروژه بررسی نشده است."],
                "cutoff": stamp + 1,
                "read_operations": 0,
                "model_calls": [],
            },
        )
        if case == "stale":
            incident["generation"] += 1
        if case == "recovered":
            incident["state"] = "recovered"
        with monitor.connect() as db:
            db.execute(
                "UPDATE incidents SET state=?,data=? WHERE id=?",
                (incident["state"], json.dumps(incident), incident["id"]),
            )
        if case not in ("repair", "stale", "recovered", "submitted"):
            continue
        op = operations.propose(
            owner,
            OperationSpec(
                kind="redeploy_known_good",
                team_id=target.team_id,
                app_id=target.app_id,
                app_name=target.app_name,
                artifact_sha256="a" * 64,
                before_release_id="ui-before-release",
                incident_id=incident["id"],
                incident_generation=1,
                failure_fingerprint="ui-failure",
                verification_policy_hash="b" * 64,
            ),
        )
        if case in ("recovered", "submitted"):
            result = {
                "state": "recovered" if case == "recovered" else "inconclusive",
                "reason": "original_checks_and_serving_build_verified"
                if case == "recovered"
                else "insufficient_fresh_identity_proof",
                "probe_ids": ["ui-round-1", "ui-round-2", "ui-round-3"],
                "observed_window": [stamp + 1, stamp + 2],
            }
            operations.update(
                op,
                state="completed" if case == "recovered" else "failed",
                release_id="ui-submitted-release",
                submitted_at=stamp + 2,
                recovery_rechecks_used=1,
                verification=result,
                verification_attempts=[{"attempt": 1, "result": result}],
            )
            if case == "recovered":
                incident["verification"] = result
                with monitor.connect() as db:
                    db.execute(
                        "UPDATE incidents SET state=?,data=? WHERE id=?",
                        (incident["state"], json.dumps(incident), incident["id"]),
                    )
