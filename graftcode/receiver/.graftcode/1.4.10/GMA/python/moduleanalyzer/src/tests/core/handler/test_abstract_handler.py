from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel
import pytest

from moduleanalyzer.src.core.handler.abstract_handler import AbstractHandler


class ConcreteHandler(AbstractHandler):
    def generate_unified_graft_model(self, analyzed_object, parent_command, handlers):
        return self.create_unified_graft_model(UnifiedGraftModelType.TYPE_USAGE)


class TestAbstractHandler:
    def setup_method(self):
        self.handler = ConcreteHandler()

    def test_create_unified_graft_model(self):
        model_type = UnifiedGraftModelType.TYPE_USAGE
        result = self.handler.create_unified_graft_model(model_type)

        assert isinstance(result, UnifiedGraftModel)
        assert result.runtime_name == RuntimeName.Python
        assert result.graft_model_type == model_type
        assert result.payload == []


if __name__ == "__main__":
    pytest.main()
