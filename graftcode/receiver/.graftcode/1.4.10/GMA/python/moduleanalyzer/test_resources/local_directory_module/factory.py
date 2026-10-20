# factory.py

from .car import Car


class CarFactory:
    def __init__(self, factoryName: str):
        self.factoryName = factoryName

    def create_car(self, name: str) -> Car:
        return Car(name)
