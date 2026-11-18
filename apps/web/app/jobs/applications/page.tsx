import type { Metadata } from "next";
import ApplicationTracker from "../../../features/jobs/application-tracker";

export const metadata: Metadata = { title: "Applications — AgentCrescendo" };

export default function ApplicationsPage() {
  return <ApplicationTracker />;
}
