import type {Evidence} from './types'
import {resourceValue,resourceSamples,uiLabel,when} from './presentation'
import {FileSearch} from 'lucide-react'

interface Measurement {metric:string;applet:string;value:number;unit:string;observed_at:number;age_seconds?:number}
export function ResourcePanel({evidence,history,onEvidence}:{evidence:Evidence|undefined;history?:Evidence;onEvidence:(value:Evidence)=>void}){
 if(!evidence&&!history)return null
 const samples:Measurement[]=resourceSamples(evidence)
 const historical:Measurement[]=samples.length?[]:resourceSamples(history)
 const shown=historical.length?historical:samples
 const source=historical.length?history:evidence
 return <div className="resource-panel" role="region" aria-label="مشاهدهٔ مصرف CPU و RAM"><div className="resource-heading"><h3>مصرف منابع در آخرین نمونه‌ها</h3><span>{uiLabel(evidence?.quality||'unavailable')}</span></div>
  {!samples.length&&<p className="coverage-note">{evidence?.quality==='invalid'?'زمان یا قالب نمونه‌های خلاصه معتبر نیست؛ مصرف فعلی نمایش داده نمی‌شود.':'نمونهٔ خلاصهٔ معتبر با واحد شناخته‌شده در دسترس نیست؛ مصرف صفر یا ظرفیت سالم فرض نمی‌شود.'}</p>}
  {!!historical.length&&<div className="coverage-note" data-testid="historical-resource-notice"><h4>مشاهدات تاریخی CPU و RAM</h4><p>این مقادیر از تاریخچهٔ لیارا و فقط از زمان‌های پیش از دریافت انتخاب شده‌اند؛ مصرف لحظه‌ای نیستند. ناسازگاری ساعت‌ها و هشدار خلاصه همچنان برقرار است.</p><p>پایان بازهٔ انتخاب: {when(history?.redacted_payload.cutoff)} · منبع: <bdi className="technical">/metrics/cpu · /metrics/memory</bdi></p></div>}
  {!!shown.length&&<><div className="resource-samples">{shown.map((sample,index)=><article key={index}><span><bdi className="technical">{sample.metric==='cpu'?'CPU':'RAM'}</bdi> · <bdi className="technical">{sample.applet}</bdi></span><strong>{resourceValue(sample)}</strong><small>{when(sample.observed_at)}</small>{historical.length>0&&<small>سن نمونه هنگام دریافت: {new Intl.NumberFormat('fa-IR',{maximumFractionDigits:1}).format(sample.age_seconds||0)} ثانیه</small>}</article>)}</div><p>نمونهٔ مصرف هر پردازش جداست. درصد CPU مطابق نمایش لیارا است؛ مقدار RAM به MiB تبدیل شده است.</p><p className="coverage-note">این یک مشاهده است، نه آزمون تحمل بار. سقف اختصاص‌یافته و تداوم مصرف باید پیش از نتیجه‌گیری دربارهٔ کمبود ظرفیت بررسی شوند.{source?.quality==='stale'?' این نمونه‌ها قدیمی‌اند و وضعیت فعلی را ثابت نمی‌کنند.':''}</p></>}
  {!samples.length&&history&&<p className="coverage-note">نمونه‌های کنارگذاشته‌شده از تاریخچه: آینده {history.coverage?.excluded_future||0}، قدیمی {history.coverage?.excluded_stale||0}، نامعتبر {history.coverage?.excluded_invalid||0}.{!historical.length?' نمونهٔ تاریخی واجد شرایط در دسترس نیست.':''}{history.coverage?.truncated?' نمایش نمونه‌ها محدود شده است.':''}{Object.keys(history.coverage?.source_errors||{}).length?' دریافت بخشی از تاریخچه کامل نشده است؛ شواهد خام را بررسی کنید.':''}</p>}
  {evidence&&<button onClick={()=>onEvidence(evidence)}><FileSearch size={14}/>شواهد خلاصه و منبع واحدها</button>}
  {history&&!samples.length&&<button onClick={()=>onEvidence(history)}><FileSearch size={14}/>تاریخچه و سری‌های خام برای بررسی</button>}
 </div>
}
