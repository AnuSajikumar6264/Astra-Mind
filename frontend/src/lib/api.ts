const API='/api/v1';
export async function req<T>(path:string,init?:RequestInit):Promise<T>{const r=await fetch(API+path,{...init,headers:{'Content-Type':'application/json',...(init?.headers||{})}});if(!r.ok)throw new Error(await r.text());return r.json()}
export const dashboard=()=>req<any>('/dashboard');
export const observations=(domain='')=>req<any[]>(`/observations?limit=200${domain?`&domain=${domain}`:''}`);
export const simulate=(scenario:string)=>req<any>('/simulation/run',{method:'POST',body:JSON.stringify({scenario,samples:1})});
export const acknowledge=(id:string)=>req<any>(`/alerts/${id}/acknowledge`,{method:'POST'});
export const forecast=(domain:string,metric:string)=>req<any>(`/forecast/crew-01?domain=${domain}&metric=${metric}&horizon=8`);
export const twin=()=>req<any>('/twin/crew-01');
