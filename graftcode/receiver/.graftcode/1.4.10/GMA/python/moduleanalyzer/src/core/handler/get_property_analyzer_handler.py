from typing import Any

from graftcode_protocol.enums.runtime_name import RuntimeName
from graftcode_protocol.enums.unified_graft_model_type import (
    UnifiedGraftModelType,
)
from graftcode_protocol.models.unified_graft_model import UnifiedGraftModel

from moduleanalyzer.src.core.handler.base_method_handler import BaseMethodHandler


class GetPropertyAnalyzerHandler(BaseMethodHandler):
    """Handler for analyzing properties and generating graft models."""

    def generate_unified_graft_model(
        self,
        analyzed_object: Any,
        parent_command: UnifiedGraftModel,
        handlers: Any,
    ) -> UnifiedGraftModel:
        """
        Generates a UnifiedGraftModel for a property.
        
        Structure matches .NET Core:
        PROPERTY -> [PROPERTY_NAME, TYPE_USAGE, SETTER, GETTER]
        Where SETTER and GETTER are UnifiedGraftModel objects with payload: [MODIFIER]
        
        :param analyzed_object: The property object (property descriptor).
        :param parent_command: The parent TYPE_DEF command.
        :param handlers: Handlers collection.
        :return: UnifiedGraftModel representing the property.
        """
        # Get the property name - check if it's a wrapper with name attribute
        if hasattr(analyzed_object, 'name'):
            property_name = analyzed_object.name
        elif hasattr(analyzed_object, 'fget') and analyzed_object.fget:
            property_name = getattr(analyzed_object.fget, '__name__', None)
        elif hasattr(analyzed_object, '__name__'):
            property_name = analyzed_object.__name__
        else:
            property_name = str(analyzed_object)

        # Get the actual property object (handle PropertyWithName wrapper)
        prop = analyzed_object
        if hasattr(analyzed_object, 'prop'):
            prop = analyzed_object.prop

        property_command = self.create_unified_graft_model(
            UnifiedGraftModelType.PROPERTY
        )
        # Add property name to payload
        property_command = property_command.add_arg_to_payload(property_name)
        
        # Add return type (TYPE_USAGE) from fget method annotations
        # Create a wrapper that exposes __annotations__ from fget
        class PropertyWrapper:
            def __init__(self, prop):
                self.prop = prop
                if hasattr(prop, 'fget') and prop.fget:
                    self.__annotations__ = getattr(prop.fget, '__annotations__', {})
                elif hasattr(prop, 'prop') and hasattr(prop.prop, 'fget') and prop.prop.fget:
                    # Handle PropertyWithName wrapper
                    self.__annotations__ = getattr(prop.prop.fget, '__annotations__', {})
                else:
                    self.__annotations__ = {}
        
        property_wrapper = PropertyWrapper(prop)
        property_command = self.add_return_type_to_payload(
            property_command, property_wrapper, handlers
        )
        
        # Create SETTER UnifiedGraftModel with modifier
        setter_modifier = self._get_setter_modifier(prop, handlers)
        setter_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.SETTER, []
        )
        setter_command = setter_command.add_arg_to_payload(setter_modifier)
        property_command = property_command.add_arg_to_payload(setter_command)
        
        # Create GETTER UnifiedGraftModel with modifier
        getter_modifier = self._get_getter_modifier(prop, handlers)
        getter_command = UnifiedGraftModel(
            RuntimeName.Python, UnifiedGraftModelType.GETTER, []
        )
        getter_command = getter_command.add_arg_to_payload(getter_modifier)
        property_command = property_command.add_arg_to_payload(getter_command)

        return property_command
    
    def _get_setter_modifier(self, prop: Any, handlers: Any) -> int:
        """
        Gets the modifier for the property setter.
        
        :param prop: The property object.
        :param handlers: Handlers collection.
        :return: ModifierType value (int).
        """
        # Get the setter method (fset) if it exists
        setter_method = None
        if hasattr(prop, 'fset') and prop.fset:
            setter_method = prop.fset
        
        if setter_method:
            # Use SharedModifierHandler to determine modifier from method name
            modifier_handler = handlers.shared_handler.get(UnifiedGraftModelType.MODIFIER)
            if modifier_handler:
                return modifier_handler.generate_unified_graft_model(
                    setter_method, None, handlers
                )
        
        # If no setter exists, return PRIVATE (read-only property)
        from graftcode_protocol.enums.modifier_type import ModifierType
        return ModifierType.PRIVATE.value
    
    def _get_getter_modifier(self, prop: Any, handlers: Any) -> int:
        """
        Gets the modifier for the property getter.
        
        :param prop: The property object.
        :param handlers: Handlers collection.
        :return: ModifierType value (int).
        """
        # Get the getter method (fget)
        getter_method = None
        if hasattr(prop, 'fget') and prop.fget:
            getter_method = prop.fget
        
        if getter_method:
            # Use SharedModifierHandler to determine modifier from method name
            modifier_handler = handlers.shared_handler.get(UnifiedGraftModelType.MODIFIER)
            if modifier_handler:
                return modifier_handler.generate_unified_graft_model(
                    getter_method, None, handlers
                )
        
        # Fallback to PUBLIC if no getter found (shouldn't happen for valid properties)
        from graftcode_protocol.enums.modifier_type import ModifierType
        return ModifierType.PUBLIC.value
