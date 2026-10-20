from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DependencyTreeModel:
    dependency_namespace: str = ""
    dependency_name: str = ""
    dependency_version: str = ""
    dependency_children: list["DependencyTreeModel"] = field(default_factory=list)
    required_constraint: Optional[str] = None
    is_version_satisfied: Optional[bool] = None

    def to_dict(self) -> dict:
        result = {
            "DependencyNamespace": self.dependency_namespace,
            "DependencyName": self.dependency_name,
            "DependencyVersion": self.dependency_version,
            "DependencyChildren": [child.to_dict() for child in self.dependency_children],
        }
        if self.required_constraint is not None:
            result["RequiredConstraint"] = self.required_constraint
        if self.is_version_satisfied is not None:
            result["IsVersionSatisfied"] = self.is_version_satisfied
        return result

    @staticmethod
    def from_dict(data: dict) -> "DependencyTreeModel":
        children_data = data.get("DependencyChildren", [])
        children = [
            DependencyTreeModel.from_dict(child)
            for child in children_data
            if isinstance(child, dict)
        ]
        return DependencyTreeModel(
            dependency_namespace=str(data.get("DependencyNamespace", "")),
            dependency_name=str(data.get("DependencyName", "")),
            dependency_version=str(data.get("DependencyVersion", "")),
            dependency_children=children,
            required_constraint=data.get("RequiredConstraint"),
            is_version_satisfied=data.get("IsVersionSatisfied"),
        )
