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
 return ['checking','uploading','creating_release','pending','ready','awaiting_serving','verifying'].includes(operation.state)
}
export function mayReplaceOperation(operation:{state:string;expires_at:number}|undefined,stale:boolean,now:number):boolean{
 return !operation||['failed','completed'].includes(operation.state)||stale||(['proposed','approved'].includes(operation.state)&&operation.expires_at<=now)
}

/** Presentation only: API states and technical identifiers are never rewritten. */
const labels:Record<string,string>={
 'No enrolled verified repair artifact for this service.':'برای این سرویس، سورس سالم و تأییدشده‌ای برای رفع مشکل ثبت نشده است.',
 'Fixture metadata':'اطلاعات شبیه‌سازی‌شده', fixture_metadata:'اطلاعات شبیه‌سازی‌شده', invalid:'نامعتبر', READY:'آماده', Running:'در حال اجرا', Failed:'ناموفق', Stopped:'متوقف', ERROR:'خطا', http_probe:'بررسی نشانی سرویس', project:'پروژه', logs:'گزارش‌های سرویس', metrics:'مصرف منابع', metrics_history:'تاریخچهٔ مصرف منابع', releases:'انتشارها', applets:'نمونه‌های اجرا', events:'رویدادها',
 fresh:'تازه', stale:'قدیمی', unavailable:'در دسترس نیست', partial:'ناقص', unknown:'نامعلوم',
 need_evidence:'نیاز به شواهد بیشتر', done:'پایان‌یافته', unresolved:'علت مشخص نشده', guidance:'راهنمایی', observation_gap:'کمبود شواهد', active:'فعال', stopped:'متوقف‌شده', expired:'پایان‌یافته', queued:'در صف', running:'در حال اجرا', completed:'تکمیل‌شده', canceled:'لغوشده', failed:'ناموفق', idle:'آماده', open:'باز', recovered:'بازیابی‌شده',
 awaiting_serving:'در انتظار نسخهٔ در حال سرویس‌دهی',serving_identity_pending:'هویت نسخهٔ در حال سرویس‌دهی هنوز تأیید نشده',operation_binding_changed:'ارتباط عملیات، تصمیم یا سیاست تغییر کرده است',
 proposed:'پیشنهادشده', approved:'تأییدشده', checking:'در حال بررسی', uploading:'در حال بارگذاری', creating_release:'در حال ساخت انتشار', pending:'در انتظار', ready:'آماده', verifying:'در حال راستی‌آزمایی',
 dependency_schema:'ناسازگاری پاسخ سرویس وابسته', dependency_timeout:'پایان مهلت سرویس وابسته', process_crash:'خطا در راه‌اندازی پردازش', observer_access:'دسترسی به شواهد ممکن نیست', unrelated_change:'علت بودن تغییر اثبات نشده',
 repair_candidate:'نیازمند پیشنهاد رفع مشکل', read_only:'فقط بررسی', inconclusive:'نتیجه نامشخص', unsupported:'پشتیبانی‌نشده', healthy:'سالم', unhealthy:'ناسالم',
 diagnosed:'بررسی‌شده', read_only_guidance:'راهنمایی بدون تغییر', uncertain:'نامشخص', repair_recommended:'پیشنهاد رفع مشکل', original_checks_and_serving_build_verified:'نشانی‌های اصلی و هویت نسخهٔ در حال اجرا تأیید شدند', original_symptom_persists:'نشانهٔ اصلی خطا همچنان دیده می‌شود', insufficient_fresh_identity_proof:'شواهد تازه برای تأیید هویت نسخه کافی نیست', verification_deadline:'مهلت راستی‌آزمایی تمام شد', policy_changed:'سیاست راستی‌آزمایی تغییر کرده است', approved_policy_changed:'سیاست تأییدشده تغییر کرده است', incident_operation_changed:'ارتباط بررسی و عملیات تغییر کرده است', verification_unavailable:'راستی‌آزمایی در دسترس نیست', not_started:'هنوز آغاز نشده', verification_interrupted:'راستی‌آزمایی قطع شده است', verification_passed:'راستی‌آزمایی موفق', symptom_persists:'نشانهٔ خطا همچنان دیده می‌شود',
}
export function uiLabel(value:string):string{return labels[value]||labels[value.replaceAll(' ','_')]||value}

