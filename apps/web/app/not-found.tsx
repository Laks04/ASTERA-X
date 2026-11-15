import Link from 'next/link';
export default function NotFound() {
  return <section className="page-shell"><div className="page-intro"><span className="eyebrow">SIGNAL NOT FOUND / 404</span><h1>This trail leads <em>nowhere.</em></h1><p>The page or mission record you requested is not part of the current ASTERA collection.</p><Link href="/discover" className="button-primary">Return to the archive ↗</Link></div></section>;
}
