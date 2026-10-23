import type {Evidence,Guidance} from './types'
import {evidenceLocation,uiLabel} from './presentation'
import {FileSearch,ShieldCheck} from 'lucide-react'

export function Remediation({guidance,evidence,onEvidence}:{guidance:Guidance;evidence:Evidence[];onEvidence:(value:Evidence)=>void}){
 return <section className="remediation" aria-label="قدم بعدی برای رفع مشکل">
  <h3>حالا چه کار کنم؟</h3><p className="guidance-limit"><ShieldCheck size={16}/>{guidance.limitation}</p>
  <ol>{guidance.steps.map(step=><li key={step.id}><div><h4>{step.title}</h4><span>{step.actor==='owner'?'با مالک سرویس':'بازبینی با دستیار'}</span></div><p>{step.detail}</p>
   {step.evidence_ids.length>0&&<div className="step-citations">{step.evidence_ids.map(id=>{const source=evidence.find(item=>item.id===id);return source?<button key={id} onClick={()=>onEvidence(source)}><FileSearch size={13}/>{uiLabel(source.kind)}<bdi className="technical">{evidenceLocation(source)}</bdi></button>:null})}</div>}
  </li>)}</ol><p className="coverage-note">این فهرست اقدامی اجرا نمی‌کند. بازیابی فقط با مشاهدهٔ تازه و نتیجهٔ مورد انتظار سنجیده می‌شود.</p>
 </section>
}
