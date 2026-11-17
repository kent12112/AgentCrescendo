"""Run a local Temporal development server until Ctrl+C.

Uses the Temporal Python SDK's downloader, so no Docker or Homebrew install is
needed. State is in memory: stopping the server forgets every workflow.

    .venv/bin/python scripts/temporal_dev_server.py
    # frontend 127.0.0.1:7233 (TEMPORAL_ADDRESS), web UI http://127.0.0.1:8233
"""

import asyncio

from temporalio.testing import WorkflowEnvironment


async def main() -> None:
    env = await WorkflowEnvironment.start_local(ip="127.0.0.1", port=7233, ui=True, ui_port=8233)
    print("Temporal dev server on 127.0.0.1:7233; UI http://127.0.0.1:8233 (Ctrl+C stops it)", flush=True)
    try:
        await asyncio.Event().wait()
    finally:
        await env.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
