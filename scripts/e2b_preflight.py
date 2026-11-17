"""Explicit cloud-resource smoke check; requires E2B_API_KEY."""
# Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Import os: reads process environment/configuration and OS facilities.
import os
# Import sys: reads the --public command-line flag.
import sys

# Import from crescendo_agent.local_env: load_local_env (loads root .env values without replacing
# existing process values).
from crescendo_agent.local_env import load_local_env
# Import from crescendo_agent.e2b_preflight: evaluate_preflight (judges the raw results);
# run_preflight (creates the desktop, probes, and destroys it).
from crescendo_agent.e2b_preflight import (
    evaluate_preflight, evaluate_public_preflight, run_preflight, run_public_preflight,
)


# Define main with no parameters.
def main():
    # Call load_local_env with no arguments.
    load_local_env()
    # Check whether not (os.environ['E2B_API_KEY'], or None if absent).
    if not os.environ.get("E2B_API_KEY"):
        # Raise SystemExit('Set E2B_API_KEY in your shell first. This check uses E2B resources.') to
        # stop the normal path.
        raise SystemExit("Set E2B_API_KEY in your shell first. This check uses E2B resources.")
    # --public tests public-web mode (W1X-F02): no allowlist, private ranges denied.
    public = "--public" in sys.argv[1:]
    # Set results to the chosen mode's raw probe results.
    results = run_public_preflight() if public else run_preflight()
    # Print json.dumps(results, indent=2) so the raw evidence is always visible.
    print(json.dumps(results, indent=2))
    # Set verdict to the chosen mode's judgment.
    verdict = evaluate_public_preflight(results) if public else evaluate_preflight(results)
    # Print each informational note.
    for note in verdict.notes:
        # Print note.
        print(note)
    # Check whether the verdict failed.
    if not verdict.passed:
        # Raise SystemExit with every failure, one per line, to stop with a nonzero exit status.
        raise SystemExit("\n".join(verdict.failures))
    # Print 'External probes matched expectations; full network isolation remains unverified.'.
    print("External probes matched expectations; full network isolation remains unverified.")
    # Print 'Connection failures alone do not prove firewall enforcement.'.
    print("Connection failures alone do not prove firewall enforcement.")


# Check whether __name__ equals '__main__'.
if __name__ == "__main__":
    # Call main with no arguments.
    main()
