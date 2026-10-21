import {useCallback,useEffect,useRef,useState} from 'react';
import {api} from './api';
import type {Telemetry} from './simulation/telemetry';
export function useTelemetry(payment=''){
 const [data,setData]=useState<Telemetry|null>(null),[error,setError]=useState('');const active=useRef(false),generation=useRef(0);
 const refresh=useCallback(async()=>{if(active.current)return;const epoch=generation.current;active.current=true;try{const d=await api<Telemetry>('/lab/telemetry'+(payment?'?payment='+encodeURIComponent(payment):''));if(epoch===generation.current){setData(d);setError('');}}catch(e){if(epoch===generation.current)setError((e as Error).message);}finally{active.current=false;}},[payment]);
 useEffect(()=>{generation.current++;refresh();const tick=setInterval(()=>{if(!document.hidden)refresh();},2000);return()=>{clearInterval(tick);generation.current++;};},[refresh]);
 return {data,error,refresh};
}
