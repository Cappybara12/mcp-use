from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.core.handler.GetInstanceFieldHandler import GetInstanceFieldHandler
from hypertube.core.valueTypesParser.ValueTypeParser import ValueTypeParser
from hypertube.utils.Command import Command
from hypertube.utils.CommandType import CommandType
from hypertube.utils.RuntimeName import RuntimeName
from hypertube.utils.TypesHandler import TypesHandler


class PassByValueHandler(AbstractHandler):
    _required_parameters_count = 1

    def process(self, command):
        self.validate(command, self._required_parameters_count, self.__class__.__name__)
        instance = command.payload[0]
        return self._project_value(instance)

    def _project_value(self, value):
        if TypesHandler.is_primitive_or_none(value):
            return value

        if isinstance(value, (list, tuple)):
            projected_elements = [self._project_value(item) for item in value]
            return Command(RuntimeName.python, CommandType.Array, projected_elements)

        if ValueTypeParser.is_parsable_value_type(type(value)):
            return ValueTypeParser.get_command_for_parsable_value_type(value, RuntimeName.python)

        return self._project_object(value)

    def _project_object(self, instance):
        type_name = instance.__class__.__name__
        module_name = getattr(instance.__class__, "__module__", "")
        if module_name:
            type_name = f"{module_name}.{type_name}".lstrip(".")

        property_names = []
        if hasattr(instance, "__dict__"):
            for property_name in instance.__dict__.keys():
                if property_name not in property_names:
                    property_names.append(property_name)

        for property_name, property_value in vars(instance.__class__).items():
            if isinstance(property_value, property) and property_name not in property_names:
                property_names.append(property_name)

        get_type_command = Command(RuntimeName.python, CommandType.GetType, [type_name])
        current_chain = Command(RuntimeName.python, CommandType.CreateClassInstance, [get_type_command])

        get_instance_field_handler = GetInstanceFieldHandler()
        for property_name in property_names:
            property_value = get_instance_field_handler.process(
                Command(RuntimeName.python, CommandType.GetInstanceField, [instance, property_name])
            )
            projected_value = self._project_value(property_value)
            current_chain = Command(
                RuntimeName.python,
                CommandType.SetInstanceField,
                [current_chain, property_name, projected_value],
            )

        return current_chain
