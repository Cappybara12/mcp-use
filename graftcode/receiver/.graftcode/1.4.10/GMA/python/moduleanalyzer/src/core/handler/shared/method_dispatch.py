from graftcode_protocol.enums.unified_graft_model_type import UnifiedGraftModelType


class MethodDispatch:
    @staticmethod
    def resolve_node_type(is_static: bool, is_abstract: bool) -> UnifiedGraftModelType:
        if is_static:
            return (
                UnifiedGraftModelType.ABSTRACT_STATIC_METHOD
                if is_abstract
                else UnifiedGraftModelType.STATIC_METHOD
            )

        return (
            UnifiedGraftModelType.ABSTRACT_INSTANCE_METHOD
            if is_abstract
            else UnifiedGraftModelType.INSTANCE_METHOD
        )

    @staticmethod
    def resolve_node_type_for_method(method: object, is_static: bool) -> UnifiedGraftModelType:
        is_abstract = getattr(method, "__isabstractmethod__", False)
        return MethodDispatch.resolve_node_type(is_static, is_abstract)
