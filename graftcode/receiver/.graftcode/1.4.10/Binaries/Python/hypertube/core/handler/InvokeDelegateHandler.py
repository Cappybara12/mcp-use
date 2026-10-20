from hypertube.core.delegateCache.DelegatesCache import DelegatesCache
from hypertube.core.handler.AbstractHandler import AbstractHandler


class InvokeDelegateHandler(AbstractHandler):

    def __init__(self):
        self._required_parameters_count = 1

    def process(self, command):
        self.validate(command, self._required_parameters_count, self.__class__.__name__)

        delegates_cache = DelegatesCache()
        method = delegates_cache.get_delegate(command.payload[0])
        arguments, kwargs = self._split_arguments_and_kwargs(command.payload, 1)
        return self.resolve_async_result(method(*arguments, **kwargs))


