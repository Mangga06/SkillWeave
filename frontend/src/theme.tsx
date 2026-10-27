import {createContext,useContext,useEffect,useState} from 'react';
import {Sun,Moon,Monitor} from 'lucide-react';
type Theme='light'|'dark'|'system';
const Context=createContext<{theme:Theme;setTheme:(x:Theme)=>void}>({theme:'system',setTheme:()=>{}});
export function ThemeProvider({children}:{children:React.ReactNode}){
 const [theme,setTheme]=useState<Theme>(()=>(localStorage.getItem('sw-theme') as Theme)||'system');
 useEffect(()=>{const mq=matchMedia('(prefers-color-scheme: dark)');const apply=()=>{document.documentElement.dataset.theme=theme==='system'?(mq.matches?'dark':'light'):theme};apply();localStorage.setItem('sw-theme',theme);mq.addEventListener('change',apply);return()=>mq.removeEventListener('change',apply)},[theme]);
 return <Context.Provider value={{theme,setTheme}}>{children}</Context.Provider>
}
export function ThemeToggle(){const {theme,setTheme}=useContext(Context);return <label className="theme-control"><span className="sr-only">Appearance</span>{theme==='dark'?<Moon size={16}/>:theme==='light'?<Sun size={16}/>:<Monitor size={16}/>}<select aria-label="Theme preference" value={theme} onChange={e=>setTheme(e.target.value as Theme)}><option value="light">Light</option><option value="dark">Dark</option><option value="system">System</option></select></label>}
