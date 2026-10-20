class TypesHandler:

    @staticmethod
    def is_primitive_or_none(item):
        return isinstance(item, (int, float, bool, str)) or item is None
