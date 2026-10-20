from hypertube.utils.ConnectionType import ConnectionType
from hypertube.utils.connectionData.IConnectionData import IConnectionData
from hypertube.utils.connectionData.Ipv4HostResolver import resolve_ipv4_host


class PluginConnectionData(IConnectionData):

    def __init__(self, hostname: str, plugin_config: str):
        super().__init__()
        if hostname is None or str(hostname).strip() == "":
            hostname = "127.0.0.1:0"
        host_only, port = self.__parse_hostname(hostname)
        self._hostname = f"{host_only}:{port}"
        self._port = port
        self._plugin_config = plugin_config
        self._ip_address = resolve_ipv4_host(host_only, "Plugin")

    @staticmethod
    def __parse_hostname(hostname: str):
        value = str(hostname).strip()
        scheme_separator = value.find("://")
        if scheme_separator > 0:
            value = value[scheme_separator + 3:]

        colon = value.rfind(":")
        if colon <= 0 or colon >= len(value) - 1:
            raise ValueError("Hostname must use host:port format.")

        host_only = value[:colon].strip()
        try:
            port = int(value[colon + 1:])
        except Exception:
            raise ValueError("Hostname must contain a numeric port.")

        if not host_only or port < 0 or port > 65535:
            raise ValueError("Hostname must contain a non-empty host and port between 0 and 65535.")

        return host_only, port

    @property
    def connection_type(self):
        return ConnectionType.Plugin

    @property
    def hostname(self):
        return self._hostname

    def serialize_connection_data(self):
        return [self.connection_type.value] + self.__get_address_bytes() + self.__get_port_bytes()

    def __get_address_bytes(self):
        return [int(x) for x in self._ip_address.split(".")]

    def __get_port_bytes(self):
        return [self._port & 0xFF, self._port >> 8]

    def get_config(self):
        return self._plugin_config

    def __str__(self):
        return f"plugin|{self._hostname}"
