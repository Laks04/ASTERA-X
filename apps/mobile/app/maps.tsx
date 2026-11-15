import { useState } from 'react';
import { Pressable, ScrollView, Text, View } from 'react-native';
const places = {
  Moon: [
    ['Apollo 11', 'Crewed landing site', 'The Apollo 11 Lunar Module landed in the Sea of Tranquility. This is a contextual reference, not a coordinate marker.'],
    ['Surveyor 3', 'Robotic lander', 'Surveyor 3 landed in Oceanus Procellarum and was later visited by Apollo 12 astronauts.'],
    ['ALSEP stations', 'Scientific instruments', 'Apollo surface experiments were deployed at several landing sites. This groups a topic, not one location.'],
  ],
  Mars: [
    ['Pathfinder region', 'Lander and rover', 'Mars Pathfinder delivered Sojourner to the Martian surface in 1997.'],
    ['MER mission regions', 'Rover exploration', 'Spirit and Opportunity explored separate regions of Mars.'],
    ['InSight region', 'Geophysical lander', 'InSight studied the interior of Mars.'],
  ],
} as const;
export default function MapsPage() {
  const [body, setBody] = useState<'Moon' | 'Mars'>('Moon');
  const [selected, setSelected] = useState(0);
  const item = places[body][selected];
  return <ScrollView style={{ flex: 1, backgroundColor: '#050711' }} contentContainerStyle={{ padding: 20, gap: 14 }}>
    <Text style={{ color: '#a9a5ff', fontSize: 11, letterSpacing: 2 }}>PLANETARY FIELD ATLAS</Text>
    <Text style={{ color: '#eef1ff', fontSize: 28, fontWeight: '700' }}>Explore mission places.</Text>
    <View style={{ flexDirection: 'row', gap: 10 }}>{(['Moon', 'Mars'] as const).map((name) => <Pressable key={name} onPress={() => { setBody(name); setSelected(0); }} style={{ padding: 12, borderRadius: 8, backgroundColor: body === name ? '#595b91' : '#111a32' }}><Text style={{ color: '#f0f1ff' }}>{name}</Text></Pressable>)}</View>
    <View style={{ minHeight: 210, backgroundColor: body === 'Moon' ? '#24283b' : '#422b2a', borderRadius: 14, justifyContent: 'center', padding: 18, gap: 10 }}><Text style={{ color: '#f4eaff', fontSize: 20, fontWeight: '700' }}>{body.toUpperCase()} · SCHEMATIC ATLAS</Text><Text style={{ color: '#c3c8df', lineHeight: 22 }}>Select a mission reference below. This view is conceptual and does not display verified geographic coordinates or terrain imagery.</Text></View>
    {places[body].map((place, index) => <Pressable key={place[0]} onPress={() => setSelected(index)} style={{ padding: 15, borderWidth: 1, borderColor: selected === index ? '#a9a5ff' : '#303a63', borderRadius: 8, backgroundColor: '#10172b' }}><Text style={{ color: '#a9a5ff', fontSize: 10 }}>REFERENCE 0{index + 1} · {place[1]}</Text><Text style={{ color: '#eef1ff', fontSize: 16, marginTop: 5 }}>{place[0]}</Text></Pressable>)}
    <View style={{ backgroundColor: '#111a32', padding: 16, borderRadius: 8 }}><Text style={{ color: '#eef1ff', fontWeight: '700' }}>{item[0]}</Text><Text style={{ color: '#a4afcd', lineHeight: 22, marginTop: 7 }}>{item[2]}</Text></View>
  </ScrollView>;
}
