from __future__ import annotations

import json

from graftcode_protocol.models.dependency_tree_model import DependencyTreeModel


class DependencyTreeFromJsonDeserializer:
    @staticmethod
    def deserialize(json_data: str) -> DependencyTreeModel:
        if json_data is None:
            raise ValueError("Invalid JSON data")

        trimmed_json = json_data.strip()
        if not trimmed_json or not trimmed_json.startswith("{") or trimmed_json == "{}":
            raise ValueError("Invalid JSON data")

        try:
            parsed = json.loads(trimmed_json)
        except json.JSONDecodeError as exc:
            raise ValueError("Invalid JSON data") from exc

        if not isinstance(parsed, dict):
            raise ValueError("Invalid JSON data")

        return DependencyTreeModel.from_dict(parsed)
