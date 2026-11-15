'use client';
import dynamic from 'next/dynamic';
const UniverseCanvas = dynamic(() => import('./UniverseCanvas'), { ssr: false, loading: () => <div className="universe-frame loading-scene">Preparing the solar system…</div> });
export default function UniverseExperience(){return <UniverseCanvas/>}
