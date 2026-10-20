from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.utils.CommandType import CommandType
from hypertube.utils.RuntimeName import RuntimeName
from hypertube.utils.connectionData.InMemoryConnectionData import InMemoryConnectionData
from hypertube.utils.Command import Command
from hypertube.utils.exception.ExceptionThrower import ExceptionThrower


class PassDelegateHandler(AbstractHandler):
    _required_parameters_count = 1

    def process(self, command):
        try:
            self.validate(command, self._required_parameters_count, self.__class__.__name__)

            delegate_guid = command.payload[0]
            calling_runtime = RuntimeName(command.payload[1])

            # not used in this context, but kept for reference
            #parameters_from_command = command.payload[2:] if len(command.payload) > 2 else []
            #delegate_param_types = parameters_from_command[:-1]
            #delegate_return_type = parameters_from_command[-1] if parameters_from_command else None

            def dynamic_delegate(*args):
                # Prepare the command to invoke the delegate
                args_array = [delegate_guid] + list(args)
                invoke_delegate_command = Command(
                    calling_runtime,
                    CommandType.InvokeDelegate,
                    args_array
                )
                from hypertube.core.interpreter.Interpreter import Interpreter
                response = Interpreter.execute(invoke_delegate_command, InMemoryConnectionData())
                if response.command_type == CommandType.Exception:
                    raise Exception("Exception occurred while invoking delegate:\n" + str(ExceptionThrower.throw_exception(response)))

                # not used in this context, but kept for reference
                # if delegate_return_type is not None and delegate_return_type.__name__ == "HypertubeVoidType":
                #     return None

                return response.payload[0] if response.payload else None

            return dynamic_delegate

        except Exception as e:
            exc_type, exc_value = type(e), e
            new_exc = exc_type(exc_value).with_traceback(e.__traceback__)
            raise new_exc from None