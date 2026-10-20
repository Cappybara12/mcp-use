from hypertube.core.handler.AbstractHandler import AbstractHandler


class ValueHandler(AbstractHandler):
    def process(self, command):
        return command.payload[0]
