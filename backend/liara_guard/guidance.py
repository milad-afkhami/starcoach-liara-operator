"""Fixed evidence-linked owner checklists, never executable model instructions."""


CAUSE_STEPS = {
    'dependency_schema': (
        'پاسخ دو سرویس را مقایسه کنید',
        'با شناسهٔ همان درخواست، نام و نوع فیلدهای پاسخ سرویس وابسته را با انتظار سرویس فراخوان مقایسه کنید. هم‌زمانی انتشار به‌تنهایی علت را ثابت نمی‌کند.',
        'اصلاح سازگار را با مالک سرویس هماهنگ کنید',
        'اگر ناسازگاری قرارداد تأیید شد، پاسخ یا مصرف‌کنندهٔ آن باید هماهنگ شود. پیش از هر استقرار، سورس، سرویس هدف و اثر تغییر را جداگانه بازبینی کنید.',
    ),
    'dependency_timeout': (
        'زمان پاسخ وابستگی را بررسی کنید',
        'درخواست خطادار و زمان پاسخ سرویس وابسته را در یک بازه مقایسه کنید؛ قطع شبکه، پاسخ کند و مهلت کوتاه علت‌های متفاوتی دارند.',
        'مهلت یا مسیر کند را با شواهد اصلاح کنید',
        'پس از مشخص شدن بخش کند، با مالک همان سرویس دربارهٔ اصلاح مسیر یا مهلت تصمیم بگیرید. افزایش منابع بدون سنجش مصرف و سقف آن توصیه نمی‌شود.',
    ),
    'process_crash': (
        'اولین خطای راه‌اندازی را پیدا کنید',
        'لاگ نزدیک به توقف پردازش را همراه وضعیت نمونه‌های اجرا و هویت انتشار بررسی کنید؛ پاسخ ندادن یک نشانی به‌تنهایی به معنی توقف پردازش نیست.',
        'پیکربندی و نسخهٔ مربوط را بازبینی کنید',
        'مالک سرویس باید خطای مشخص راه‌اندازی یا وابستگی را اصلاح کند. مقدار رمزها یا متغیرهای محرمانه را در پرسش یا شواهد وارد نکنید.',
    ),
    'observer_access': (
        'دسترسی مشاهده را برگردانید',
        'مالک حساب باید اعتبار دسترسی API و محدودهٔ تیم را در سرور بررسی کند؛ خطای دسترسی به شواهد، خرابی خود برنامه را ثابت نمی‌کند.',
        'مشاهده را پس از رفع دسترسی تکرار کنید',
        'فهرست سرویس‌ها و شواهد فعلی را تازه کنید. نتیجهٔ این بررسی مجوز تغییر برنامه نیست.',
    ),
    'unknown': (
        'یک نشانهٔ قابل بازتولید انتخاب کنید',
        'نشانی کاربردی خطادار، زمان وقوع و نتیجهٔ مورد انتظار را مشخص کنید؛ سپس وضعیت پردازش و لاگ همان بازه را مقایسه کنید.',
        'شاهد جداکنندهٔ علت‌ها را جمع کنید',
        'شواهد تازهٔ همان سرویس و وابستگی مشخص را بررسی کنید. بدون واحد معتبر منابع یا پاسخ خطادار، علت یا راهکار قطعی انتخاب نکنید.',
    ),
}


def remediation_guidance(incident, evidence, *, can_repair):
    diagnosis = incident.get('diagnosis')
    if (not diagnosis or incident.get('investigation_state') != 'done'
            or diagnosis.get('generation') != incident.get('generation')):
        return None
    cutoff = diagnosis['cutoff']
    frozen = [item for item in evidence if item['available_at'] <= cutoff and item['quality'] != 'invalid']
    supporting = [item for item in frozen if item['id'] in diagnosis['evidence_ids']]
    decisive = [item for item in supporting if item['kind'] in ('logs', 'http_probe')]
    cited = [item['id'] for item in (decisive or supporting)[:3]]
    release_ids = [item['id'] for item in supporting if item['kind'] == 'releases'][:2]
    failed = [item for item in frozen
              if item['kind'] == 'http_probe' and item['quality'] == 'fresh'
              and item['target']['app_id'] == incident['target']['app_id']
              and item['redacted_payload'].get('check_pass') is False]
    checks = list(dict.fromkeys(item['redacted_payload']['check_id'] for item in failed))[:3]
    failures = ', '.join(f"{item['redacted_payload']['check_id']} (HTTP {item['redacted_payload'].get('http_status')})"
                         for item in failed[:3])
    cause = diagnosis['cause_family']
    first, detail, second, followup = CAUSE_STEPS.get(cause, CAUSE_STEPS['unknown'])
    mode = ('restore_observation' if cause == 'observer_access' else 'gather_evidence'
            if cause in ('unknown', 'unrelated_change') else 'review_proposal'
            if can_repair and diagnosis['outcome'] == 'repair_candidate' else 'owner_checklist')
    recheck = (f'پس از اصلاح تأییدشده، همان بررسی‌های اولیه را تکرار کنید: {failures}. '
               'پاسخ مورد انتظار و هویت نسخهٔ در حال سرویس‌دهی را بررسی کنید؛ آماده بودن انتشار کافی نیست.'
               if checks else 'نشانی یا وضعیت اصلی مورد انتظار را پس از تغییر مجاز دوباره بررسی کنید. '
               'تا مشاهدهٔ تازه ثبت نشود، رفع مشکل تأیید نشده است.')
    if cause == 'observer_access':
        recheck = 'پس از برقراری دسترسی، شواهد تازه را دریافت و بررسی را تکرار کنید؛ وضعیت سلامت برنامه هنوز مستقل از دسترسی API است.'
    return {
        'mode': mode,
        'automatic_changes': False,
        'limitation': ('هر استقرار به پیشنهاد دقیق و تأیید جداگانهٔ شما نیاز دارد.' if can_repair else
                       'راهکار اصلاحی تأییدشده‌ای برای اجرای این دستیار ثبت نشده است؛ این فهرست را با مالک سرویس دنبال کنید.'),
        'steps': [
            {'id': 'inspect', 'title': first, 'detail': detail, 'actor': 'owner',
             'evidence_ids': cited, 'check_ids': []},
            {'id': 'coordinate', 'title': second, 'detail': followup, 'actor': 'owner',
             'evidence_ids': release_ids, 'check_ids': []},
            {'id': 'verify', 'title': 'رفع مشکل را با مشاهدهٔ تازه بسنجید', 'detail': recheck,
             'actor': 'assistant', 'evidence_ids': [item['id'] for item in failed[:3]], 'check_ids': checks},
        ],
    }
