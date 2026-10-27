import {useRef,useState,useEffect} from 'react';
import {Canvas,useFrame} from '@react-three/fiber';
import {Float,Line,OrbitControls} from '@react-three/drei';
import * as THREE from 'three';
export type NodeData={id:number;name:string;group?:number};
function Graph({nodes,motion}:{nodes:NodeData[];motion:boolean}){
 const group=useRef<THREE.Group>(null);const [hover,setHover]=useState<number|null>(null);
 useFrame(({pointer})=>{if(group.current&&motion){group.current.rotation.y=THREE.MathUtils.lerp(group.current.rotation.y,pointer.x*.18,.03);group.current.rotation.x=THREE.MathUtils.lerp(group.current.rotation.x,-pointer.y*.12,.03)}});
 const points=nodes.slice(0,24).map((n,i)=>{const a=i*2.39996;const r=1.3+(i%3)*.45;return new THREE.Vector3(Math.cos(a)*r,Math.sin(a)*r*.67,Math.sin(i*1.7)*.8)});
 return <group ref={group}><Float speed={motion?1:0} rotationIntensity={motion?.12:0} floatIntensity={motion?.3:0}><mesh rotation={[.5,.3,0]}><icosahedronGeometry args={[.58,1]}/><meshStandardMaterial color="#72efd1" roughness={.2} metalness={.65}/></mesh><mesh><sphereGeometry args={[.88,24,24]}/><meshStandardMaterial color="#60cbb8" wireframe transparent opacity={.15}/></mesh>{nodes.slice(0,24).map((node,i)=><group key={node.id}><Line points={[[0,0,0],points[i]]} color={hover===i?'#b1ffed':'#429baf'} lineWidth={hover===i?2:1} transparent opacity={.4}/><mesh position={points[i]} onPointerOver={()=>setHover(i)} onPointerOut={()=>setHover(null)} scale={hover===i?1.3:1}><icosahedronGeometry args={[.13+(i%3)*.035,1]}/><meshStandardMaterial color={node.group===1?'#7499ff':i%3===0?'#7995ff':'#89f6db'} roughness={.3} metalness={.4}/></mesh></group>)}</Float></group>
}
export default function Network({nodes}:{nodes:NodeData[]}){
 const [motion,setMotion]=useState(!matchMedia('(prefers-reduced-motion: reduce)').matches);
 useEffect(()=>{const mq=matchMedia('(prefers-reduced-motion: reduce)');const cb=()=>setMotion(!mq.matches);mq.addEventListener('change',cb);return()=>mq.removeEventListener('change',cb)},[]);
 return <Canvas aria-label="Interactive team network. A text list is available below." dpr={[1,1.5]} camera={{position:[0,0,5.7],fov:44}} frameloop={motion?'always':'demand'}><ambientLight intensity={1.5}/><directionalLight position={[3,4,4]} intensity={3}/><pointLight position={[-3,1,2]} color="#6495ff" intensity={15}/><Graph nodes={nodes} motion={motion}/><OrbitControls enableZoom={false} enablePan={false} autoRotate={false}/></Canvas>
}
