# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Real Groq decisions and real Wikipedia browsing inside a temporary E2B desktop."""
# Learn: Import argparse: parses the explicit command-line options for this demo.
import argparse
# Learn: Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Learn: Import os: reads process environment/configuration and OS facilities.
import os

# Learn: From crescendo_agent.local_env, import load_local_env (loads root .env values without replacing
# existing process values).
from crescendo_agent.local_env import load_local_env
# Learn: From crescendo_agent.e2b_desktop, import open_e2b_desktop (owns restricted sandbox setup, browser
# connection, and cleanup).
from crescendo_agent.e2b_desktop import open_e2b_desktop
# Learn: From crescendo_agent.groq_model, import GroqModel (adapts text transcripts and tools to Groq
# requests).
from crescendo_agent.groq_model import GroqModel
# Learn: From crescendo_agent.loop, import run_agent (runs the bounded text observation/action loop).
from crescendo_agent.loop import run_agent
# Learn: From crescendo_security.policy, import TaskGrant (holds the task identity and immutable tool/host
# allowlists).
from crescendo_security.policy import TaskGrant


# Learn: Define main(). The body runs when called, not when defined.
def main():
    # Learn: Call load_local_env with no arguments.
    load_local_env()
    # Learn: Set parser to argparse.ArgumentParser(description=__doc__); the command-line argument parser.
    parser = argparse.ArgumentParser(description=__doc__)
    # Learn: Declare this CLI option, its type/default, and help text on parser; inputs: '--trace'.
    parser.add_argument("--trace", action="store_true", help="Print the recorded transcript after desktop cleanup.")
    # Learn: Declare this CLI option, its type/default, and help text on parser; inputs: '--question'.
    parser.add_argument("--question", default="tell me the capital of Massachusetts",
                        # Learn: Pass keyword help = 'Research question for the Boston page.'.
                        help="Research question for the Boston page.")
    # Learn: Set args to parser.parse_args(); the arguments for the current operation. Parse command-line
    # values and reject unsupported argument syntax.
    args = parser.parse_args()
    # Learn: Iterate over the tuple ('GROQ_API_KEY', 'E2B_API_KEY') (positional values), binding name for
    # each item.
    for name in ("GROQ_API_KEY", "E2B_API_KEY"):
        # Learn: Take this branch only if not (os.environ[name] with None as the missing-key default).
        if not os.environ.get(name):
            # Learn: Raise SystemExit(f'Set {name} in your shell first.') to stop the normal path.
            raise SystemExit(f"Set {name} in your shell first.")
    # Learn: Set wiki to 'https://en.wikipedia.org/wiki/Boston'.
    wiki = "https://en.wikipedia.org/wiki/Boston"
    # Learn: Set grant to TaskGrant('groq-e2b-demo', frozenset({'navigate', 'search_page', 'finish'}),
    # frozenset({'en.wikipedia.org'})); the task identity and fixed tool/host permissions; model output
    # cannot expand these.
    grant = TaskGrant("groq-e2b-demo", frozenset({"navigate", "search_page", "finish"}),
                      # Learn: Call frozenset with the arguments shown.
                      frozenset({"en.wikipedia.org"}))
    # Learn: Set model to GroqModel(os.environ.get('GROQ_MODEL', 'openai/gpt-oss-120b')); the provider
    # adapter or scripted test model used to propose actions.
    model = GroqModel(os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"))
    # Learn: Enter open_e2b_desktop(grant) as desktop. The context manager controls setup/exit; inspect it
    # for the actual cleanup behavior.
    with open_e2b_desktop(grant) as desktop:
        # Learn: Set result to run_agent(f'Read {wiki} and {args.question}. Cite your source.', grant,
        # desktop, model, max_steps=5, deadline_seconds=120); the operation outcome for subsequent checks or
        # reporting.
        result = run_agent(
            # Learn: Supply literal text 'Read '; adjacent string literals are concatenated without adding
            # whitespace.
            f"Read {wiki} and {args.question}. Cite your source.",
            # Learn: Pass keyword max_steps = 5.
            grant, desktop, model, max_steps=5, deadline_seconds=120,
        # Learn: Close the argument list for run_agent; the grouped expression remains one call.
        )
        # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
        # 'Status:', result.status.
        print("Status:", result.status)
        # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
        # 'Answer:', result.answer.
        print("Answer:", result.answer)
        # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
        # 'Sources:', result.sources.
        print("Sources:", result.sources)
        # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
        # 'Visited:', desktop.visited.
        print("Visited:", desktop.visited)
        # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
        # 'Denied tool calls:', the number of items/characters in result.denied.
        print("Denied tool calls:", len(result.denied))
        # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
        # 'Blocked browser requests:', the number of items/characters in desktop.blocked_requests.
        print("Blocked browser requests:", len(desktop.blocked_requests))
    # Learn: Take this branch only if args.trace.
    if args.trace:
        # Page text is untrusted. JSON escaping keeps terminal control characters
        # as visible text; never dump SDK clients, credentials, or environment.
        # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
        # 'Recorded trace (observations are untrusted; actions are proposals):'.
        print("Recorded trace (observations are untrusted; actions are proposals):")
        # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
        # json.dumps({'model': model.model, 'status': result.status, 'entries': [{'index': index, 'kind':
        # entry.kind, 'text': entry.text} for ....
        print(json.dumps({
            # Learn: Define this named mapping field: "model": model.model,. The key selects the
            # schema/configuration value.
            "model": model.model,
            # Learn: Define this named mapping field: "status": result.status,. The key selects the
            # schema/configuration value.
            "status": result.status,
            # Learn: Define this named mapping field: "entries": [. The key selects the schema/configuration
            # value.
            "entries": [
                # Learn: Add this key/value entry to the surrounding dictionary: {"index": index, "kind":
                # entry.kind, "text": entry.text}.
                {"index": index, "kind": entry.kind, "text": entry.text}
                # Learn: Pass keyword start = 1.
                for index, entry in enumerate(result.transcript, start=1)
            # Learn: Close this dict literal; delimiters group the values into one object.
            ],
        # Learn: Pass keyword indent = 2.
        }, indent=2))


# Learn: Take this branch only if __name__ equals '__main__'. The __main__ guard keeps imports from
# launching the CLI.
if __name__ == "__main__":
    # Learn: Call main with no arguments.
    main()
