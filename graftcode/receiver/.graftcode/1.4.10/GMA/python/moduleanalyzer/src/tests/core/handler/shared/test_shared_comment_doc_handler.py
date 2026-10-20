"""Tests for SharedCommentDocHandler."""

from __future__ import annotations

from graftcode_protocol.commentdoc import exception_mapping as em
from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.handlers import Handlers
from moduleanalyzer.src.core.handler.shared.shared_comment_doc_handler import (
    SharedCommentDocHandler,
    _read_docstring,
)
from moduleanalyzer.src.utils.analyzer_config import ENV_EMIT_CODE_EXAMPLES


class BillingService:
    """Issues sales invoices and persists them in the billing database."""

    def issue_invoice(self, customer_id: int, amount: float) -> str:
        """Issues an invoice for the given customer and amount.

        The invoice number is generated atomically by the repository.
        Amounts are stored with the currency's natural precision; the
        caller is responsible for rounding.

        Args:
            customer_id (int): Numeric identifier of the customer being billed.
            amount (float): Gross amount to invoice, in the customer's home currency.

        Returns:
            str: The newly assigned invoice number.

        Raises:
            ValueError: When amount is not positive.
        """
        if amount <= 0:
            raise ValueError("amount must be positive")
        return f"INV-{customer_id}"


def _find_child(
    root: UnifiedGraftModel, graft_type: UnifiedGraftModelType
) -> UnifiedGraftModel | None:
    for item in root.get_payload():
        if isinstance(item, UnifiedGraftModel) and item.graft_model_type == graft_type:
            return item
    return None


def test_returns_none_without_docstring():
    def bare():
        pass

    handler = SharedCommentDocHandler()
    assert handler.generate_unified_graft_model(bare, None, Handlers()) is None


def test_read_docstring_ignores_object_init_mro():
    class Child(BillingService):
        def __init__(self):
            """Child-only constructor docs."""

            super().__init__()

    assert _read_docstring(Child.__init__) == "Child-only constructor docs."
    assert "object" not in (_read_docstring(Child.__init__) or "").lower()


def test_google_style_builds_comment_doc_subtree():
    handler = SharedCommentDocHandler()
    result = handler.generate_unified_graft_model(
        BillingService.issue_invoice, None, Handlers()
    )

    assert isinstance(result, UnifiedGraftModel)
    assert result.graft_model_type == UnifiedGraftModelType.COMMENT_DOC

    summary = _find_child(result, UnifiedGraftModelType.COMMENT_SUMMARY)
    assert summary is not None
    assert (
        "Issues an invoice for the given customer and amount."
        in summary.get_payload()[0]
    )

    params_array = _find_child(result, UnifiedGraftModelType.COMMENT_PARAMETERS_ARRAY)
    assert params_array is not None
    param_nodes = [
        p
        for p in params_array.get_payload()
        if isinstance(p, UnifiedGraftModel)
        and p.graft_model_type == UnifiedGraftModelType.COMMENT_PARAMETER
    ]
    assert len(param_nodes) == 2
    assert param_nodes[0].get_payload()[0] == "customer_id"
    assert param_nodes[0].get_payload()[2] == "integer"
    assert param_nodes[1].get_payload()[0] == "amount"
    assert param_nodes[1].get_payload()[2] == "number"

    returns = _find_child(result, UnifiedGraftModelType.COMMENT_RETURNS)
    assert returns is not None
    assert returns.get_payload()[0] == "str"
    assert returns.get_payload()[1] == "string"

    throws_array = _find_child(result, UnifiedGraftModelType.COMMENT_THROWS_ARRAY)
    assert throws_array is not None
    throw_node = throws_array.get_payload()[0]
    assert throw_node.get_payload()[0] == "ValueError"
    assert throw_node.get_payload()[1] == em.ILLEGAL_ARGUMENT_EXCEPTION

    source = _find_child(result, UnifiedGraftModelType.COMMENT_SOURCE)
    assert source is not None
    source_file = str(source.get_payload()[1])
    assert source_file == "test_shared_comment_doc_handler.py"
    assert "/" not in source_file
    assert "\\" not in source_file


def test_emit_code_examples_gates_source_raw(monkeypatch):
    handler = SharedCommentDocHandler()

    monkeypatch.delenv(ENV_EMIT_CODE_EXAMPLES, raising=False)
    without = handler.generate_unified_graft_model(
        BillingService.issue_invoice, None, Handlers()
    )
    source = _find_child(without, UnifiedGraftModelType.COMMENT_SOURCE)
    assert source is not None
    assert source.get_payload()[-1] == ""

    monkeypatch.setenv(ENV_EMIT_CODE_EXAMPLES, "true")
    with_code = handler.generate_unified_graft_model(
        BillingService.issue_invoice, None, Handlers()
    )
    source_on = _find_child(with_code, UnifiedGraftModelType.COMMENT_SOURCE)
    assert source_on is not None
    assert "Issues an invoice" in str(source_on.get_payload()[-1])


def test_normalize_optional_union_types():
    handler = SharedCommentDocHandler()

    def documented(x):
        """Do work.

        Args:
            x (Optional[str]): maybe a value.

        Returns:
            Union[str, None]: maybe a result.
        """
        return x

    result = handler.generate_unified_graft_model(documented, None, Handlers())
    assert result is not None
    params_array = _find_child(result, UnifiedGraftModelType.COMMENT_PARAMETERS_ARRAY)
    param = params_array.get_payload()[0]
    assert param.get_payload()[2] == "string"
    returns = _find_child(result, UnifiedGraftModelType.COMMENT_RETURNS)
    assert returns.get_payload()[1] == "string"


def test_handlers_registry_includes_comment_doc():
    handlers = Handlers()
    assert UnifiedGraftModelType.COMMENT_DOC in handlers.shared_handler
    assert isinstance(
        handlers.shared_handler[UnifiedGraftModelType.COMMENT_DOC],
        SharedCommentDocHandler,
    )


def test_unknown_exception_category_is_empty():
    handler = SharedCommentDocHandler()

    def documented():
        """Raises.

        Raises:
            MyCustomError: when things break.
        """
        raise RuntimeError

    result = handler.generate_unified_graft_model(documented, None, Handlers())
    throws_array = _find_child(result, UnifiedGraftModelType.COMMENT_THROWS_ARRAY)
    throw_node = throws_array.get_payload()[0]
    assert throw_node.get_payload()[0] == "MyCustomError"
    assert throw_node.get_payload()[1] == ""
