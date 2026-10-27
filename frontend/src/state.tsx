import {createContext,useContext} from 'react';
import {useQuery,useQueryClient} from '@tanstack/react-query';
import {api, type Person} from './api';
export const Auth=createContext<Person|null>(null);
export const Toast=createContext<(message:string,error?:boolean)=>void>(()=>{});
export function useMe(){return useContext(Auth)!}
export function useData<T>(path:string){return useQuery({queryKey:[path],queryFn:()=>api<T>(path)});}
export function useAction(){const qc=useQueryClient();const toast=useContext(Toast);return async(action:()=>Promise<unknown>,success='Changes saved')=>{try{await action();await qc.invalidateQueries();toast(success);return true}catch(e){toast((e as Error).message,true);return false}}}
export function QueryState({query}:{query:{isPending:boolean;error:Error|null;refetch:()=>unknown}}){return query.isPending?<p className="loading" role="status">Loading your workspace…</p>:query.error?<div className="error" role="alert">{query.error.message} <button onClick={()=>query.refetch()}>Try again</button></div>:null}
