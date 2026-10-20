from hypertube.core.handler.AbstractHandler import AbstractHandler

class ValueForUpdateHandler(AbstractHandler):
    def process(self, command):
        # Special-cased in Handler.handle_command; placeholder only.
        raise NotImplementedError(f"{self.__class__.__name__} is not implemented in Python.")
