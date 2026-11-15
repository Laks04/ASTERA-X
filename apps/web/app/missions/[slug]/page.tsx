import Link from 'next/link';
import { notFound } from 'next/navigation';
import MissionTimeline from '../../../components/MissionTimeline';
import { missions } from '../../../lib/data';

type Props = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return missions.map((mission) => ({ slug: mission.slug }));
}

export async function generateMetadata({ params }: Props) {
  const { slug } = await params;
  const mission = missions.find((item) => item.slug === slug);
  return {
    title: mission ? `${mission.name} | ASTERA` : 'Mission not found | ASTERA',
    description: mission?.summary ?? 'Explore the ASTERA mission archive.',
  };
}

export default async function MissionDetail({ params }: Props) {
  const { slug } = await params;
  const mission = missions.find((item) => item.slug === slug);
  if (!mission) notFound();

  const lifecycleNote = mission.type === 'travelling'
    ? 'This spacecraft is classified as still travelling. It is not surface debris or abandoned equipment on another world.'
    : mission.type === 'orbit'
      ? 'This mission is represented as an inactive or completed orbital spacecraft. An object in orbit is not the same as hardware left on a planetary surface.'
      : 'This collection concerns hardware associated with a planetary surface. Individual components can have different operational and end-of-mission histories.';

  return (
    <section className="page-shell">
      <div className="detail-hero">
        <div>
          <Link href="/discover" className="text-link">← Back to the archive</Link>
          <span className="eyebrow" style={{ display: 'flex', marginTop: 28 }}>MISSION RECORD / ASTERA COLLECTION</span>
          <h1>{mission.name.split(' ').slice(0, -1).join(' ')} <em>{mission.name.split(' ').slice(-1).join(' ')}</em></h1>
          <p>{mission.summary}</p>
          <div className="detail-tags"><span>{mission.destination}</span><span>{mission.era}</span><span>{mission.category}</span></div>
          <a className="button-primary" href={mission.source} target="_blank" rel="noreferrer">Open official NASA source ↗</a>
        </div>
        <div className="detail-orb" aria-hidden="true"><div style={{ background: `radial-gradient(circle at 30% 28%, #f1efff 0%, ${mission.color} 20%, #252b58 64%, #080b19 82%)` }} /></div>
      </div>
      <div className="detail-grid">
        <article className="content-panel">
          <span className="eyebrow">WHY THIS MISSION MATTERS</span>
          <h2>Its lasting contribution</h2>
          <p>{mission.legacy}</p>
          <div className="notice-box"><b>Lifecycle context</b><p>{lifecycleNote}</p><p><strong>Collection status:</strong> {mission.status}. This is a curated summary; component-level status requires individual source evidence and review.</p></div>
          <MissionTimeline />
        </article>
        <aside className="content-panel">
          <span className="eyebrow">MISSION SNAPSHOT</span>
          <dl className="mission-facts">
            <div><dt>Destination</dt><dd>{mission.destination}</dd></div>
            <div><dt>Mission era</dt><dd>{mission.era}</dd></div>
            <div><dt>Hardware class</dt><dd>{mission.category}</dd></div>
            <div><dt>Lifecycle label</dt><dd>{mission.status}</dd></div>
            <div><dt>Evidence</dt><dd>Official source linked</dd></div>
          </dl>
          <p className="micro-note">ASTERA does not infer precise coordinates, component condition or scientific measurements from this summary. Consult the linked source for the official mission record.</p>
        </aside>
      </div>
      <div className="notice-box"><b>About this record</b><p>This page is a curated educational summary linked to an official NASA resource. It is not a claim that the full source dataset has been downloaded, parsed or independently verified by ASTERA.</p></div>
    </section>
  );
}
