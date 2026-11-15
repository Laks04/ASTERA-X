'use client';
import { useEffect } from 'react';
export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => { console.error('ASTERA page error:', error); }, [error]);
  return <section className="page-shell"><div className="page-intro"><span className="eyebrow">TEMPORARY INTERRUPTION</span><h1>We lost the <em>signal.</em></h1><p>This page encountered an unexpected error. Your saved local learning progress has not been intentionally cleared.</p><button className="button-primary" onClick={() => reset()}>Try this page again ↻</button></div></section>;
}
