// Import types { Metadata } from "next"; these are removed from emitted JavaScript.
import type { Metadata } from "next";
// Import these module exports for use below: import "./globals.css";. Named imports use braces; a
// default import has no braces.
import "./globals.css";

// Define export const metadata: Metadata = {
export const metadata: Metadata = {
  // Set this named object/configuration property: title: "AgentCrescendo — Your agent workspace",.
  // The receiving API determines how the value is used.
  title: "AgentCrescendo — Your agent workspace",
  // Set this named object/configuration property: description: "A workspace for agents to
  // coordinate everyday tasks.",. The receiving API determines how the value is used.
  description: "A workspace for agents to coordinate everyday tasks.",
};

// Define export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>)
// {
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  // JSX line 1: Render the document root. Expressions in braces read current props/state.
  return <html lang="en"><body>{children}</body></html>;
}
