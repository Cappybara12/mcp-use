"""Test module for setup.py based project."""


class DataService:
    """Service for data operations."""

    def __init__(self, name: str):
        """Initialize service with name."""
        self.name = name

    def process(self, data: list) -> list:
        """Process data."""
        return [item for item in data if item]


def filter_none(items: list) -> list:
    """Filter None values from list."""
    return [item for item in items if item is not None]


MAX_ITEMS = 100
