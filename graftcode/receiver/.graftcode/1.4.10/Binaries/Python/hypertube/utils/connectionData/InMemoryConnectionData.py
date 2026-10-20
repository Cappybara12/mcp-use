from hypertube.utils.ConnectionType import ConnectionType
from hypertube.utils.connectionData.IConnectionData import IConnectionData


class InMemoryConnectionData(IConnectionData):
    def __init__(self):
        super().__init__()

    @property
    def connection_type(self):
        return ConnectionType.InMemory

    @property
    def hostname(self):
        return "inmemory"

    def serialize_connection_data(self):
        return [self.connection_type.value, 0, 0, 0, 0, 0, 0]
