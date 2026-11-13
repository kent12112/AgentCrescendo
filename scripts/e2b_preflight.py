"""Explicit cloud-resource smoke check; requires E2B_API_KEY."""
import json
import os

from crescendo_agent.e2b_preflight import run_preflight


def main():
    if not os.environ.get("E2B_API_KEY"):
        raise SystemExit("Set E2B_API_KEY in your shell first. This check uses E2B resources.")
    results = run_preflight()
    print(json.dumps(results, indent=2))
    if not results["allowed_wikipedia"]["reachable"]:
        raise SystemExit("Wikipedia was unreachable; permitted browsing is not verified.")
    if any(results[name]["reachable"] for name in (
        "unlisted_example", "private_tcp",
    )):
        raise SystemExit("A disallowed destination was reachable; do not enable browsing.")
    if results["metadata_tcp"]["reachable"]:
        print("Metadata TCP accepted: consistent with E2B's sandbox-local MMDS exception.")
        print("This probe does not identify the service or read metadata.")
    print("External probes matched expectations; full network isolation remains unverified.")
    print("Connection failures alone do not prove firewall enforcement.")


if __name__ == "__main__":
    main()
