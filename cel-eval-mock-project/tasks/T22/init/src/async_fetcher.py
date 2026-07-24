"""Buggy async resource lifecycle used by task T22."""

from __future__ import annotations

import asyncio
from typing import Any, Iterable, Protocol


class AsyncTransport(Protocol):
    async def open(self) -> None: ...

    async def fetch(self, key: str) -> Any: ...

    async def close(self) -> None: ...


class AsyncBatchFetcher:
    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def fetch_all(self, keys: Iterable[str], timeout: float) -> list[Any]:
        key_list = list(keys)
        if not key_list:
            return []
        await self._transport.open()
        tasks = [asyncio.create_task(self._transport.fetch(key)) for key in key_list]
        # Defect: close only runs on success. A worker error also leaves sibling
        # tasks running, while timeout/caller cancellation can skip all cleanup.
        result = await asyncio.wait_for(asyncio.gather(*tasks), timeout=timeout)
        await self._transport.close()
        return result
