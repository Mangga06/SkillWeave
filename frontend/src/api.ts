export type Role = 'admin'|'coordinator'|'leader'|'volunteer';
export interface WorkProject {project_id:number;name:string;category:string;status:string;start:string;end:string;approved_hours:number;tasks:{name:string;status:string;progress:number}[]}
export interface Person {work_history?:WorkProject[];id:number;name:string;email:string;role:Role;org_id:number;active:boolean;weekly_hours:number;experience:number;interests:string[];learning_goals:string[];notifications_enabled:boolean;skills:{skill_id:number;level:number;verified:boolean}[];availability:{start:string;end:string}[]}
export interface Project {id:number;name:string;description:string;category:string;location:string;start:string;end:string;status:string;leader_id:number|null}
export interface Task {id:number;project_id:number;name:string;description:string;start:string;end:string;hours:number;capacity:number;minimum:number;priority:number;difficulty:number;status:string;progress:number;requirements:{skill_id:number;level:number;mandatory:boolean;verified:boolean}[];dependencies:number[]}
export interface Assignment {id:number;task_id:number;user_id:number;status:string;locked:boolean;task_name:string;volunteer_name:string}
export interface Skill {id:number;name:string;category:string}
export interface Run {id:number;status:string;error:string;created_at:string;scenario:Record<string,unknown>;published:boolean;snapshot:{tasks:Task[];volunteers:Person[]};config:{seed:number;generations:number};result:null|{fitness:number;breakdown:Record<string,number>;history:{generation:number;best:number;mean:number}[];allocation:Record<string,number[]>;workload:Record<string,number>;missing_skills:{task_id:number;skill_id:number}[];unfilled:{task_id:number;missing:number}[];weights:Record<string,number>;warnings:string[];exclusions:{task_id:number;user_id:number;reason:string}[];explanations:{task_id:number;user_id:number;score:number;rules:{rule:string;strength:number}[]}[];runtime_ms:number;imbalance:number;constraint_violations:number;changed_assignments:number;baselines:Record<string,{fitness:number;breakdown:Record<string,number>;runtime_ms:number;unfilled:unknown[];imbalance:number;constraint_violations:number;changed_assignments:number}>}}
export async function api<T=unknown>(path:string,options:RequestInit={}):Promise<T>{
  const res=await fetch('/api/v1'+path,{...options,credentials:'include',headers:{...(options.body instanceof FormData?{}:{'Content-Type':'application/json'}),'X-Requested-With':'SkillWeave',...options.headers}});
  if(!res.ok){const err=await res.json().catch(()=>({detail:'Server unavailable'}));throw new Error(typeof err.detail==='string'?err.detail:err.detail?.map((x:{msg:string})=>x.msg).join('; ')||'Request failed');}
  return res.json();
}
export const post=<T=unknown>(path:string,data:unknown={})=>api<T>(path,{method:'POST',body:JSON.stringify(data)});
export const put=<T=unknown>(path:string,data:unknown)=>api<T>(path,{method:'PUT',body:JSON.stringify(data)});
