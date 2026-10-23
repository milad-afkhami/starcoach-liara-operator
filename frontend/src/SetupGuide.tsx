import {useEffect,useRef,useState} from 'react'
import {LoaderCircle,X} from 'lucide-react'
import {api} from './api'
import {Dialog} from './Dialog'
import {when} from './presentation'

interface Advice {scope:string;mode:string;checked_at:number;catalogue_status:string;catalogue_error:string|null;recommended_plan:{plan_id:string;bundle_plan_id:string;ram_gb:string;cpu:string;disk_gb:number;hourly_price_toman:string;vat_rate:string}|null;limitations:string[];steps:{id:string;title:string;detail:string}[];sources:{label:string;url:string}[]}
export function SetupGuide({onClose,onError}:{onClose:()=>void;onError:(error:unknown)=>void}){
 const [workload,setWorkload]=useState('web'),[ram,setRam]=useState('0.5'),[cpu,setCpu]=useState('0.5'),[disk,setDisk]=useState('5')
 const [advice,setAdvice]=useState<Advice|null>(null),[loading,setLoading]=useState(false)
 const active=useRef(true)
 useEffect(()=>()=>{active.current=false},[])
 async function submit(event:React.FormEvent){event.preventDefault();setLoading(true);setAdvice(null);try{const value=await api.post<Advice>('/api/setup/recommendation',{workload,ram_gb:Number(ram),cpu_cores:Number(cpu),disk_gb:Number(disk)});if(active.current)setAdvice(value)}catch(error){if(active.current)onError(error)}finally{if(active.current)setLoading(false)}}
 return <Dialog className="setup-dialog" label="راهنمای راه‌اندازی" onClose={onClose}>
  <div className="section-head"><h2>شروع یک سرویس در لیارا</h2><button className="icon-button" aria-label="بستن راهنمای راه‌اندازی" onClick={onClose}><X size={20}/></button></div>
  <p>نوع پروژه و حداقل منابع موردنیاز را مشخص کنید. دستیار مسیر شروع را توضیح می‌دهد و اگر فهرست پلن‌ها در دسترس باشد، یک گزینهٔ سازگار پیشنهاد می‌کند.</p>
  <form onSubmit={event=>void submit(event)} onChange={()=>setAdvice(null)}>
   <label>نوع پروژه<select value={workload} onChange={event=>setWorkload(event.target.value)} disabled={loading}><option value="web">سرویس وب</option><option value="worker">پردازش پس‌زمینه</option><option value="static">وب‌سایت استاتیک</option></select></label>
   <div className="setup-resources"><label>حداقل RAM (GB)<input dir="ltr" type="number" min="0.25" max="128" step="0.25" value={ram} onChange={event=>setRam(event.target.value)} required disabled={loading}/></label><label>حداقل CPU (هسته)<input dir="ltr" type="number" min="0.1" max="64" step="0.1" value={cpu} onChange={event=>setCpu(event.target.value)} required disabled={loading}/></label><label>حداقل دیسک (GB)<input dir="ltr" type="number" min="1" max="1024" step="1" value={disk} onChange={event=>setDisk(event.target.value)} required disabled={loading}/></label></div>
   <p className="coverage-note">این اعداد نیازمندی اعلام‌شدهٔ شما هستند؛ تعداد کاربر یا تحمل بار از روی آن‌ها تخمین زده نمی‌شود.</p><button className="button primary" disabled={loading}>{loading?<LoaderCircle size={16} className="spin"/>:null}{loading?'در حال بررسی پلن‌های در دسترس…':'دریافت راهنمای پلن و deploy'}</button>
  </form>
  {advice&&<div className="setup-result" role="status"><h3>پیشنهاد شروع</h3>{advice.mode==='fixture'&&<p className="coverage-note">این اجرا محلی است؛ قیمت و فهرست حساب واقعی تأیید نشده است.</p>}
   {advice.recommended_plan?<><dl className="plan-quote"><div><dt>پلن و امکانات</dt><dd><bdi className="technical">{advice.recommended_plan.plan_id} / {advice.recommended_plan.bundle_plan_id}</bdi></dd></div><div><dt>منابع</dt><dd><bdi>RAM {advice.recommended_plan.ram_gb} GB · CPU {advice.recommended_plan.cpu} · دیسک {advice.recommended_plan.disk_gb} GB</bdi></dd></div><div><dt>برآورد ساعتی با مالیات</dt><dd>{Number(advice.recommended_plan.hourly_price_toman).toLocaleString('fa-IR')} تومان</dd></div></dl><p className="coverage-note">دریافت فهرست: {when(advice.checked_at)}. پیش از خرید دوباره بررسی شود.</p></>:<p className="setup-unavailable">{advice.catalogue_status==='no_matching_plan'?'پلن موجودی با همهٔ حداقل‌های شما پیدا نشد. نیازمندی را بازبینی کنید یا پلن‌های حساب را در لیارا ببینید.':advice.catalogue_error==='observer_auth'?'دسترسی به فهرست پلن‌ها رد شد؛ مالک باید اتصال حساب را در سرور بررسی کند. راهنمای deploy همچنان در دسترس است.':'فهرست پلن یا قیمت حساب در دسترس نیست؛ قیمت یا پلن فرضی پیشنهاد نمی‌شود. مسیر شروع را در ادامه ببینید.'}</p>}
   <ol className="setup-steps">{advice.steps.map(step=><li key={step.id}><h4>{step.title}</h4><p>{step.detail}</p></li>)}</ol><ul className="setup-limitations">{advice.limitations.map(item=><li key={item}>{item}</li>)}</ul><div className="setup-sources">{advice.sources.map(source=><a key={source.url} href={source.url} target="_blank" rel="noreferrer">{source.label}</a>)}</div>
  </div>}
 </Dialog>
}
