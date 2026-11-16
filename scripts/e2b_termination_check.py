"""Live check that E2B really destroys our desktops (plan W1-F11).

Creates up to three short metered desktops. No model calls are made.

Scenarios:
  normal   The with-block finishes; the adapter's `finally` calls kill().
  failure  A deliberate exception escapes the with-block; the same `finally` runs.
  abandon  A child process opens a desktop, then exits with os._exit(), which skips
           every `finally`. Only E2B's own lifetime timer can remove that desktop.

Every result is checked by asking E2B's control-plane API for the sandbox by ID.
That is stronger than `is_running()`, which only pings a health endpoint inside the
guest: "no answer" there could also mean a network problem, not a destroyed desktop.
"""
# Read command-line options such as --scenario.
import argparse
# Read environment variables such as E2B_API_KEY and E2B_DEBUG.
import os
# Find the sandbox ID line in the child's printed output.
import re
# Start the child process for the abandon scenario.
import subprocess
# Find the current Python interpreter so the child uses the same virtual environment.
import sys
# Measure waiting time and pause between provider lookups.
import time
# Record wall-clock times in UTC so they compare with E2B's timestamps.
from datetime import datetime, timezone
# Generate a fresh task ID for each grant.
from uuid import uuid4

# Load E2B_API_KEY from the project .env without overriding the terminal's values.
from crescendo_agent.local_env import load_local_env
# The real adapter: creates the restricted desktop and kills it when the block exits.
from crescendo_agent.e2b_desktop import open_e2b_desktop
# The task permission record: which tools and hosts this run may use.
from crescendo_security.policy import TaskGrant

# The one permitted page each scenario loads, so the desktop does real work before cleanup.
URL = "https://en.wikipedia.org/wiki/Boston"
# The shortest lifetime the adapter accepts; keeps the abandoned desktop's cost small.
ABANDON_LIFETIME_SECONDS = 60
# Extra time we allow E2B to act after the lifetime ends before calling it a failure.
ABANDON_GRACE_SECONDS = 120
# How long a normal kill() may take to show up in the control plane.
KILL_CONFIRM_SECONDS = 30
# The line format the child prints so the parent can learn which desktop to watch.
ID_LINE = re.compile(r"^SANDBOX_ID=(\S+)$", re.MULTILINE)


# The error raised on purpose in the failure scenario, so we catch only our own error.
class DeliberateFailure(RuntimeError):
    pass


def provider_state(api, sandbox_id):
    """Ask the control plane about one sandbox: 'gone', 'running', or 'paused'."""
    # Import the SDK's "this sandbox does not exist" error (a 404 from the API).
    from e2b import SandboxNotFoundException

    try:
        # GET /sandboxes/{id} on E2B's API, not on the desktop itself.
        info = api.get_info(sandbox_id)
    except SandboxNotFoundException:
        # The provider no longer knows this sandbox: it has been destroyed.
        return "gone"
    # Otherwise report the provider's state, e.g. "running" or "paused".
    return str(info.state.value if hasattr(info.state, "value") else info.state)


def wait_until_gone(api, sandbox_id, limit_seconds, *, poll_seconds=5,
                    clock=time.monotonic, sleep=time.sleep):
    """Poll until the sandbox is gone. Return seconds waited, or None at the limit."""
    # Remember when waiting started.
    start = clock()
    while True:
        # Ask the provider for the current state.
        state = provider_state(api, sandbox_id)
        # Report how long it took once the sandbox no longer exists.
        if state == "gone":
            return clock() - start
        # A paused sandbox is not destroyed; stop waiting and let the caller fail.
        if state == "paused" or clock() - start >= limit_seconds:
            return None
        # Wait a little before asking again.
        sleep(poll_seconds)


def confirm_gone(api, sandbox_id, label, limit_seconds, **wait_options):
    """Pass if the sandbox disappears in time; otherwise kill it and fail loudly."""
    waited = wait_until_gone(api, sandbox_id, limit_seconds, **wait_options)
    if waited is None:
        # Record what the provider last said, then clean up so the check does not leak cost.
        state = provider_state(api, sandbox_id)
        api.kill(sandbox_id)
        raise RuntimeError(f"{label}: sandbox {sandbox_id} still {state!r} after "
                           f"{limit_seconds}s; kill retried.")
    print(f"PASS {label}: provider reports sandbox {sandbox_id} gone "
          f"(confirmed after {waited:.0f}s of polling)", flush=True)
    return waited


def tracking_factory(api, created, *, announce=False):
    """Wrap Sandbox.create so we learn each new sandbox's ID."""
    class Tracked:
        @staticmethod
        def create(**kwargs):
            # Create the real desktop with the adapter's arguments.
            sandbox = api.create(**kwargs)
            # Keep it so the caller can check it after cleanup.
            created.append(sandbox)
            if announce:
                # The child prints its ID immediately, before slower browser setup.
                print(f"SANDBOX_ID={sandbox.sandbox_id}", flush=True)
            return sandbox
    return Tracked


def as_utc(moment):
    """Treat a timestamp without a time zone as UTC so it can be compared with now()."""
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def new_grant():
    """A grant that allows only navigation to Wikipedia."""
    return TaskGrant(str(uuid4()), frozenset({"navigate"}), frozenset({"en.wikipedia.org"}))


