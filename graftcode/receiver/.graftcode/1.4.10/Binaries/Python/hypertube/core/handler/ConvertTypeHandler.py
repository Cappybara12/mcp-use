from hypertube.core.handler.AbstractHandler import AbstractHandler
from hypertube.utils.Type import Type


class ConvertTypeHandler(AbstractHandler):
    def process(self, command):
        return Type.HypertubeNoneType
