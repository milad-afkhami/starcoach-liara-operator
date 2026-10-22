import test from 'node:test'
import assert from 'node:assert/strict'
import {httpSummary,remainingTime} from './presentation.ts'

test('HTTP failure is distinct from absent observation and healthy process',()=>{
 assert.deepEqual(httpSummary({http_status:502,check_pass:false,reason:'unexpected_status'}),{label:'HTTP 502',tone:'bad'})
 assert.deepEqual(httpSummary({http_status:null,check_pass:null,reason:'observer_network'}),{label:'Observation unavailable',tone:'unknown'})
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
