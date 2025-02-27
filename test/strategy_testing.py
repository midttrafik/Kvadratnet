import os
import sys
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname+'\\..')
sys.path.insert(0, os.getcwd())

import pandas as pd
import numpy as np
from src.strategy.TaskStrategy import ShortestPath

import unittest

class TestShortestPath(unittest.TestCase):
    def setUp(self):
        # Example centroid data
        kvadratnet_data = {
            'centroid_id': [0, 1, 2, 3],  # ID
            'dist_path': [100000, 100000, 100000, 9],  # Current shortest distances
            'dist_input': [5, 10, 7, 2],  # Distance from centroid to nearest OSMID
            'dist_stop': [None, None, None, 2],  
            'stop_name': [None, None, None, 'Stop E'],
            'stop_id': [None, None, None, 105],
            'stop_osmid': [None, None, None, 1005],
            'stop_iGraph_id': [None, None, None, 50]
        }
        self.kvadratnet_df = pd.DataFrame(kvadratnet_data)

        # Example stop data
        stop_data = {
            'stop_name': ['Stop A', 'Stop B', 'Stop C', 'Stop D'],  # Stop names
            'stop_code': [101, 102, 103, 104],  # Stop codes
            'dist_stop': [3, 4, 2, 4],  # Distance from stop to nearest OSMID
            'osmid': [1001, 1002, 1003, 1004],  # Nearest OSMID
            'iGraph_id': [10, 20, 30, 40]  # iGraph ID for stops
        }
        self.stop_gdf = pd.DataFrame(stop_data)

        # Example computed distances (stop-to-centroid matrix)
        self.distances = np.array([
            [20, 50, 25, 10],  # Stop A to centroids
            [15, 30, 25, 12],  # Stop B to centroids
            [5, 40, 10, 25],   # Stop C to centroids
            [50, 999, 10, 10]  # Stop D to centroids
        ])

        self.centroid_nodes_ig = kvadratnet_data['centroid_id']
        self.stop_nodes_ig = stop_data['iGraph_id']
        
        self.task_strategy = ShortestPath()

    def test_stop_name(self):
        updated_kvadratnet_df = self.task_strategy.associate_centroids_and_stops(
                                                              self.kvadratnet_df, 
                                                              self.stop_gdf, 
                                                              self.distances, 
                                                              self.centroid_nodes_ig, 
                                                              self.stop_nodes_ig)

        expected_stop_names = ['Stop C', 'Stop B', 'Stop C', 'Stop E']
        
        self.assertEqual(updated_kvadratnet_df['stop_name'].tolist(), expected_stop_names)
    
    def test_total_dist(self):
        updated_kvadratnet_df = self.task_strategy.associate_centroids_and_stops(
                                                              self.kvadratnet_df, 
                                                              self.stop_gdf, 
                                                              self.distances, 
                                                              self.centroid_nodes_ig, 
                                                              self.stop_nodes_ig)


        expected_total_dist = [5+5+2, 10+30+4, 7+10+2, 2+9+2]
        
        self.assertEqual(updated_kvadratnet_df['dist_total'].tolist(), expected_total_dist)


if __name__ == '__main__':
    unittest.main()
