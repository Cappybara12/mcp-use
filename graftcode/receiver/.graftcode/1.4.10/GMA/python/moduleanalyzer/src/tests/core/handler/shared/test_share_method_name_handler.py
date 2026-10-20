from moduleanalyzer.src.core.handler.shared.share_method_name_handler import (
    SharedMethodNameHandler,
)


def test_generate_unified_graft_model_returns_analyzed_object():
    handler = SharedMethodNameHandler()

    class TestAnalyzedObject:
        pass

    analyzed_object = TestAnalyzedObject()
    parent_command = "TestParentCommand"
    handlers = ["Handler1", "Handler2"]

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )

    assert result is analyzed_object, "The method should return the analyzed object"
