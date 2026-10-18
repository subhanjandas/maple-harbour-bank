import type {Account,Actor,Detail,Payment,Publication} from '../api';
export type Principal=Actor & {org?:string;permission?:'maker'|'checker'};
export const people:Record<string,Principal>={
 subhanjan:{id:'subhanjan',name:'Subhanjan Das',role:'customer',tenant_id:'sandbox',scope:'TORONTO'},
 sam:{id:'sam',name:'Sam Chen',role:'customer',tenant_id:'sandbox',scope:'TORONTO'},
 maker:{id:'maker',name:'Avery Patel',role:'business',tenant_id:'sandbox',scope:'TORONTO',org:'studio',permission:'maker'},
 checker:{id:'checker',name:'Morgan Chen',role:'business',tenant_id:'sandbox',scope:'TORONTO',org:'studio',permission:'checker'},
 otherbiz:{id:'otherbiz',name:'Robin Singh',role:'business',tenant_id:'sandbox',scope:'TORONTO',org:'other',permission:'checker'},
 ops:{id:'ops',name:'Taylor Reid',role:'operations',tenant_id:'sandbox',scope:'TORONTO'},
 analyst:{id:'analyst',name:'Jordan Martin',role:'analyst',tenant_id:'sandbox',scope:'TORONTO'},
 engineer:{id:'engineer',name:'Casey Roy',role:'engineer',tenant_id:'sandbox',scope:'TORONTO'}
};
export type BankAccount=Account & {owner:string;org?:string;opening:number};
export type BankPayment=Payment & {owner_id:string;destination_id?:string;beneficiary_id?:string;org?:string};
export type Journal=Detail['journals'][number] & {payment_id:string|null};
export type Envelope={schema_version:number;source_system:string;event_id:string;aggregate_id:string;aggregate_version:number;tenant_id:string;event_time:string;correlation_id:string;causation_id:string;currency:string;currency_exponent:number;payload:BankPayment & {returns:Detail['returns']}};
export type Event={seq:number;envelope:Envelope;checksum:string;acknowledged_at:string|null;attempts:number};
export type Archive={event:Event;received_at:string;ingestion_run_id:string};
export type Approval={id:string;org:string;maker:string;amount_minor:number;status:'PENDING'|'APPROVED'|'REJECTED';created_at:string;checker?:string;payment_id?:string};
export type Run={id:string;status:string;cutoff:number;source_count:number;codes:string[];created_at:string};
export type State={schema:1;revision:number;scenario:string;accounts:BankAccount[];payments:BankPayment[];journals:Journal[];returns:Record<string,Detail['returns']>;events:Event[];bronze:Archive[];silver:Record<string,Envelope>;runs:Run[];publication:Publication|null;commands:Record<string,{signature:string;response:unknown}>;approvals:Approval[];paused:boolean;fault:'none'|'after_archive'|'missing_source';fault_fired:boolean;audit:{id:string;actor:string;action:string;at:string}[]};
export const now=()=>new Date().toISOString();
export const id=()=>crypto.randomUUID();
export const day=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'America/Toronto',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
export function seed():State{
 const accounts:BankAccount[]=[['chequing','Everyday Chequing','subhanjan',500000],['savings','Harbour Savings','subhanjan',1250000],['sam','Everyday Chequing','sam',300000],['business','Studio Operating','maker',2500000],['other-business','Other Organization','otherbiz',1000000]].map(([aid,label,owner,amount])=>({id:String(aid),label:String(label),owner:String(owner),opening:Number(amount),booked_minor:Number(amount),available_minor:Number(amount),hold_minor:0,currency:'CAD',currency_exponent:2,status:'OPEN',...(aid==='business'?{org:'studio'}:aid==='other-business'?{org:'other'}:{})}));
 const s:State={schema:1,revision:0,scenario:id(),accounts,payments:[],journals:[],returns:{},events:[],bronze:[],silver:{},runs:[],publication:null,commands:{},approvals:[],paused:false,fault:'none',fault_fired:false,audit:[]};
 for(const a of accounts)post(s,null,'OPENING',a.opening,'cash',a.id);
 return s;
}
export function fail(message:string):never{throw Error(message);}
export function amount(value:unknown):number{if(typeof value!=='number'||!Number.isSafeInteger(value)||value<1||value>100000000)fail('INVALID_EXACT_CAD_AMOUNT');return value;}
export function post(s:State,payment:string|null,kind:string,n:number,debit:string,credit:string){amount(n);const jid=id();s.journals.push(...([['DEBIT',debit],['CREDIT',credit]] as const).map(([direction,ledger_id],i)=>({id:jid,kind,booked_date:day(),line_no:i+1,ledger_id,direction,amount_minor:n,payment_id:payment})));}
export function assertMoney(s:State){
 const totals=new Map<string,number>();for(const j of s.journals){amount(j.amount_minor);totals.set(j.id,(totals.get(j.id)||0)+(j.direction==='DEBIT'?j.amount_minor:-j.amount_minor));}
 if([...totals.values()].some(n=>n!==0))fail('UNBALANCED_JOURNAL');
 for(const a of s.accounts){const n=s.journals.filter(j=>j.ledger_id===a.id).reduce((sum,j)=>sum+(j.direction==='CREDIT'?j.amount_minor:-j.amount_minor),0);if(n!==a.booked_minor||a.booked_minor<0||a.hold_minor<0||a.hold_minor>a.booked_minor)fail('ACCOUNT_LEDGER_MISMATCH');a.available_minor=a.booked_minor-a.hold_minor;}
 for(const p of s.payments)if((s.returns[p.id]||[]).reduce((n,r)=>n+r.amount_minor,0)!==p.returned_minor||p.returned_minor>p.amount_minor)fail('RETURN_CONTROL_MISMATCH');
}
export function canonical(value:unknown):string{if(Array.isArray(value))return '['+value.map(canonical).join(',')+']';if(value&&typeof value==='object')return '{'+Object.entries(value).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>JSON.stringify(k)+':'+canonical(v)).join(',')+'}';return JSON.stringify(value)??'null';}
export async function checksum(value:unknown){const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(canonical(value)));return [...new Uint8Array(bytes)].map(b=>b.toString(16).padStart(2,'0')).join('');}
export function emit(s:State,p:BankPayment,status:string,causation:string){if(s.events.length>=5000)fail('SCENARIO_EVENT_LIMIT_5000');p.version++;p.status=status;s.events.push({seq:s.events.length+1,checksum:'',acknowledged_at:null,attempts:0,envelope:{schema_version:1,source_system:'mhb-browser-simulation',event_id:id(),aggregate_id:p.id,aggregate_version:p.version,tenant_id:s.scenario,event_time:now(),correlation_id:p.correlation_id,causation_id:causation,currency:'CAD',currency_exponent:2,payload:{...structuredClone(p),returns:structuredClone(s.returns[p.id]||[])}}});}
export function createPayment(s:State,actor:Principal,b:Record<string,unknown>,key:string,org?:string){
 if(s.payments.length>=500)fail('SCENARIO_PAYMENT_LIMIT_500');const n=amount(b.amount_minor);if(b.currency!==undefined&&b.currency!=='CAD')fail('CAD_ONLY');
 const a=s.accounts.find(a=>a.id===b.source_id&&(org?a.org===org:a.owner===actor.id));if(!a)fail('ACCOUNT_NOT_FOUND');if(a.booked_minor-a.hold_minor<n)fail('INSUFFICIENT_AVAILABLE_FUNDS');
 const internal=b.kind==='INTERNAL';if(b.kind!==undefined&&!['INTERNAL','OUTBOUND'].includes(String(b.kind)))fail('INVALID_PAYMENT_KIND');
 const dest=internal?s.accounts.find(d=>d.id===b.destination_id&&d.owner===actor.id&&!d.org&&d.id!==a.id):undefined;
 if(internal&&!dest)fail('DESTINATION_NOT_FOUND');if(!internal&&b.beneficiary_id!=='energy')fail('BENEFICIARY_NOT_FOUND');
 const p:BankPayment={id:id(),owner_id:actor.id,source_id:a.id,kind:internal?'INTERNAL':'OUTBOUND',amount_minor:n,currency:'CAD',status:'RECEIVED',returned_minor:0,version:0,business_date:day(),created_at:now(),correlation_id:id(),...(dest?{destination_id:dest.id}:{beneficiary_id:'energy'}),...(org?{org}:{})};
 a.booked_minor-=n;if(dest)dest.booked_minor+=n;s.payments.push(p);post(s,p.id,'PAYMENT',n,a.id,dest?.id||'clearing');for(const status of ['RECEIVED','VALIDATED','POSTED'])emit(s,p,status,key);return {payment_id:p.id,correlation_id:p.correlation_id,status:p.status};
}
