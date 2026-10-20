from __future__ import annotations

import json

from graftcode_protocol.models.dependency_tree_model import DependencyTreeModel


class DependencyTreeToJsonSerializer:
    @staticmethod
    def serialize(model: DependencyTreeModel) -> str:
        return json.dumps(model.to_dict(), separators=(",", ":"))
