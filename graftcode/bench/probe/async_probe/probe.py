"""Tiny receiver for the async probe: the same 200 ms wait, written sync and async."""
import asyncio
import time


class AsyncProbe:
    def wait_sync(self, ms: int) -> int:
        time.sleep(ms / 1000)
        return ms

    async def wait_async(self, ms: int) -> int:
        await asyncio.sleep(ms / 1000)
        return ms
