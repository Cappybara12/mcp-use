import uuid
import threading


class DelegatesCache(object):
    _instance = None
    delegates_cache = dict()
    _lock = threading.Lock()  # Initialize a lock object

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(DelegatesCache, cls).__new__(cls)
        return cls._instance

    def add_delegate(self, object_delegate):
        with self._lock:
            uuid_ = str(uuid.uuid4())
            self.delegates_cache[uuid_] = object_delegate
            return uuid_

    def get_delegate(self, delegate_guid):
        with self._lock:
            try:
                return self.delegates_cache[delegate_guid]
            except KeyError:
                raise Exception("Object not found in delegates")
