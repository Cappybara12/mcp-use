from moduleanalyzer.src.core.handler.shared.shared_namespace_handler import (
    SharedNamespaceHandler,
)


class TestSharedNamespaceHandler:

    def setup_method(self):
        self.handler = SharedNamespaceHandler()

    def test_generate_unified_graft_model_with_string(self):
        analyzed_object = "test_string"
        parent_command = None
        handlers = None
        result = self.handler.generate_unified_graft_model(
            analyzed_object, parent_command, handlers
        )
        assert result == analyzed_object

    def test_generate_unified_graft_model_with_list(self):
        analyzed_object = [1, 2, 3]
        parent_command = None
        handlers = None
        result = self.handler.generate_unified_graft_model(
            analyzed_object, parent_command, handlers
        )
        assert result == analyzed_object

    def test_generate_unified_graft_model_with_dict(self):
        analyzed_object = {"key": "value"}
        parent_command = None
        handlers = None
        result = self.handler.generate_unified_graft_model(
            analyzed_object, parent_command, handlers
        )
        assert result == analyzed_object

    def test_generate_unified_graft_model_with_none(self):
        analyzed_object = None
        parent_command = None
        handlers = None
        result = self.handler.generate_unified_graft_model(
            analyzed_object, parent_command, handlers
        )
        assert result == analyzed_object

    def test_generate_unified_graft_model_with_custom_object(self):

        class CustomObject:
            pass

        analyzed_object = CustomObject()
        parent_command = None
        handlers = None
        result = self.handler.generate_unified_graft_model(
            analyzed_object, parent_command, handlers
        )
        assert result == analyzed_object
