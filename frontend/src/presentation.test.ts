import test from 'node:test'
import assert from 'node:assert/strict'
import {httpSummary,remainingTime} from './presentation.ts'

test('HTTP failure is distinct from absent observation and healthy process',()=>{
 assert.deepEqual(httpSummary({http_status:502,check_pass:false,reason:'unexpected_status'}),{label:'HTTP 502',tone:'bad'})
 assert.deepEqual(httpSummary({http_status:null,check_pass:null,reason:'observer_network'}),{label:'مشاهده در دسترس نیست',tone:'unknown'})
 assert.deepEqual(httpSummary({http_status:200,check_pass:true,reason:'pass'}),{label:'HTTP 200',tone:'good'})
})
test('watch countdown never becomes negative or extends the deadline',()=>{
 assert.equal(remainingTime(1000,100),'15:00');assert.equal(remainingTime(1000,1001),'00:00');assert.equal(remainingTime(1000,999),'00:01')
})

test('investigation of an open selected alert reuses its incident',async()=>{
 const {investigationEndpoint}=await import('./presentation.ts')
 assert.equal(investigationEndpoint('service',{id:'incident',target:{app_id:'service'},state:'open'}),'/api/incidents/incident/investigate')
 assert.equal(investigationEndpoint('service',{id:'incident',target:{app_id:'service'},state:'recovered'}),'/api/services/service/investigate')
 assert.equal(investigationEndpoint('other',{id:'incident',target:{app_id:'service'},state:'open'}),'/api/services/other/investigate')
})

test('ambiguous submitted operation remains observable only inside reconciliation budget',async()=>{
 const {operationNeedsPolling,mayReplaceOperation}=await import('./presentation.ts')
 assert.equal(operationNeedsPolling({state:'unknown',reconcile_until:200},100),true)
 assert.equal(operationNeedsPolling({state:'unknown',reconcile_until:200},201),false)
 assert.equal(operationNeedsPolling({state:'completed'},100),false)
 assert.equal(operationNeedsPolling({state:'verifying'},100),true)
 assert.equal(mayReplaceOperation({state:'proposed',expires_at:99},false,100),true)
 assert.equal(mayReplaceOperation({state:'approved',expires_at:199},false,100),false)
})

test('Persian UI labels cover service states, evidence and investigation without rewriting identifiers', async()=>{
 const {uiLabel}=await import('./presentation.ts')
 assert.equal(uiLabel('http_probe'),'بررسی نشانی سرویس')
 assert.equal(uiLabel('running'),'در حال اجرا')
 assert.equal(uiLabel('dependency_schema'),'ناسازگاری پاسخ سرویس وابسته')
 assert.equal(uiLabel('USDTTMN'),'USDTTMN')
})

test('missing observations and provider errors explain uncertainty in Persian',async()=>{
 const {when}=await import('./presentation.ts')
 const {messageFor}=await import('./api.ts')
 assert.equal(when(null),'هنوز مشاهده نشده')
 assert.equal(httpSummary({http_status:null,check_pass:null,reason:'observer_network'}).label,'مشاهده در دسترس نیست')
 assert.match(messageFor('observer_auth'),/دسترسی/)
 assert.match(messageFor('observer_auth'),/خرابی/)
 assert.match(messageFor('new_unknown_code'),/دوباره/)
})

test('legacy server policy caveat is localized without translating arbitrary model evidence',async()=>{
 const {uiLabel}=await import('./presentation.ts')
 assert.equal(uiLabel('No enrolled verified repair artifact for this service.'),'برای این سرویس، سورس سالم و تأییدشده‌ای برای رفع مشکل ثبت نشده است.')
 assert.equal(uiLabel('shipping_toman'),'shipping_toman')
})

test('need-evidence state is Persian for both API and legacy normalized forms',async()=>{
 const {uiLabel}=await import('./presentation.ts')
 assert.equal(uiLabel('need_evidence'),'نیاز به شواهد بیشتر')
 assert.equal(uiLabel('need evidence'),'نیاز به شواهد بیشتر')
 assert.equal(uiLabel('shipping_toman'),'shipping_toman')
})

test('observations show absolute Persian date and Tehran time across UTC midnight',async()=>{
 const {when}=await import('./presentation.ts')
 const value=when('2026-10-22T21:30:00Z')
 assert.match(value,/۱۴۰۵\/۰۸\/۰۱/)
 assert.match(value,/۰۱:۰۰:۰۰/)
 assert.match(value,/تهران/)
 assert.equal(when(Date.parse('2026-10-22T21:30:00Z')/1000),value)
 assert.equal(when('not a timestamp'),'زمان در دسترس نیست')
})

