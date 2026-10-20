import json

from graftcode_protocol.models.hosted_library_statistics_model import (
    HostedLibraryStatisticsModel,
)


class HostedLibraryStatisticsToJsonSerializer:
    @staticmethod
    def serialize(model: HostedLibraryStatisticsModel) -> str:
        return json.dumps(model.to_dict(), separators=(",", ":"))
