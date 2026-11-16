"""Model-free live browser check. Creates one metered E2B desktop."""
# Import os: reads process environment/configuration and OS facilities.
import os
# Import from uuid: uuid4 (generates independent random UUID identifiers).
from uuid import uuid4

# Import from crescendo_agent.local_env: load_local_env (loads root .env values without replacing
# existing process values).
from crescendo_agent.local_env import load_local_env
# Import from crescendo_agent.e2b_desktop: open_e2b_desktop (owns restricted sandbox setup, browser
# connection, and cleanup).
from crescendo_agent.e2b_desktop import open_e2b_desktop
# Import from crescendo_security.policy: TaskGrant (holds the task identity and immutable tool/host
# allowlists).
from crescendo_security.policy import TaskGrant


# Define run_smoke with parameters sandbox_type.
def run_smoke(sandbox_type):
    # Set created to an empty list.
    created = []

    # Define TrackedFactory.
    class TrackedFactory:
        # Apply staticmethod to the following function/class at definition time.
        @staticmethod
        # Define create with no parameters.
        def create(**kwargs):
            # Set sandbox to sandbox_type.create(**kwargs).
            sandbox = sandbox_type.create(**kwargs)
            # Append sandbox to created.
            created.append(sandbox)
            # Return sandbox.
            return sandbox

    # Set url to 'https://en.wikipedia.org/wiki/Boston'.
    url = "https://en.wikipedia.org/wiki/Boston"
    # Set grant to TaskGrant(str(uuid4()), frozenset({'navigate'}),
    # frozenset({'en.wikipedia.org'})).
    grant = TaskGrant(str(uuid4()), frozenset({"navigate"}), frozenset({"en.wikipedia.org"}))
    # Try the following operations; matching except clauses handle failures. The finally block runs
    # on every exit.
    try:
        # Use open_e2b_desktop(grant, sandbox_type=TrackedFactory) as desktop; leave the context and
        # run its cleanup when this block ends.
        with open_e2b_desktop(grant, sandbox_type=TrackedFactory) as desktop:
            # Call desktop.navigate with url.
            desktop.navigate(url)
            # Set observation to desktop.observe().
            observation = desktop.observe()
            # Check whether observation.url does not equal url or 'Boston' is not in
            # observation.text.
            if observation.url != url or "Boston" not in observation.text:
                # Raise RuntimeError('Permitted page did not produce the expected Boston
                # observation.') to stop the normal path.
                raise RuntimeError("Permitted page did not produce the expected Boston observation.")
            # Print 'PASS: real browser loaded Wikipedia and observed Boston text'.
            print("PASS: real browser loaded Wikipedia and observed Boston text")
            # Iterate over the tuple ('https://example.com/', 'https://127.0.0.1:8000/runs')
            # (positional values), binding forbidden for each item.
            for forbidden in ("https://example.com/", "https://127.0.0.1:8000/runs"):
                # Try the following operations; matching except clauses handle failures.
                try:
                    # Call desktop.navigate with forbidden.
                    desktop.navigate(forbidden)
                # Handle ValueError; unmatched errors propagate.
                except ValueError:
                    pass
                # Run this alternative only when the preceding conditional did not select its first
                # branch.
                else:
                    # Raise RuntimeError('Forbidden navigation was not denied by the gateway.') to
                    # stop the normal path.
                    raise RuntimeError("Forbidden navigation was not denied by the gateway.")
            # Check whether desktop.visited does not equal [url].
            if desktop.visited != [url]:
                # Raise RuntimeError('Unexpected navigation history.') to stop the normal path.
                raise RuntimeError("Unexpected navigation history.")
            # Print 'PASS: gateway denied unlisted and loopback destinations before navigation'.
            print("PASS: gateway denied unlisted and loopback destinations before navigation")
    # Always run cleanup, whether the operation succeeds, returns, or raises.
    finally:
        # The adapter has already attempted kill() when its context exits.
        # Iterate over created, binding sandbox for each item.
        for sandbox in created:
            # Check whether sandbox.is_running(request_timeout=10).
            if sandbox.is_running(request_timeout=10):
                # Retry cleanup, but still fail the check: initial cleanup failed.
                # Ask the provider to terminate sandbox.
                sandbox.kill()
                # Raise RuntimeError('Desktop remained running after adapter cleanup; kill
                # retried.') to stop the normal path.
                raise RuntimeError("Desktop remained running after adapter cleanup; kill retried.")
            # Print 'PASS: provider reports desktop no longer running after cleanup'.
            print("PASS: provider reports desktop no longer running after cleanup")
    # Print 'No model calls. Gateway checks do not prove network-level isolation.'.
    print("No model calls. Gateway checks do not prove network-level isolation.")


# Define main with no parameters.
def main():
    # Call load_local_env with no arguments.
    load_local_env()
    # Check whether not (os.environ['E2B_API_KEY'], or None if absent).
    if not os.environ.get("E2B_API_KEY"):
        # Raise SystemExit('Set E2B_API_KEY in this terminal. This check uses E2B resources.') to
        # stop the normal path.
        raise SystemExit("Set E2B_API_KEY in this terminal. This check uses E2B resources.")
    # Import from e2b_desktop: Sandbox (creates the provider desktop and exposes its
    # lifecycle/control API).
    from e2b_desktop import Sandbox

    # Call run_smoke with Sandbox.
    run_smoke(Sandbox)


# Check whether __name__ equals '__main__'.
if __name__ == "__main__":
    # Call main with no arguments.
    main()
