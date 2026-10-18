import {change,read} from './store';
import {checksum,id,now,fail,canonical,type State,type Envelope,type Run} from './model';
import type {Daily} from '../api';
function reject(s:State,code:string){const run:Run={id:id(),status:'REJECTED',cutoff:s.events.length,source_count:s.events.length,codes:[code],created_at:now()};s.runs.unshift(run);s.runs=s.runs.slice(0,100);return run;}
export async function processBatch(force=false){
 const before=await read();if(before.paused&&!force)return {status:'PAUSED'};if(!force&&before.fault==='none'&&before.publication?.cutoff===before.events.length)return {status:'UNCHANGED'};
 // Archive commit is deliberately separate from acknowledgement. Both are durable.
 const archived=await change(s=>{if(s.paused&&!force)return false;const pending=s.events.filter(e=>!e.acknowledged_at).slice(0,50);const run=id();for(const e of pending){e.attempts++;if(!s.bronze.some(b=>b.event.envelope.event_id===e.envelope.event_id))s.bronze.push({event:structuredClone(e),received_at:now(),ingestion_run_id:run});}return pending.length>0;});
 const failure=await change(s=>{if(archived&&s.fault==='after_archive'&&!s.fault_fired){s.fault_fired=true;s.paused=true;return true;}return false;});
 if(failure)return {status:'INTERRUPTED_AFTER_ARCHIVE'};
 await change(s=>{for(const e of s.events)if(!e.acknowledged_at&&s.bronze.some(b=>b.event.envelope.event_id===e.envelope.event_id))e.acknowledged_at=now();});
 return change(async s=>{
  if(s.events.some(e=>!e.acknowledged_at))return {status:'CATCHING_UP'};
  const controls=await checksum(s.events.map(e=>[e.seq,e.envelope.event_id,e.checksum]));
  if(!force&&s.publication?.source_checksum===controls&&s.fault==='none')return {status:'UNCHANGED'};
  const input=s.fault==='missing_source'?s.bronze.slice(1):s.bronze;
  if(input.length!==s.events.length||input.some(b=>!s.events.some(e=>e.seq===b.event.seq&&e.checksum===b.event.checksum&&e.envelope.event_id===b.event.envelope.event_id)))return reject(s,'MISSING_OR_CHANGED_SOURCE');
  const latest:Record<string,Envelope>={};const history=new Map<string,number>();
  for(const b of [...input].sort((a,b)=>a.event.seq-b.event.seq)){
   const e=b.event.envelope;if(e.schema_version!==1||e.tenant_id!==s.scenario||e.currency!=='CAD'||e.currency_exponent!==2||!Number.isSafeInteger(e.payload.amount_minor)||e.payload.amount_minor<=0||await checksum(e)!==b.event.checksum)return reject(s,'CONTRACT_OR_CHECKSUM_REJECTED');
   if(e.aggregate_version!==(history.get(e.aggregate_id)||0)+1)return reject(s,'AGGREGATE_VERSION_GAP');
   history.set(e.aggregate_id,e.aggregate_version);latest[e.aggregate_id]=e;
  }
  if(Object.keys(latest).length!==s.payments.length)return reject(s,'SOURCE_COMPLETENESS_MISMATCH');
  for(const p of s.payments)if(canonical(latest[p.id]?.payload)!==canonical({...p,returns:s.returns[p.id]||[]}))return reject(s,'OPERATIONAL_PROJECTION_MISMATCH');
  const daily:Record<string,Daily>={};const get=(date:string)=>daily[date]??={business_date:date,currency:'CAD',channel:'WEB',instruction_count:0,instruction_minor:0,return_count:0,return_minor:0,settled_count:0};
  for(const e of Object.values(latest)){const p=e.payload,d=get(p.business_date);d.instruction_count++;d.instruction_minor+=p.amount_minor;if(['SETTLED','PARTIALLY_RETURNED','RETURNED'].includes(p.status))d.settled_count++;for(const r of p.returns){const rd=get(r.reporting_date);rd.return_count++;rd.return_minor+=r.amount_minor;}}
  const totals={instruction_count:0,instruction_minor:0,return_count:0,return_minor:0,settled_count:0,reconciled:true,metric_semantics:'Accepted instruction activity; not settled cash flow'};
  for(const d of Object.values(daily))for(const key of ['instruction_count','instruction_minor','return_count','return_minor','settled_count'] as const)totals[key]+=d[key];
  if(totals.instruction_minor!==s.payments.reduce((n,p)=>n+p.amount_minor,0)||totals.return_minor!==s.payments.reduce((n,p)=>n+p.returned_minor,0))fail('FINANCIAL_CONTROL_MISMATCH');
  const run:Run={id:id(),status:'SUCCEEDED',cutoff:s.events.length,source_count:s.events.length,codes:[],created_at:now()};s.runs.unshift(run);s.runs=s.runs.slice(0,100);s.silver=latest;
  s.publication={id:id(),run_id:run.id,cutoff:s.events.length,source_count:s.events.length,source_checksum:controls,refreshed_at:now(),source_cutoff_at:s.events.at(-1)?.envelope.event_time||null,daily:Object.values(daily).sort((a,b)=>a.business_date.localeCompare(b.business_date)),totals};return run;
 });
}
