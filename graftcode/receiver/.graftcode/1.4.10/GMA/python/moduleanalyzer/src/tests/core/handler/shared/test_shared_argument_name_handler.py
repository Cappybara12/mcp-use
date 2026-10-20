from moduleanalyzer.src.core.handler.shared.shared_argument_name_handler import (
    SharedArgumentNameHandler,
)


def test_generate_unified_graft_model_returns_string_representation():
    handler = SharedArgumentNameHandler()

    class TestAnalyzedObject:
        def __str__(self):
            return "TestAnalyzedObjectRepresentation"

    analyzed_object = TestAnalyzedObject()
    parent_command = "TestParentCommand"
    handlers = ["Handler1", "Handler2"]

    result = handler.generate_unified_graft_model(
        analyzed_object, parent_command, handlers
    )
    expected = str(analyzed_object)

    assert (
        result == expected
    ), "The method should return the string representation of the analyzed object"
