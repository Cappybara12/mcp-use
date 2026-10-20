# car.py

class Car:
    def __init__(self, name: str):
        self.name = name

    def get_name(self) -> str:
        return f"Samochód: {self.name}"