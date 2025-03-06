import pandas as pd
import geopandas as gpd
import numpy as np
from src.abstract.TaskStrategy import TaskStrategy

#####################################################
# Find det nærmeste stop
#####################################################
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
    
    
    def associate_centroids_and_stops(self, 
                                      kvadratnet_df,
                                      stop_gdf,
                                      distances,
                                      centroid_nodes_ig,
                                      stop_nodes_ig):
        
        distances = np.array(distances)
        
        # iterer igennem igraph listen af centroider
        for idx, centroid_node_ig in enumerate(centroid_nodes_ig):
            # find det stop index som minimerer distancen mellem stop og centroide
            min_distance_stop_idx = np.argmin(distances[:, centroid_node_ig])
            min_distance = distances[min_distance_stop_idx, centroid_node_ig]
            min_distance_formatted = round(min_distance, 2)
            
            if min_distance < kvadratnet_df.loc[idx, 'dist_path']:
                # opdater distancen hvis den er mindre end den nuværende
                kvadratnet_df.loc[idx, 'dist_path'] = min_distance_formatted
                
                # find matchende stop
                stop_igraph_id = stop_nodes_ig[min_distance_stop_idx]
                stop_gdf_match = stop_gdf[stop_gdf['iGraph_id'] == stop_igraph_id]
                
                # opdater værdier som skal gemmes
                if not stop_gdf_match.empty:
                    kvadratnet_df.loc[idx, 'dist_stop'] = stop_gdf_match['dist_stop'].values[0]
                    kvadratnet_df.loc[idx, 'stop_name'] = stop_gdf_match['stop_name'].values[0]
                    kvadratnet_df.loc[idx, 'stop_id'] = stop_gdf_match['stop_code'].values[0]
                    kvadratnet_df.loc[idx, 'stop_osmid'] = stop_gdf_match['osmid'].values[0]
                    kvadratnet_df.loc[idx, 'stop_iGraph_id'] = stop_gdf_match['iGraph_id'].values[0]
        
        # beregn total distance fra centroid -> node -> node -> stop
        kvadratnet_df['dist_total'] = (kvadratnet_df['dist_path'] 
                                    + kvadratnet_df['dist_input'] 
                                    + kvadratnet_df['dist_stop'])
        
        del distances
                
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


#####################################################
# Find alle stop indenfor distance
#####################################################
class AllNearbyStops(TaskStrategy):
    def __init__(self, max_distances: list) -> None:
        assert isinstance(max_distances, list), 'max_distance skal være en liste f.eks. [500] eller [500, 1000]'
        self.max_distances = max_distances
    
    
    def prepare_input(self, 
                      input_gdf):
        
        # tilføj en kolonne for hver distance.
        # hver række i kolonnen vil indeholde en tekststreng hvor stop er ";"-separaret
        for max_dist in self.max_distances:
            input_gdf[f'stops_{max_dist}'] = ''
            
        return input_gdf
    
    
    def associate_centroids_and_stops(self, 
                                      kvadratnet_df,
                                      stop_gdf,
                                      distances,
                                      centroid_nodes_ig,
                                      stop_nodes_ig):
        
        distances = np.array(distances)
        stop_nodes_ig = np.array(stop_nodes_ig)
        
        # iterer igennem igraph listen af centroider
        for idx, centroid_node_ig in enumerate(centroid_nodes_ig):
            
            # iterer igennem alle max distancer
            for max_dist in self.max_distances:
                # find alle stop med kortere distance
                dist_mask = distances[:, centroid_node_ig] <= max_dist
                
                # find deres igraph id'er og find datarækkerne som matcher
                stop_igraph_ids = stop_nodes_ig[dist_mask]
                stop_gdf_match = stop_gdf[stop_gdf['iGraph_id'].isin(stop_igraph_ids)]
                
                # lav stop id'er til en tekst og join til en samlet tekststreng og sammensæt med nuværende
                new_nearby_stops = ';'.join(stop_gdf_match['stop_code'].astype(str).tolist())
                old_nearby_stops = kvadratnet_df.loc[idx, f'stops_{max_dist}']
                if old_nearby_stops == '':
                    kvadratnet_df.loc[idx, f'stops_{max_dist}'] = new_nearby_stops
                else:
                    kvadratnet_df.loc[idx, f'stops_{max_dist}'] = old_nearby_stops + ';' + new_nearby_stops
        
        del distances
        
        return kvadratnet_df
    
    
    def get_route_items(self, kvadratnet):
        # der skal ikke findes rutegeometrier fra hvert kvadrat til hvert stop indenfor distance
        centroids = []
        closest_stops = []
        return centroids, closest_stops
    
    
    def prepare_output(self,
                       kvadratnet_df):
        
        # behold kun relevant kolonner
        output = kvadratnet_df[['id', 'osmid'] + [f'stops_{max_dist}' for max_dist in self.max_distances]]
        
        # formater datatyper og afrunding
        output['osmid'] = output['osmid'].astype(str)
        
        return output
    
    
    def get_output_suffix(self):
        return 'allnearbystops.csv'
    
    
    def write_output(self, output, path, filename) -> None:
        output.to_csv(path + filename, sep=',', header=True)

    
    