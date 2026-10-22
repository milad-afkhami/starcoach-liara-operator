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
