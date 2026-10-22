export function httpSummary(value:{http_status:number|null;check_pass:boolean|null;reason:string}):{label:string;tone:string}{
 if(value.http_status===null||value.check_pass===null)return {label:'Observation unavailable',tone:'unknown'}
 return {label:`HTTP ${value.http_status}`,tone:value.check_pass?'good':'bad'}
}
export function remainingTime(end:number,now:number):string{
 const seconds=Math.max(0,Math.ceil(end-now));return `${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`
}
export function when(value:number|string|null|undefined):string{
 if(value===null||value===undefined)return 'Not observed'
 const date=new Date(typeof value==='number'?value*1000:value)
 return Number.isNaN(date.valueOf())?'Time unavailable':date.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'})
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
