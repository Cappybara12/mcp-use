from hypertube.utils.ConnectionType import ConnectionType
from hypertube.utils.connectionData.IConnectionData import IConnectionData


DEFAULT_RESPONSE_TIMEOUT_SECONDS = 180


class Http2ConnectionData(IConnectionData):

    def __init__(self, hostname: str, response_timeout_in_seconds: int = DEFAULT_RESPONSE_TIMEOUT_SECONDS):
        super().__init__()
        self._hostname = hostname
        self._response_timeout_in_seconds = response_timeout_in_seconds

    @property
    def connection_type(self):
        return ConnectionType.Http2

    @property
    def hostname(self):
        return self._hostname

    def serialize_connection_data(self):
        return [self.connection_type.value, 0, 0, 0, 0, 0, 0]

    @hostname.setter
    def hostname(self, value):
        self._hostname = value

    @property
    def response_timeout_in_seconds(self):
        return self._response_timeout_in_seconds

    @response_timeout_in_seconds.setter
    def response_timeout_in_seconds(self, value):
        self._response_timeout_in_seconds = value

