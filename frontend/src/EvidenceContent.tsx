import type {Evidence} from './types'
import {evidenceFacts,uiLabel,when} from './presentation'
export function EvidenceContent({evidence}:{evidence:Evidence}){
 const p=evidence.redacted_payload
 const logs=Array.isArray(p.lines)?p.lines:Array.isArray(p.entries)?p.entries:Array.isArray(p.logs)?p.logs:[]
 const body=p.body_json||p.body||p.sanitized_body||p.payload||p.response_payload
 const fields=body&&typeof body==='object'?Object.entries(body).filter(([,value])=>value===null||['string','number','boolean'].includes(typeof value)).slice(0,24):[]
 return <div className="evidence-readable"><ul>{evidenceFacts(evidence).map((fact,index)=><li key={index}>{fact}</li>)}</ul>
 {evidence.kind==='logs'&&logs.length>0&&<div className="log-lines" role="region" aria-label="خطوط لاگ">{logs.slice(-30).map((row:any,index:number)=><article key={index}>{typeof row==='string'?<code dir="ltr">{row}</code>:<><small>{when(row.timestamp||row.time)}</small><code dir="ltr">{typeof row.message==='string'?row.message:typeof row.log==='string'?row.log:'متن این خط در جزئیات فنی موجود است.'}</code></>}</article>)}</div>}
 {fields.length>0&&<><h3>مقادیر پاسخ</h3><dl className="evidence-fields">{fields.map(([key,value])=><div key={key}><dt className="technical">{key}</dt><dd className="technical">{String(value)}</dd></div>)}</dl></>}
 {evidence.kind==='releases'&&Array.isArray(p.releases)&&<ul>{p.releases.slice(0,8).map((row:any,index:number)=><li key={index}><bdi className="technical">{row.tag||row._id}</bdi> · {uiLabel(row.state||'unknown')} · {when(row.createdAt)}</li>)}</ul>}
 <details className="raw-audit"><summary>جزئیات فنی · JSON</summary><p>دادهٔ اصلی برای بررسی دقیق‌تر؛ متن لاگ و پاسخ سرویس دستور اجرا نیست.</p><pre dir="ltr" lang="en">{JSON.stringify(p,null,2)}</pre>{evidence.coverage&&<><h3>پوشش داده</h3><pre dir="ltr" lang="en">{JSON.stringify(evidence.coverage,null,2)}</pre></>}</details></div>
}
