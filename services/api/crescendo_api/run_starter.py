"""How the API hands a run to Temporal.

Routes depend on the small RunStarter interface so tests can substitute a fake;
TemporalRunStarter is the real implementation.
"""

import asyncio
import logging
from datetime import timedelta
from functools import lru_cache
from typing import Protocol

from temporalio.client import Client

from crescendo_workers.run_start import StartResult, start_run_workflow

from .config import get_settings

logger = logging.getLogger(__name__)
# Fail an unreachable server quickly; the HTTP caller can retry the start.
CONNECT_TIMEOUT = timedelta(seconds=5)


class RunStartUnavailable(Exception):
    """Temporal could not confirm the start. Safe to retry: the ID is stable."""


class RunStarter(Protocol):
    async def start(self, run_id: str) -> StartResult: ...


class TemporalRunStarter:
    """Connects lazily, once per process, and reuses the client afterward."""

    def __init__(self, address: str, namespace: str):
        self._address = address
        self._namespace = namespace
        self._client: Client | None = None
        self._lock = asyncio.Lock()

    async def _get_client(self) -> Client:
        # The lock stops two concurrent first requests from opening two clients. A
        # failed connect is not cached, so the next request tries again.
        async with self._lock:
            if self._client is None:
                self._client = await asyncio.wait_for(
                    Client.connect(self._address, namespace=self._namespace),
                    timeout=CONNECT_TIMEOUT.total_seconds(),
                )
            return self._client

    async def start(self, run_id: str) -> StartResult:
        try:
            client = await self._get_client()
            return await start_run_workflow(client, run_id)
        except Exception as error:
            # Connection refused, RPC timeout, server error: to the caller these
            # all mean "not confirmed, retry". Log the cause; never show it in HTTP.
            logger.warning("Temporal start for run %s not confirmed: %r", run_id, error)
            raise RunStartUnavailable from error


@lru_cache
def get_run_starter() -> RunStarter:
    """FastAPI dependency: one starter (and so one Temporal client) per process."""
    settings = get_settings()
    return TemporalRunStarter(settings.temporal_address, settings.temporal_namespace)
