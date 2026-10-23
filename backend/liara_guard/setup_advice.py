"""Read-only deployment guidance and explicit requirement matching, no provisioning."""
from .bootstrap import select_quote
from .client import ProviderError


def setup_recommendation(provider, requirements, *, checked_at, mode):
    result = {
        'scope': 'guidance_only', 'mode': mode, 'checked_at': checked_at,
        'requirements': requirements, 'catalogue_status': 'unavailable', 'catalogue_error': None,
        'recommended_plan': None,
        'limitations': [
            'این پیشنهاد فقط حداقل منابع اعلام‌شدهٔ شما را با پلن‌های موجود مقایسه می‌کند؛ تحمل بار یا تعداد کاربر را تضمین نمی‌کند.',
            'پیش از خرید، قیمت و امکانات روز را دوباره بررسی کنید. ترافیک، دیسک اضافه و خدمات جانبی ممکن است هزینهٔ جدا داشته باشند.',
            'ساخت برنامه، تغییر پلن، تنظیم دامنه و استقرار در این فرم اجرا نمی‌شود. هر تغییر باید جداگانه بازبینی و تأیید شود.',
        ],
        'sources': [
            {'label': 'راهنمای رسمی استقرار', 'url': 'https://docs.liara.ir/paas/'},
            {'label': 'APIهای لیارا', 'url': 'https://docs.liara.ir/references/api/about/'},
        ],
    }
    try:
        read = getattr(provider, 'plan_catalogue', None)
        if read is None:
            result['catalogue_error'] = 'catalogue_unavailable'
        else:
            catalogue = read()
            try:
                result['recommended_plan'] = select_quote(
                    catalogue, min_ram_gb=requirements['ram_gb'], min_cpu=requirements['cpu_cores'],
                    min_disk_gb=requirements['disk_gb'],
                )
                result['catalogue_status'] = 'available'
            except ValueError:
                result['catalogue_status'] = 'no_matching_plan'
    except ProviderError as exc:
        result['catalogue_error'] = exc.code
    workload = requirements['workload']
    method = ('برای فایل‌های خروجی وب‌سایت استاتیک، مسیر استقرار استاتیک لیارا را انتخاب کنید؛ پردازش پس‌زمینه لازم نیست.'
              if workload == 'static' else 'برای پردازش پس‌زمینه، فرمان شروع و صف یا وابستگی لازم را مشخص کنید؛ نبود نشانی HTTP به معنی خرابی نیست.'
              if workload == 'worker' else 'برای سرویس وب، پلتفرم پروژه یا Dockerfile، فرمان شروع و پورت گوش‌دادن برنامه را مشخص کنید.')
    result['steps'] = [
        {'id': 'prepare', 'title': 'روش استقرار و وابستگی‌ها را مشخص کنید', 'detail': method},
        {'id': 'resources', 'title': 'حداقل منابع و سقف هزینه را بازبینی کنید',
         'detail': 'اندازهٔ برنامه را با اندازه‌گیری مصرف یا نیازمندی پروژه تعیین کنید. اعداد این فرم، حداقل منابع درخواستی هستند و اندازه‌گیری مصرف نیستند.'},
        {'id': 'deploy', 'title': 'نسخهٔ مشخصی را پس از تأیید مستقر کنید',
         'detail': 'در حساب لیارا، تیم و شبکهٔ درست را انتخاب کنید. تنظیمات محرمانه در سرور می‌مانند. قبل از استقرار، نسخه، سورس و اثر تغییر را بازبینی کنید.'},
        {'id': 'verify', 'title': 'ابتدا نشانی پیش‌فرض را بررسی کنید',
         'detail': 'لاگ راه‌اندازی، وضعیت نمونه‌ها و یک مسیر کاربردی را بررسی کنید. برای سرویس وب، پاسخ مورد انتظار را روی نشانی پیش‌فرض لیارا ببینید؛ آماده بودن انتشار کافی نیست.'},
        {'id': 'domain', 'title': 'دامنهٔ اختصاصی را در صورت نیاز متصل کنید',
         'detail': 'پس از کارکرد نشانی پیش‌فرض، دامنه را در پنل لیارا اضافه کنید و فقط رکوردهای DNS نمایش‌داده‌شدهٔ همان برنامه را در ثبت‌کنندهٔ دامنه تنظیم کنید. سپس وضعیت DNS و گواهی HTTPS را بررسی کنید؛ رکورد فرضی نسازید.'},
    ]
    return result
