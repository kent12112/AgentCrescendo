import type { Metadata } from "next";
import LetterWorkspace from "../../../features/jobs/letter-workspace";

export const metadata: Metadata = { title: "Cover letters — AgentCrescendo" };

export default function LettersPage() { return <LetterWorkspace />; }
