import {request} from './commands';
import {processBatch} from './pipeline';
import {pulseWorkload} from './workload';
let chain:Promise<unknown>=Promise.resolve();
self.onmessage=(event:MessageEvent)=>{const {ticket,persona,path,method,body,key}=event.data;chain=chain.then(async()=>{try{const result=await request(persona,path,method,body,key);self.postMessage({ticket,result});}catch(e){self.postMessage({ticket,error:(e as Error).message});}});};
setInterval(()=>{chain=chain.then(()=>processBatch()).catch(()=>undefined);},2500);

setInterval(()=>{chain=chain.then(()=>pulseWorkload()).catch(()=>undefined);},1000);
