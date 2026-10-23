import {useRef} from 'react'
import type {Evidence} from './types'
import {resourceSeries,resourceInstanceAliases,chartSegments,uiLabel,when} from './presentation'
import type {ResourceSeries} from './presentation'
import {FileSearch} from 'lucide-react'
const format=(value:number)=>value.toLocaleString('fa-IR',{maximumFractionDigits:2})
function Chart({series,instanceLabel}:{series:ResourceSeries;instanceLabel:string}){
 const valid=series.points.filter(p=>p.value!==null),first=valid[0],last=valid[valid.length-1],min=first.at,max=last.at
 const peak=Math.max(...valid.map(p=>p.value!)),ceiling=peak||1
 const x=(at:number)=>44+(max===min?216:(at-min)/(max-min)*432),y=(value:number)=>130-value/ceiling*104
 const clock=(stamp:number)=>new Intl.DateTimeFormat('fa-IR',{timeZone:'Asia/Tehran',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).format(stamp*1000)
 return <article className="resource-chart"><div><h3><bdi className="technical">{series.metric==='cpu'?'CPU':'RAM'}</bdi><small className="instance-alias" title={series.applet}>{instanceLabel}</small></h3><strong>{format(last.value!)} <bdi>{series.unit}</bdi></strong></div><p>{valid.length.toLocaleString('fa-IR')} نمونهٔ معتبر · {series.historical?'تاریخچهٔ پنج دقیقهٔ دریافت‌شده':'یک مشاهده؛ روند مصرف مشخص نیست'}</p>
 {valid.length>1?<svg viewBox="0 0 500 165" role="img" aria-label={`${series.metric==='cpu'?'CPU':'RAM'}؛ ${valid.length} نمونه با واحد ${series.unit}`} style={{direction:'ltr'}}><line x1="44" y1="26" x2="476" y2="26" className="chart-grid"/><line x1="44" y1="78" x2="476" y2="78" className="chart-grid"/><line x1="44" y1="130" x2="476" y2="130" className="chart-grid"/><text x="38" y="30" textAnchor="end">{format(peak)}</text><text x="38" y="134" textAnchor="end">۰</text>{chartSegments(series.points).map((segment,index)=><g key={index}>{segment.length>1&&<polyline points={segment.map(p=>`${x(p.at)},${y(p.value!)}`).join(' ')} fill="none" className="chart-line"/>}{segment.map((p,i)=><circle key={i} cx={x(p.at)} cy={y(p.value!)} r="3" className="chart-point"><title>{when(p.at)}: {format(p.value!)} {series.unit}</title></circle>)}</g>)}<text x="44" y="156" textAnchor="start">{clock(min)}</text><text x="476" y="156" textAnchor="end">{clock(max)}</text></svg>:<div className="single-sample">فقط یک نمونه داریم؛ برای رسم روند کافی نیست.</div>}
 <small>{when(first.at)}{max!==min?` تا ${when(last.at)}`:''}</small><details><summary>زمان و مقدار نمونه‌ها</summary><p className="instance-provenance">شناسهٔ دقیق {instanceLabel}: <bdi className="technical">{series.applet}</bdi></p><table><thead><tr><th>زمان تهران</th><th>{series.unit}</th></tr></thead><tbody>{valid.map((p,i)=><tr key={i}><td>{when(p.at)}</td><td>{format(p.value!)}</td></tr>)}</tbody></table></details></article>
}
export function ResourcePanel({evidence,history,onEvidence}:{evidence:Evidence|undefined;history?:Evidence;onEvidence:(value:Evidence)=>void}){
 const instanceAliases=useRef({target:'',values:new Map<string,string>()})
 const series=resourceSeries(evidence,history),historical=series.some(s=>s.historical)
 const target=history?.target?.app_id||evidence?.target?.app_id||''
 if(instanceAliases.current.target!==target)instanceAliases.current={target,values:new Map()}
 instanceAliases.current.values=resourceInstanceAliases(series,instanceAliases.current.values)
 return <section className="resource-panel" role="region" aria-label="مشاهدهٔ مصرف CPU و RAM"><div className="resource-heading"><h2>مصرف CPU و RAM</h2><span>{uiLabel(evidence?.quality||'unavailable')}</span></div>
 {evidence?.quality==='invalid'&&<p className="resource-warning">زمان یا قالب خلاصهٔ مصرف معتبر نیست؛ مصرف فعلی مشخص نیست.</p>}
 {historical&&<p className="coverage-note" data-testid="historical-resource-notice">این نمودار تاریخچه است، مصرف لحظه‌ای نیست. اختلاف ساعت لیارا و دریافت‌کننده هنوز مشخص نیست. نقاط آینده یا قدیمی‌تر از بازه نمایش داده نمی‌شوند.</p>}
 {series.length?<div className="resource-charts">{series.map((s,index)=><Chart key={index} series={s} instanceLabel={instanceAliases.current.values.get(s.applet)!}/>)}</div>:<div className="unconfigured">دادهٔ معتبر با واحد مشخص نداریم؛ نمودار یا مصرف صفر فرضی نمایش نمی‌دهیم.</div>}
 <p className="coverage-note">هر نمونهٔ اجرا جداست. CPU با واحد تأییدشدهٔ لیارا و RAM به MiB نمایش داده می‌شود. بریدگی خط یعنی دادهٔ نامعتبر یا فاصلهٔ بیش از ۶۰ ثانیه؛ بین این نقاط حدس نمی‌زنیم. این داده‌ها کافی بودن پلن را ثابت نمی‌کنند.</p>
 <details className="resource-audit"><summary>منبع و محدودیت داده‌ها</summary><p>زمان‌ها به وقت تهران‌اند و از زمان اصلی نمونه می‌آیند؛ ساعت یا داده جابه‌جا نشده است.</p>{history&&<p>نمونه‌های حذف‌شده: آینده {history.coverage?.excluded_future||0}، قدیمی {history.coverage?.excluded_stale||0}، نامعتبر {history.coverage?.excluded_invalid||0}.{history.coverage?.truncated?' تعداد سری‌ها محدود شده است.':''}{Object.keys(history.coverage?.source_errors||{}).length?' بخشی از تاریخچه دریافت نشده است.':''}</p>}{evidence&&<button onClick={()=>onEvidence(evidence)}><FileSearch size={14}/>جزئیات خلاصه و واحدها</button>}{history&&<button onClick={()=>onEvidence(history)}><FileSearch size={14}/>جزئیات تاریخچه</button>}</details></section>
}
