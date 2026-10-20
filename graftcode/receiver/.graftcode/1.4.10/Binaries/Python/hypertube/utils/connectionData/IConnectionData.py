from abc import ABC, abstractmethod
import threading

from hypertube.utils.ConnectionType import ConnectionType


class IConnectionData(ABC):
    _thread_local = threading.local()

    def __init__(self):
        self._headers = {}

    @property
    @abstractmethod
    def connection_type(self):
        pass

    @property
    @abstractmethod
    def hostname(self):
        pass

    @abstractmethod
    def serialize_connection_data(self):
        pass

    def to_canonical_key(self):
        key = str(self)
        if self.get_headers():
            key += f"|h:{self.serialize_headers_for_key()}"
        config = self.get_config()
        if config:
            key += f"|c:{config}"
        return key

    def set_headers(self, headers):
        self._headers = self._normalize_headers(headers)

    def set_thread_local_headers(self, headers):
        self._thread_local._thread_local_headers = self._normalize_headers(headers)

    def get_headers(self):
        combined = dict(self._headers)
        thread_local_headers = self._thread_local_headers
        if thread_local_headers:
            combined.update(thread_local_headers)
        return combined

    def get_thread_local_headers(self):
        return dict(self._thread_local_headers)

    def get_config(self):
        return ""

    @property
    def _thread_local_headers(self):
        storage = self._thread_local
        if not hasattr(storage, '_thread_local_headers'):
            return {}
        return storage._thread_local_headers

    def serialize_headers_for_key(self):
        headers = self.get_headers()
        return ";".join(f"{key}={headers[key]}" for key in sorted(headers))

    @staticmethod
    def _normalize_headers(headers):
        if not headers:
            return {}
        return {
            str(key).strip().lower(): str(value).strip()
            for key, value in headers.items()
        }

    def __str__(self):
        mapping = {
            ConnectionType.InMemory: "inmemory",
            ConnectionType.Tcp: "tcp",
            ConnectionType.WebSocket: "websocket",
            ConnectionType.Http2: "http2",
        }
        return f"{mapping.get(self.connection_type, 'unknown')}|{self.hostname}"
