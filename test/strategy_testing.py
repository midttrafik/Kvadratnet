import os
import sys
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname+'\\..')
sys.path.insert(0, os.getcwd())

import pandas as pd
import numpy as np
from shapely import Point, LineString
from src.strategy.TaskStrategy import *

import unittest


class TestShortestPath(unittest.TestCase):
    def setUp(self):
        # eksempel på kvadratnet data
        kvadratnet_data = {
            'id': [0, 1, 2, 3],
            'geometry': [None, None, None, None], # original geometri
            'geometry_center': [None, None, None, None], # centroid af geometri
            'the_geom': [None, None, None, None], # geometri for korteste vej
            'osmid': [2000, 2001, 2002, 2003],
            'iGraph_id': [0, 1, 2, 3],
            'dist_path': [100000, 100000, 100000, 9],  # nuværende fundet korteste distance
            'dist_input': [5, 10, 7, 2],  # distance fra centroid til nærmeste osmid
            'dist_stop': [100000, 100000, 100000, 2], # nuværende distance fra nærmeste stop til dets osmid
            'stop_name': [None, None, None, 'Stop E'], # nuværende nærmeste stop
            'stop_id': [None, None, None, 105],
            'stop_osmid': [None, None, None, 2005],
            'stop_iGraph_id': [None, None, None, 50]
        }
        self.kvadratnet_gdf = gpd.GeoDataFrame(kvadratnet_data, crs='EPSG:25832').set_geometry('geometry_center')

        # eksempel på stop data
        stop_data = {
            'geometry': [None, None, None, None],
            'stop_name': ['Stop A', 'Stop B', 'Stop C', 'Stop D'], # stop navn
            'stop_code': [101, 102, 103, 104],  # Stop nummer
            'dist_stop': [3, 4, 2, 4],  # distance fra stop til nærmeste osmid
            'osmid': [1001, 1002, 1003, 1004],
            'iGraph_id': [10, 20, 30, 40]
        }
        self.stop_gdf = gpd.GeoDataFrame(stop_data, crs='EPSG:25832')

        # eksempel på distancer
        self.distances = np.array([
            [20, 50,  25, 10],  # Stop A til centroids
            [15, 30,  25, 12],  # Stop B til centroids
            [5,  40,  10, 25],  # Stop C til centroids
            [50, 999, 10, 10]   # Stop D til centroids
        ])

        self.centroid_nodes_ig = self.kvadratnet_gdf['iGraph_id']
        self.stop_nodes_ig = self.stop_gdf['iGraph_id']
        
        # vælg opgave
        self.task_strategy = ShortestPath()
        
        # opdater kvadratnet med nærmeste stop
        self.updated_kvadratnet_gdf = self.task_strategy.associate_centroids_and_stops(
            self.kvadratnet_gdf, 
            self.stop_gdf, 
            self.distances, 
            self.centroid_nodes_ig, 
            self.stop_nodes_ig
        )
    
    
    # test om filnavnet får den rigtige endelse
    def test_output_suffix(self):
        self.assertEqual(self.task_strategy.get_output_suffix(), 'shortestpath.shp')
        
    
    # test om output kun indeholder de relevante kolonner
    def test_prepare_output(self):
        output = self.task_strategy.prepare_output(self.updated_kvadratnet_gdf)
        
        expected_columns = ['id', 'the_geom', 'osmid', 'dist_total', 'dist_path', 'dist_input', 'dist_stop', 'stop_name', 'stop_id', 'stop_osmid']
        
        self.assertCountEqual(output.columns, expected_columns)
        self.assertTrue(isinstance(output, gpd.GeoDataFrame))


    # test om navn på nærmeste stop tildeles korrekt til hvert kvadrat
    def test_stop_name(self):
        expected_stop_names = ['Stop C', 'Stop B', 'Stop C', 'Stop E']
        
        self.assertListEqual(self.updated_kvadratnet_gdf['stop_name'].tolist(), expected_stop_names)
    
    
    # test om distance fra stop til osm node tildeles korrekt til hvert kvadrat
    def test_stop_dist(self):
        expected_stop_dist = [2, 4, 2, 2]
        
        self.assertListEqual(self.updated_kvadratnet_gdf['dist_stop'].tolist(), expected_stop_dist)
    
    
    # test om total distance udregnes korrekt for hvert kvadrat
    def test_total_dist(self):
        expected_total_dist = [5+5+2, 10+30+4, 7+10+2, 2+9+2]
        
        self.assertListEqual(self.updated_kvadratnet_gdf['dist_total'].tolist(), expected_total_dist)
    
    
    # test om der returneres centroide og stop id'er så rutegeometrier kan udregnes
    def test_route_items(self):
        centroids, closest_stops = self.task_strategy.get_route_items(self.updated_kvadratnet_gdf)
                
        self.assertTrue(len(centroids) > 0)
        self.assertTrue(len(closest_stops) > 0)



