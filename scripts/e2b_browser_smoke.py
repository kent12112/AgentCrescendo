# Learn: Document this module, class, or function with a docstring; it is not an action or a model
# instruction.
"""Model-free live browser check. Creates one metered E2B desktop."""
# Learn: Import os: reads process environment/configuration and OS facilities.
import os
# Learn: From uuid, import uuid4 (generates independent random UUID identifiers).
from uuid import uuid4

# Learn: From crescendo_agent.local_env, import load_local_env (loads root .env values without replacing
# existing process values).
from crescendo_agent.local_env import load_local_env
# Learn: From crescendo_agent.e2b_desktop, import open_e2b_desktop (owns restricted sandbox setup, browser
# connection, and cleanup).
from crescendo_agent.e2b_desktop import open_e2b_desktop
# Learn: From crescendo_security.policy, import TaskGrant (holds the task identity and immutable tool/host
# allowlists).
from crescendo_security.policy import TaskGrant


# Learn: Define run_smoke(sandbox_type). The body runs when called, not when defined.
def run_smoke(sandbox_type):
    # Learn: Set created to a new list (empty).
    created = []

    # Learn: Define TrackedFactory. Indented methods and attributes belong to this class.
    class TrackedFactory:
        # Learn: Apply staticmethod to the following function/class at definition time.
        @staticmethod
        # Learn: Define create(). The body runs when called, not when defined.
        def create(**kwargs):
            # Learn: Set sandbox to sandbox_type.create(**kwargs); the E2B desktop instance; its owner must
            # attempt cleanup. Create the requested SDK resource or provider response.
            sandbox = sandbox_type.create(**kwargs)
            # Learn: Append one item to the ordered collection on created; inputs: sandbox.
            created.append(sandbox)
            # Learn: Return sandbox to the caller and stop this function.
            return sandbox

    # Learn: Set url to 'https://en.wikipedia.org/wiki/Boston'; the destination or current page address.
    url = "https://en.wikipedia.org/wiki/Boston"
    # Learn: Set grant to TaskGrant(str(uuid4()), frozenset({'navigate'}), frozenset({'en.wikipedia.org'}));
    # the task identity and fixed tool/host permissions; model output cannot expand these.
    grant = TaskGrant(str(uuid4()), frozenset({"navigate"}), frozenset({"en.wikipedia.org"}))
    # Learn: Try the following operations; matching except clauses handle failures. The finally block runs
    # on every exit.
    try:
        # Learn: Enter open_e2b_desktop(grant, sandbox_type=TrackedFactory) as desktop. The context manager
        # controls setup/exit; inspect it for the actual cleanup behavior.
        with open_e2b_desktop(grant, sandbox_type=TrackedFactory) as desktop:
            # Learn: Open the requested destination through the desktop adapter on desktop; inputs: url.
            desktop.navigate(url)
            # Learn: Set observation to desktop.observe().
            observation = desktop.observe()
            # Learn: Take this branch only if observation.url does not equal url OR 'Boston' is not in
            # observation.text.
            if observation.url != url or "Boston" not in observation.text:
                # Learn: Raise RuntimeError('Permitted page did not produce the expected Boston
                # observation.') to stop the normal path.
                raise RuntimeError("Permitted page did not produce the expected Boston observation.")
            # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
            # 'PASS: real browser loaded Wikipedia and observed Boston text'.
            print("PASS: real browser loaded Wikipedia and observed Boston text")
            # Learn: Iterate over the tuple ('https://example.com/', 'https://127.0.0.1:8000/runs')
            # (positional values), binding forbidden for each item.
            for forbidden in ("https://example.com/", "https://127.0.0.1:8000/runs"):
                # Learn: Try the following operations; matching except clauses handle failures.
                try:
                    # Learn: Open the requested destination through the desktop adapter on desktop; inputs:
                    # forbidden.
                    desktop.navigate(forbidden)
                # Learn: Handle ValueError; unmatched errors propagate.
                except ValueError:
                    # Learn: No operation: this body intentionally needs no executable statement.
                    pass
                # Learn: Run this alternative only when the preceding conditional did not select its first
                # branch.
                else:
                    # Learn: Raise RuntimeError('Forbidden navigation was not denied by the gateway.') to
                    # stop the normal path.
                    raise RuntimeError("Forbidden navigation was not denied by the gateway.")
            # Learn: Take this branch only if desktop.visited does not equal a new list containing url.
            if desktop.visited != [url]:
                # Learn: Raise RuntimeError('Unexpected navigation history.') to stop the normal path.
                raise RuntimeError("Unexpected navigation history.")
            # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
            # 'PASS: gateway denied unlisted and loopback destinations before navigation'.
            print("PASS: gateway denied unlisted and loopback destinations before navigation")
    # Learn: Always run cleanup, whether the operation succeeds, returns, or raises.
    finally:
        # The adapter has already attempted kill() when its context exits.
        # Learn: Iterate over created, binding sandbox for each item.
        for sandbox in created:
            # Learn: Take this branch only if sandbox.is_running(request_timeout=10).
            if sandbox.is_running(request_timeout=10):
                # Retry cleanup, but still fail the check: initial cleanup failed.
                # Learn: Ask E2B to terminate the sandbox; successful return alone is not independent
                # termination evidence on sandbox.
                sandbox.kill()
                # Learn: Raise RuntimeError('Desktop remained running after adapter cleanup; kill retried.')
                # to stop the normal path.
                raise RuntimeError("Desktop remained running after adapter cleanup; kill retried.")
            # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs:
            # 'PASS: provider reports desktop no longer running after cleanup'.
            print("PASS: provider reports desktop no longer running after cleanup")
    # Learn: Display diagnostic/result text without treating it as verified model evidence; inputs: 'No
    # model calls. Gateway checks do not prove network-level isolation.'.
    print("No model calls. Gateway checks do not prove network-level isolation.")


# Learn: Define main(). The body runs when called, not when defined.
def main():
    # Learn: Call load_local_env with no arguments.
    load_local_env()
    # Learn: Take this branch only if not (os.environ['E2B_API_KEY'] with None as the missing-key default).
    if not os.environ.get("E2B_API_KEY"):
        # Learn: Raise SystemExit('Set E2B_API_KEY in this terminal. This check uses E2B resources.') to
        # stop the normal path.
        raise SystemExit("Set E2B_API_KEY in this terminal. This check uses E2B resources.")
    # Learn: From e2b_desktop, import Sandbox (creates the provider desktop and exposes its
    # lifecycle/control API).
    from e2b_desktop import Sandbox

    # Learn: Call run_smoke with the arguments shown.
    run_smoke(Sandbox)


# Learn: Take this branch only if __name__ equals '__main__'. The __main__ guard keeps imports from
# launching the CLI.
if __name__ == "__main__":
    # Learn: Call main with no arguments.
    main()
