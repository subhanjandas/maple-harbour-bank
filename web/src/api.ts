export const PUBLIC_DEMO=import.meta.env.VITE_PUBLIC_DEMO==='true';
export type Actor={id:string;name:string;role:'customer'|'business'|'operations'|'analyst'|'engineer';tenant_id:string;scope:string};
export type Account={id:string;label:string;currency:string;currency_exponent:number;booked_minor:number;hold_minor:number;available_minor:number;status:string};
export type Beneficiary={id:string;name:string};
export type Payment={id:string;kind:string;source_id:string;amount_minor:number;currency:string;status:string;returned_minor:number;version:number;business_date:string;created_at:string;correlation_id:string};
export type Detail={payment:Payment;events:{id:string;version:number;status:string;reason:string;occurred_at:string}[];returns:{id:string;amount_minor:number;booked_date:string;reporting_date:string;revision:number}[];journals:{id:string;kind:string;booked_date:string;line_no:number;ledger_id:string;direction:string;amount_minor:number}[];lineage:{event_id:string;seq:number;aggregate_version:number;acknowledged_at:string|null;received_at:string|null;ingestion_run_id:string|null;silver_validated:boolean|null;publication_id:string|null;publication_run_id:string|null}[]};
export type Daily={business_date:string;currency:string;channel:string;instruction_count:number;instruction_minor:number;return_count:number;return_minor:number;settled_count:number};
export type Publication={id:string;run_id:string;cutoff:number;source_count:number;source_checksum:string;refreshed_at:string;source_cutoff_at:string|null;daily:Daily[];totals:{instruction_count:number;instruction_minor:number;return_count:number;return_minor:number;settled_count:number;reconciled:boolean;metric_semantics:string}};
export type Analytics={publication:Publication|null;freshness:string;age_seconds?:number;unpublished_events?:number};
export type Engineering={topology:string;layers:string;outbox:{total:number;pending:number;max_attempts:number};runs:{id:string;status:string;cutoff:number;source_count:number;codes:string[];created_at:string}[];quarantine:{code:string;n:number}[]};
export function csrf(){return document.cookie.split('; ').find(v=>v.startsWith('mhb_csrf='))?.split('=')[1]||'';}
export async function api<T>(path:string,method='GET',body?:unknown,key?:string):Promise<T>{
 if(PUBLIC_DEMO){const {browserApi}=await import('./simulation/client');return browserApi<T>(path,method,body,key);}
 const response=await fetch('/api'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json',...(method==='GET'?{}:{'X-CSRF-Token':csrf()}),...(key?{'Idempotency-Key':key}:{})},body:body===undefined?undefined:JSON.stringify(body)});
 if(!response.ok){const data=await response.json().catch(()=>({detail:'Service unavailable'}));throw new Error(typeof data.detail==='string'?data.detail:`Request validation failed (${response.status})`);}
 return response.json();
}
export const money=(n:number)=>new Intl.NumberFormat('en-CA',{style:'currency',currency:'CAD'}).format(n/100);
export const dateTime=(value:string|null)=>value?new Intl.DateTimeFormat('en-CA',{dateStyle:'medium',timeStyle:'short',timeZone:'America/Toronto'}).format(new Date(value))+' ET':'Not available';
export function parseMinor(value:string){if(!/^\d{1,7}(\.\d{1,2})?$/.test(value))throw new Error('Enter a CAD amount with up to two decimal places.');const [whole,fraction='']=value.split('.');const n=Number(whole)*100+Number(fraction.padEnd(2,'0'));if(n<1||n>100000000)throw new Error('Enter between $0.01 and $1,000,000.00.');return n;}
