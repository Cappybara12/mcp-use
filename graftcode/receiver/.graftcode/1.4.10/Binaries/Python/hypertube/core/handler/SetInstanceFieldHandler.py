from hypertube.core.handler.AbstractHandler import AbstractHandler
import inspect


class SetInstanceFieldHandler(AbstractHandler):

    def __init__(self):
        self._required_parameters_count = 3

    def process(self, command):
        try:
            self.validate(command, self._required_parameters_count, self.__class__.__name__)
            instance = command.payload[0]
            field = command.payload[1]
            new_value = command.payload[2]

            # Do not create new attributes dynamically; only allow existing fields.
            try:
                inspect.getattr_static(instance, field)
            except AttributeError as e:
                raise AttributeError(self.__build_attribute_error_message(instance, field, new_value, e))

            try:
                setattr(instance, field, new_value)
            except AttributeError as e:
                raise AttributeError(self.__build_attribute_error_message(instance, field, new_value, e))
            return instance
        except Exception as e:
            exc_type, exc_value = type(e), e
            new_exc = exc_type(exc_value).with_traceback(e.__traceback__)
            raise new_exc from None

    def __build_attribute_error_message(self, instance, field, new_value, error):
        fields = [attr for attr in dir(instance) if not callable(getattr(instance, attr, None))]
        value_type = type(new_value).__name__ if new_value is not None else "null"
        class_name = instance.__class__.__name__
        message = "Failed to set value of type {} for {} in class {}.\nAvailable public instance attributes:\n".format(value_type, field, class_name)
        for attr in fields:
            message += "{}\n".format(attr)
        message += "Root error message: {}".format(str(error))
        return message

