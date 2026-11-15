// Learn: Import compile-time types only; this import is erased from emitted JavaScript: import type { Metadata } from "next";.
import type { Metadata } from "next";
// Learn: Import these module exports for use below: import "./globals.css";. Named imports use braces; a default import has no braces.
import "./globals.css";

// Learn: Declare this block-scoped binding: export const metadata: Metadata = {. const prevents reassignment of the binding, not mutation of an object it references.
export const metadata: Metadata = {
  // Learn: Set this named object/configuration property: title: "AgentCrescendo — Your agent workspace",. The receiving API determines how the value is used.
  title: "AgentCrescendo — Your agent workspace",
  // Learn: Set this named object/configuration property: description: "A workspace for agents to coordinate everyday tasks.",. The receiving API determines how the value is used.
  description: "A workspace for agents to coordinate everyday tasks.",
// Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
};

// Learn: Define a function/component: export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {. Its body executes when called/rendered.
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  // Learn JSX line 1: Render the document root. Expressions in braces read current props/state.
  return <html lang="en"><body>{children}</body></html>;
// Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
}
