from hypertube.core.referenceCache.ReferencesCache import ReferencesCache
from hypertube.core.handler.AbstractHandler import AbstractHandler


class DestructReferenceHandler(AbstractHandler):
    def __init__(self):
        self._required_parameters_count = 1

    def process(self, command):
        try:
            payload = command.payload
            try:
                self.validate(command, self._required_parameters_count, self.__class__.__name__)
            except Exception:
                return False

            reference_id = payload[0]
            if reference_id is None or not isinstance(reference_id, str):
                return False

            return ReferencesCache().delete_reference(reference_id)
        except Exception:
            raise
