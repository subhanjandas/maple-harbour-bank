import {seed,assertMoney,checksum,type State} from './model';
const DB='maple-harbour-public-v1';
let connection:Promise<IDBDatabase>|undefined;
function database(){return connection??=new Promise<IDBDatabase>((resolve,reject)=>{const request=indexedDB.open(DB,1);request.onupgradeneeded=()=>request.result.createObjectStore('state');request.onerror=()=>reject(Error('BROWSER_STORAGE_UNAVAILABLE'));request.onsuccess=()=>resolve(request.result);});}
export async function read():Promise<State>{const db=await database();return new Promise((resolve,reject)=>{const tx=db.transaction('state','readonly');const request=tx.objectStore('state').get('bank');request.onsuccess=()=>resolve(request.result||seed());request.onerror=()=>reject(request.error);});}
async function compareAndSet(previous:number,next:State):Promise<boolean>{const db=await database();return new Promise((resolve,reject)=>{const tx=db.transaction('state','readwrite');const store=tx.objectStore('state');let written=false;const r=store.get('bank');r.onsuccess=()=>{if((r.result?.revision??0)===previous){store.put(next,'bank');written=true;}};tx.oncomplete=()=>resolve(written);tx.onabort=()=>reject(Error('BROWSER_STORAGE_COMMIT_FAILED'));tx.onerror=()=>reject(tx.error);});}
export async function change<T>(operation:(s:State)=>T|Promise<T>):Promise<T>{
 for(let retry=0;retry<20;retry++){const s=await read(),version=s.revision;const result=await operation(s);assertMoney(s);for(const e of s.events)if(!e.checksum)e.checksum=await checksum(e.envelope);s.revision=version+1;if(await compareAndSet(version,s))return structuredClone(result);}
 throw Error('RETRYABLE_BROWSER_CONTENTION');
}
