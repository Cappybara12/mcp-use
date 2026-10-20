from graftcode_protocol.enums.modifier_type import ModifierType
import pytest

from moduleanalyzer.src.core.handler.shared.shared_modifier_handler import (
    SharedModifierHandler,
)


def public_function():
    pass


def _protected_function():
    pass


def __private_function():
    pass


class TestSharedModifierHandler:
    def setup_method(self):
        self.handler = SharedModifierHandler()

    def test_generate_unified_graft_model_public_function(self):
        result = self.handler.generate_unified_graft_model(public_function, None, None)
        assert result == ModifierType.PUBLIC.value

    def test_generate_unified_graft_model_protected_function(self):
        result = self.handler.generate_unified_graft_model(
            _protected_function, None, None
        )
        assert result == ModifierType.PROTECTED.value

    def test_generate_unified_graft_model_non_function(self):
        result = self.handler.generate_unified_graft_model("not_a_function", None, None)
        assert result == ModifierType.PUBLIC.value


if __name__ == "__main__":
    pytest.main()
