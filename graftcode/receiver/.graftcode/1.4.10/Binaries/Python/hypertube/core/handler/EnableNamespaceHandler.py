from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.core.namespaceCache.NamespaceCache import NamespaceCache


class EnableNamespaceHandler(AbstractHandler):
    def __init__(self):
        self._required_parameters_count = 1

    def process(self, command):
        try:
            self.validate(command, self._required_parameters_count, self.__class__.__name__)

            namespace_cache = NamespaceCache()

            for payload in command.payload:
                if isinstance(payload, str):
                    namespace_cache.cache_namespace(payload)
                if isinstance(payload, list):
                    for namespace_to_enable in payload:
                        namespace_cache.cache_namespace(namespace_to_enable)

            return 0

        except Exception as e:
            exc_type, exc_value = type(e), e
            new_exc = exc_type(exc_value).with_traceback(e.__traceback__)
            raise new_exc from None
