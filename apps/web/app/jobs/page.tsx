import type { Metadata } from "next";
import JobSearch from "../../features/jobs/job-search";

export const metadata: Metadata = { title: "Job search — AgentCrescendo" };

export default function JobsPage() {
  return <JobSearch />;
}
