import type { ReactNode } from "react";
import styles from "./jobs.module.css";

export function JobShell({ active, children }: { active: "search" | "letters" | "applications"; children: ReactNode }) {
  return <div className={styles.jobWorkspace}>
    <header className={styles.jobHeader}>
      <a className="brand" href="/jobs" aria-label="AgentCrescendo home"><span className="brandmark">≋</span> Agent<span>Crescendo</span></a>
      <nav aria-label="Workspace">
        <a aria-current={active === "search" ? "page" : undefined} href="/jobs">Find jobs</a>
        <a aria-current={active === "letters" ? "page" : undefined} href="/jobs/letters">Why company?</a>
        <a aria-current={active === "applications" ? "page" : undefined} href="/jobs/applications">Applications</a>
      </nav>
      <span className={styles.localLabel}>Local workspace</span>
    </header>
    <main className={styles.jobMain}>
      {children}
    </main>
  </div>;
}

export function ProcessSteps({ current, includeWriter = false }: { current: number; includeWriter?: boolean }) {
  const steps = ["Find jobs", "Pick up to 3", "Review inputs", includeWriter ? "Draft live" : "Draft letters", "Review & approve", ...(includeWriter ? ["Final PDF"] : [])];
  return <ol className={styles.process} aria-label="Job search process">
    {steps.map((step, i) =>
      <li key={step} className={i < current ? styles.stepDone : i === current ? styles.stepCurrent : ""}
          aria-current={i === current ? "step" : undefined}><span aria-hidden="true">{i < current ? "✓" : i + 1}</span>{step}</li>)}
  </ol>;
}
