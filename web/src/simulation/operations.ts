import {amount,day,emit,fail,id,post,type State} from './model';
/** Shared command implementation: simulator acknowledgements use the same posting rules as operations. */
export function operateState(s:State,pid:string,action:string,body:Record<string,unknown>,key:string,returnId?:string){
 const p=s.payments.find(p=>p.id===pid);if(!p)fail('PAYMENT_NOT_FOUND');const a=s.accounts.find(a=>a.id===p.source_id)!;
 if(action==='settle'){if(p.kind!=='OUTBOUND'||p.status!=='POSTED')fail('INVALID_TRANSITION');post(s,p.id,'SETTLEMENT',p.amount_minor,'clearing','cash');emit(s,p,'SETTLED',key);}
 else if(action==='reverse'){if(p.kind!=='INTERNAL'||p.status!=='POSTED')fail('INVALID_TRANSITION');const dest=s.accounts.find(a=>a.id===p.destination_id)!;if(dest.booked_minor-dest.hold_minor<p.amount_minor)fail('INSUFFICIENT_AVAILABLE_FUNDS');dest.booked_minor-=p.amount_minor;a.booked_minor+=p.amount_minor;post(s,p.id,'REVERSAL',p.amount_minor,dest.id,a.id);emit(s,p,'REVERSED',key);}
 else if(action==='returns'&&!returnId){if(!['SETTLED','PARTIALLY_RETURNED'].includes(p.status))fail('INVALID_TRANSITION');const n=amount(body.amount_minor);if(n+p.returned_minor>p.amount_minor)fail('RETURN_EXCEEDS_ORIGINAL');const returns=s.returns[p.id]??=[];if(returns.length>=100)fail('RETURN_INSTALLMENT_LIMIT');returns.push({id:id(),amount_minor:n,booked_date:day(),reporting_date:day(),revision:1});a.booked_minor+=n;p.returned_minor+=n;post(s,p.id,'RETURN',n,'cash',a.id);emit(s,p,p.returned_minor===p.amount_minor?'RETURNED':'PARTIALLY_RETURNED',key);}
 else if(action==='reporting-date'){const r=s.returns[p.id]?.find(r=>r.id===returnId);if(!r)fail('RETURN_NOT_FOUND');const date=String(body.reporting_date);if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||new Date(date+'T12:00:00Z').toISOString().slice(0,10)!==date||date>day())fail('INVALID_REPORTING_DATE');r.reporting_date=date;r.revision++;emit(s,p,p.status,key);}
 else fail('UNKNOWN_OPERATION');return {payment_id:p.id,status:p.status,version:p.version};
}
