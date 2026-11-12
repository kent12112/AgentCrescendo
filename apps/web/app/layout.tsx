import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentCrescendo — Your agent workspace",
  description: "A workspace for agents to coordinate everyday tasks.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
