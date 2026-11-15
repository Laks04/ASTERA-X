'use client';
import {useEffect,useState} from 'react';
export default function ApiStatus(){const [s,setS]=useState('Checking API');useEffect(()=>{fetch(`${process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000'}/api/v1/health`,{signal:AbortSignal.timeout(2500)}).then(r=>r.json()).then(d=>setS(`API ${d.status} · database ${d.database}`)).catch(()=>setS('API offline · preview data active'))},[]);return <span className="api-status"><i/> {s}</span>}
