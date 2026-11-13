"""Model-free live browser check. Creates one metered E2B desktop."""
import os
from uuid import uuid4

from crescendo_agent.e2b_desktop import open_e2b_desktop
from crescendo_security.policy import TaskGrant


def run_smoke(sandbox_type):
    created = []

    class TrackedFactory:
        @staticmethod
        def create(**kwargs):
            sandbox = sandbox_type.create(**kwargs)
            created.append(sandbox)
            return sandbox

    url = "https://en.wikipedia.org/wiki/Boston"
    grant = TaskGrant(str(uuid4()), frozenset({"navigate"}), frozenset({"en.wikipedia.org"}))
    try:
        with open_e2b_desktop(grant, sandbox_type=TrackedFactory) as desktop:
            desktop.navigate(url)
            observation = desktop.observe()
            if observation.url != url or "Boston" not in observation.text:
                raise RuntimeError("Permitted page did not produce the expected Boston observation.")
            print("PASS: real browser loaded Wikipedia and observed Boston text")
            for forbidden in ("https://example.com/", "https://127.0.0.1:8000/runs"):
                try:
                    desktop.navigate(forbidden)
                except ValueError:
                    pass
                else:
                    raise RuntimeError("Forbidden navigation was not denied by the gateway.")
            if desktop.visited != [url]:
                raise RuntimeError("Unexpected navigation history.")
            print("PASS: gateway denied unlisted and loopback destinations before navigation")
    finally:
        # The adapter has already attempted kill() when its context exits.
        for sandbox in created:
            if sandbox.is_running(request_timeout=10):
                # Retry cleanup, but still fail the check: initial cleanup failed.
                sandbox.kill()
                raise RuntimeError("Desktop remained running after adapter cleanup; kill retried.")
            print("PASS: provider reports desktop no longer running after cleanup")
    print("No model calls. Gateway checks do not prove network-level isolation.")


def main():
    if not os.environ.get("E2B_API_KEY"):
        raise SystemExit("Set E2B_API_KEY in this terminal. This check uses E2B resources.")
    from e2b_desktop import Sandbox

    run_smoke(Sandbox)


if __name__ == "__main__":
    main()
