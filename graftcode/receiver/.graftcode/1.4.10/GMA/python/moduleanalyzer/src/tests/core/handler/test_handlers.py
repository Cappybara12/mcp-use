from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
import pytest

from moduleanalyzer.src.core.handler.create_instance_analyzer_handler import (
    CreateInstanceAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.get_instance_field_analyzer_handler import (
    GetInstanceFieldAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.get_static_field_analyzer_handler import (
    GetStaticFieldAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.get_property_analyzer_handler import (
    GetPropertyAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.get_type_analyzer_handler import (
    GetTypeAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.handlers import Handlers
from moduleanalyzer.src.core.handler.invoke_abstract_instance_method_analyzer_handler import (
    InvokeAbstractInstanceMethodAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.invoke_abstract_static_method_analyzer_handler import (
    InvokeAbstractStaticMethodAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.invoke_instance_method_analyzer_handler import (
    InvokeInstanceMethodAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.invoke_static_method_analyzer_handler import (
    InvokeStaticMethodAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.shared.share_class_name_handler import (
    SharedClassNameHandler,
)
from moduleanalyzer.src.core.handler.shared.share_method_name_handler import (
    SharedMethodNameHandler,
)
from moduleanalyzer.src.core.handler.shared.shared_argument_name_handler import (
    SharedArgumentNameHandler,
)
from moduleanalyzer.src.core.handler.shared.shared_modifier_handler import (
    SharedModifierHandler,
)
from moduleanalyzer.src.core.handler.shared.shared_module_full_name_handler import (
    SharedModuleFullNameHandler,
)
from moduleanalyzer.src.core.handler.shared.shared_module_hash_handler import (
    SharedModuleHashHandler,
)
from moduleanalyzer.src.core.handler.shared.shared_namespace_handler import (
    SharedNamespaceHandler,
)
from moduleanalyzer.src.core.handler.shared.shared_parameters_array_handler import (
    SharedParametersArrayHandler,
)
from moduleanalyzer.src.core.handler.shared.shared_type_handler import SharedTypeHandler


class TestHandlers:
    def setup_method(self):
        self.handlers = Handlers()

    def test_analyzer_handlers_initialization(self):
        assert isinstance(
            self.handlers.analyzer_handler[UnifiedGraftModelType.TYPE_DEF],
            GetTypeAnalyzerHandler,
        )
        assert isinstance(
            self.handlers.analyzer_handler[UnifiedGraftModelType.INSTANCE_METHOD],
            InvokeInstanceMethodAnalyzerHandler,
        )
        assert isinstance(
            self.handlers.analyzer_handler[UnifiedGraftModelType.ABSTRACT_INSTANCE_METHOD],
            InvokeAbstractInstanceMethodAnalyzerHandler,
        )
        assert isinstance(
            self.handlers.analyzer_handler[UnifiedGraftModelType.STATIC_METHOD],
            InvokeStaticMethodAnalyzerHandler,
        )
        assert isinstance(
            self.handlers.analyzer_handler[UnifiedGraftModelType.ABSTRACT_STATIC_METHOD],
            InvokeAbstractStaticMethodAnalyzerHandler,
        )
        assert isinstance(
            self.handlers.analyzer_handler[UnifiedGraftModelType.STATIC_FIELD],
            GetStaticFieldAnalyzerHandler,
        )
        assert isinstance(
            self.handlers.analyzer_handler[UnifiedGraftModelType.CONSTRUCTOR],
            CreateInstanceAnalyzerHandler,
        )
        assert isinstance(
            self.handlers.analyzer_handler[UnifiedGraftModelType.INSTANCE_FIELD],
            GetInstanceFieldAnalyzerHandler,
        )
        assert isinstance(
            self.handlers.analyzer_handler[UnifiedGraftModelType.PROPERTY],
            GetPropertyAnalyzerHandler,
        )

    def test_shared_handlers_initialization(self):
        assert isinstance(
            self.handlers.shared_handler[UnifiedGraftModelType.ARGUMENT_NAME],
            SharedArgumentNameHandler,
        )
        assert isinstance(
            self.handlers.shared_handler[UnifiedGraftModelType.CLASS_NAME],
            SharedClassNameHandler,
        )
        assert isinstance(
            self.handlers.shared_handler[UnifiedGraftModelType.METHOD_NAME],
            SharedMethodNameHandler,
        )
        assert isinstance(
            self.handlers.shared_handler[UnifiedGraftModelType.MODIFIER],
            SharedModifierHandler,
        )
        assert isinstance(
            self.handlers.shared_handler[UnifiedGraftModelType.TYPE_USAGE],
            SharedTypeHandler,
        )
        assert isinstance(
            self.handlers.shared_handler[UnifiedGraftModelType.PARAMETERS_ARRAY],
            SharedParametersArrayHandler,
        )
        assert isinstance(
            self.handlers.shared_handler[UnifiedGraftModelType.NAMESPACE],
            SharedNamespaceHandler,
        )
        assert isinstance(
            self.handlers.shared_handler[UnifiedGraftModelType.MODULE_FULL_NAME],
            SharedModuleFullNameHandler,
        )
        assert isinstance(
            self.handlers.shared_handler[UnifiedGraftModelType.MODULE_HASH],
            SharedModuleHashHandler,
        )

    def test_types_to_analyze_initialization(self):
        assert self.handlers.types_to_analyze == []


if __name__ == "__main__":
    pytest.main()
