import os
import sys
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname+'\\..')
sys.path.insert(0, os.getcwd())

import pandas as pd
import numpy as np
from src.strategy.TaskStrategy import *

import unittest


class TestShortestPath(unittest.TestCase):
    def setUp(self):
        # Example centroid data
        kvadratnet_data = {
            'id': [0, 1, 2, 3],
            'osmid': [100, 101, 102, 103],
            'iGraph_id': [0, 1, 2, 3],
            'dist_path': [100000, 100000, 100000, 9],  # nuværende fundet korteste distance
            'dist_input': [5, 10, 7, 2],  # distance fra centroid til nærmeste osmid
            'dist_stop': [100000, 100000, 100000, 2], # nuværende distance fra nærmeste stop til dets osmid
            'stop_name': [None, None, None, 'Stop E'], # nuværende nærmeste stop
            'stop_id': [None, None, None, 105],
            'stop_osmid': [None, None, None, 1005],
            'stop_iGraph_id': [None, None, None, 50]
        }
        self.kvadratnet_df = pd.DataFrame(kvadratnet_data)

        # Example stop data
        stop_data = {
            'stop_name': ['Stop A', 'Stop B', 'Stop C', 'Stop D'],  # Stop navn
            'stop_code': [101, 102, 103, 104],  # Stop nummer
            'dist_stop': [3, 4, 2, 4],  # distance fra stop til nærmeste osmid
            'osmid': [1001, 1002, 1003, 1004],
            'iGraph_id': [10, 20, 30, 40]
        }
        self.stop_gdf = pd.DataFrame(stop_data)

        # Example computed distances (stop-to-centroid matrix)
        self.distances = np.array([
            [20, 50, 25, 10],  # Stop A til centroids
            [15, 30, 25, 12],  # Stop B til centroids
            [5, 40, 10, 25],   # Stop C til centroids
            [50, 999, 10, 10]  # Stop D til centroids
        ])

        self.centroid_nodes_ig = kvadratnet_data['iGraph_id']
        self.stop_nodes_ig = stop_data['iGraph_id']
        
        self.task_strategy = ShortestPath()
    
    
    # test om filnavnet får den rigtige endelse
    def test_output_suffix(self):
        self.assertEqual(self.task_strategy.get_output_suffix(), 'shortestpath.shp')


    # test om navn på nærmeste stop tildeles korrekt til hvert kvadrat
    def test_stop_name(self):
        updated_kvadratnet_df = self.task_strategy.associate_centroids_and_stops(
                                                              self.kvadratnet_df, 
                                                              self.stop_gdf, 
                                                              self.distances, 
                                                              self.centroid_nodes_ig, 
                                                              self.stop_nodes_ig)

        expected_stop_names = ['Stop C', 'Stop B', 'Stop C', 'Stop E']
        
        self.assertEqual(updated_kvadratnet_df['stop_name'].tolist(), expected_stop_names)
    
    
    # test om distance fra stop til osm node tildeles korrekt til hvert kvadrat
    def test_stop_dist(self):
        updated_kvadratnet_df = self.task_strategy.associate_centroids_and_stops(
                                                              self.kvadratnet_df, 
                                                              self.stop_gdf, 
                                                              self.distances, 
                                                              self.centroid_nodes_ig, 
                                                              self.stop_nodes_ig)

        expected_stop_dist = [2, 4, 2, 2]
        
        self.assertEqual(updated_kvadratnet_df['dist_stop'].tolist(), expected_stop_dist)
    
    
    # test om total distance udregnes korrekt for hvert kvadrat
    def test_total_dist(self):
        updated_kvadratnet_df = self.task_strategy.associate_centroids_and_stops(
                                                              self.kvadratnet_df, 
                                                              self.stop_gdf, 
                                                              self.distances, 
                                                              self.centroid_nodes_ig, 
                                                              self.stop_nodes_ig)


        expected_total_dist = [5+5+2, 10+30+4, 7+10+2, 2+9+2]
        
        self.assertEqual(updated_kvadratnet_df['dist_total'].tolist(), expected_total_dist)



class TestAllNearbyStops(unittest.TestCase):
    def setUp(self):
        # Kvadratnet data
        kvadratnet_data = {
            'id': [0, 1, 2, 3], # kvadratnet id
            'osmid': [100, 101, 102, 103],
            'iGraph_id': [0, 1, 2, 3],
            'stops_10': ['', '', '', 'Stop E'], # nuværende liste af stop indenfor 10m
            'stops_20': ['', '', '', 'Stop E'] # nuværende liste af stop indenfor 20m
        }
        self.kvadratnet_df = pd.DataFrame(kvadratnet_data)

        # Stop data
        stop_data = {
            'stop_name': ['Stop A', 'Stop B', 'Stop C', 'Stop D'],  # Stop navne
            'stop_code': [101, 102, 103, 104],  # Stop nummer
            'dist_stop': [3, 4, 2, 4],  # Distance fra stop til nærmeste OSM node
            'osmid': [1001, 1002, 1003, 1004],  # Nærmeste OSM node
            'iGraph_id': [10, 20, 30, 40]  # iGraph ID for stop
        }
        self.stop_gdf = pd.DataFrame(stop_data)

        # Distance data
        self.distances = np.array([
            [20, 50, 25, 10],  # Stop A til centroids
            [15, 30, 25, 12],  # Stop B til centroids
            [5, 40, 10, 25],   # Stop C til centroids
            [50, 999, 10, 10]  # Stop D til centroids
        ])

        self.centroid_nodes_ig = kvadratnet_data['iGraph_id']
        self.stop_nodes_ig = stop_data['iGraph_id']
        
        # sæt distancer til 10m og 20m
        self.task_strategy = AllNearbyStops(max_distances=[10, 20])
    
    
    # test om filnavnet får den rigtige endelse
    def test_output_suffix(self):
        self.assertEqual(self.task_strategy.get_output_suffix(), 'allnearbystops.csv')
        
        
    # test om listen af stop udregnes korrekt for hvert kvadrat
    def test_stop_names(self):
        updated_kvadratnet_df = self.task_strategy.associate_centroids_and_stops(
            self.kvadratnet_df,
            self.stop_gdf,
            self.distances,
            self.centroid_nodes_ig,
            self.stop_nodes_ig
        )
        
        expected_stop_names_10 = ['Stop C', '', 'Stop C;Stop D', 'Stop E;Stop A;Stop D']
        expected_stop_names_20 = ['Stop A;Stop B;Stop C', '', 'Stop C;Stop D', 'Stop E;Stop A;Stop B;Stop C']
        
        self.assertEqual(updated_kvadratnet_df['stops_10'].tolist(), expected_stop_names_10)
        self.assertEqual(updated_kvadratnet_df['stops_20'].tolist(), expected_stop_names_20)




if __name__ == '__main__':
    unittest.main(verbosity=2)
