export class ApiError extends Error {status:number;code:string;constructor(status:number,code:string){super(messageFor(code));this.status=status;this.code=code}}
const messages:Record<string,string>={
 invalid_login:'That password did not match. Try again.',rate_limited:'Too many attempts. Wait a minute before trying again.',unauthenticated:'Your session ended. Sign in again.',
 provider_not_configured:'The provider connection is not configured. Your local operator is available; owner setup is still needed.',observer_auth:'Provider access was rejected. This is an observation gap, not proof that the service is down.',
 observer_network:'The provider could not be reached. Existing observations remain available.',runtime_unavailable:'The AI runtime is unavailable. You can still inspect evidence and use monitoring.',
 investigation_in_progress:'An investigation is already running in this session. Finish or cancel it first.',investigation_queue_full:'The investigation queue is full. Monitoring still works; try again shortly.',
 stale_generation:'The service changed while it was being investigated. Run again against the current evidence.',server_restarted:'The operator restarted. The old investigation was stopped; start a new one when ready.',
 canceled:'Investigation canceled.',expired:'The investigation reached its time limit. Inspect the collected evidence or try a narrower question.',
 busy:'The model is busy with another entry. Monitoring remains available.',budget_exhausted:'The configured model budget is exhausted. Monitoring and evidence inspection remain available.',
 repair_not_enrolled_or_supported:'This service has no supported, verified repair enrolled. It remains available for monitoring and investigation.',
 live_provider_required_for_deployment:'Actual deployment requires the authorized live provider connection.',approval_rejected:'The approval is expired, used, or no longer matches the service. Prepare a fresh proposal.',
 watch_scope_or_state_conflict:'A watch is already active, or this selection exceeds the bounded watch scope.',not_found:'That item is not available in this session.',
 evidence_read_failed:'A required evidence read failed. The assistant has not claimed a cause.',invalid_model_output:'The model response could not be validated. No action was taken.',
}
export function messageFor(code:string){return messages[code]||'The request could not be completed. Refresh the evidence and try again.'}
async function request<T>(path:string,method:string,body?:unknown):Promise<T>{
 let response:Response
 try{response=await fetch(path,{method,credentials:'same-origin',headers:body===undefined?undefined:{'content-type':'application/json'},body:body===undefined?undefined:JSON.stringify(body)})}catch{throw new Error('Connection failed. Your current view is retained; try again.')}
 const data=await response.json().catch(()=>({}))
 if(!response.ok)throw new ApiError(response.status,typeof data.detail==='string'?data.detail:'invalid_request')
 return data as T
}
export const api={get:<T,>(path:string)=>request<T>(path,'GET'),post:<T,>(path:string,body:unknown={})=>request<T>(path,'POST',body)}
