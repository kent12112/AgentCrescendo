// Learn: Import these module exports for use below: import Workspace from "../features/drafts/workspace";. Named imports use braces; a default import has no braces.
import Workspace from "../features/drafts/workspace";

// Learn: Define a function/component: export default function Page() {. Its body executes when called/rendered.
export default function Page() {
  // Learn JSX line 1: Render the draft workspace client component.
  return <Workspace />;
// Learn: Close the surrounding object, function, call, or type expression; delimiters determine which construct ends here.
}
