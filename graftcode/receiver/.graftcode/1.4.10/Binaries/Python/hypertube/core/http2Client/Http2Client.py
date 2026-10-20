from __future__ import annotations

import select
import socket
import ssl
import threading
import time
from urllib.parse import urlparse

from h2.config import H2Configuration
from h2.connection import H2Connection
from h2.events import (
    ConnectionTerminated,
    DataReceived,
    ResponseReceived,
    StreamEnded,
    StreamReset,
    WindowUpdated,
)

from hypertube.utils.connectionData.Http2ConnectionData import Http2ConnectionData

# cache of clients keyed by connection identity
_clients = {}
_clients_lock = threading.Lock()
MAX_ATTEMPTS = 2
DEFAULT_CONNECT_TIMEOUT_SECONDS = 120
DEFAULT_RESPONSE_TIMEOUT_SECONDS = 180


class Http2ClientDisposedError(RuntimeError):
    pass


class Http2ProtocolError(RuntimeError):
    pass


class Http2ResponseError(RuntimeError):
    pass


class Http2TransportError(RuntimeError):
    pass


class Http2StreamError(RuntimeError):
    pass


class _StreamState:
    def __init__(self) -> None:
        self.body = bytearray()
        self.status = None
        self.reason = ""
        self.ended = False
        self.error = None


