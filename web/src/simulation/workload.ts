import {change,read} from './store';
import {createPayment,fail,id,idempotent,now,people,type State,type Workload} from './model';
import {operateState} from './operations';
export function plannedAmount(seed:number,index:number){return 100+(((seed^Math.imul(index+1,0x9e3779b1))>>>0)%2401);}
export function startWorkload(s:State,body:Record<string,unknown>){
 const {seed,count,interval_ms}=body;
 if(typeof seed!=='number'||!Number.isSafeInteger(seed)||seed<0||seed>2147483647)fail('INVALID_SEED');
 if(typeof count!=='number'||!Number.isInteger(count)||count<1||count>40)fail('WORKLOAD_LIMIT_1_TO_40');
 if(typeof interval_ms!=='number'||!Number.isInteger(interval_ms)||interval_ms<1000||interval_ms>10000)fail('INTERVAL_LIMIT_1000_TO_10000');
 const runs=s.workloads??=[];if(runs.some(r=>r.status==='RUNNING'||r.status==='PAUSED'))fail('WORKLOAD_ALREADY_ACTIVE');if(runs.length>=10)fail('WORKLOAD_HISTORY_LIMIT_10');
 const run:Workload={id:id(),seed,count,interval_ms,cursor:0,status:'RUNNING',started_at:now(),updated_at:now(),next_at:now(),payment_ids:[],duplicate_requests:0};runs.push(run);return run;
}
export function controlWorkload(s:State,rid:string,action:string){
 const r=s.workloads?.find(r=>r.id===rid);if(!r)fail('WORKLOAD_NOT_FOUND');
 if(action==='pause'&&r.status==='RUNNING')r.status='PAUSED';
 else if(action==='resume'&&r.status==='PAUSED'){r.status='RUNNING';r.next_at=now();}
 else if(action==='stop'&&['RUNNING','PAUSED'].includes(r.status))r.status='STOPPED';else fail('INVALID_WORKLOAD_TRANSITION');
 r.updated_at=now();return r;
}
/** One bounded banking cycle per tick, atomic with its durable cursor. No catch-up burst after sleep/reopen. */
export async function pulseWorkload(){
 const snapshot=await read(),candidate=snapshot.workloads?.find(r=>r.status==='RUNNING');
 if(!candidate||Date.parse(candidate.next_at)>Date.now())return;
 const cursor=candidate.cursor;
 try{return await change(s=>{
  const r=s.workloads?.find(r=>r.id===candidate.id);if(!r||r.status!=='RUNNING'||Date.parse(r.next_at)>Date.now())return;
  const n=plannedAmount(r.seed,r.cursor),key='sim:'+r.id+':'+r.cursor;
  const body={source_id:'chequing',beneficiary_id:'energy',amount_minor:n,currency:'CAD'};
  const pay=()=>idempotent(s,people.subhanjan,'/payments',body,key,()=>createPayment(s,people.subhanjan,body,key));
  const payment=pay();if((r.cursor+1)%4===0){const duplicate=pay();if(duplicate.payment_id!==payment.payment_id)fail('DUPLICATE_EFFECT');r.duplicate_requests++;}
  const settlePath='/operations/payments/'+payment.payment_id+'/settle';
  idempotent(s,people.ops,settlePath,{},key+':settle',()=>operateState(s,payment.payment_id,'settle',{},key+':settle'));
  if(r.cursor%3===2){const ret={amount_minor:Math.floor(n/4)},returnPath='/operations/payments/'+payment.payment_id+'/returns';idempotent(s,people.ops,returnPath,ret,key+':return',()=>operateState(s,payment.payment_id,'returns',ret,key+':return'));}
  r.payment_ids.push(payment.payment_id);r.cursor++;r.updated_at=now();r.next_at=new Date(Date.now()+r.interval_ms).toISOString();if(r.cursor===r.count)r.status='COMPLETED';return r;
 });}catch(e){
  // A failed financial transaction rolls back. Only then record its operator-visible disposition.
  return change(s=>{const r=s.workloads?.find(r=>r.id===candidate.id);if(r?.status==='RUNNING'&&r.cursor===cursor){r.status='FAILED';r.last_error=(e as Error).message;r.updated_at=now();}return r;});
 }
}