def load_page(desktop):
    """Do a little real work so cleanup happens after a used browser, not an idle one."""
    desktop.navigate(URL)
    observation = desktop.observe()
    if "Boston" not in observation.text:
        # Show the start of what loaded (e.g. a rate-limit page) to explain the failure.
        raise RuntimeError("Permitted page did not show the expected Boston text; page began: "
                           + repr(observation.text[:160]))


def run_normal(api, **wait_options):
    created = []
    # The adapter's finally block runs kill() when this block ends normally.
    with open_e2b_desktop(new_grant(), sandbox_type=tracking_factory(api, created)) as desktop:
        load_page(desktop)
    return confirm_gone(api, created[0].sandbox_id, "normal", KILL_CONFIRM_SECONDS, **wait_options)


def run_failure(api, **wait_options):
    created = []
    try:
        with open_e2b_desktop(new_grant(), sandbox_type=tracking_factory(api, created)) as desktop:
            load_page(desktop)
            # Fail on purpose after setup, the way an agent bug or model error would.
            raise DeliberateFailure("deliberate failure inside the desktop block")
    except DeliberateFailure:
        # Expected: the error escaped the block, and the adapter's finally still ran.
        print("Deliberate failure raised and escaped the desktop block, as intended.", flush=True)
    else:
        raise RuntimeError("failure: the deliberate exception did not escape.")
    return confirm_gone(api, created[0].sandbox_id, "failure", KILL_CONFIRM_SECONDS, **wait_options)


def abandon_child(api):
    """Child-process body: open a desktop, then exit without running any cleanup."""
    created = []
    with open_e2b_desktop(new_grant(), sandbox_type=tracking_factory(api, created, announce=True),
                          lifetime_seconds=ABANDON_LIFETIME_SECONDS) as desktop:
        load_page(desktop)
        print("CHILD_READY", flush=True)
        # os._exit ends the process immediately: no finally, no kill(), no browser close.
        # This stands in for a crash, an out-of-memory kill, or a closed laptop.
        os._exit(0)


def run_abandon(api, *, run_child=None, **wait_options):
    """Parent side: start the child, then watch E2B's timer remove its desktop."""
    if run_child is None:
        # Run this same file as a child; capture its output to read the sandbox ID.
        def run_child():
            return subprocess.run([sys.executable, __file__, "--abandon-child"],
                                  capture_output=True, text=True, timeout=150)
    result = run_child()
    match = ID_LINE.search(result.stdout)
    if match is None:
        raise RuntimeError("abandon: child printed no sandbox ID; nothing to watch.\n" + result.stderr)
    sandbox_id = match.group(1)
    # If the child failed before abandoning, the adapter may have killed the desktop itself,
    # and a quick "gone" would wrongly look like the lifetime timer working.
    if result.returncode != 0 or "CHILD_READY" not in result.stdout:
        api.kill(sandbox_id)
        raise RuntimeError("abandon: child failed before abandoning the desktop; kill retried.\n"
                           + result.stderr)
    # The child is gone. The desktop should still exist: nothing has cleaned it up.
    info = api.get_info(sandbox_id)
    end_at = as_utc(info.end_at)
    state = provider_state(api, sandbox_id)
    if state != "running":
        raise RuntimeError(f"abandon: expected the orphaned desktop to be running, got {state!r}.")
    # Show what the provider scheduled: when the timer ends and what it will do then.
    print(f"Orphaned desktop {sandbox_id} is running after its process exited.", flush=True)
    print(f"  provider lifetime: started_at={info.started_at.isoformat()} "
          f"end_at={info.end_at.isoformat()} lifecycle={getattr(info, 'lifecycle', None)}", flush=True)
    seconds_to_end = max(0, (end_at - datetime.now(timezone.utc)).total_seconds())
    print(f"  waiting about {seconds_to_end:.0f}s for the lifetime timer...", flush=True)
    waited = confirm_gone(api, sandbox_id, "abandon (lifetime fallback)",
                          seconds_to_end + ABANDON_GRACE_SECONDS, **wait_options)
    # How long after the scheduled end the desktop actually disappeared.
    lag = datetime.now(timezone.utc) - end_at
    print(f"  disappeared about {lag.total_seconds():.0f}s after end_at "
          f"(polling granularity {wait_options.get('poll_seconds', 5)}s)", flush=True)
    return waited


SCENARIOS = {"normal": run_normal, "failure": run_failure, "abandon": run_abandon}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scenario", choices=[*SCENARIOS, "all"], default="all")
    # Internal flag: the parent uses it to start the abandon child. Not for direct use.
    parser.add_argument("--abandon-child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    load_local_env()
    if not os.environ.get("E2B_API_KEY"):
        raise SystemExit("Set E2B_API_KEY in this terminal. This check uses E2B resources.")
    # In SDK debug mode kill() returns True without contacting E2B, which would fake a pass.
    if os.environ.get("E2B_DEBUG", "false").lower() == "true":
        raise SystemExit("Unset E2B_DEBUG: in debug mode the SDK skips kill().")
    from e2b_desktop import Sandbox

    if args.abandon_child:
        abandon_child(Sandbox)
        return
    chosen = list(SCENARIOS) if args.scenario == "all" else [args.scenario]
    for name in chosen:
        print(f"--- {name} ---", flush=True)
        SCENARIOS[name](Sandbox)
    print("All selected scenarios passed. No model calls were made.")


if __name__ == "__main__":
    main()
