import asyncio

import pytest

from src.async_fetcher import AsyncBatchFetcher


class FakeTransport:
    def __init__(self, delays=None):
        self.delays = delays or {}
        self.open_count = 0
        self.close_count = 0
        self.active = set()
        self.cancelled = set()

    async def open(self):
        self.open_count += 1

    async def close(self):
        await asyncio.sleep(0)
        self.close_count += 1

    async def fetch(self, key):
        self.active.add(key)
        try:
            await asyncio.sleep(self.delays.get(key, 0))
            if key == "error":
                raise RuntimeError("remote failure")
            return key.upper()
        except asyncio.CancelledError:
            self.cancelled.add(key)
            raise
        finally:
            self.active.discard(key)


def test_success_preserves_order_and_closes_once():
    async def scenario():
        transport = FakeTransport({"a": 0.02, "b": 0.001})
        result = await AsyncBatchFetcher(transport).fetch_all(["a", "b"], timeout=1)
        assert result == ["A", "B"]
        assert transport.open_count == 1
        assert transport.close_count == 1
        assert not transport.active

    asyncio.run(scenario())


def test_worker_failure_cancels_siblings_and_closes():
    async def scenario():
        transport = FakeTransport({"error": 0.001, "slow": 10})
        with pytest.raises(RuntimeError, match="remote failure"):
            await AsyncBatchFetcher(transport).fetch_all(["error", "slow"], timeout=1)
        assert "slow" in transport.cancelled
        assert not transport.active
        assert transport.close_count == 1

    asyncio.run(scenario())


def test_timeout_cancels_all_workers_and_closes():
    async def scenario():
        transport = FakeTransport({"a": 10, "b": 10})
        with pytest.raises(asyncio.TimeoutError):
            await AsyncBatchFetcher(transport).fetch_all(["a", "b"], timeout=0.01)
        assert transport.cancelled == {"a", "b"}
        assert not transport.active
        assert transport.close_count == 1

    asyncio.run(scenario())


def test_caller_cancellation_still_cleans_up():
    async def scenario():
        transport = FakeTransport({"slow": 10})
        task = asyncio.create_task(
            AsyncBatchFetcher(transport).fetch_all(["slow"], timeout=20)
        )
        await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert transport.cancelled == {"slow"}
        assert not transport.active
        assert transport.close_count == 1

    asyncio.run(scenario())


def test_empty_input_does_not_open_transport():
    async def scenario():
        transport = FakeTransport()
        assert await AsyncBatchFetcher(transport).fetch_all([], timeout=1) == []
        assert transport.open_count == 0
        assert transport.close_count == 0

    asyncio.run(scenario())
