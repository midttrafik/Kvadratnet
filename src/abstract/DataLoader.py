from abc import ABC, abstractmethod

class DataLoader(ABC):
    @abstractmethod
    def get_data(self):
        pass