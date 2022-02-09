from abc import ABC, abstractmethod


class Parser(ABC):
    # абстрактные методы, который будет необходимо переопределять для каждого класса наследника
    @abstractmethod
    def save_to_csv(self):
        pass

    @abstractmethod
    def save_to_xls(self):
        pass

    @abstractmethod
    def save_to_txt(self):
        pass

# class Parser
