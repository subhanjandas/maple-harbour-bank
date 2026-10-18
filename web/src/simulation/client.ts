const worker=new Worker(new URL('./worker.ts',import.meta.url),{type:'module'});
const waiting=new Map<string,{resolve:(value:unknown)=>void;reject:(e:Error)=>void;timer:ReturnType<typeof setTimeout>}>();
worker.onmessage=({data})=>{const w=waiting.get(data.ticket);if(!w)return;clearTimeout(w.timer);waiting.delete(data.ticket);if(data.error)w.reject(Error(data.error));else w.resolve(data.result);};
worker.onerror=()=>{for(const w of waiting.values()){clearTimeout(w.timer);w.reject(Error('WORKER_INTERRUPTED_RELOAD_TO_RECOVER'));}waiting.clear();};
export function browserApi<T>(path:string,method='GET',body?:unknown,key?:string):Promise<T>{
 if(path.startsWith('/auth/development/')){sessionStorage.setItem('mhb-public-persona',path.split('/').at(-1)==='alex'?'subhanjan':path.split('/').at(-1)!);return Promise.resolve({authenticated:true} as T);}
 if(path==='/auth/logout'){sessionStorage.removeItem('mhb-public-persona');return Promise.resolve({revoked:true} as T);}
 const ticket=crypto.randomUUID();return new Promise((resolve,reject)=>{const timer=setTimeout(()=>{waiting.delete(ticket);reject(Error('WORKER_TIMEOUT_RETRY_SAME_KEY'));},30000);waiting.set(ticket,{resolve:resolve as (v:unknown)=>void,reject,timer});worker.postMessage({ticket,persona:sessionStorage.getItem('mhb-public-persona'),path,method,body,key});});
}
