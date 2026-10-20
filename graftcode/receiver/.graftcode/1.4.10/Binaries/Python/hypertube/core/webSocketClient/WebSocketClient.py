# python
from __future__ import annotations

import sys
import threading
from inspect import signature
from urllib.parse import urlparse
from websockets.protocol import State
from websockets.sync.client import connect
from websockets.exceptions import WebSocketException, ConnectionClosedOK, ConnectionClosedError

from hypertube.utils.connectionData.WsConnectionData import WsConnectionData

# cache of clients keyed by URI
_clients: dict[str, WebSocketClient] = {}
_clients_lock = threading.Lock()
MAX_ATTEMPTS = 2
DEFAULT_CONNECT_TIMEOUT_SECONDS = 120
DEFAULT_RESPONSE_TIMEOUT_SECONDS = 180


class WebSocketClient:
    def __init__(self, connection_data: WsConnectionData):
        self.connection_data = connection_data
        self.uri = connection_data.hostname
        parsed_uri = urlparse(self.uri)
        if parsed_uri.scheme.lower() not in ("ws", "wss"):
            raise ValueError(
                "WebSocketClient requires 'ws' (WebSocket) or 'wss' (WebSocket over TLS) scheme. "
                f"Provided URL: {self.uri}"
            )
        self._request_headers_value = self._request_headers()
        self._send_receive_lock = threading.Lock()
        self._disposed = False
        # disable frame size limit
        try:
            self.ws = self._connect()
        except (WebSocketException, OSError, ConnectionClosedOK, ConnectionClosedError) as ex:
            raise WebSocketException(
                f"WebSocket connection to {self.uri} failed: {ex}. "
                "Check that the server is running, the URL is correct (ws:// or wss://), "
                "and that no firewall or proxy is blocking the connection."
            ) from ex

    @staticmethod
    def _connection_key(connection_data: WsConnectionData) -> str:
        return connection_data.to_canonical_key()

    @staticmethod
    def create_or_get_client(connection_data: WsConnectionData, expected_current: WebSocketClient | None = None) -> WebSocketClient:
        """
        If expected_current is None -> add-or-get semantics.
        If expected_current is not None -> recreate semantics (always create new, but dispose old only if it's the expected one).
        """
        key = WebSocketClient._connection_key(connection_data)
        with _clients_lock:
            if expected_current is None:
                current = _clients.get(key)
                if current is not None:
                    if current.ws is not None and current.ws.protocol.state == State.OPEN:
                        return current
                    # Replace stale/broken client
                    try:
                        current.close()
                    except Exception:
                        pass
                    created = WebSocketClient(connection_data)
                    _clients[key] = created
                    return created
                # No existing client
                created = WebSocketClient(connection_data)
                _clients[key] = created
                return created
            else:
                # Recreate behavior: dispose old only if it matches expected_current, but always create new and store it
                current = _clients.get(key)
                try:
                    if current is not None and current is expected_current:
                        current.close()
                        _clients.pop(key, None)
                except Exception:
                    pass
                new_client = WebSocketClient(connection_data)
                _clients[key] = new_client
                return new_client

    def _connect(self):
        kwargs = {"uri": self.uri, "max_size": None}
        connect_timeout_in_seconds = DEFAULT_CONNECT_TIMEOUT_SECONDS
        kwargs["open_timeout"] = (
            None if connect_timeout_in_seconds < 0 else connect_timeout_in_seconds
        )
        headers = self._request_headers_value
        if headers:
            parameters = signature(connect).parameters
            if "additional_headers" in parameters:
                kwargs["additional_headers"] = headers
            elif "extra_headers" in parameters:
                kwargs["extra_headers"] = headers
            else:
                raise WebSocketException(
                    "WebSocket custom headers aren't supported by the installed websockets package."
                )
        return connect(**kwargs)

    def _request_headers(self):
        headers = {}
        for key, value in self.connection_data.get_headers().items():
            if key is None or value is None:
                continue
            if _is_restricted_websocket_header(str(key)):
                print(f"WebSocket header '{key}' is reserved and was ignored.", file=sys.stderr)
                continue
            headers[str(key)] = str(value)
        return headers

    @staticmethod
    def send_message(connection_data: WsConnectionData, message: bytes) -> bytes:
        try:
            return WebSocketClient.send_message_body(connection_data, message)
        except (WebSocketException, OSError, RuntimeError, ConnectionClosedOK, ConnectionClosedError):
            # Evict desynced/broken connection after final failure (bug 32346).
            WebSocketClient.close_client(connection_data)
            raise

    @staticmethod
    def send_message_body(connection_data: WsConnectionData, message: bytes) -> bytes:
        if connection_data is None:
            raise ValueError("connection_data must not be None")
        if message is None:
            raise ValueError("message must not be None")

        client = WebSocketClient.create_or_get_client(connection_data, None)

        last_ex = None

        for attempt in range(MAX_ATTEMPTS):
            try:
                # Lock the current client only for this send+receive pair so a
                # recreate on retry switches to the new client's gate.
                with client._send_receive_lock:
                    client.send_byte_array(message)
                    return client.receive_byte_array()
            except (WebSocketException, OSError, RuntimeError, ConnectionClosedOK, ConnectionClosedError) as ex:
                last_ex = ex
                if attempt == MAX_ATTEMPTS - 1:
                    break
                client = WebSocketClient.create_or_get_client(connection_data, client)

        raise last_ex or RuntimeError(
            f"WebSocket send to {connection_data.hostname} failed after {MAX_ATTEMPTS} attempts. "
            "Check that the server is running and the connection is valid."
        )

    def send_byte_array(self, message: bytes) -> None:
        if self.ws is None:
            raise RuntimeError(
                f"WebSocket to {self.uri} is not open. "
                "The connection may have been closed or never established."
            )
        if message is None:
            raise ValueError("message must not be None")
        try:
            # websockets sync client will send full message
            self.ws.send(message)
        except (ConnectionClosedOK, ConnectionClosedError) as ex:
            raise WebSocketException(
                f"WebSocket send to {self.uri} failed: {ex}. "
                "The connection was closed by the server or due to an error."
            ) from ex

    def receive_byte_array(self) -> bytes:
        if self.ws is None:
            raise RuntimeError(
                f"WebSocket to {self.uri} is not open. "
                "The connection may have been closed or never established."
            )
        response_timeout_in_seconds = (
            self.connection_data.response_timeout_in_seconds
            if self.connection_data.response_timeout_in_seconds is not None
            else DEFAULT_RESPONSE_TIMEOUT_SECONDS
        )
        try:
            response = self.ws.recv(
                timeout=None if response_timeout_in_seconds < 0 else response_timeout_in_seconds
            )
        except TimeoutError as ex:
            raise TimeoutError(
                f"WebSocket receive from {self.uri} timed out after {response_timeout_in_seconds} seconds. "
                "The server may not have responded in time."
            ) from ex
        except (ConnectionClosedOK, ConnectionClosedError) as ex:
            # Mirror C# behavior: close and raise WebSocketException
            try:
                self.close()
            except Exception:
                pass
            raise WebSocketException(
                f"WebSocket connection to {self.uri} was closed by the remote endpoint: {ex}. "
                "The server may have shut down or closed the connection."
            ) from ex

        if isinstance(response, str):
            return response.encode("utf-8")
        return response

    def close(self) -> None:
        if self.ws is not None:
            try:
                # attempt graceful close; ignore errors
                try:
                    # best-effort close if state suggests open/closing
                    state = None
                    try:
                        state = self.ws.protocol.state
                    except Exception:
                        state = None
                    if state in (State.OPEN, State.CLOSING):
                        try:
                            self.ws.close()
                        except Exception:
                            pass
                    else:
                        try:
                            self.ws.close()
                        except Exception:
                            pass
                finally:
                    pass
            finally:
                self.ws = None
        self._disposed = True

    @staticmethod
    def close_client(connection_data: WsConnectionData) -> None:
        key = WebSocketClient._connection_key(connection_data)
        with _clients_lock:
            client = _clients.pop(key, None)
        if client is not None:
            client.close()

    @staticmethod
    def get_state(connection_data: WsConnectionData):
        key = WebSocketClient._connection_key(connection_data)
        with _clients_lock:
            client = _clients.get(key)
        if client is None or client.ws is None:
            return None
        return client.ws.protocol.state


def _is_restricted_websocket_header(key: str) -> bool:
    normalized = key.lower()
    return (
        normalized in {"host", "upgrade", "connection"}
        or normalized.startswith("sec-websocket-")
    )
