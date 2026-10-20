# giga_factory.py

from .car import Car
from .factory import CarFactory


class GigaFactory:
    def __init__(self):
        self.factory = CarFactory()

    def build_super_car(self, name: str) -> Car:
        return self.factory.create_car(name)