class TestAllNearbyStops(unittest.TestCase):
    def setUp(self):
        # eksempel på kvadratnet data
        kvadratnet_data = {
            'id': [0, 1, 2, 3], # kvadratnet id
            'geometry': [None, None, None, None], # original geometri
            'geometry_center': [None, None, None, None], # centroid af geometri
            'osmid': [2000, 2001, 2002, 2003],
            'iGraph_id': [0, 1, 2, 3],
            'dist_input': [5, 10, 7, 2],  # distance fra centroid til nærmeste osmid
            'stops_10': ['', '', '', '105'], # nuværende liste af stop indenfor 10m
            'stops_20': ['', '', '', '105'] # nuværende liste af stop indenfor 20m
        }
        self.kvadratnet_gdf = gpd.GeoDataFrame(kvadratnet_data, crs='EPSG:25832').set_geometry('geometry_center')

        # Eksempel på stop data
        stop_data = {
            'geometry': [None, None, None, None], # original geometri
            'stop_name': ['Stop A', 'Stop B', 'Stop C', 'Stop D'],  # Stop navne
            'stop_code': [101, 102, 103, 104],  # Stop nummer
            'dist_stop': [3, 4, 2, 4],  # Distance fra stop til nærmeste OSM node
            'osmid': [1001, 1002, 1003, 1004],
            'iGraph_id': [10, 20, 30, 40]
        }
        self.stop_gdf = gpd.GeoDataFrame(stop_data, crs='EPSG:25832')

        # eksempel på distance data
        self.distances = np.array([
            [20, 50,  25, 10], # Stop A til centroids
            [15, 30,  25, 12], # Stop B til centroids
            [5,  40,  10, 25], # Stop C til centroids
            [50, 999, 10, 10]  # Stop D til centroids
        ])

        self.centroid_nodes_ig = self.kvadratnet_gdf['iGraph_id']
        self.stop_nodes_ig = self.stop_gdf['iGraph_id']
        
        # sæt max_distancer til 10m og 20m
        self.task_strategy = AllNearbyStops(max_distances=[10, 20])
        
        # opdater kvadratnet med alle stop indenfor hhv. 10m og 20m
        self.updated_kvadratnet_gdf = self.task_strategy.associate_centroids_and_stops(
            self.kvadratnet_gdf, 
            self.stop_gdf, 
            self.distances, 
            self.centroid_nodes_ig, 
            self.stop_nodes_ig
        )
    
    
    # test om filnavnet får den rigtige endelse
    def test_output_suffix(self):
        self.assertEqual(self.task_strategy.get_output_suffix(), 'allnearbystops.csv')
        
        
    # test om listen af stop udregnes korrekt for hvert kvadrat
    def test_stop_names(self):
        expected_stop_names_10 = ['103', '', '103;104', '105;101;104'] # 'Stop C', '', 'Stop C;Stop D', 'Stop E;Stop A;Stop D'
        expected_stop_names_20 = ['101;102;103', '', '103;104', '105;101;102;104'] # 'Stop A;Stop B;Stop C', '', 'Stop C;Stop D', 'Stop E;Stop A;Stop B;Stop D'
        
        self.assertListEqual(self.updated_kvadratnet_gdf['stops_10'].tolist(), expected_stop_names_10)
        self.assertListEqual(self.updated_kvadratnet_gdf['stops_20'].tolist(), expected_stop_names_20)


    # test at der ikke returneres centroide og stop id'er da rutegeometrier ikke skal findes
    def test_route_items(self):
        centroids, closest_stops = self.task_strategy.get_route_items(self.updated_kvadratnet_gdf)
                
        self.assertTrue(len(centroids) == 0)
        self.assertTrue(len(closest_stops) == 0)
    
    
    # test om output kun indeholder de relevante kolonner
    def test_prepare_output(self):
        output = self.task_strategy.prepare_output(self.updated_kvadratnet_gdf)
        
        expected_columns = ['id', 'osmid', 'stops_10', 'stops_20']
        
        self.assertCountEqual(output.columns, expected_columns)
        self.assertTrue(isinstance(output, pd.DataFrame))


