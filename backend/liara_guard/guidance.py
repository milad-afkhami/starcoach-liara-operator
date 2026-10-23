"""Fixed evidence-linked owner checklists, never executable model instructions."""


CAUSE_STEPS = {
    'dependency_schema': (
        'پاسخ دو سرویس را مقایسه کنید',
        'ببینید سرویس شما چه فیلدی از سرویس دیگر می‌خواهد و واقعاً چه فیلدی دریافت می‌کند. از لاگ همان درخواست کمک بگیرید؛ تازه بودن یک release به‌تنهایی علت خطا نیست.',
        'از Codex بخواهید سورس دو طرف را بررسی کند',
        'اگر فیلدها هماهنگ نیستند، کد تولیدکننده یا مصرف‌کنندهٔ پاسخ باید اصلاح شود. از Codex بخواهید علت را در ریپازیتوری پیدا کند و تست بگیرد. پیش از deploy، تغییر و سرویس هدف را تأیید کنید.',
    ),
    'dependency_timeout': (
        'زمان پاسخ وابستگی را بررسی کنید',
        'ببینید درخواست در کدام سرویس معطل می‌شود. لاگ و زمان پاسخ همان درخواست را کنار هم بگذارید؛ مشکل شبکه و کد کند راه‌حل یکسانی ندارند.',
        'بخش کند را در سورس بررسی کنید',
        'از Codex بخواهید بخش کند را پیدا کند و با تست بررسی کند. بدون دادهٔ مصرف و سقف پلن، افزایش منابع را راه‌حل قطعی ندانید.',
    ),
    'process_crash': (
        'اولین خطای راه‌اندازی را پیدا کنید',
        'لاگ قبل از توقف برنامه را ببینید و با release در حال اجرا مقایسه کنید. خطای یک URL به‌تنهایی نشان نمی‌دهد برنامه خاموش شده است.',
        'خطای شروع برنامه را در پروژه بررسی کنید',
        'مالک سرویس باید خطای مشخص راه‌اندازی یا وابستگی را اصلاح کند. مقدار رمزها یا متغیرهای محرمانه را در پرسش یا شواهد وارد نکنید.',
    ),
    'observer_access': (
        'اتصال دستیار به لیارا را بررسی کنید',
        'کلید API و تیم انتخاب‌شده را در تنظیمات خصوصی سرور بررسی کنید. خطای دسترسی دستیار لزوماً به معنی خرابی برنامه نیست؛ کلید را در چت نفرستید.',
        'مشاهده را پس از رفع دسترسی تکرار کنید',
        'فهرست سرویس‌ها و شواهد فعلی را تازه کنید. نتیجهٔ این بررسی مجوز تغییر برنامه نیست.',
    ),
    'unknown': (
        'یک نشانهٔ قابل بازتولید انتخاب کنید',
        'بگویید کدام درخواست خطا می‌دهد، چه زمانی و چه پاسخی انتظار داشتید. لاگ همان زمان را بررسی کنید.',
        'یک بررسی برای مشخص شدن علت انجام دهید',
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
               'پاسخ مورد انتظار و release واقعاً در حال اجرا را بررسی کنید؛ آماده بودن release در پنل کافی نیست.'
               if checks else 'نشانی یا وضعیت اصلی مورد انتظار را پس از تغییر مجاز دوباره بررسی کنید. '
               'تا مشاهدهٔ تازه ثبت نشود، رفع مشکل تأیید نشده است.')
    if cause == 'observer_access':
        recheck = 'پس از برقراری دسترسی، شواهد تازه را دریافت و بررسی را تکرار کنید؛ وضعیت سلامت برنامه هنوز مستقل از دسترسی API است.'
    return {
        'mode': mode,
        'automatic_changes': False,
        'limitation': ('هر deploy به پیشنهاد دقیق و تأیید جداگانهٔ شما نیاز دارد.' if can_repair else
                       'دستیار نمی‌تواند این سرویس را خودکار اصلاح کند. برای بررسی سورس و تست، متن آماده را به Codex پروژه‌تان بدهید.'),
        'steps': [
            {'id': 'inspect', 'title': first, 'detail': detail, 'actor': 'owner',
             'evidence_ids': cited, 'check_ids': []},
            {'id': 'coordinate', 'title': second, 'detail': followup, 'actor': 'owner',
             'evidence_ids': release_ids, 'check_ids': []},
            {'id': 'verify', 'title': 'همان درخواست خطادار را دوباره امتحان کنید', 'detail': recheck,
             'actor': 'assistant', 'evidence_ids': [item['id'] for item in failed[:3]], 'check_ids': checks},
        ],
    }
