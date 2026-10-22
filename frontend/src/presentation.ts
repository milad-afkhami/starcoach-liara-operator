export function httpSummary(value:{http_status:number|null;check_pass:boolean|null;reason:string}):{label:string;tone:string}{
 if(value.http_status===null||value.check_pass===null)return {label:'مشاهده در دسترس نیست',tone:'unknown'}
 return {label:`HTTP ${value.http_status}`,tone:value.check_pass?'good':'bad'}
}
export function remainingTime(end:number,now:number):string{
 const seconds=Math.max(0,Math.ceil(end-now));return `${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`
}
export function when(value:number|string|null|undefined):string{
 if(value===null||value===undefined)return 'هنوز مشاهده نشده'
 const date=new Date(typeof value==='number'?value*1000:value)
 return Number.isNaN(date.valueOf())?'زمان در دسترس نیست':new Intl.DateTimeFormat('fa-IR-u-ca-persian',{timeZone:'Asia/Tehran',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).format(date)+' — به وقت تهران'
}

export function investigationEndpoint(serviceId:string,incident?:{id:string;target:{app_id:string};state:string}):string{
 return incident?.target.app_id===serviceId&&incident.state==='open'?`/api/incidents/${encodeURIComponent(incident.id)}/investigate`:`/api/services/${encodeURIComponent(serviceId)}/investigate`
}

export function operationNeedsPolling(operation:{state:string;reconcile_until?:number|null},now:number):boolean{
 if(operation.state==='unknown')return operation.reconcile_until!=null&&now<=operation.reconcile_until
 return ['checking','uploading','creating_release','pending','ready','verifying'].includes(operation.state)
}
export function mayReplaceOperation(operation:{state:string;expires_at:number}|undefined,stale:boolean,now:number):boolean{
 return !operation||['failed','completed'].includes(operation.state)||stale||(['proposed','approved'].includes(operation.state)&&operation.expires_at<=now)
}

/** Presentation only: API states and technical identifiers are never rewritten. */
const labels:Record<string,string>={
 'No enrolled verified repair artifact for this service.':'برای این سرویس، سورس سالم و تأییدشده‌ای برای رفع مشکل ثبت نشده است.',
 'Fixture metadata':'اطلاعات شبیه‌سازی‌شده', fixture_metadata:'اطلاعات شبیه‌سازی‌شده', invalid:'نامعتبر', READY:'آماده', Running:'در حال اجرا', Failed:'ناموفق', Stopped:'متوقف', ERROR:'خطا', http_probe:'بررسی نشانی سرویس', project:'پروژه', logs:'گزارش‌های سرویس', metrics:'مصرف منابع', releases:'انتشارها', applets:'نمونه‌های اجرا', events:'رویدادها',
 fresh:'تازه', stale:'قدیمی', unavailable:'در دسترس نیست', partial:'ناقص', unknown:'نامعلوم',
 need_evidence:'نیاز به شواهد بیشتر', done:'پایان‌یافته', unresolved:'علت مشخص نشده', guidance:'راهنمایی', observation_gap:'کمبود شواهد', active:'فعال', stopped:'متوقف‌شده', expired:'پایان‌یافته', queued:'در صف', running:'در حال اجرا', completed:'تکمیل‌شده', canceled:'لغوشده', failed:'ناموفق', idle:'آماده', open:'باز', recovered:'بازیابی‌شده',
 proposed:'پیشنهادشده', approved:'تأییدشده', checking:'در حال بررسی', uploading:'در حال بارگذاری', creating_release:'در حال ساخت انتشار', pending:'در انتظار', ready:'آماده', verifying:'در حال راستی‌آزمایی',
 dependency_schema:'ناسازگاری پاسخ سرویس وابسته', dependency_timeout:'پایان مهلت سرویس وابسته', process_crash:'خطا در راه‌اندازی پردازش', observer_access:'دسترسی به شواهد ممکن نیست', unrelated_change:'علت بودن تغییر اثبات نشده',
 repair_candidate:'نیازمند پیشنهاد رفع مشکل', read_only:'فقط بررسی', inconclusive:'نتیجه نامشخص', unsupported:'پشتیبانی‌نشده', healthy:'سالم', unhealthy:'ناسالم',
 diagnosed:'بررسی‌شده', read_only_guidance:'راهنمایی بدون تغییر', uncertain:'نامشخص', repair_recommended:'پیشنهاد رفع مشکل', original_checks_and_serving_build_verified:'نشانی‌های اصلی و هویت نسخهٔ در حال اجرا تأیید شدند', original_symptom_persists:'نشانهٔ اصلی خطا همچنان دیده می‌شود', insufficient_fresh_identity_proof:'شواهد تازه برای تأیید هویت نسخه کافی نیست', verification_deadline:'مهلت راستی‌آزمایی تمام شد', policy_changed:'سیاست راستی‌آزمایی تغییر کرده است', approved_policy_changed:'سیاست تأییدشده تغییر کرده است', incident_operation_changed:'ارتباط بررسی و عملیات تغییر کرده است', verification_unavailable:'راستی‌آزمایی در دسترس نیست', not_started:'هنوز آغاز نشده', verification_interrupted:'راستی‌آزمایی قطع شده است', verification_passed:'راستی‌آزمایی موفق', symptom_persists:'نشانهٔ خطا همچنان دیده می‌شود',
}
export function uiLabel(value:string):string{return labels[value]||labels[value.replaceAll(' ','_')]||value}