class TestFlextur(unittest.TestCase):
    def setUp(self):
        self.crs = 'EPSG:25832'
        
        # eksempel flexturs data
        kvadratnet_data = {
            'id': [0, 1, 2, 3],
            'Antal Rejser': [5, 2, 6, 7],
            'Antal passagerer': [10, 56, 23, 24],
            'Kommune1': [None, None, None, None],
            'Planet1': [None, None, None, None],
            'Fra X': [None, None, None, None],
            'Fra Y': [None, None, None, None],
            'Kommune2': [None, None, None, None],
            'Planet2': [None, None, None, None],
            'Til X': [None, None, None, None],
            'Til Y': [None, None, None, None],
            'Rejsetype': [None, None, None, None],
            'Periode': [None, None, None, None],
            'Retning': [None, None, None, None],
            'geometry_center': [Point(1, 1), 
                                Point(2, 2), 
                                Point(3, 3), 
                                Point(4, 4)], # fra punkt
            'point_to': [Point(2, 2), 
                         Point(1, 1), 
                         Point(1, 1), 
                         Point(3, 3)], # til punkt
            'bird_flight': [LineString([[1, 1], [2, 2]]), 
                            LineString([[2, 2], [1, 1]]), 
                            LineString([[3, 3], [1, 1]]), 
                            LineString([[4, 4], [3, 3]])], # fugleflugtslinje
            'the_geom': [LineString([[1, 1], [1, 2], [2, 2]]),
                         LineString([[2, 2], [1, 2], [1, 1]]), 
                         LineString([]), # ingen vej på vejnettet
                         LineString([[4, 4], [4, 3], [3, 3]])], # geometri for korteste vej
            'osmid': [2000, 2001, 2002, 2003],
            'iGraph_id': [3000, 3001, 3002, 3003],
        }
        self.kvadratnet_gdf = gpd.GeoDataFrame(kvadratnet_data).set_geometry('geometry_center', crs=self.crs)

        # kopi af flexturs data kun for til-punkt
        stop_data = {
            'geometry': [Point(2, 2), 
                         Point(1, 1), 
                         Point(1, 1), 
                         Point(3, 3)], # til punkt
            'osmid': [1001, 1002, 1003, 1004],
            'iGraph_id': [10, 20, 30, 40],
        }
        self.stop_gdf = gpd.GeoDataFrame(stop_data, crs=self.crs)
        
        # vælg opgave
        self.task_strategy = Flextur()
        
    
    def test_prepare_input(self):
        pass
    
    
    def test_associate_centroids_and_stops(self):
        pass
    
    
    def test_get_route_items(self):
        pass
    
    
    def test_prepare_output_linestring(self):
        expected_line = [LineString([[1, 1], [1, 2], [2, 2]]),
                         LineString([[2, 2], [1, 2], [1, 1]]), 
                         LineString([[3, 3], [1, 1]]), # fugleflugt
                         LineString([[4, 4], [4, 3], [3, 3]])]
        
        output = self.task_strategy.prepare_output(self.kvadratnet_gdf)
        
        self.assertListEqual(output['the_geom'].to_list(), expected_line)
        
        self.assertTrue(output.geometry.name == 'the_geom')
    
    
    def test_prepare_output_columns(self):
        output = self.task_strategy.prepare_output(self.kvadratnet_gdf)
        
        self.assertTrue('geometry_center' not in output.columns)
        self.assertTrue('point_to' not in output.columns)
        self.assertTrue('bird_flight' not in output.columns)
        self.assertTrue('Fra X' not in output.columns)
        self.assertTrue('Fra Y' not in output.columns)
        self.assertTrue('Til X' not in output.columns)
        self.assertTrue('Til Y' not in output.columns)
    
    
    def test_get_output_suffix(self):
        self.assertEqual(self.task_strategy.get_output_suffix(), 'vejnet.csv')


if __name__ == '__main__':
    unittest.main(verbosity=2)