test('evidence references identify the service and exact registered check',async()=>{
 const {evidenceLocation,progressLabel}=await import('./presentation.ts')
 assert.equal(evidenceLocation({target:{app_name:'delivery'},redacted_payload:{check_id:'dep-quote'}}),'delivery · dep-quote')
 assert.equal(evidenceLocation({target:{app_name:'storefront'},redacted_payload:{}}),'storefront')
 assert.match(progressLabel({stage:'collecting',read_name:'dependency:dep-quote',reads_completed:5}),/dep-quote/)
 assert.match(progressLabel({stage:'analyzing',reads_completed:6,model_call:2}),/۲|2/)
 assert.match(progressLabel({stage:'validating',reads_completed:6,model_call:2}),/اعتبار/)
})

test('resource values keep verified units and unavailable values never become zero',async()=>{
 const {resourceValue}=await import('./presentation.ts')
 assert.match(resourceValue({metric:'memory',value:67108864,unit:'bytes'}),/۶۴ MiB/)
 assert.match(resourceValue({metric:'cpu',value:12.5,unit:'percent'}),/۱۲٫۵/)
 assert.equal(resourceValue({metric:'cpu',value:NaN,unit:'percent'}),'در دسترس نیست')
 assert.equal(resourceValue({metric:'cpu',value:0.5,unit:'unknown'}),'واحد تأیید نشده')
})

test('read-only recovery recheck is once-only within original deadline and exact generation',async()=>{
 const {mayRecheckRecovery,operationNeedsPolling}=await import('./presentation.ts')
 const op={state:'failed',release_id:'r2',reconcile_until:700,recovery_rechecks_used:0,spec:{kind:'redeploy_known_good',incident_generation:2},verification:{state:'inconclusive'}}
 assert.equal(mayRecheckRecovery(op,100,2),true)
 assert.equal(mayRecheckRecovery(op,701,2),false)
 assert.equal(mayRecheckRecovery({...op,recovery_rechecks_used:1},100,2),false)
 assert.equal(mayRecheckRecovery(op,100,3),false)
 assert.equal(mayRecheckRecovery({...op,verification:{state:'failed'}},100,2),false)
 assert.equal(operationNeedsPolling({state:'awaiting_serving',reconcile_until:700},100),true)
})

test('recovered incidents present the preserved diagnosis as pre-action history',async()=>{
 const {diagnosisPresentation,releasePresentation}=await import('./presentation.ts')
 assert.deepEqual(diagnosisPresentation('recovered',true),{historical:true,title:'تحلیل پیش از اقدام',outcomePrefix:'نتیجه در زمان تحلیل: ',unknownsTitle:'موارد نامعلوم در زمان تحلیل'})
 assert.equal(diagnosisPresentation('open').historical,false)
 assert.equal(diagnosisPresentation('open',true).historical,true)
 assert.equal(diagnosisPresentation('recovered').title,'تحلیل ثبت‌شدهٔ پیشین')
 assert.equal(releasePresentation('pending','inconclusive').afterLabel,'release ارسال‌شده')
 assert.equal(releasePresentation('completed','recovered').afterLabel,'release تأییدشده پس از deploy')
 assert.equal(releasePresentation('completed','recovered').beforeLabel,'release پیش از deploy')
})

test('historical resource fallback keeps source and clock uncertainty distinct from summary',async()=>{
 const {resourceSamples}=await import('./presentation.ts')
 const historical={kind:'metrics_history',quality:'fresh',coverage:{unit_verified:true},redacted_payload:{historical_only:true,measurements:[{metric:'cpu',applet:'old',value:12.5,unit:'percent',observed_at:99}]}}
 assert.equal(resourceSamples(historical).length,1)
 assert.deepEqual(resourceSamples({...historical,quality:'unavailable'}),[])
 assert.deepEqual(resourceSamples({...historical,coverage:{unit_verified:false}}),[])
 assert.deepEqual(resourceSamples({...historical,redacted_payload:{...historical.redacted_payload,historical_only:false}}),[])
 assert.deepEqual(resourceSamples({...historical,quality:'invalid'}),[])
})

