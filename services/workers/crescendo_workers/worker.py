"""Worker process: polls the coordinator queue and runs workflow/activity code.

Run from the repository root with a Temporal server listening:
    .venv/bin/python -m crescendo_workers.worker
The worker holds no secrets yet; it only needs the Temporal address.
"""

import asyncio
import logging
import os

from temporalio.client import Client
from temporalio.worker import Worker

from .activities import record_run_start
from .run_start import COORDINATOR_TASK_QUEUE
from .workflows import RunWorkflow


def build_worker(client: Client) -> Worker:
    """One place lists what this worker serves, shared by main() and tests."""
    return Worker(
        client,
        task_queue=COORDINATOR_TASK_QUEUE,
        workflows=[RunWorkflow],
        activities=[record_run_start],
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    # Same variable names and defaults as the API settings.
    address = os.environ.get("TEMPORAL_ADDRESS", "127.0.0.1:7233")
    namespace = os.environ.get("TEMPORAL_NAMESPACE", "default")
    client = await Client.connect(address, namespace=namespace)
    logging.info("Worker polling %r on %s/%s", COORDINATOR_TASK_QUEUE, address, namespace)
    await build_worker(client).run()


if __name__ == "__main__":
    asyncio.run(main())
