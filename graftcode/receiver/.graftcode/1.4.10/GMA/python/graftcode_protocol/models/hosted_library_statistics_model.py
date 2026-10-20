from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HostedLibraryStatisticsModel:
    name: str = ""
    namespace: str = ""
    runtime: str = ""
    types_exposed: int = 0
    fields_exposed: int = 0
    methods_exposed: int = 0

    def to_dict(self) -> dict:
        return {
            "Name": self.name,
            "Namespace": self.namespace,
            "Runtime": self.runtime,
            "TypesExposed": self.types_exposed,
            "FieldsExposed": self.fields_exposed,
            "MethodsExposed": self.methods_exposed,
        }
