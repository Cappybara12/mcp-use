from hypertube.core.handler.AbstractHandler import AbstractHandler

class AsRefHandler(AbstractHandler):
    def process(self, command):
        raise NotImplementedError(f"{self.__class__.__name__} is not implemented in Python")

