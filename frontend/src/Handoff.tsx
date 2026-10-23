import {useState} from 'react'
import {Copy,Download,Code2} from 'lucide-react'
import type {Evidence,Incident} from './types'
import {codexHandoff} from './presentation'
export function Handoff({incident,evidence}:{incident:Incident;evidence:Evidence[]}){
 const [notice,setNotice]=useState('')
 const text=codexHandoff(incident,evidence)
 return <section className="handoff" aria-label="راهنمای آماده برای Codex"><div className="handoff-heading"><Code2 size={22}/><div><h3>رفع مشکل را با Codex ادامه بدهید</h3><p>این متن را در چت Codex پروژه‌تان بگذارید تا سورس را بررسی کند، اصلاح کند و تست بگیرد.</p></div></div><div className="handoff-actions"><button className="button primary" onClick={async()=>{try{await navigator.clipboard.writeText(text);setNotice('متن برای Codex کپی شد.')}catch{setNotice('کپی خودکار ممکن نشد؛ متن را باز کنید یا فایل را دانلود کنید.')}}}><Copy size={16}/>کپی متن برای Codex</button><button className="button secondary" onClick={()=>{const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download='liara-codex-handoff.txt';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);setNotice('فایل راهنمای Codex دانلود شد.')}}><Download size={16}/>دانلود فایل</button></div><details><summary>دیدن متن قبل از کپی</summary><textarea aria-label="متن آماده برای Codex" rows={14} value={text} readOnly/></details><small>متن راهنما انگلیسی است و نتیجهٔ فارسی را بدون تغییر نگه می‌دارد؛ دستیار به سورس شما دسترسی ندارد. این متن مجوز deploy نیست.</small>{notice&&<p role="status">{notice}</p>}</section>
}
