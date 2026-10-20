from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.core.handler.ValueHandler import ValueHandler
from hypertube.core.handler.LoadLibraryHandler import LoadLibraryHandler
from hypertube.core.handler.InvokeStaticMethodHandler import InvokeStaticMethodHandler
from hypertube.core.handler.GetStaticFieldHandler import GetStaticFieldHandler
from hypertube.core.handler.SetStaticFieldHandler import SetStaticFieldHandler
from hypertube.core.handler.CreateClassInstanceHandler import CreateClassInstanceHandler
from hypertube.core.handler.GetTypeHandler import GetTypeHandler
from hypertube.core.handler.ResolveInstanceHandler import ResolveInstanceHandler
from hypertube.core.handler.GetModuleHandler import GetModuleHandler
from hypertube.core.handler.InvokeInstanceMethodHandler import InvokeInstanceMethodHandler
from hypertube.core.handler.ExceptionHandler import ExceptionHandler
from hypertube.core.handler.HeartBeatHandler import HeartBeatHandler
from hypertube.core.handler.CastingHandler import CastingHandler
from hypertube.core.handler.GetInstanceFieldHandler import GetInstanceFieldHandler
from hypertube.core.handler.OptimizeHandler import OptimizeHandler
from hypertube.core.handler.GenerateLibHandler import GenerateLibHandler
from hypertube.core.handler.InvokeGlobalFunctionHandler import InvokeGlobalFunctionHandler
from hypertube.core.handler.DestructReferenceHandler import DestructReferenceHandler
from hypertube.core.handler.ArrayReferenceHandler import ArrayReferenceHandler
from hypertube.core.handler.ArrayGetItemHandler import ArrayGetItemHandler
from hypertube.core.handler.ArrayGetSizeHandler import ArrayGetSizeHandler
from hypertube.core.handler.ArrayGetRankHandler import ArrayGetRankHandler
from hypertube.core.handler.ArraySetItemHandler import ArraySetItemHandler
from hypertube.core.handler.ArrayHandler import ArrayHandler
from hypertube.core.handler.RetrieveArrayHandler import RetrieveArrayHandler
from hypertube.core.handler.SetInstanceFieldHandler import SetInstanceFieldHandler
from hypertube.core.handler.InvokeGenericStaticMethodHandler import InvokeGenericStaticMethodHandler
from hypertube.core.handler.InvokeGenericMethodHandler import InvokeGenericMethodHandler
from hypertube.core.handler.GetEnumItemHandler import GetEnumItemHandler
from hypertube.core.handler.GetEnumNameHandler import GetEnumNameHandler
from hypertube.core.handler.GetEnumValueHandler import GetEnumValueHandler
from hypertube.core.handler.AsRefHandler import AsRefHandler
from hypertube.core.handler.AsOutHandler import AsOutHandler
from hypertube.core.handler.GetRefValueHandler import GetRefValueHandler
from hypertube.core.handler.EnableNamespaceHandler import EnableNamespaceHandler
from hypertube.core.handler.EnableTypeHandler import EnableTypeHandler
from hypertube.core.handler.CreateNullHandler import CreateNullHandler
from hypertube.core.handler.GetStaticMethodAsDelegateHandler import GetStaticMethodAsDelegateHandler
from hypertube.core.handler.GetInstanceMethodAsDelegateHandler import GetInstanceMethodAsDelegateHandler
from hypertube.core.handler.PassDelegateHandler import PassDelegateHandler
from hypertube.core.handler.InvokeDelegateHandler import InvokeDelegateHandler
from hypertube.core.handler.ConvertTypeHandler import ConvertTypeHandler
from hypertube.core.handler.AddEventListenerHandler import AddEventListenerHandler
from hypertube.core.handler.PluginWrapperHandler import PluginWrapperHandler
from hypertube.core.handler.GetAsyncOperationResultHandler import GetAsyncOperationResultHandler
from hypertube.core.handler.GetKwargHandler import GetKwargHandler
from hypertube.core.handler.GetResultTypeHandler import GetResultTypeHandler
from hypertube.core.handler.GetGlobalFieldHandler import GetGlobalFieldHandler
from hypertube.core.handler.RegisterForUpdateHandler import RegisterForUpdateHandler
from hypertube.core.handler.ValueForUpdateHandler import ValueForUpdateHandler
from hypertube.core.handler.AsDtoHandler import AsDtoHandler
from hypertube.core.handler.DtoPropertyHandler import DtoPropertyHandler
from hypertube.core.handler.ProjectResultAsDtoHandler import ProjectResultAsDtoHandler
from hypertube.core.handler.PassByValueHandler import PassByValueHandler
from hypertube.core.handler.ContextMetadataHandler import ContextMetadataHandler
from hypertube.core.valueTypesParser.ValueTypeParser import ValueTypeParser