class Http2Client:
    def __init__(self, connection_data: Http2ConnectionData):
        self.connection_data = connection_data
        self.uri = connection_data.hostname
        self._parsed_uri = urlparse(self.uri)
        if self._parsed_uri.scheme.lower() not in ("http", "https"):
            raise ValueError(
                "Http2Client requires 'http' (h2c) or 'https' (h2 over TLS) scheme. "
                f"Provided connection data: {connection_data}"
            )
        if not self._parsed_uri.hostname:
            raise ValueError(f"HTTP/2 connection data contains invalid URI: {self.uri}")

        self.response_timeout_in_seconds = (
            connection_data.response_timeout_in_seconds
            if connection_data.response_timeout_in_seconds is not None
            else DEFAULT_RESPONSE_TIMEOUT_SECONDS
        )
        self._cv = threading.Condition()
        self._streams = {}
        self._reader = None
        self._reader_stop = False
        self._broken = False
        self._socket = None
        self._connection = None
        self._wake_read = None
        self._wake_write = None
        self._disposed = False

    @staticmethod
    def _connection_key(connection_data: Http2ConnectionData) -> str:
        return connection_data.to_canonical_key()

    @staticmethod
    def create_or_get_client(connection_data: Http2ConnectionData, expected_current=None):
        key = Http2Client._connection_key(connection_data)
        with _clients_lock:
            if expected_current is None:
                current = _clients.get(key)
                if current is not None:
                    return current
                created = Http2Client(connection_data)
                _clients[key] = created
                return created

            current = _clients.get(key)
            if current is expected_current:
                current.close()
                _clients.pop(key, None)
            elif current is not None:
                return current
            created = Http2Client(connection_data)
            _clients[key] = created
            return created

    @staticmethod
    def send_message(connection_data: Http2ConnectionData, message: bytes) -> bytes:
        if connection_data is None:
            raise ValueError("connection_data must not be None")
        if message is None:
            raise ValueError("message must not be None")

        try:
            return Http2Client.send_message_body(connection_data, message)
        except (Http2ResponseError, Http2StreamError):
            raise
        except (OSError, TimeoutError, Http2ClientDisposedError, Http2TransportError, RuntimeError):
            # Evict desynced/broken connection after final failure (bug 32346).
            Http2Client.close_client(connection_data)
            raise

    @staticmethod
    def send_message_body(connection_data: Http2ConnectionData, message: bytes) -> bytes:
        client = Http2Client.create_or_get_client(connection_data, None)

        last_ex = None
        for attempt in range(MAX_ATTEMPTS):
            try:
                return client.send_byte_array(message)
            except (Http2ResponseError, Http2StreamError):
                raise
            except (OSError, TimeoutError, Http2ClientDisposedError, Http2TransportError) as ex:
                last_ex = ex
                if attempt == MAX_ATTEMPTS - 1:
                    break
                client = Http2Client.create_or_get_client(connection_data, client)

        raise RuntimeError(
            f"HTTP/2 send to {connection_data.hostname} failed after {MAX_ATTEMPTS} attempts. "
            f"Last error: {last_ex}"
        ) from last_ex

    def send_byte_array(self, message: bytes) -> bytes:
        self._ensure_open()
        if message is None:
            raise ValueError("message must not be None")

        deadline = None
        if self.response_timeout_in_seconds >= 0:
            deadline = time.monotonic() + self.response_timeout_in_seconds

        with self._cv:
            self._ensure_connected_locked()
            connection = self._connection
            if connection is None:
                raise Http2TransportError(f"HTTP/2 connection to {self.uri} is not open.")

            stream_id = connection.get_next_available_stream_id()
            state = _StreamState()
            self._streams[stream_id] = state
            try:
                connection.send_headers(
                    stream_id,
                    self._build_headers(message),
                    end_stream=len(message) == 0,
                )
                self._write_body_locked(stream_id, message, state, deadline)
                self._wake_locked()

                while not state.ended and state.error is None:
                    remaining = None if deadline is None else deadline - time.monotonic()
                    if remaining is not None and remaining <= 0:
                        self._reset_stream_locked(stream_id)
                        raise Http2StreamError(
                            f"HTTP/2 request to {self.uri} timed out after {self.response_timeout_in_seconds} seconds."
                        )
                    self._cv.wait(remaining)
            finally:
                self._streams.pop(stream_id, None)
            error = state.error
            status = state.status
            reason = state.reason
            body = bytes(state.body)

        if error is not None:
            raise error
        if status is None:
            raise Http2StreamError(f"HTTP/2 request to {self.uri} completed without a response status.")
        if status < 200 or status >= 300:
            raise Http2ResponseError(
                f"HTTP/2 request to {self.uri} failed with status {status} {reason}. "
            )
        return body

    def _write_body_locked(self, stream_id: int, message: bytes, state: _StreamState, deadline) -> None:
        connection = self._connection
        if connection is None or not message:
            return
        offset = 0
        while offset < len(message):
            if state.error is not None or state.ended:
                raise Http2TransportError(f"HTTP/2 stream ended before request body was sent. URL: {self.uri}")
            window = connection.local_flow_control_window(stream_id)
            max_chunk_size = min(window, connection.max_outbound_frame_size)
            if max_chunk_size <= 0:
                self._wake_locked()
                remaining = None if deadline is None else deadline - time.monotonic()
                if remaining is not None and remaining <= 0:
                    self._reset_stream_locked(stream_id)
                    raise Http2StreamError(
                        f"HTTP/2 request to {self.uri} timed out after {self.response_timeout_in_seconds} seconds."
                    )
                self._cv.wait(remaining)
                continue
            chunk = message[offset : offset + max_chunk_size]
            offset += len(chunk)
            connection.send_data(stream_id, chunk, end_stream=offset == len(message))
        self._wake_locked()

    def _reset_stream_locked(self, stream_id: int) -> None:
        self._streams.pop(stream_id, None)
        connection = self._connection
        if connection is None:
            return
        try:
            connection.reset_stream(stream_id)
        except Exception:
            return
        self._wake_locked()

    def _ensure_connected_locked(self) -> None:
        if self._broken:
            raise Http2TransportError(f"HTTP/2 connection to {self.uri} is no longer usable.")
        if self._socket is not None and self._connection is not None and self._reader is not None and self._reader.is_alive():
            return

        sock = self._open_socket()
        configuration = H2Configuration(client_side=True, header_encoding="utf-8")
        connection = H2Connection(config=configuration)
        connection.initiate_connection()
        self._socket = sock
        self._connection = connection
        self._wake_read, self._wake_write = _open_wake_pair()
        self._reader_stop = False
        self._reader = threading.Thread(target=self._reader_loop, name="hypertube-http2", daemon=True)
        self._reader.start()
        self._wake_locked()

    def _open_socket(self):
        host = self._parsed_uri.hostname
        port = self._parsed_uri.port or (443 if self._parsed_uri.scheme.lower() == "https" else 80)
        raw_socket = socket.create_connection((host, port), timeout=DEFAULT_CONNECT_TIMEOUT_SECONDS)

        if self._parsed_uri.scheme.lower() == "https":
            context = ssl.create_default_context()
            context.set_alpn_protocols(["h2"])
            try:
                tls_socket = context.wrap_socket(raw_socket, server_hostname=host)
            except Exception:
                raw_socket.close()
                raise
            if tls_socket.selected_alpn_protocol() != "h2":
                tls_socket.close()
                raise Http2ProtocolError(f"The endpoint did not negotiate HTTP/2. URL: {self.uri}")
            tls_socket.settimeout(None)
            return tls_socket

        raw_socket.settimeout(None)
        return raw_socket

    def _build_headers(self, message: bytes):
        custom_headers = self.connection_data.get_headers()
        content_type = "application/octet-stream"
        normalized_headers = []
        for key, value in custom_headers.items():
            if key is None or value is None:
                continue
            normalized_key = str(key).lower()
            if normalized_key.startswith(":"):
                continue
            if normalized_key == "content-type":
                content_type = str(value)
                continue
            normalized_headers.append((normalized_key, str(value)))

        path = self._parsed_uri.path or "/"
        if self._parsed_uri.query:
            path = f"{path}?{self._parsed_uri.query}"

        headers = [
            (":method", "POST"),
            (":scheme", self._parsed_uri.scheme.lower()),
            (":authority", self._authority_header()),
            (":path", path),
            ("content-type", content_type),
            ("content-length", str(len(message))),
        ]
        headers.extend(normalized_headers)
        return headers

    def _authority_header(self) -> str:
        host = self._parsed_uri.hostname or ""
        port = self._parsed_uri.port
        if port is None:
            return host
        return f"{host}:{port}"

    def _reader_loop(self) -> None:
        while not self._reader_stop:
            sock = self._socket
            wake_read = self._wake_read
            if sock is None or wake_read is None:
                return
            pending_tls = hasattr(sock, "pending") and sock.pending() > 0
            readable = []
            if not pending_tls:
                try:
                    readable, _, _ = select.select([sock, wake_read], [], [], 0.5)
                except (OSError, ValueError):
                    self._fail_connection(Http2TransportError(f"HTTP/2 connection to {self.uri} closed before the response completed."))
                    return
                if self._reader_stop:
                    return
                if wake_read in readable:
                    try:
                        wake_read.recv(4096)
                    except OSError:
                        pass
            data = None
            if pending_tls or sock in readable:
                try:
                    data = sock.recv(65535)
                except OSError as ex:
                    self._fail_connection(
                        Http2TransportError(f"HTTP/2 connection to {self.uri} closed before the response completed. {ex}")
                    )
                    return
                if not data:
                    self._fail_connection(
                        Http2TransportError(f"HTTP/2 connection to {self.uri} closed before the response completed.")
                    )
                    return
            pending = b""
            with self._cv:
                connection = self._connection
                if connection is None:
                    return
                if data:
                    try:
                        events = connection.receive_data(data)
                    except Exception as ex:
                        self._fail_streams_locked(
                            Http2TransportError(f"HTTP/2 connection to {self.uri} failed: {ex}")
                        )
                        self._cv.notify_all()
                        return
                    self._dispatch_locked(connection, events)
                pending = connection.data_to_send()
                self._cv.notify_all()
            if pending and sock is not None:
                try:
                    sock.sendall(pending)
                except OSError as ex:
                    self._fail_connection(
                        Http2TransportError(f"HTTP/2 write to {self.uri} failed: {ex}")
                    )
                    return

    def _dispatch_locked(self, connection: H2Connection, events) -> None:
        for event in events:
            if isinstance(event, ResponseReceived):
                state = self._streams.get(event.stream_id)
                if state is None:
                    continue
                for key, value in event.headers:
                    if key == ":status":
                        state.status = int(value)
                    elif key == "x-http2-reason":
                        state.reason = value
            elif isinstance(event, DataReceived):
                state = self._streams.get(event.stream_id)
                if state is not None:
                    state.body.extend(event.data)
                connection.acknowledge_received_data(event.flow_controlled_length, event.stream_id)
            elif isinstance(event, StreamEnded):
                state = self._streams.get(event.stream_id)
                if state is not None:
                    state.ended = True
            elif isinstance(event, StreamReset):
                state = self._streams.get(event.stream_id)
                if state is not None:
                    state.error = Http2StreamError(
                        f"HTTP/2 stream was reset by the remote endpoint. Error code: {event.error_code}"
                    )
                    state.ended = True
            elif isinstance(event, ConnectionTerminated):
                self._reader_stop = True
                self._broken = True
                self._fail_streams_locked(
                    Http2TransportError(
                        f"HTTP/2 connection was terminated by the remote endpoint. Error code: {event.error_code}"
                    )
                )
            elif isinstance(event, WindowUpdated):
                pass

    def _fail_streams_locked(self, error: Exception) -> None:
        for state in self._streams.values():
            if state.error is None and not state.ended:
                state.error = error
                state.ended = True
        self._broken = True

    def _fail_connection(self, error: Exception) -> None:
        with self._cv:
            self._reader_stop = True
            self._fail_streams_locked(error)
            self._cv.notify_all()

    def _wake_locked(self) -> None:
        wake_write = self._wake_write
        if wake_write is None:
            return
        try:
            wake_write.send(b"\x00")
        except OSError:
            pass

    def _ensure_open(self) -> None:
        if self._disposed:
            raise Http2ClientDisposedError(
                f"HTTP/2 client is disposed for {self.uri}. "
                "The connection may have been closed and should be recreated."
            )

    def close(self) -> None:
        reader = None
        sock = None
        wake_read = None
        wake_write = None
        with self._cv:
            reader = self._reader
            sock = self._socket
            wake_read = self._wake_read
            wake_write = self._wake_write
            self._disposed = True
            self._reader_stop = True
            self._broken = True
            self._fail_streams_locked(
                Http2ClientDisposedError(
                    f"HTTP/2 client is disposed for {self.uri}. "
                    "The connection may have been closed and should be recreated."
                )
            )
            self._socket = None
            self._connection = None
            self._wake_read = None
            self._wake_write = None
            if wake_write is not None:
                try:
                    wake_write.send(b"\x00")
                except OSError:
                    pass
            self._cv.notify_all()
        for handle in (sock, wake_read, wake_write):
            if handle is None:
                continue
            try:
                handle.close()
            except Exception:
                pass
        if reader is not None and reader is not threading.current_thread():
            reader.join(timeout=2)

    @staticmethod
    def close_client(connection_data) -> None:
        key = Http2Client._connection_key(connection_data)
        with _clients_lock:
            client = _clients.pop(key, None)
        if client is not None:
            client.close()

    @staticmethod
    def get_state(connection_data):
        key = Http2Client._connection_key(connection_data)
        with _clients_lock:
            if key not in _clients:
                return None
            return True


def _open_wake_pair():
    try:
        read_socket, write_socket = socket.socketpair()
    except (AttributeError, OSError):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            listener.bind(("127.0.0.1", 0))
            listener.listen(1)
            write_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            write_socket.connect(listener.getsockname())
            read_socket, _ = listener.accept()
        finally:
            listener.close()
    read_socket.setblocking(False)
    write_socket.setblocking(False)
    return read_socket, write_socket
