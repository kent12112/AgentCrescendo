# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Explicit cloud-resource smoke check; requires E2B_API_KEY."""
# Learn: Import json: encodes/decodes JSON for tool arguments, transcripts, or HTTP payloads.
import json
# Learn: Import os: reads process environment/configuration and OS facilities.
import os

# Learn: From crescendo_agent.local_env, import load_local_env (loads root .env values without replacing
# existing process values).
from crescendo_agent.local_env import load_local_env
# Learn: From crescendo_agent.e2b_preflight, import run_preflight (a dependency used below).
from crescendo_agent.e2b_preflight import run_preflight


# Learn: Define main(). The body runs when called, not when defined.
def main():
    # Learn: Call load_local_env with no arguments.
    load_local_env()
    # Learn: Take this branch only if not (os.environ['E2B_API_KEY'] with None as the missing-key default).
    if not os.environ.get("E2B_API_KEY"):
        # Learn: Raise SystemExit('Set E2B_API_KEY in your shell first. This check uses E2B resources.') to
        # stop the normal path.
        raise SystemExit("Set E2B_API_KEY in your shell first. This check uses E2B resources.")
    # Learn: Set results to run_preflight().
    results = run_preflight()
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
    # json.dumps(results, indent=2).
    print(json.dumps(results, indent=2))
    # Learn: Take this branch only if not (results['allowed_wikipedia']['reachable']).
    if not results["allowed_wikipedia"]["reachable"]:
        # Learn: Raise SystemExit('Wikipedia was unreachable; permitted browsing is not verified.') to stop
        # the normal path.
        raise SystemExit("Wikipedia was unreachable; permitted browsing is not verified.")
    # Learn: Take this branch only if any((results[name]['reachable'] for name in ('unlisted_example',
    # 'private_tcp'))).
    if any(results[name]["reachable"] for name in (
        # Learn: Supply literal text 'unlisted_example'; adjacent string literals are concatenated without
        # adding whitespace.
        "unlisted_example", "private_tcp",
    # Learn: Finish the function signature; -> declares the return type and the following indented lines
    # form the function body.
    )):
        # Learn: Raise SystemExit('A disallowed destination was reachable; do not enable browsing.') to stop
        # the normal path.
        raise SystemExit("A disallowed destination was reachable; do not enable browsing.")
    # Learn: Take this branch only if results['metadata_tcp']['reachable'].
    if results["metadata_tcp"]["reachable"]:
        # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
        # "Metadata TCP accepted: consistent with E2B's sandbox-local MMDS exception.".
        print("Metadata TCP accepted: consistent with E2B's sandbox-local MMDS exception.")
        # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
        # 'This probe does not identify the service or read metadata.'.
        print("This probe does not identify the service or read metadata.")
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
    # 'External probes matched expectations; full network isolation remains unverified.'.
    print("External probes matched expectations; full network isolation remains unverified.")
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
    # 'Connection failures alone do not prove firewall enforcement.'.
    print("Connection failures alone do not prove firewall enforcement.")


# Learn: Take this branch only if __name__ equals '__main__'. The __main__ guard keeps imports from
# launching the CLI.
if __name__ == "__main__":
    # Learn: Call main with no arguments.
    main()
