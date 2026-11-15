'use client';
import {useMemo,useState} from 'react';

type SeriesKey='seismic'|'thermal'|'magnetic';
const labels:Record<SeriesKey,{name:string;unit:string;description:string}>={
 seismic:{name:'Seismic wave',unit:'relative amplitude',description:'A synthetic damped wave used to teach amplitude, frequency and attenuation. It is not an Apollo seismometer record.'},
 thermal:{name:'Thermal cycle',unit:'relative temperature',description:'A normalized day/night-style cycle for exploring periodic signals. It is not a measured lunar temperature series.'},
 magnetic:{name:'Magnetic variation',unit:'relative field',description:'A low-amplitude illustrative signal for practicing trend interpretation. It is not an ALSEP magnetometer observation.'}
};
export default function ScienceWorkbench(){
 const [series,setSeries]=useState<SeriesKey>('seismic');const [phase,setPhase]=useState(0);
 const values=useMemo(()=>Array.from({length:64},(_,i)=>{const x=i/63; if(series==='seismic')return Math.exp(-x*3.1)*Math.sin(x*15*Math.PI+phase)*.82; if(series==='thermal')return Math.sin(x*2*Math.PI+phase)*.62+.12*Math.sin(x*6*Math.PI);return .32*Math.sin(x*4*Math.PI+phase)+.13*Math.cos(x*13*Math.PI)}),[series,phase]);
 const points=values.map((v,i)=>`${(i/63*1000).toFixed(1)},${(110-v*78).toFixed(1)}`).join(' ');
 return <section className="science-workbench"><div className="chart-head"><div><span className="eyebrow">SCIENTIFIC DATA WORKBENCH</span><h3>Learn to read a signal.</h3></div><span className="chart-tag">SIMULATED · NOT NASA DATA</span></div>
 <div className="science-toolbar"><div className="switcher" role="group" aria-label="Signal type">{(['seismic','thermal','magnetic'] as SeriesKey[]).map(k=><button key={k} className={series===k?'active':''} onClick={()=>setSeries(k)}>{labels[k].name}</button>)}</div><button className="button-quiet" onClick={()=>setPhase(p=>p+.65)}>Change phase ↻</button></div>
 <div className="signal-chart"><div className="chart-y-label">{labels[series].unit}</div><svg viewBox="0 0 1000 150" role="img" aria-label={`${labels[series].name} illustrative waveform`}><defs><linearGradient id="signalFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#91a6ff" stopOpacity=".34"/><stop offset="100%" stopColor="#91a6ff" stopOpacity="0"/></linearGradient></defs>{[32,71,110].map(y=><line key={y} x1="0" x2="1000" y1={y} y2={y} stroke="#a9b7e8" strokeOpacity=".13" strokeDasharray="4 8"/>)}<polygon points={`0,110 ${points} 1000,110`} fill="url(#signalFill)"/><polyline points={points} fill="none" stroke="#a9a5ff" strokeWidth="3" strokeLinejoin="round" strokeLinecap="round"/></svg><div className="chart-x-label">SIMULATION WINDOW →</div></div>
 <div className="signal-readout"><div><span className="eyebrow">SELECTED SIGNAL</span><b>{labels[series].name}</b><p>{labels[series].description}</p></div><div className="signal-stats"><span>Samples <b>64</b></span><span>Peak magnitude <b>{Math.max(...values.map(Math.abs)).toFixed(2)}</b></span><span>Source <b>Local simulation</b></span></div></div>
 <div className="science-tags"><span>Signal interpretation</span><span>Waveform visualization</span><span>Instrument literacy</span><span>Source provenance</span></div>
 <p className="micro-note">When verified ALSEP data is ingested, this workbench should switch to the original observations with instrument, units, timestamp range, archive identifier and source citation. The current traces are generated locally for learning only.</p></section>
}
