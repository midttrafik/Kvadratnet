from abc import ABC, abstractmethod

class TaskStrategy(ABC):
    """ Strategy Interface til alle typer af opgaver.
    """
    
    @abstractmethod
    def prepare_input(self, input_gdf):
        """ Tilføj kolonner som denne strategi skal bruge.

        Args:
            input_gdf (GeoDataFrame): kvadratnet
        
        Output:
            - kvadratnet med nye kolonner
        """
        pass
    
    @abstractmethod
    def associate_centroids_and_stops(self,
                                      kvadratnet_df,
                                      stop_gdf,
                                      distances,
                                      centroid_nodes_ig,
                                      stop_nodes_ig):
        """ Tilføj stop til kvadratnet hvis de opfylder en regel f.eks. nærmeste stop eller alle stop indenfor 500m.

        Args:
            kvadratnet_df (GeoDataFrame): kvadratnet
            stop_gdf (GeoDataFrame): stop
            distances (list): 2D liste hvor rækker er stop og kolonner er OSM nodes
            centroid_nodes_ig (list): liste over igraph node id'er for kvadratnet
            stop_nodes_ig (_type_): liste over igraph node id'er for stop
        
        Output:
            - kvadratnet hvor den/de relevante stop er skrevet ind
        """
        pass
    
    @abstractmethod
    def get_route_items(self, kvadratnet):
        """ Hent id'er på kvadratnet og tilhørende stop hvor geometrien for korteste vej skal udregnes.

        Args:
            kvadratnet (GeoDataFrame): kvadratnet
        
        Output:
            - igraph id'er for kvadratnet eller tom liste
            - igraph id'er for stop eller tom liste
        """            
        pass
    
    @abstractmethod
    def prepare_output(self, 
                       kvadratnet_df):
        """ Fjern kolonner som ikke er relevante for output.

        Args:
            kvadratnet_df (GeoDataFrame): kvadratnet
        
        Output:
            - kvadratnet klar til udskrivning
        """
        pass
    
    @abstractmethod
    def get_output_suffix(self):
        """ Endelse til output fil og filtype f.eks. shortestpath.shp.
        
        Output:
            - endelse til output fil
        """
        pass
    
    @abstractmethod
    def write_output(self, output, path, filename):
        """ Skriv kvadratnetsfil.

        Args:
            output (DataFrame/GeoDataFrame): kvadratnet
            path (str): sti hvor filen skal skrives
            filename (str): navn til output fil som er navn på input + suffix.
        
        Output:
            - intet
        """
        pass
    
    