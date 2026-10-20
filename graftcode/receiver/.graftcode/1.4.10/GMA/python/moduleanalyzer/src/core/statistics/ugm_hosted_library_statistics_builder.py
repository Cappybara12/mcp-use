from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.hosted_library_statistics_model import (
    HostedLibraryStatisticsModel,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel
from graftcode_protocol.protocol.deserializers.unified_graft_model_deserializer import (
    UnifiedGraftModelDeserializer,
)


class UgmHostedLibraryStatisticsBuilder:
    @staticmethod
    def build(ugm_bytes: bytes) -> HostedLibraryStatisticsModel:
        deserializer = UnifiedGraftModelDeserializer(ugm_bytes)
        return UgmHostedLibraryStatisticsBuilder.build_from_model(deserializer.deserialize())

    @staticmethod
    def build_from_model(ugm: UnifiedGraftModel) -> HostedLibraryStatisticsModel:
        counters = {"types": 0, "fields": 0, "methods": 0}
        UgmHostedLibraryStatisticsBuilder._collect_exposure_counts(ugm, counters)

        library_namespace = ""
        library_name = ""
        if (
            ugm.graft_model_type == UnifiedGraftModelType.LIBRARY
            and len(ugm.payload) >= 2
        ):
            library_namespace = str(ugm.payload[0] or "")
            library_name = str(ugm.payload[1] or "")

        return HostedLibraryStatisticsModel(
            name=library_name,
            namespace=library_namespace,
            runtime=ugm.runtime_name.name,
            types_exposed=counters["types"],
            fields_exposed=counters["fields"],
            methods_exposed=counters["methods"],
        )

    @staticmethod
    def _collect_exposure_counts(node: UnifiedGraftModel, counters: dict) -> None:
        node_type = node.graft_model_type
        if node_type in (
            UnifiedGraftModelType.TYPE_DEF,
            UnifiedGraftModelType.MODULE,
            UnifiedGraftModelType.ENUM,
            UnifiedGraftModelType.GENERIC_TYPE_DEF,
        ):
            counters["types"] += 1
        elif node_type in (
            UnifiedGraftModelType.STATIC_FIELD,
            UnifiedGraftModelType.INSTANCE_FIELD,
            UnifiedGraftModelType.GLOBAL_FIELD,
            UnifiedGraftModelType.PROPERTY,
        ):
            counters["fields"] += 1
        elif node_type in (
            UnifiedGraftModelType.STATIC_METHOD,
            UnifiedGraftModelType.INSTANCE_METHOD,
            UnifiedGraftModelType.CONSTRUCTOR,
            UnifiedGraftModelType.GLOBAL_METHOD,
            UnifiedGraftModelType.DESTRUCTOR,
            UnifiedGraftModelType.GENERIC_STATIC_METHOD,
            UnifiedGraftModelType.GENERIC_INSTANCE_METHOD,
            UnifiedGraftModelType.OVERLOADED_CONSTRUCTOR,
            UnifiedGraftModelType.OVERLOADED_STATIC_METHOD,
            UnifiedGraftModelType.OVERLOADED_INSTANCE_METHOD,
            UnifiedGraftModelType.OVERLOADED_GLOBAL_METHOD,
        ):
            counters["methods"] += 1

        for payload_item in node.payload or []:
            if isinstance(payload_item, UnifiedGraftModel):
                UgmHostedLibraryStatisticsBuilder._collect_exposure_counts(
                    payload_item, counters
                )