from hypertube.core.handler.HandlerDictionary import handler_dict
from hypertube.core.referenceCache.ReferencesCache import ReferencesCache
from hypertube.utils.TypesHandler import TypesHandler
from hypertube.utils.exception.ExceptionSerializer import ExceptionSerializer
from hypertube.utils.CommandType import CommandType
from hypertube.utils.Command import Command


class Handler:
    _initialized = False

    @staticmethod
    def _initialize():
        """Initialize the handler dictionary. Should be called once."""
        if not Handler._initialized:
            handler_dict[CommandType.Value] = ValueHandler()
            handler_dict[CommandType.LoadLibrary] = LoadLibraryHandler()
            handler_dict[CommandType.InvokeStaticMethod] = InvokeStaticMethodHandler()
            handler_dict[CommandType.GetStaticField] = GetStaticFieldHandler()
            handler_dict[CommandType.SetStaticField] = SetStaticFieldHandler()
            handler_dict[CommandType.CreateClassInstance] = CreateClassInstanceHandler()
            handler_dict[CommandType.GetType] = GetTypeHandler()
            handler_dict[CommandType.Reference] = ResolveInstanceHandler()
            handler_dict[CommandType.GetModule] = GetModuleHandler()
            handler_dict[CommandType.InvokeInstanceMethod] = InvokeInstanceMethodHandler()
            handler_dict[CommandType.Exception] = ExceptionHandler()
            handler_dict[CommandType.HeartBeat] = HeartBeatHandler()
            handler_dict[CommandType.Cast] = CastingHandler()
            handler_dict[CommandType.GetInstanceField] = GetInstanceFieldHandler()
            handler_dict[CommandType.Optimize] = OptimizeHandler()
            handler_dict[CommandType.GenerateLib] = GenerateLibHandler()
            handler_dict[CommandType.InvokeGlobalFunction] = InvokeGlobalFunctionHandler()
            handler_dict[CommandType.DestructReference] = DestructReferenceHandler()
            handler_dict[CommandType.ArrayReference] = ArrayReferenceHandler()
            handler_dict[CommandType.ArrayGetItem] = ArrayGetItemHandler()
            handler_dict[CommandType.ArrayGetSize] = ArrayGetSizeHandler()
            handler_dict[CommandType.ArrayGetRank] = ArrayGetRankHandler()
            handler_dict[CommandType.ArraySetItem] = ArraySetItemHandler()
            handler_dict[CommandType.Array] = ArrayHandler()
            handler_dict[CommandType.RetrieveArray] = RetrieveArrayHandler()
            handler_dict[CommandType.SetInstanceField] = SetInstanceFieldHandler()
            handler_dict[CommandType.InvokeGenericStaticMethod] = InvokeGenericStaticMethodHandler()
            handler_dict[CommandType.InvokeGenericMethod] = InvokeGenericMethodHandler()
            handler_dict[CommandType.GetEnumItem] = GetEnumItemHandler()
            handler_dict[CommandType.GetEnumName] = GetEnumNameHandler()
            handler_dict[CommandType.GetEnumValue] = GetEnumValueHandler()
            handler_dict[CommandType.AsRef] = AsRefHandler()
            handler_dict[CommandType.AsOut] = AsOutHandler()
            handler_dict[CommandType.GetRefValue] = GetRefValueHandler()
            handler_dict[CommandType.EnableNamespace] = EnableNamespaceHandler()
            handler_dict[CommandType.EnableType] = EnableTypeHandler()
            handler_dict[CommandType.CreateNull] = CreateNullHandler()
            handler_dict[CommandType.GetStaticMethodAsDelegate] = GetStaticMethodAsDelegateHandler()
            handler_dict[CommandType.GetInstanceMethodAsDelegate] = GetInstanceMethodAsDelegateHandler()
            handler_dict[CommandType.PassDelegate] = PassDelegateHandler()
            handler_dict[CommandType.InvokeDelegate] = InvokeDelegateHandler()
            handler_dict[CommandType.ConvertType] = ConvertTypeHandler()
            handler_dict[CommandType.AddEventListener] = AddEventListenerHandler()
            handler_dict[CommandType.PluginWrapper] = PluginWrapperHandler()
            handler_dict[CommandType.GetAsyncOperationResult] = GetAsyncOperationResultHandler()
            handler_dict[CommandType.AsKwargs] = GetKwargHandler()
            handler_dict[CommandType.GetResultType] = GetResultTypeHandler()
            handler_dict[CommandType.GetGlobalField] = GetGlobalFieldHandler()
            handler_dict[CommandType.RegisterForUpdate] = RegisterForUpdateHandler()
            handler_dict[CommandType.ValueForUpdate] = ValueForUpdateHandler()
            handler_dict[CommandType.AsDto] = AsDtoHandler()
            handler_dict[CommandType.DtoProperty] = DtoPropertyHandler()
            handler_dict[CommandType.ProjectResultAsDto] = ProjectResultAsDtoHandler()
            handler_dict[CommandType.PassByValue] = PassByValueHandler()
            handler_dict[CommandType.ContextMetadata] = ContextMetadataHandler()
            Handler._initialized = True

    def __init__(self):
        """Initialize Handler instance and set up handler dictionary if not already done."""
        Handler._initialize()

    @staticmethod
    def handle_command(command):
        """
        Handle a command by routing it to the appropriate handler.

        Args:
            command: The command to handle.

        Returns:
            Command: The response command.
        """
        Handler._initialize()
        try:
            if command.command_type == CommandType.PluginWrapper:
                command = PluginWrapperHandler().handle_command(command)

            if command.command_type == CommandType.ContextMetadata:
                handler_dict[CommandType.ContextMetadata].process(command)
                command = command.payload[1]

            response = AbstractHandler.get_handler(command.command_type).handle_command(command)
            return Handler.__parse_response(response, command.runtime_name)
        except Exception as e:
            return ExceptionSerializer.serialize_exception(e, command)

    @staticmethod
    def __parse_response(response, runtime_name):
        if TypesHandler.is_primitive_or_none(response):
            response_command = Command.create_response(response, runtime_name)
        elif isinstance(response, Command):
            response_command = response
        elif ValueTypeParser.is_parsable_value_type(type(response)):
            response_command = ValueTypeParser.get_command_for_parsable_value_type(response, runtime_name)
        else:
            guid = ReferencesCache().cache_reference(response)
            response_command = Command.create_reference(guid, runtime_name)

        # Append ValueForUpdate commands from RegisterForUpdateHandler contexts
        contexts = RegisterForUpdateHandler._invocation_contexts.map
        if contexts:
            for guid, instance in list(contexts.items()):
                instance_guid = ReferencesCache().cache_reference(instance)
                update_cmd = Command(
                    runtime_name,
                    CommandType.ValueForUpdate,
                    [str(guid) if guid is not None else "", instance_guid]
                )
                response_command = response_command.add_arg_to_payload(update_cmd)

            contexts.clear()

        return response_command

    @staticmethod
    def __is_response_array(response):
        return isinstance(response, list)
