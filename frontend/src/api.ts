export class ApiError extends Error {status:number;code:string;constructor(status:number,code:string){super(messageFor(code));this.status=status;this.code=code}}
const messages:Record<string,string>={
 invalid_login:'رمز ورود درست نیست. دوباره تلاش کنید.',rate_limited:'تعداد تلاش\u200cها زیاد است. یک دقیقه صبر کنید و دوباره تلاش کنید.',unauthenticated:'نشست شما پایان یافته است. دوباره وارد شوید.',
 provider_not_configured:'اتصال لیارا تنظیم نشده است. دستیار محلی آماده است؛ مالک باید حساب را متصل کند.',observer_auth:'دسترسی به لیارا رد شد. این کمبود شواهد است و خرابی سرویس را ثابت نمی\u200cکند.',
 observer_network:'اتصال به لیارا ممکن نشد. مشاهدات قبلی در دسترس می\u200cمانند.',runtime_unavailable:'دستیار هوشمند در دسترس نیست. پایش و مشاهدهٔ شواهد همچنان قابل استفاده است.',
 investigation_in_progress:'یک بررسی در همین نشست در حال اجراست. ابتدا آن را تمام یا لغو کنید.',investigation_queue_full:'صف بررسی پر است. پایش ادامه دارد؛ کمی بعد دوباره تلاش کنید.',
 stale_generation:'سرویس در حین بررسی تغییر کرد. بررسی را با شواهد فعلی تکرار کنید.',server_restarted:'دستیار دوباره راه\u200cاندازی شد و بررسی قبلی متوقف شد. بررسی تازه\u200cای شروع کنید.',
 canceled:'بررسی لغو شد.',expired:'مهلت بررسی تمام شد. شواهد دریافت\u200cشده را ببینید یا پرسش دقیق\u200cتری بپرسید.',
 busy:'مدل مشغول بررسی دیگری است. پایش همچنان در دسترس است.',budget_exhausted:'سهمیهٔ تنظیم\u200cشدهٔ مدل تمام شده است. پایش و مشاهدهٔ شواهد همچنان ممکن است.',
 recovery_recheck_unavailable:'بازبینی بازیابی برای این عملیات در دسترس نیست؛ ارتباط تصمیم، نسخه و مهلت اصلی را بررسی کنید.',
 repair_not_enrolled_or_supported:'برای این سرویس، رفع مشکل پشتیبانی\u200cشده و تأییدشده ثبت نشده است. پایش و بررسی همچنان ممکن است.',
 live_provider_required_for_deployment:'استقرار واقعی به اتصال مجاز و زندهٔ لیارا نیاز دارد.',approval_rejected:'تأیید منقضی یا استفاده شده، یا دیگر با سرویس تطابق ندارد. پیشنهاد تازه\u200cای آماده کنید.',
 watch_scope_or_state_conflict:'پایش دیگری فعال است یا انتخاب شما از محدودهٔ پایش فراتر می\u200cرود.',not_found:'این مورد در نشست فعلی در دسترس نیست.',
 evidence_read_failed:'دریافت یکی از شواهد لازم ناموفق بود. دستیار هنوز علتی اعلام نکرده است.',invalid_model_output:'پاسخ مدل معتبر نبود و هیچ اقدامی انجام نشد.',
}
export function messageFor(code:string){return messages[code]||'درخواست انجام نشد. شواهد را تازه کنید و دوباره تلاش کنید.'}
async function request<T>(path:string,method:string,body?:unknown):Promise<T>{
 let response:Response
 try{response=await fetch(path,{method,credentials:'same-origin',headers:body===undefined?undefined:{'content-type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)})}catch{throw new Error('اتصال برقرار نشد. نمای فعلی حفظ شده است؛ دوباره تلاش کنید.')}
 const data=await response.json().catch(()=>({}))
 if(!response.ok)throw new ApiError(response.status,typeof data.detail==='string'?data.detail:'invalid_request')
 return data as T
}
export const api={get:<T,>(path:string)=>request<T>(path,'GET'),post:<T,>(path:string,body:unknown={})=>request<T>(path,'POST',body)}
