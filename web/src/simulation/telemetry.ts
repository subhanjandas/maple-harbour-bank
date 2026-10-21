import type {State} from './model';
export function percentile(values:number[],p:number){if(!values.length)return null;const sorted=[...values].sort((a,b)=>a-b);return sorted[Math.max(0,Math.ceil(sorted.length*p)-1)];}
/** Instrumented metadata plus financial values from the last approved publication only. */
export function telemetry(s:State,selected:string|null){
 const instant=Date.now(),windowStart=instant-60000,pending=s.events.filter(e=>!e.acknowledged_at),published=s.publication;
 const delays=s.bronze.map(b=>Date.parse(b.received_at)-Date.parse(b.event.envelope.event_time)),validDelays=delays.filter(n=>Number.isFinite(n)&&n>=0);
 const source=s.events.map(e=>({seq:e.seq,event_id:e.envelope.event_id,payment_id:e.envelope.aggregate_id,version:e.envelope.aggregate_version,status:e.envelope.payload.status,at:e.envelope.event_time}));
 const archive=s.bronze.map(b=>({event_id:b.event.envelope.event_id,at:b.received_at}));
 const rates={accepted_commands_per_second:s.audit.filter(a=>Date.parse(a.at)>=windowStart&&(a.action==='/payments'||a.action.startsWith('/operations/payments/')||a.action==='/business/proposals'||a.action.startsWith('/business/approvals/'))).length/60,instructions_per_second:s.payments.filter(p=>Date.parse(p.created_at)>=windowStart).length/60,ledger_lines_per_second:s.journals.filter(j=>j.kind!=='OPENING'&&j.created_at&&Date.parse(j.created_at)>=windowStart).length/60,events_per_second:source.filter(e=>Date.parse(e.at)>=windowStart).length/60,archived_records_per_second:archive.filter(e=>Date.parse(e.at)>=windowStart).length/60};
 const latest=s.events.filter(e=>!selected||e.envelope.aggregate_id===selected).slice(-100);
 const lineage=latest.map(e=>{const b=s.bronze.find(b=>b.event.envelope.event_id===e.envelope.event_id),silver=s.silver[e.envelope.aggregate_id];return {event_id:e.envelope.event_id,payment_id:e.envelope.aggregate_id,version:e.envelope.aggregate_version,status:e.envelope.payload.status,source_seq:e.seq,occurred_at:e.envelope.event_time,received_at:b?.received_at||null,ingestion_run_id:b?.ingestion_run_id||null,validated:!!silver&&silver.aggregate_version>=e.envelope.aggregate_version,publication_id:published&&published.cutoff>=e.seq?published.id:null,publication_run_id:published&&published.cutoff>=e.seq?published.run_id:null};});
 const oldest=pending.length?Math.max(0,(instant-Math.min(...pending.map(e=>Date.parse(e.envelope.event_time))))/1000):0;
 return {observed_at:new Date(instant).toISOString(),scenario:s.scenario,revision:s.revision,profile:'public-browser-simulation',paused:s.paused,fault:s.fault,
  counts:{instructions:s.payments.length,ledger_lines:s.journals.filter(j=>j.kind!=='OPENING').length,events:s.events.length,pending:pending.length,bronze:s.bronze.length,silver:Object.keys(s.silver).length,rejected_runs:s.runs.filter(r=>r.status==='REJECTED').length,successful_runs:s.runs.filter(r=>r.status==='SUCCEEDED').length},rates,
  latency:{archive_p50_ms:percentile(validDelays,.5),archive_p95_ms:percentile(validDelays,.95),archive_p99_ms:percentile(validDelays,.99),samples:validDelays.length,clock_skew_samples:delays.length-validDelays.length,oldest_pending_seconds:oldest,untimed_legacy_ledger_lines:s.journals.filter(j=>j.kind!=='OPENING'&&!j.created_at).length},
  publication:published,publication_age_seconds:published?Math.max(0,(instant-Date.parse(published.refreshed_at))/1000):null,unpublished_events:s.events.length-(published?.cutoff||0),
  source:source.slice(-5000),archive:archive.slice(-5000),payments:Object.values(s.silver).map(e=>({id:e.aggregate_id,status:e.payload.status,amount_minor:e.payload.amount_minor,returned_minor:e.payload.returned_minor,business_date:e.payload.business_date})).slice(-100).reverse(),
  lineage,workloads:s.workloads||[],runs:s.runs.slice(0,30)};
}
export type Telemetry=ReturnType<typeof telemetry>;
