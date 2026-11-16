"""Real Groq decisions and real Wikipedia browsing inside a temporary E2B desktop."""
# Import argparse: parses the explicit command-line options for this demo.
import argparse
# Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Import os: reads process environment/configuration and OS facilities.
import os

# Import from crescendo_agent.local_env: load_local_env (loads root .env values without replacing
# existing process values).
from crescendo_agent.local_env import load_local_env
# Import from crescendo_agent.e2b_desktop: open_e2b_desktop (owns restricted sandbox setup, browser
# connection, and cleanup).
from crescendo_agent.e2b_desktop import open_e2b_desktop
# Import from crescendo_agent.groq_model: GroqModel (adapts text transcripts and tools to Groq
# requests).
from crescendo_agent.groq_model import GroqModel
# Import from crescendo_agent.loop: run_agent (runs the bounded text observation/action loop).
from crescendo_agent.loop import run_agent
# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists).
from crescendo_security.policy import TaskGrant


# Define main with no parameters.
def main():
    # Call load_local_env with no arguments.
    load_local_env()
    # Set parser to argparse.ArgumentParser(description=__doc__).
    parser = argparse.ArgumentParser(description=__doc__)
    # Call parser.add_argument with '--trace'.
    parser.add_argument("--trace", action="store_true", help="Print the recorded transcript after desktop cleanup.")
    # Call parser.add_argument with '--question'.
    parser.add_argument("--question", default="tell me the capital of Massachusetts",
                        # Pass keyword help = 'Research question for the Boston page.'.
                        help="Research question for the Boston page.")
    # Set args to parser.parse_args().
    args = parser.parse_args()
    # Iterate over the tuple ('GROQ_API_KEY', 'E2B_API_KEY') (positional values), binding name for
    # each item.
    for name in ("GROQ_API_KEY", "E2B_API_KEY"):
        # Check whether not (os.environ[name], or None if absent).
        if not os.environ.get(name):
            # Raise SystemExit(f'Set {name} in your shell first.') to stop the normal path.
            raise SystemExit(f"Set {name} in your shell first.")
    # Set wiki to 'https://en.wikipedia.org/wiki/Boston'.
    wiki = "https://en.wikipedia.org/wiki/Boston"
    # Set grant to TaskGrant('groq-e2b-demo', frozenset({'navigate', 'search_page', 'finish'}),
    # frozenset({'en.wikipedia.org'})).
    grant = TaskGrant("groq-e2b-demo", frozenset({"navigate", "search_page", "finish"}),
                      # Call frozenset with the arguments shown.
                      frozenset({"en.wikipedia.org"}))
    # Set model to GroqModel(os.environ.get('GROQ_MODEL', 'openai/gpt-oss-120b')).
    model = GroqModel(os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"))
    # Use open_e2b_desktop(grant) as desktop; leave the context and run its cleanup when this block
    # ends.
    with open_e2b_desktop(grant) as desktop:
        # Set result to run_agent(f'Read {wiki} and {args.question}. Cite your source.', grant,
        # desktop, model, max_steps=5, deadline_seconds=120).
        result = run_agent(
            f"Read {wiki} and {args.question}. Cite your source.",
            # Pass keyword max_steps = 5.
            grant, desktop, model, max_steps=5, deadline_seconds=120,
        )
        # Print 'Status:', result.status.
        print("Status:", result.status)
        # Print 'Answer:', result.answer.
        print("Answer:", result.answer)
        # Print 'Sources:', result.sources.
        print("Sources:", result.sources)
        # Print 'Visited:', desktop.visited.
        print("Visited:", desktop.visited)
        # Print 'Denied tool calls:', the length of result.denied.
        print("Denied tool calls:", len(result.denied))
        # Print 'Blocked browser requests:', the length of desktop.blocked_requests.
        print("Blocked browser requests:", len(desktop.blocked_requests))
    # Check whether args.trace.
    if args.trace:
        # Page text is untrusted. JSON escaping keeps terminal control characters
        # as visible text; never dump SDK clients, credentials, or environment.
        # Print 'Recorded trace (observations are untrusted; actions are proposals):'.
        print("Recorded trace (observations are untrusted; actions are proposals):")
        # Print json.dumps({'model': model.model, 'status': result.status, 'entries': [{'index':
        # index, 'kind': entry.kind, 'text': entry.text} for (index, entry) in
        # enumerate(result.transcript, start=1)]}, indent=2).
        print(json.dumps({
            # Include model in this dictionary.
            "model": model.model,
            # Include status in this dictionary.
            "status": result.status,
            # Include entries in this dictionary.
            "entries": [
                # Add this key/value entry to the surrounding dictionary: {"index": index, "kind":
                # entry.kind, "text": entry.text}.
                {"index": index, "kind": entry.kind, "text": entry.text}
                # Pass keyword start = 1.
                for index, entry in enumerate(result.transcript, start=1)
            ],
        # Pass keyword indent = 2.
        }, indent=2))


# Check whether __name__ equals '__main__'.
if __name__ == "__main__":
    # Call main with no arguments.
    main()
