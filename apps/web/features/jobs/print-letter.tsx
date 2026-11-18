"use client";

import { useEffect, useState } from "react";
import { getLetter, type Letter } from "./letters-api";
import styles from "./jobs.module.css";

export default function PrintLetter({ id }: { id: string }) {
  const [letter, setLetter] = useState<Letter | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let cancelled = false;
    void getLetter(id).then(data => {
      if (cancelled) return;
      if (data.status !== "approved") setError("Approve the letter before printing.");
      else setLetter(data);
    }).catch(() => { if (!cancelled) setError("Could not load this letter. Return to the letters page and retry."); });
    return () => { cancelled = true; };
  }, [id]);
  return <main className={styles.printPage}>
    <div className={styles.printControls}><a href="/jobs/letters">← Cover letters</a><button className="primary" onClick={() => window.print()} disabled={!letter}>Print / save as PDF</button></div>
    {error ? <p role="alert">{error}</p> : letter ? <article className={styles.printText}>{letter.text}</article> : <p role="status">Loading approved letter…</p>}
  </main>;
}
