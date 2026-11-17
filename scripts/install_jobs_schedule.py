"""Install (or remove) the launchd agent that runs the daily Ashby crawl (JOB-F07). macOS only.

Writes ~/Library/LaunchAgents/com.agentcrescendo.jobs-daily.plist and loads it for the
current user. launchd then runs scripts/crawl_jobs_daily.py at --hour:--minute every
day; if the Mac was asleep at that time, launchd runs it once on wake. Output goes to
.cache/jobs/daily.log in this repository.

  python scripts/install_jobs_schedule.py              # install for 08:00 daily
  python scripts/install_jobs_schedule.py --run-now    # install and start one run now
  python scripts/install_jobs_schedule.py --uninstall  # unload and delete the agent
"""
import argparse
import os
from pathlib import Path
import plistlib
import subprocess
import sys

LABEL = "com.agentcrescendo.jobs-daily"
REPO = Path(__file__).resolve().parent.parent
PLIST = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def launchctl(*args) -> subprocess.CompletedProcess:
    return subprocess.run(["launchctl", *args], capture_output=True, text=True)


def agent(hour: int, minute: int) -> dict:
    log = REPO / ".cache" / "jobs" / "daily.log"
    return {
        "Label": LABEL,
        "ProgramArguments": [str(REPO / ".venv" / "bin" / "python"), str(REPO / "scripts" / "crawl_jobs_daily.py")],
        "WorkingDirectory": str(REPO),  # .env and .cache/jobs are found relative to the repository
        "StartCalendarInterval": {"Hour": hour, "Minute": minute},
        "StandardOutPath": str(log),
        "StandardErrorPath": str(log),
        # Docker's CLI (used to start Postgres if it is down) lives here on most Macs.
        "EnvironmentVariables": {"PATH": "/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"},
        "ProcessType": "Background",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hour", type=int, default=8, help="Local hour to run (0-23; default 8).")
    parser.add_argument("--minute", type=int, default=0, help="Minute (0-59; default 0).")
    parser.add_argument("--run-now", action="store_true", help="Also start one run immediately.")
    parser.add_argument("--uninstall", action="store_true", help="Unload and delete the agent.")
    args = parser.parse_args()
    if sys.platform != "darwin":
        raise SystemExit("launchd is macOS only.")
    domain = f"gui/{os.getuid()}"

    launchctl("bootout", f"{domain}/{LABEL}")  # ignore "not loaded"
    if args.uninstall:
        PLIST.unlink(missing_ok=True)
        print(f"Removed {LABEL}.")
        return 0
    if not (0 <= args.hour <= 23 and 0 <= args.minute <= 59):
        raise SystemExit("--hour must be 0-23 and --minute 0-59.")
    if not (REPO / ".venv" / "bin" / "python").exists():
        raise SystemExit(f"No virtualenv at {REPO / '.venv'}; create it first.")

    (REPO / ".cache" / "jobs").mkdir(parents=True, exist_ok=True)
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    with PLIST.open("wb") as handle:
        plistlib.dump(agent(args.hour, args.minute), handle)
    loaded = launchctl("bootstrap", domain, str(PLIST))
    if loaded.returncode != 0:
        raise SystemExit(f"launchctl bootstrap failed: {loaded.stderr.strip()}")
    print(f"Installed {LABEL}: daily at {args.hour:02d}:{args.minute:02d}; log {REPO / '.cache/jobs/daily.log'}")
    if args.run_now:
        started = launchctl("kickstart", f"{domain}/{LABEL}")
        print("Started one run now." if started.returncode == 0 else f"kickstart failed: {started.stderr.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
