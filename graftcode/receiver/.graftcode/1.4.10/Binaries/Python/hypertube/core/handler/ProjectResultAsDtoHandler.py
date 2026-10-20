from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.core.handler.GetInstanceFieldHandler import GetInstanceFieldHandler
from hypertube.utils.Command import Command
from hypertube.utils.CommandType import CommandType


class ProjectResultAsDtoHandler(AbstractHandler):
    def __init__(self):
        self._required_parameters_count = 1

    def process(self, command):
        self.validate(command, self._required_parameters_count, self.__class__.__name__)

        instance = command.payload[0]
        response_array = [None] * (len(command.payload) + 1)
        response_array[0] = instance

        type_name = getattr(instance.__class__, '__module__', '') + '.' + instance.__class__.__name__
        if type_name.startswith('.'):
            type_name = type_name[1:]
        if not type_name:
            type_name = instance.__class__.__name__

        response_array[1] = Command(command.runtime_name, CommandType.GetType, [type_name])

        get_instance_field_handler = GetInstanceFieldHandler()
        for i in range(1, len(command.payload)):
            property_name = command.payload[i]
            property_value = get_instance_field_handler.process(
                Command(command.runtime_name, CommandType.GetInstanceField, [instance, property_name])
            )
            response_array[i + 1] = Command(
                command.runtime_name, CommandType.DtoProperty, [property_name, property_value]
            )


        return response_array
