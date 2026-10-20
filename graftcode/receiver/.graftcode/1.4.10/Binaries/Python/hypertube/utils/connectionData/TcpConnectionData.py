from hypertube.utils.ConnectionType import ConnectionType
from hypertube.utils.connectionData.IConnectionData import IConnectionData
from hypertube.utils.connectionData.Ipv4HostResolver import resolve_ipv4_host


class TcpConnectionData(IConnectionData):

    def __init__(self, hostname: str):
        super().__init__()
        host_only, port = self.__parse_hostname(hostname)
        self._hostname = f"{host_only}:{port}"
        self._port = port
        self._ip_address = resolve_ipv4_host(host_only, "TCP")

    @staticmethod
    def __parse_hostname(hostname: str):
        value = str(hostname).strip()
        if value.lower().startswith("tcp://"):
            value = value[6:]
        if "/" in value:
            raise ValueError("TCP addresses do not support route paths.")

        colon = value.rfind(":")
        if colon <= 0 or colon >= len(value) - 1:
            raise ValueError("TCP hostname must use host:port format.")

        host_only = value[:colon].strip()
        try:
            port = int(value[colon + 1:])
        except Exception:
            raise ValueError("TCP hostname must contain a numeric port.")

        if not host_only or port < 0 or port > 65535:
            raise ValueError("TCP hostname must contain a non-empty host and port between 0 and 65535.")

        return host_only, port

    @property
    def connection_type(self):
        return ConnectionType.Tcp

    @property
    def hostname(self):
        return self._hostname

    @property
    def ip_address(self):
        return self._ip_address

    @property
    def port(self):
        return self._port

    def serialize_connection_data(self):
        address_bytes = self.__get_address_bytes()
        port_bytes = self.__get_pot_bytes()
        return [self.connection_type.value] + address_bytes + port_bytes

    def __get_address_bytes(self):
        return [int(x) for x in self._ip_address.split(".")]

    def __get_pot_bytes(self):
        return [self._port & 0xFF, self._port >> 8]

    @hostname.setter
    def hostname(self, value):
        self._hostname = value

    @port.setter
    def port(self, value):
        self._port = value

    @ip_address.setter
    def ip_address(self, value):
        self._ip_address = value