test('resource history charts use native timestamps and verified units while excluding invalid/future points and breaking gaps',async()=>{
 const {resourceSeries,chartSegments}=await import('./presentation.ts')
 const history:any={kind:'metrics_history',quality:'fresh',available_at:1000,coverage:{unit_verified:true},redacted_payload:{historical_only:true,cutoff:1000,window_start:700,provider_data:{cpu:{result:[{applet:'a',values:[[710,'0.1'],[730,'0.2'],[740,'NaN'],[750,'0.3'],[900,'0.4'],[1001,'0.9'],[600,'0.2'],[920,-1]]}]},memory:{result:[{applet:'a',values:[[730,'1048576'],[750,'2097152']]}]}}}}
 const series=resourceSeries(undefined,history)
 assert.equal(series.length,2)
 assert.deepEqual(series[0].points.filter((p:any)=>p.value!==null).map((p:any)=>[p.at,p.value]),[[710,10],[730,20],[750,30],[900,40]])
 assert.equal(series[1].unit,'MiB');assert.equal(series[1].points[0].value,1)
 assert.deepEqual(chartSegments(series[0].points).map((s:any)=>s.length),[2,1,1])
 assert.deepEqual(resourceSeries(undefined,{...history,coverage:{unit_verified:false}}),[])
 assert.deepEqual(resourceSeries(undefined,{...history,quality:'invalid'}),[])
})

test('resource snapshots reject corrupt values, preserve lone sample state and never invent CPU percent',async()=>{
 const {resourceSeries}=await import('./presentation.ts')
 const summary:any={kind:'metrics',quality:'fresh',available_at:1000,coverage:{unit_verified:true},redacted_payload:{measurements:[{metric:'cpu',applet:'a',value:20,unit:'percent',observed_at:990},{metric:'memory',applet:'a',value:1048576,unit:'bytes',observed_at:990},{metric:'cpu',applet:'b',value:2,unit:'cores',observed_at:990},{metric:'cpu',applet:'c',value:NaN,unit:'percent',observed_at:990}]}}
 const series=resourceSeries(summary)
 assert.equal(series.length,2);assert.equal(series[0].points.length,1);assert.equal(series[0].historical,false)
 assert.deepEqual(resourceSeries({...summary,quality:'invalid'}),[])
})

test('Codex handoff is frozen and scoped to cited evidence with explicit uncertainty and no raw secrets or invented repo paths',async()=>{
 const {codexHandoff,evidenceFacts}=await import('./presentation.ts')
 const incident:any={id:'i',state:'open',target:{app_id:'a',app_name:'storefront'},question:'چرا خطا می‌دهد؟',diagnosis:{summary:'پاسخ وابستگی ناسازگار است.',cause_family:'dependency_schema',cutoff:1000,unknowns:['فایل مسئول مشخص نیست.'],evidence_ids:['cited','late','foreign'],contradiction_ids:['against']}}
 const e=(id:string,extra:any={})=>({id,kind:'http_probe',quality:'fresh',target:incident.target,observed_at:990,available_at:995,redacted_payload:{check_id:'preview',http_status:502,check_pass:false,body:{secret:'DO_NOT_EXPORT'},token:'DO_NOT_EXPORT'},...extra})
 const source=[e('cited'),e('late',{available_at:1001}),e('foreign',{target:{app_id:'other',app_name:'other'}}),e('against',{redacted_payload:{check_id:'health',http_status:200,check_pass:true}})]
 const prompt=codexHandoff(incident,source)
 for(const expected of ['storefront','cited','against','فایل مسئول مشخص نیست.','regression test','repository','approval'])assert.ok(prompt.includes(expected),expected)
 for(const forbidden of ['DO_NOT_EXPORT','src/','late —','foreign —'])assert.ok(!prompt.includes(forbidden),forbidden)
 assert.ok(codexHandoff({...incident,state:'recovered'},source).includes('Historical'))
 assert.ok(evidenceFacts(source[0]).some((s:string)=>s.includes('502')))
})

test('chart evidence with malformed series and duplicate times cannot crash or imply conflicting observations',async()=>{
 const {resourceSeries}=await import('./presentation.ts')
 const history:any={kind:'metrics_history',quality:'fresh',available_at:1000,coverage:{unit_verified:true},redacted_payload:{historical_only:true,cutoff:1000,window_start:700,provider_data:{cpu:{result:{malformed:true}},memory:{result:[]}}}}
 assert.deepEqual(resourceSeries(undefined,history),[])
 history.redacted_payload.provider_data.cpu.result=[{applet:'a',values:[[900,.1],[900,.2],[920,.3]]}]
 assert.deepEqual(resourceSeries(undefined,history)[0].points,[{at:900,value:null},{at:920,value:30}])
})