export function evidenceLocation(value:{target?:{app_name:string};redacted_payload:Record<string,any>}):string{
 const target=value.target?.app_name||'سرویس نامشخص'
 const check=typeof value.redacted_payload.check_id==='string'?value.redacted_payload.check_id:null
 return check?`${target} · ${check}`:target
}
export function progressLabel(progress?:{stage:string;read_name?:string|null;reads_completed:number;model_call?:number|null}):string{
 if(!progress||progress.stage==='queued')return 'در صف بررسی؛ هنوز علتی اعلام نشده است.'
 if(progress.stage==='collecting'){
  const name=progress.read_name||''
  const source=name.startsWith('dependency:')?'بررسی وابستگی '+name.slice(11):name.startsWith('http:')?'بررسی نشانی '+name.slice(5):uiLabel(name)
  return `دریافت ${source}؛ ${progress.reads_completed.toLocaleString('fa-IR')} دریافت شواهد کامل شده است.`
 }
 if(progress.stage==='analyzing')return `تحلیل شواهد؛ مرحلهٔ ${(progress.model_call||1).toLocaleString('fa-IR')} از حداکثر ۲ تحلیل. ${progress.reads_completed.toLocaleString('fa-IR')} دریافت شواهد کامل شده است.`
 if(progress.stage==='validating')return 'اعتبارسنجی پاسخ و ارجاع‌های آن؛ هنوز هیچ تغییری اجرا نشده است.'
 return 'بررسی پایان یافته است.'
}

export function resourceValue(sample:{metric:string;value:number;unit:string}):string{
 if(!Number.isFinite(sample.value)||sample.value<0)return 'در دسترس نیست'
 const format=(value:number)=>value.toLocaleString('fa-IR',{maximumFractionDigits:2})
 if(sample.metric==='memory'&&sample.unit==='bytes')return `${format(sample.value/1048576)} MiB`
 if(sample.metric==='cpu'&&sample.unit==='percent')return `${format(sample.value)}٪`
 return 'واحد تأیید نشده'
}

export function mayRecheckRecovery(operation:{state:string;release_id:string|null;reconcile_until?:number|null;recovery_rechecks_used?:number;spec:{kind:string;incident_generation:number};verification?:{state:string}}|undefined,now:number,generation:number|undefined):boolean{
 return !!operation&&operation.state==='failed'&&operation.verification?.state==='inconclusive'&&operation.spec.kind==='redeploy_known_good'&&!!operation.release_id&&(operation.recovery_rechecks_used||0)===0&&operation.reconcile_until!=null&&now<operation.reconcile_until&&operation.spec.incident_generation===generation
}

export function diagnosisPresentation(state:string,actionStarted=false){
 const historical=state==='recovered'||actionStarted
 return {historical,title:historical?(actionStarted?'تحلیل پیش از اقدام':'تحلیل ثبت‌شدهٔ پیشین'):'تحلیل ثبت‌شده',outcomePrefix:historical?'نتیجه در زمان تحلیل: ':'',unknownsTitle:historical?'موارد نامعلوم در زمان تحلیل':'چه چیزهایی هنوز نامعلوم است؟'}
}
export function releasePresentation(state:string,verification?:string){
 return {beforeLabel:'انتشار پیش از استقرار',afterLabel:state==='completed'&&verification==='recovered'?'انتشار مستقرشده و تأییدشده':'انتشار ارسال‌شده'}
}

export function resourceSamples(evidence:any):any[]{
 if(!evidence||evidence.coverage?.unit_verified!==true||!['fresh','stale'].includes(evidence.quality)||!Array.isArray(evidence.redacted_payload?.measurements))return []
 if(evidence.kind==='metrics_history'&&evidence.redacted_payload.historical_only!==true)return []
 return evidence.redacted_payload.measurements.slice(0,12)
}
