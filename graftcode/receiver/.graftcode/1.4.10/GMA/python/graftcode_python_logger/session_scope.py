from __future__ import annotations

import time
from typing import TYPE_CHECKING

DEFAULT_DRAIN_TIMEOUT_SECONDS: float = 3.0

if TYPE_CHECKING:
    from .logger_factory import GCLoggerFactory

#Disposable 
class SessionScope:

    def __init__(
        self,
        factory: "GCLoggerFactory",
        drain_timeout: float = DEFAULT_DRAIN_TIMEOUT_SECONDS,
    ):
        self._factory = factory
        self._drain_timeout = max(drain_timeout, 0.0)
        self._closed = False

    @property
    def drain_timeout(self) -> float:
        return self._drain_timeout

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._factory.flush()
            if self._drain_timeout > 0:
                time.sleep(self._drain_timeout)
        finally:
            self._factory.shutdown()

    def __enter__(self) -> "SessionScope":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
