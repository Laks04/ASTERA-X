import { useMemo, useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';

type ControlProps = { label: string; value: number; unit: string; min: number; max: number; step: number; onChange: (value: number) => void };
function Control({ label, value, unit, min, max, step, onChange }: ControlProps) {
  return <View style={{ backgroundColor: '#111a32', padding: 14, borderRadius: 8, gap: 9 }}>
    <Text style={{ color: '#dfe4ff' }}>{label}: {value} {unit}</Text>
    <View style={{ flexDirection: 'row', gap: 10 }}>
      <Pressable disabled={value <= min} onPress={() => onChange(Math.max(min, value - step))} style={{ padding: 10, backgroundColor: '#252d55', borderRadius: 6 }}><Text style={{ color: '#fff' }}>−</Text></Pressable>
      <Pressable disabled={value >= max} onPress={() => onChange(Math.min(max, value + step))} style={{ padding: 10, backgroundColor: '#595b91', borderRadius: 6 }}><Text style={{ color: '#fff' }}>+</Text></Pressable>
    </View>
  </View>;
}

export default function SimulatorPage() {
  const [thrust, setThrust] = useState(60);
  const [mass, setMass] = useState(1200);
  const [duration, setDuration] = useState(60);
  const [stage, setStage] = useState(0);
  const force = thrust * 180;
  const acceleration = force / mass;
  const velocity = acceleration * duration;
  const distance = .5 * acceleration * duration * duration;
  const fmt = useMemo(() => (n: number) => n.toLocaleString('en-US', { maximumFractionDigits: 1 }), []);
  return <ScrollView style={{ flex: 1, backgroundColor: '#050711' }} contentContainerStyle={{ padding: 20, gap: 16 }}>
    <Text style={{ color: '#a9a5ff', fontSize: 11, letterSpacing: 2 }}>MISSION DESIGN LAB</Text><Text style={{ color: '#eef1ff', fontSize: 28, fontWeight: '700' }}>A simplified flight model</Text>
    <Text style={{ color: '#9eabc9', lineHeight: 22 }}>Change the controls to explore constant-force motion. This is an educational calculation, not a validated spacecraft trajectory.</Text>
    <Control label="Thrust setting" value={thrust} unit="%" min={10} max={100} step={5} onChange={setThrust} />
    <Control label="Vehicle mass" value={mass} unit="kg" min={500} max={5000} step={100} onChange={setMass} />
    <Control label="Duration" value={duration} unit="s" min={10} max={180} step={5} onChange={setDuration} />
    <View style={{ backgroundColor: '#141c36', padding: 16, borderRadius: 8, gap: 10 }}><Text style={{ color: '#a9a5ff', fontSize: 11 }}>CALCULATED OUTPUTS</Text><Text style={{ color: '#eef1ff' }}>Acceleration · {fmt(acceleration)} m/s²</Text><Text style={{ color: '#eef1ff' }}>Velocity change · {fmt(velocity)} m/s</Text><Text style={{ color: '#eef1ff' }}>Distance from rest · {fmt(distance)} m</Text><Text style={{ color: '#8e9ab9', fontSize: 11 }}>F = ma · Δv = at · s = ½at²</Text></View>
    <Text style={{ color: '#a9a5ff', fontSize: 11 }}>MISSION STAGE · {stage + 1} / 4</Text><View style={{ flexDirection: 'row', gap: 8, flexWrap: 'wrap' }}>{['Pre-launch', 'Ascent', 'Cruise', 'Operations'].map((name, index) => <Pressable key={name} onPress={() => setStage(index)} style={{ padding: 9, borderRadius: 6, backgroundColor: stage === index ? '#595b91' : '#111a32' }}><Text style={{ color: '#eef1ff', fontSize: 11 }}>{name}</Text></Pressable>)}</View>
    <Text style={{ color: '#7180a4', fontSize: 11, lineHeight: 18 }}>Assumptions: constant thrust and mass, starting from rest, no gravity, drag, staging or guidance. Results are not real mission performance.</Text>
  </ScrollView>;
}
