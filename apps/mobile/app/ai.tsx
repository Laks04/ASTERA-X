import { useMemo, useState } from 'react';
import { ScrollView, Text, TextInput, View, Pressable } from 'react-native';
const knowledge = [
  { key: 'alsep', title: 'What was ALSEP?', answer: 'The Apollo Lunar Surface Experiments Packages carried scientific instruments that continued collecting measurements after astronauts departed. Source: NSSDCA — https://nssdc.gsfc.nasa.gov/nmc/spacecraft/display.action?id=1969-099C' },
  { key: 'sojourner', title: 'Tell me about Sojourner', answer: 'Sojourner was the first successful Mars rover, delivered by Mars Pathfinder in 1997. Source: NASA — https://science.nasa.gov/mission/mars-pathfinder/' },
  { key: 'pioneer', title: 'Are Pioneer probes abandoned?', answer: 'Pioneer 10 and 11 are deep-space probes that travelled outward from the solar system. They are not surface artifacts. Source: NASA — https://science.nasa.gov/mission/pioneer-10/' },
  { key: 'ingenuity', title: 'What happened to Ingenuity?', answer: 'Ingenuity demonstrated powered, controlled flight on Mars. NASA reported that the helicopter ended its flight operations in January 2024 after rotor damage. Source: NASA — https://science.nasa.gov/mission/mars-2020-perseverance/ingenuity-mars-helicopter/' },
];
export default function AIPage() {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState('');
  const suggestions = useMemo(() => knowledge, []);
  function ask(value: string) {
    setQuestion(value);
    const item = knowledge.find((entry) => value.toLowerCase().includes(entry.key));
    setAnswer(item?.answer ?? 'I do not have enough indexed source material to answer that confidently. Try ALSEP, Sojourner, Pioneer or Ingenuity. This mobile preview is source-bounded and does not connect to a live language model.');
  }
  return <ScrollView style={{ flex: 1, backgroundColor: '#050711' }} contentContainerStyle={{ padding: 20, gap: 14 }}>
    <Text style={{ color: '#a9a5ff', fontSize: 11, letterSpacing: 2 }}>ASTERA INTELLIGENCE</Text>
    <Text style={{ color: '#eef1ff', fontSize: 28, fontWeight: '700' }}>Curiosity, meet context.</Text>
    <Text style={{ color: '#9eabc9', lineHeight: 22 }}>Ask about a mission in the curated collection. Answers are deliberately limited to the source-linked facts available in this preview.</Text>
    {suggestions.map((item) => <Pressable key={item.key} onPress={() => ask(item.title)} style={{ padding: 14, borderWidth: 1, borderColor: '#303a63', borderRadius: 8 }}><Text style={{ color: '#dfe4ff' }}>{item.title}</Text></Pressable>)}
    <TextInput value={question} onChangeText={setQuestion} placeholder="Ask about a mission…" placeholderTextColor="#7481a5" style={{ color: '#eef1ff', borderWidth: 1, borderColor: '#303a63', padding: 13, borderRadius: 8 }} />
    <Pressable onPress={() => ask(question)} style={{ backgroundColor: '#a9a5ff', padding: 13, borderRadius: 8 }}><Text style={{ color: '#080b18', fontWeight: '700', textAlign: 'center' }}>Ask ASTERA</Text></Pressable>
    {!!answer && <View style={{ backgroundColor: '#111a32', borderRadius: 8, padding: 16 }}><Text style={{ color: '#e3e8ff', lineHeight: 23 }}>{answer}</Text></View>}
    <Text style={{ color: '#7180a4', fontSize: 11, lineHeight: 18 }}>Preview only · no live LLM or complete retrieval-augmented generation connection.</Text>
  </ScrollView>;
}
