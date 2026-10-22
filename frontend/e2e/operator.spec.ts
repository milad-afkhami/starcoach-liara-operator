import {test,expect} from '@playwright/test'
import {readFileSync} from 'node:fs'
const access=JSON.parse(readFileSync(process.env.LIARA_TEST_ACCESS_FILE!,'utf8'))
async function login(page:any){await page.goto('/');await page.getByLabel('Owner password').fill(access.password);await page.getByRole('button',{name:'Sign in',exact:true}).click();await expect(page.getByRole('heading',{name:'Your services'})).toBeVisible()}

test('real service evidence separates liveness from failure and watch can stop',async({page})=>{
 await login(page)
 await expect(page.getByTestId('fixture-banner')).toContainText('simulated')
 await page.getByRole('button',{name:'Open storefront'}).click()
 await expect(page.getByTestId('http-store-preview')).toContainText('HTTP 502')
 await expect(page.getByTestId('http-store-health')).toContainText('HTTP 200')
 await page.getByRole('button',{name:'Start 15-minute watch'}).click()
 await expect(page.getByTestId('watch-panel')).toContainText('Watching')
 await page.getByRole('button',{name:'Stop watch',exact:true}).click()
 await expect(page.getByTestId('watch-panel')).toContainText('stopped')
 await page.reload()
 await expect(page.getByRole('heading',{name:'Your services'})).toBeVisible()
})

test('mobile owner login and evidence dialog are keyboard usable',async({page})=>{
 await page.setViewportSize({width:390,height:844});await login(page)
 await page.getByRole('button',{name:'Open storefront'}).click()
 await page.getByRole('button',{name:'Inspect http_probe evidence'}).first().click()
 const dialog=page.getByRole('dialog',{name:'Evidence detail'});await expect(dialog).toBeVisible()
 await page.keyboard.press('Escape');await expect(dialog).toBeHidden()
 expect(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)).toBe(false)
 await page.getByRole('button',{name:'Sign out'}).click()
 await expect(page.getByLabel('Owner password')).toBeVisible()
})

test('fresh signed-out view does not claim an expired session',async({page})=>{
 await page.goto('/');await expect(page.getByLabel('Owner password')).toBeVisible()
 await expect(page.getByRole('alert')).toHaveCount(0)
})

test('reselecting a service during its real detail read does not strand refresh',async({page})=>{
 await login(page)
 await page.getByRole('button',{name:'Open delivery'}).click()
 await expect(page.getByRole('heading',{name:'delivery',exact:true})).toBeVisible()
 let release!:()=>void;const held=new Promise<void>(r=>release=r)
 let arrived!:()=>void;const started=new Promise<void>(r=>arrived=r)
 await page.route('**/api/services/local-store',async route=>{const response=await route.fetch();arrived();await held;await route.fulfill({response})})
 await page.getByRole('button',{name:'Open storefront'}).click();await started
 await page.getByRole('button',{name:'Open storefront'}).click();release()
 await expect(page.getByRole('button',{name:'Refresh observations'})).toBeEnabled()
 await expect(page.getByTestId('http-store-preview')).toContainText('HTTP 502')
})

test('failed observation read does not erase configured-check knowledge',async({page})=>{
 await login(page)
 await page.getByRole('button',{name:'Open delivery'}).click()
 await expect(page.getByRole('heading',{name:'delivery',exact:true})).toBeVisible()
 await page.route('**/api/services/local-store',route=>route.abort('failed'))
 await page.getByRole('button',{name:'Open storefront'}).click()
 await expect(page.getByRole('button',{name:'Refresh observations'})).toBeEnabled()
 await expect(page.getByText('Configured HTTP checks have no observations available. Refresh to try again.')).toBeVisible()
 await expect(page.getByText('No HTTP check is configured for this service. That does not mean it is down.')).toHaveCount(0)
 await page.unroute('**/api/services/local-store')
 await page.getByRole('button',{name:'Refresh observations'}).click()
 await expect(page.getByTestId('http-store-preview')).toContainText('HTTP 502')
})

test('real expired session with open evidence cannot restore prior-owner dialog',async({page})=>{
 await login(page)
 await page.getByRole('button',{name:'Open storefront'}).click()
 await expect(page.getByTestId('http-store-preview')).toBeVisible()
 await page.getByRole('button',{name:'Start 15-minute watch'}).click()
 await expect(page.getByTestId('watch-panel')).toContainText('Watching')
 await page.getByRole('button',{name:'Inspect http_probe evidence'}).first().click()
 await expect(page.getByRole('dialog',{name:'Evidence detail'})).toBeVisible()
 const state=await (await page.request.get('/api/state')).json()
 const watch=state.watches.find((w:any)=>w.state==='active')
 // Controlled own-session expiry uses the actual logout route; do not leave an orphan watch.
 await page.request.post('/api/watches/'+watch.id+'/stop',{headers:{Origin:'http://127.0.0.1:8661'}})
 await page.request.post('/api/logout',{headers:{Origin:'http://127.0.0.1:8661'}})
 await expect(page.getByLabel('Owner password')).toBeVisible({timeout:10000})
 await page.getByLabel('Owner password').fill(access.password)
 await page.getByRole('button',{name:'Sign in',exact:true}).click()
 await expect(page.getByRole('heading',{name:'Your services'})).toBeVisible()
 await expect(page.getByRole('dialog',{name:'Evidence detail'})).toHaveCount(0)
})
