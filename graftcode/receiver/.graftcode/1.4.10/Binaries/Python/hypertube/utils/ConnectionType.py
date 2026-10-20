from enum import Enum


class ConnectionType(Enum):
    InMemory = 0
    Tcp = 1
    WebSocket = 2
    Http2 = 3
    Tcp_Tls = 4
    Plugin = 5
