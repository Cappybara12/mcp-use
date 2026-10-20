from typing import Any, List, Optional

from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType

from moduleanalyzer.src.core.handler.create_instance_analyzer_handler import (
    CreateInstanceAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.get_global_field_analyzer_handler import (
    GetGlobalFieldAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.get_global_method_analyzer_handler import (
    GetGlobalMethodAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.get_instance_field_analyzer_handler import (
    GetInstanceFieldAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.get_property_analyzer_handler import (
    GetPropertyAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.get_static_field_analyzer_handler import (
    GetStaticFieldAnalyzerHandler,
)
from moduleanalyzer.src.core.handler.get_type_analyzer_handler import (
    GetTypeAnalyzerHandler,
)
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
from moduleanalyzer.src.core.handler.shared.comment_doc.sections.comment_deprecated_section_handler import (
    CommentDeprecatedSectionHandler,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.sections.comment_description_section_handler import (
    CommentDescriptionSectionHandler,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.sections.comment_examples_section_handler import (
    CommentExamplesSectionHandler,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.sections.comment_links_section_handler import (
    CommentLinksSectionHandler,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.sections.comment_metadata_section_handler import (
    CommentMetadataSectionHandler,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.sections.comment_parameters_section_handler import (
    CommentParametersSectionHandler,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.sections.comment_returns_section_handler import (
    CommentReturnsSectionHandler,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.sections.comment_source_section_handler import (
    CommentSourceSectionHandler,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.sections.comment_summary_section_handler import (
    CommentSummarySectionHandler,
)
from moduleanalyzer.src.core.handler.shared.comment_doc.sections.comment_throws_section_handler import (
    CommentThrowsSectionHandler,
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
from moduleanalyzer.src.core.handler.shared.shared_array_type_handler import (
    SharedArrayTypeHandler,
)
from moduleanalyzer.src.core.handler.shared.shared_comment_doc_handler import (
    SharedCommentDocHandler,
)
from moduleanalyzer.src.core.handler.shared.shared_field_name_handler import (
    SharedFieldNameHandler,
)
from moduleanalyzer.src.core.handler.shared.shared_generic_alias_type_handler import (
    SharedGenericAliasTypeHandler,
)
from moduleanalyzer.src.core.handler.shared.shared_generic_parameters_handler import (
    SharedGenericParametersHandler,
)
from moduleanalyzer.src.core.handler.shared.shared_generic_type_handler import (
    SharedGenericTypeHandler,
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
from moduleanalyzer.src.core.handler.shared.shared_primitive_type_handler import (
    SharedPrimitiveTypeHandler,
)
from moduleanalyzer.src.core.handler.shared.shared_type_handler import SharedTypeHandler
from moduleanalyzer.src.core.handler.shared.shared_void_type_handler import (
    SharedVoidTypeHandler,
)


class Handlers:
    """
    Registry for all analyzer and shared handlers.

    Provides a centralized way to access handlers for different
    UnifiedGraftModelType operations.
    """

    def __init__(self) -> None:
        # Instance variables to avoid shared mutable defaults
        self.types_to_analyze: List[Any] = []
        self.method_filter: str = ""
        # Current library name for determining external types
        self.current_library_name: Optional[str] = None
        # Top-level Python import names for the library being analyzed
        self.current_library_import_roots: frozenset[str] = frozenset()
        self.analyzer_handler = {
            UnifiedGraftModelType.TYPE_DEF: GetTypeAnalyzerHandler(),
            UnifiedGraftModelType.INSTANCE_METHOD: (
                InvokeInstanceMethodAnalyzerHandler()
            ),
            UnifiedGraftModelType.ABSTRACT_INSTANCE_METHOD: (
                InvokeAbstractInstanceMethodAnalyzerHandler()
            ),
            UnifiedGraftModelType.STATIC_METHOD: (InvokeStaticMethodAnalyzerHandler()),
            UnifiedGraftModelType.ABSTRACT_STATIC_METHOD: (
                InvokeAbstractStaticMethodAnalyzerHandler()
            ),
            UnifiedGraftModelType.STATIC_FIELD: (GetStaticFieldAnalyzerHandler()),
            UnifiedGraftModelType.CONSTRUCTOR: (CreateInstanceAnalyzerHandler()),
            UnifiedGraftModelType.INSTANCE_FIELD: (GetInstanceFieldAnalyzerHandler()),
            UnifiedGraftModelType.GLOBAL_METHOD: (GetGlobalMethodAnalyzerHandler()),
            UnifiedGraftModelType.GLOBAL_FIELD: (GetGlobalFieldAnalyzerHandler()),
            UnifiedGraftModelType.PROPERTY: (GetPropertyAnalyzerHandler()),
        }

        self.shared_handler = {
            UnifiedGraftModelType.ARGUMENT_NAME: (SharedArgumentNameHandler()),
            UnifiedGraftModelType.CLASS_NAME: SharedClassNameHandler(),
            UnifiedGraftModelType.METHOD_NAME: SharedMethodNameHandler(),
            UnifiedGraftModelType.MODIFIER: SharedModifierHandler(),
            UnifiedGraftModelType.TYPE_USAGE: SharedTypeHandler(),
            UnifiedGraftModelType.PARAMETERS_ARRAY: (SharedParametersArrayHandler()),
            UnifiedGraftModelType.NAMESPACE: SharedNamespaceHandler(),
            UnifiedGraftModelType.MODULE_FULL_NAME: (SharedModuleFullNameHandler()),
            UnifiedGraftModelType.MODULE_HASH: SharedModuleHashHandler(),
            UnifiedGraftModelType.FIELD_NAME: SharedFieldNameHandler(),
            # Additional type usage handlers (similar to netcore structure)
            # Note: These handlers still produce TYPE_USAGE (flat structure) but provide modular organization
            UnifiedGraftModelType.TYPE_USAGE_PRIMITIVE: SharedPrimitiveTypeHandler(),
            UnifiedGraftModelType.TYPE_USAGE_ARRAY: SharedArrayTypeHandler(),
            UnifiedGraftModelType.TYPE_USAGE_GENERIC: SharedGenericTypeHandler(),
            UnifiedGraftModelType.TYPE_USAGE_GENERIC_ALIAS: (
                SharedGenericAliasTypeHandler()
            ),
            UnifiedGraftModelType.TYPE_USAGE_VOID: SharedVoidTypeHandler(),
            UnifiedGraftModelType.GENERIC_PARAMETERS: SharedGenericParametersHandler(),
            UnifiedGraftModelType.COMMENT_DOC: SharedCommentDocHandler(),
        }

        self.comment_doc_section_handlers = [
            CommentSummarySectionHandler(),
            CommentDescriptionSectionHandler(),
            CommentParametersSectionHandler(),
            CommentReturnsSectionHandler(),
            CommentThrowsSectionHandler(),
            CommentExamplesSectionHandler(),
            CommentLinksSectionHandler(),
            CommentDeprecatedSectionHandler(),
            CommentMetadataSectionHandler(),
            CommentSourceSectionHandler(),
        ]
