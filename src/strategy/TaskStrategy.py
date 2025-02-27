import pandas as pd
import geopandas as gpd
from src.abstract.TaskStrategy import TaskStrategy

class ShortestPath(TaskStrategy):
    def __init__(self) -> None:
        pass
    
    def prepare_input(self, 
                      input_gdf):
        # definer kolonnerne vi ønsker at udregne
        stort_tal = 100000.0 # initialiser float til 100km
        input_gdf['dist_path'] = stort_tal
        input_gdf['dist_input'] = stort_tal
        input_gdf['dist_stop'] = stort_tal
        input_gdf['stop_name'] = None
        input_gdf['stop_id'] = None
        input_gdf['stop_osmid'] = None
        input_gdf['stop_iGraph_id'] = None
        return input_gdf
    
    
    def argmin(self, lst):
        min_val = min(lst)
        return lst.index(min_val), min_val
    
    def associate_centroids_and_stops(self, 
                                      kvadratnet_df,
                                      stop_gdf,
                                      distances,
                                      centroid_nodes_ig,
                                      stop_nodes_ig):
        
        number_of_stops = len(distances)
        
        # iterer igennem igraph listen af centroider
        for idx, centroid_node_ig in enumerate(centroid_nodes_ig):
            # find det stop index som minimerer distancen mellem stop og centroide
            min_distance_stop_idx, min_distance = self.argmin([distances[stop_idx][centroid_node_ig] for stop_idx in range(0, number_of_stops)])
            min_distance_formatted = round(min_distance, ndigits=2)
            
            if min_distance < kvadratnet_df.loc[idx, 'dist_path']:
                # opdater distancen hvis den er mindre end den nuværende
                kvadratnet_df.loc[idx, 'dist_path'] = min_distance_formatted
                
                # opdater distance fra stop til node, stop navn og stop nummer
                stop_gdf_ig_match = stop_gdf[stop_gdf['iGraph_id']==stop_nodes_ig[min_distance_stop_idx]]
                kvadratnet_df.loc[idx, 'dist_stop'] = stop_gdf_ig_match['dist_stop'].head(1).values
                kvadratnet_df.loc[idx, 'stop_name'] = stop_gdf_ig_match['stop_name'].head(1).values
                kvadratnet_df.loc[idx, 'stop_id'] = stop_gdf_ig_match['stop_code'].head(1).values
                kvadratnet_df.loc[idx, 'stop_osmid'] = stop_gdf_ig_match['osmid'].head(1).values
                kvadratnet_df.loc[idx, 'stop_iGraph_id'] = stop_gdf_ig_match['iGraph_id'].head(1).values
        
        # beregn total distance fra centroid -> node -> node -> stop
        kvadratnet_df['dist_total'] = (kvadratnet_df['dist_path'] 
                                    + kvadratnet_df['dist_input'] 
                                    + kvadratnet_df['dist_stop'])
                
        return kvadratnet_df
    
    
    def get_route_items(self, kvadratnet):
        centroids = kvadratnet['iGraph_id'].tolist()
        closest_stops = kvadratnet['stop_iGraph_id'].tolist()
        return centroids, closest_stops
    
    
    def prepare_output(self,
                       kvadratnet_df):
        # sæt sti på vejnettet som geometri
        output = kvadratnet_df.set_geometry('the_geom')
        
        # behold kun relevante kolonner
        output = output[['id', 'the_geom', 'dist_total', 'dist_path', 'dist_input', 'dist_stop', 'stop_name', 'stop_id', 'stop_osmid', 'osmid']]
        
        # formater datatyper og afrunding
        output['dist_total'] = output['dist_total'].round(2)
        output['dist_path'] = output['dist_path'].round(2)
        output['dist_input'] = output['dist_input'].round(2)
        output['dist_stop'] = output['dist_stop'].round(2)
        output['stop_name'] = output['stop_name'].astype(str)
        output['stop_id'] = output['stop_id'].astype(str)
        output['stop_osmid'] = output['stop_osmid'].astype(str)
        output['osmid'] = output['osmid'].astype(str)
        
        return output
    
    
    def get_output_suffix(self):
        return 'shortestpath.shp'
    
    
    def write_output(self, output, path, filename) -> None:
        output.to_file(path + filename, 
                       driver='ESRI Shapefile')
        
    