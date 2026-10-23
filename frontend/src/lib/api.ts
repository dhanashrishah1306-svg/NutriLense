const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api';
async function request<T>(path:string, init?:RequestInit):Promise<T>{const r=await fetch(`${API}${path}`,init); if(!r.ok){let message=`Request failed (${r.status})`;try{const d=await r.json();message=d.detail||message}catch{}throw new Error(message)}return r.json()}
export const health=()=>request<{status:string}>('/health');
export const uploadImage=async(path:'/classify'|'/ocr',file:File)=>{const f=new FormData();f.append('file',file);return request<any>(path,{method:'POST',body:f})};
export const analyze=(payload:any)=>request<any>('/analyze',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
export const nutrition=(barcode:string)=>request<any>(`/nutrition/${encodeURIComponent(barcode)}`);
