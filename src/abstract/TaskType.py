from abc import ABC, abstractmethod

class TaskType(ABC):
    @abstractmethod
    def prepare_input(self):
        pass
    
    @abstractmethod
    def add_smallest_distance_to_centroid(self):
        pass
    
    @abstractmethod
    def should_routes_be_calculated(self):
        pass
    
    @abstractmethod
    def prepare_output(self):
        pass
    
    