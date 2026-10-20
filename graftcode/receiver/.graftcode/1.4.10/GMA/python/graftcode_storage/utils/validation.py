def throw_if_null_or_empty_or_whitespace(value, name: str) -> None:
    """
    Validates that `value` is not None, not an empty string, and not a string consisting
    solely of whitespace characters. Raises ValueError otherwise.

    :param value: The value to validate.
    :param name:  The name of the parameter, used in the error message.
    :raises ValueError: If `value` is None, empty, or only whitespace.
    """
    if value is None:
        raise ValueError(f"{name} cannot be None")
    if isinstance(value, str) and not value.strip():
        raise ValueError(f"{name} cannot be empty or whitespace")