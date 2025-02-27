from abc import ABC, abstractmethod

class TaskStrategy(ABC):
    @abstractmethod
    def prepare_input(self, input_gdf):
        pass
    
    @abstractmethod
    def associate_centroids_and_stops(self,
                                      kvadratnet_df,
                                      stop_gdf,
                                      distances,
                                      centroid_nodes_ig,
                                      stop_nodes_ig):
        pass
    
    @abstractmethod
    def should_routes_be_calculated(self):
        pass
    
    @abstractmethod
    def prepare_output(self, 
                       kvadratnet_df):
        pass
    
    @abstractmethod
    def get_output_suffix(self):
        pass
    
    