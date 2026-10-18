import {test,expect,type Page} from '@playwright/test';
import {mkdirSync} from 'node:fs';
async function enter(page:Page,name='Subhanjan Das'){await page.goto('./');await page.getByRole('button',{name,exact:false}).click();}
async function call(page:Page,persona:string,path:string,method='GET',body:unknown={},key?:string){return page.evaluate(async args=>{const module=await import(/* @vite-ignore */ '/maple-harbour-bank/src/simulation/commands.ts');try{return {ok:true,data:await module.request(...args)};}catch(e){return {ok:false,error:(e as Error).message};}},[persona,path,method,body,key] as const);}
async function pay(page:Page,key='payment-test-001',n=12500){return call(page,'subhanjan','/payments','POST',{source_id:'chequing',beneficiary_id:'energy',amount_minor:n,currency:'CAD'},key);}
test('public customer journey persists across reload and publishes actual lineage',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));await enter(page);
 await expect(page.getByRole('heading',{name:'Welcome back, Subhanjan.'})).toBeVisible();await page.getByLabel('Amount (CAD)',{exact:true}).fill('125.00');await page.getByRole('button',{name:'Post simulated payment'}).click();await expect(page.getByRole('status')).toContainText('Payment posted');
 await page.reload();await expect(page.locator('.payment-row')).toHaveCount(1);await page.locator('.payment-row').click();
 await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.getByRole('button',{name:'Taylor Reid',exact:false}).click();await page.locator('.payment-row').click();await page.getByRole('button',{name:'Acknowledge settlement'}).click();await page.getByLabel('Partial return amount (CAD)',{exact:true}).fill('30.00');await page.getByRole('button',{name:'Post return installment'}).click();await expect(page.locator('.trace-summary')).toContainText('PARTIALLY_RETURNED');
 await expect.poll(async()=>{await page.getByRole('button',{name:'Refresh trace'}).click();return page.locator('table').last().innerText();},{timeout:20000}).not.toContain('Not published');
 await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.getByRole('button',{name:'Jordan Martin',exact:false}).click();await expect(page.getByText('Reconciled',{exact:true})).toBeVisible();
 mkdirSync('../docs/assets',{recursive:true});await page.screenshot({path:'../docs/assets/public-analytics.png',fullPage:true});
 await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.getByRole('button',{name:'Subhanjan Das',exact:false}).click();await expect(page.getByText('$17,405.00',{exact:true})).toBeVisible();await page.screenshot({path:'../docs/assets/public-customer.png',fullPage:true});expect(errors).toEqual([]);
});
test('atomic duplicate storm and hot account cannot overspend',async({page})=>{
 await enter(page);const results=await Promise.all(Array.from({length:12},()=>pay(page,'same-request-001',100)));expect(results.every(r=>r.ok)).toBe(true);expect(new Set(results.map(r=>(r.data as {payment_id:string}).payment_id)).size).toBe(1);
 const attempts=await Promise.all(Array.from({length:20},(_,i)=>pay(page,'hot-account-'+i,50000)));expect(attempts.filter(r=>r.ok)).toHaveLength(9);
 const accounts=await call(page,'subhanjan','/accounts');expect((accounts.data as {id:string;booked_minor:number}[]).find(a=>a.id==='chequing')?.booked_minor).toBe(49900);
 expect((await call(page,'sam','/payments','POST',{source_id:'chequing',beneficiary_id:'energy',amount_minor:100},'foreign-request-01')).error).toBe('ACCOUNT_NOT_FOUND');
 expect((await pay(page,'same-request-001',101)).error).toBe('IDEMPOTENCY_CONFLICT');
});
test('maker checker reserves funds, denies self approval, isolates organizations and posts once',async({page})=>{
 await enter(page,'Avery Patel');await page.getByLabel('Supplier payment (CAD)').fill('1250.00');await page.getByRole('button',{name:'Submit for approval'}).click();await expect(page.getByText('PENDING · maker maker')).toBeVisible();
 const b=await call(page,'maker','/business');const approvals=(b.data as {approvals:{id:string}[]}).approvals,pid=approvals[0].id;
 expect((await call(page,'maker','/business/approvals/'+pid,'POST',{decision:'approve'},'self-approve-001')).error).toBe('MAKER_CANNOT_CHECK');
 expect((await call(page,'otherbiz','/business/approvals/'+pid,'POST',{decision:'approve'},'org-attack-001')).error).toBe('APPROVAL_NOT_FOUND');
 await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.getByRole('button',{name:'Morgan Chen',exact:false}).click();await page.getByRole('button',{name:'Approve payment',exact:true}).click();await expect(page.getByText('APPROVED · maker maker')).toBeVisible();
 const after=await call(page,'checker','/business');const a=(after.data as {accounts:{booked_minor:number;hold_minor:number}[]}).accounts[0];expect(a.booked_minor).toBe(2375000);expect(a.hold_minor).toBe(0);await page.screenshot({path:'../docs/assets/public-business.png',fullPage:true});
});
test('archive interruption replays safely and missing source preserves publication',async({page})=>{
 await enter(page);await call(page,'engineer','/lab/control','POST',{command:'pause'});const result=await pay(page);expect(result.ok).toBe(true);
 await call(page,'engineer','/lab/control','POST',{command:'after_archive'});await call(page,'engineer','/lab/process','POST');let e=await call(page,'engineer','/engineering');expect((e.data as {outbox:{pending:number}}).outbox.pending).toBe(3);expect((e.data as {bronze_count:number}).bronze_count).toBe(3);
 await page.reload();await call(page,'engineer','/lab/control','POST',{command:'resume'});await call(page,'engineer','/lab/process','POST');e=await call(page,'engineer','/engineering');expect((e.data as {outbox:{pending:number}}).outbox.pending).toBe(0);expect((e.data as {bronze_count:number}).bronze_count).toBe(3);
 const a=await call(page,'analyst','/analytics'),before=(a.data as {publication:{id:string}}).publication.id;
 await call(page,'engineer','/lab/control','POST',{command:'missing_source'});const rejected=await call(page,'engineer','/lab/process','POST');expect((rejected.data as {status:string}).status).toBe('REJECTED');expect(((await call(page,'analyst','/analytics')).data as {publication:{id:string}}).publication.id).toBe(before);
 await call(page,'engineer','/lab/control','POST',{command:'resume'});expect((await call(page,'subhanjan','/engineering')).error).toBe('ROLE_DENIED');
});
test('partial return and late reporting correction change analytics without extra cash',async({page})=>{
 await enter(page);const p=await pay(page);const pid=(p.data as {payment_id:string}).payment_id;
 await call(page,'ops','/operations/payments/'+pid+'/settle','POST',{},'settle-test-001');await call(page,'ops','/operations/payments/'+pid+'/returns','POST',{amount_minor:3000},'return-test-001');
 expect((await call(page,'ops','/operations/payments/'+pid+'/returns','POST',{amount_minor:10000},'excess-return-001')).error).toBe('RETURN_EXCEEDS_ORIGINAL');
 const detail=await call(page,'subhanjan','/payments/'+pid),rid=(detail.data as {returns:{id:string}[]}).returns[0].id;
 await call(page,'ops','/operations/payments/'+pid+'/returns/'+rid+'/reporting-date','POST',{reporting_date:'2026-01-01'},'late-report-001');await call(page,'engineer','/lab/process','POST');
 const data=(await call(page,'analyst','/analytics')).data as {publication:{daily:{business_date:string;return_minor:number}[]}};expect(data.publication.daily.find(d=>d.business_date==='2026-01-01')?.return_minor).toBe(3000);
 expect(((await call(page,'subhanjan','/payments/'+pid)).data as {journals:unknown[]}).journals).toHaveLength(6);
});
test('independent browsers, mobile Dusk and truthful topology',async({page,browser})=>{
 await enter(page);await pay(page);const fresh=await browser.newContext();const other=await fresh.newPage();await other.goto('http://localhost:5174/maple-harbour-bank/');await other.getByRole('button',{name:'Subhanjan Das',exact:false}).click();await expect(other.locator('.payment-row')).toHaveCount(0);await fresh.close();
 await page.setViewportSize({width:390,height:844});await page.getByRole('button',{name:'Switch to Dusk theme'}).click();await page.reload();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.getByRole('button',{name:'Architecture & flow',exact:true}).click();await expect(page.getByText('PUBLIC DEMO · GitHub Pages',{exact:false})).toBeVisible();await page.screenshot({path:'../docs/assets/public-mobile.png',fullPage:true});
});
