from hypertube.core.transmitter.TransmitterWrapper import TransmitterWrapper


class Transmitter:

    @staticmethod
    def send_command(message, config_source):
        return TransmitterWrapper.send_command(message, config_source)

    @staticmethod
    def activate(license_key):
        return TransmitterWrapper.activate(license_key)

    @staticmethod
    def set_config_source(source_path):
        return TransmitterWrapper.set_config_source(source_path)

    @staticmethod
    def set_working_directory(path):
        return TransmitterWrapper.set_working_directory(path)