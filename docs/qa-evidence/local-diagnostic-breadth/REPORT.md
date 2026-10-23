# Local diagnostic breadth evaluation

Scope: actual isolated loopback HTTP and production probes/investigator with genuine isolated Codex. Provider metadata and unavailable metrics are explicitly fixtures; the log envelope is an evaluation adapter over actual local application events. This does not establish Liara cloud slowdown, production workload capacity or automatic repair.

No production source was changed for the initial evaluation. Its real busy failure prompted a separately authorized narrow Investigator boundary fix with 307 backend tests and independent review required before the final retest. No cloud writes, watches or enrolled repair capability exist in this evaluator.

| Case | Actual local observations | Genuine model result |
|---|---|---|
| case-1 | Gateway 504 in 847.2ms; dependency 200 in 1844.9ms; gateway/dependency liveness 200. Direct dependency baseline 19.1ms. | Initial non-final hypothesis dependency_timeout and appropriate direct read; terminal investigation failed closed with busy. This is not a completed diagnostic success. |
| case-2 | Gateway 502 in 41.4ms; dependency 503 in 18.1ms; gateway/dependency liveness 200. Direct dependency baseline 19.1ms. | Completed unknown/unresolved: identifies fast upstream 503, distinguishes older timeouts, states CPU/RAM/capacity and root cause unknown. |

Final fresh slowdown retest: dependency_timeout/no_app_change. 28 uncharged busy refusals preceded 1 actual model start; one unchanged request ID/deadline and no further read tools. Original failed case is retained.

Actual final model summary:

مرز خرابیِ مستند، انتظار gateway برای وابستگی است: /preview با مهلت ۰٫۸ ثانیه، پس از حدود ۸۴۳ میلی‌ثانیه پاسخ 504 و upstream_timeout داد؛ لاگ همان درخواست این نتیجه را تأیید می‌کند. درخواست مستقل وابستگی با 200، اما پس از ۱۸۲۰ میلی‌ثانیه پاسخ گرفت؛ این با کندی وابستگی سازگار است، هرچند همان درخواست نیست. بررسی سلامت هر دو سرویس موفق بود؛ پس پاسخ‌گویی فرایندها به معنی سلامت /preview نیست. موفقیت قبلی /preview و پاسخ سریع قبلی وابستگی، علیه خرابی دائمی هستند. کندی داخلی وابستگی، تأخیر ارتباط یا صف و نامتناسب‌بودن مهلت، توضیح‌های محتمل‌اند. شواهد محلی‌اند و وضعیت زندهٔ لیارا را نشان نمی‌دهند. هیچ تغییری انجام نشده است.

Unknowns retained by the model:

- علت دقیق کندی و سهم شبکه، صف یا پردازش وابستگی مشخص نیست.
- مصرف CPU/RAM و ظرفیت تحمل بار اندازه‌گیری نشده‌اند؛ تأخیر مشاهده‌شده اثبات کمبود منابع نیست.
- تداوم و فراوانی خطا، مناسب‌بودن مهلت ۰٫۸ ثانیه و وضعیت زندهٔ لیارا نامعلوم‌اند؛ خواندن تکمیلی در دسترس نیست.

Limits and failure inventory:

- Initial slowdown finalization failed on genuine shared-gate contention. The idle Torob worker reserves that gate while polling for work; no root inference was running. No worker was killed, gate reset or request replayed.
- Three initial actual model starts and one uncharged busy refusal were recorded. The raw ledger count fell 47 → 39 because the production rolling 24-hour policy pruned expired entries; raw prefix/count subtraction is not an appropriate reset/start-count assertion. See rolling-ledger-audit.json.
- Original model inputs, raw model responses, controller ground truth, actual probe timestamps/durations, request IDs and application events remain separate. No expected answer/controller mode is passed to the model.
- Cause vocabulary has no dedicated application-error category: cautious unknown/unresolved with the precise observed 503 boundary is appropriate; this is not an invented crash/schema diagnosis.
- One process pair and one induced delay/error setting are bounded evidence, not a broad benchmark or a cloud capacity test.
- Zero provider/application changes means the operator has no write/executor path. The independent local harness intentionally changes its in-memory response behavior to create the test fault.
