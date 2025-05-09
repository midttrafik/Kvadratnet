import os
import sys
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname+'\\..')
sys.path.insert(0, os.getcwd())

from src.abstract.DataLoader import DataLoader
from src.strategy.DataStrategy import *
from src.abstract.TaskStrategy import TaskStrategy
from src.strategy.TaskStrategy import *

import osmnx as ox
import networkx as nx
import igraph as ig
import geopandas as gpd
import pandas as pd
import numpy as np
from time import time
from shapely import Point
from shapely.geometry import LineString


class PathAlgorithm:
    """
        Klasse som effektivt udregner gå-afstand mellem alle objekter i to inputfiler på OpenStreetMaps vej- og stilag.
        Udviklet med henblik på at regne afstande mellem stoppesteder og befolkningskvadratnet men kan anvendes med vilkårligt punktbaseret data.
        
        Input:
            - stop_gdf: GeoDataFrame fra stop_loader.
                - geometry: punkt geometri.
                - stop_code: id på objektet.
                - stop_name: navn på objektet, kan være NULL hvis ikke det er relevant.
            
            - kvadratnet: GeoDataFrame fra kvadratnet_loader.
                - geometry_center: punkt geometri, f.eks. et punkt eller centrum af et polygon.
                - id: id på objektet.
        
        Output:
            - kvadratnet: skrives som fil defineret af task_loader.
                - id: samme id som input.
                - osmid: id på OSM knuden som geometry_center er tættest på.
                - Alle kolonner oprettet af task_strategy (f.eks. navn og id på nærmeste stop eller id på alle stop indenfor 500m)
        
        Metode:
            Problemet er multi-source multi-target weighted shortest path som løses med Dijkstras algoritme ved brug af C biblioteket igraph.
            Problemet omformuleres til at finde korteste vej for alle targets (stops) til alle OSM knuder da dette kan klares i one-go og udnytter igraphs multiprocessing.
            På grund af praktiske memory begrænsninger anvendes chunkinization således kun en delmængde af targets anvendes af gangen.
        
    """
    def __init__(self, 
                 kvadratnet_filename: str,
                 osm_place: str,
                 chunk_size: int,
                 minimum_components: int,
                 crs: str,
                 data_path: str,
                 result_path: str,
                 kvadratnet_loader: DataLoader, 
                 stop_loader: DataLoader,
                 task_strategy: TaskStrategy):
        """
        Args:
            kvadratnet_filename (str): kvadratnet filnavn
            osm_place (str): gyldigt OSM stednavn
            chunk_size (int): antal stop i chunk
            minimum_components (int): mindste antal nodes i uforbundet komponent på OSM graf
            crs (str): projektion
            data_path (str): sti til data mappe
            result_path (str): sti til resultat mappe
            kvadratnet_loader (DataLoader): strategi for kvadratnets data
            stop_loader (DataLoader): strategi for stop data
            task_strategy (TaskStrategy): strategi for typen af opgave
        """
        
        self.kvadratnet_filename = kvadratnet_filename
        self.osm_place = osm_place
        self.chunk_size = chunk_size
        self.minimum_components = minimum_components
        self.crs = crs
        self.data_path = data_path
        self.result_path = result_path
        self.kvadratnet_loader = kvadratnet_loader
        self.stop_loader = stop_loader
        self.task_strategy = task_strategy

        # aktiver caching
        ox.settings.use_cache = True

        # deaktiver at OSM download skrives til konsolen
        ox.settings.log_console = False
    
    
    #----------------------------------------------------------------------------------------------------------
    def read_and_project_OSM(self, place, crs):
        # hent OSM lag
        G = ox.graph_from_place(place, 
                                network_type='all', # alle vej- og stityper
                                custom_filter=None,
                                simplify=True, # reducerer antal unødvendige nodes for hurtigere udregninger
                                retain_all=True # behold alle connected components, det forhindrer at stier på Venø og Samsø droppes
        )
        
        # projicer til crs
        G_proj = ox.project_graph(G, to_crs=crs)   
        
        return G_proj


    def remove_small_components_OSM(self, G, minimum_components):
        # find alle komponenter som ikke er indbyrdes forbundende
        connected_components = list(nx.connected_components(G.to_undirected()))

        # fjern komponenter hvis komponenten indeholder for få knuder og kanter
        large_components = [c for c in connected_components if len(c) >= minimum_components]

        # genopbyg grafen ved brug af filtreret komponenter
        nodes_to_keep = set().union(*large_components)
        G_filtered = G.subgraph(nodes_to_keep).copy() 
        
        return G_filtered


    def get_OSM_polygon(self, place, crs):
        # hent polygonet tilhørende stednavnet
        place_boundary = ox.geocode_to_gdf(place)
        place_boundary = place_boundary.to_crs(crs)
        polygon = place_boundary.geometry.iloc[0]
        
        return polygon


    def remove_objects_outside_polygon(self, gdf, polygon, geom_col):
        # fjern stop som ligger udenfor polygonet tilhørende stednavnet
        gdf_filtered = gdf[gdf[geom_col].intersects(polygon)]
        gdf_filtered = gdf_filtered.reset_index(drop=True)
        
        return gdf_filtered



    #----------------------------------------------------------------------------------------------------------
    def graph_networkx_to_igraph(self, G_nx):
        osmids = list(G_nx.nodes)
        G_nx = nx.relabel.convert_node_labels_to_integers(G_nx)

        # lav mapping mellem osmid og igraph id
        map_id_to_osmid = {k: v for k, v in zip(G_nx.nodes, osmids)}
        map_osmid_to_id = {k: v for k, v in zip(osmids, G_nx.nodes)}
        
        # giv hver node en attribut osmid
        nx.set_node_attributes(G_nx, map_id_to_osmid, "osmid")

        # konverter OSM graf til igraph graf
        G_ig = ig.Graph(directed=True)
        G_ig.add_vertices(G_nx.nodes)
        G_ig.add_edges(G_nx.edges())
        G_ig.vs["osmid"] = osmids
        G_ig.es["length"] = list(nx.get_edge_attributes(G_nx, "length").values())
        
        return G_ig, map_id_to_osmid, map_osmid_to_id



    #----------------------------------------------------------------------------------------------------------
    def transform_osm_node_to_ig_node(self, points, G_proj):
        # find nærmeste osm node id til punkt
        osm_nodes, distances_point_to_node = ox.nearest_nodes(G_proj, 
                                                              X=points.x.to_list(), 
                                                              Y=points.y.to_list(), 
                                                              return_dist=True
        )
        
        # map osm nodes til igraph id
        ig_nodes = [self.map_osmid_to_id.get(node) for node in osm_nodes]
        
        return osm_nodes, ig_nodes, distances_point_to_node



    #----------------------------------------------------------------------------------------------------------
    def multi_source_all_targets_distances(self, sources, G_ig):
        # multi-soruce all target korteste distance med Dijkstra
        distances = G_ig.distances(source=sources, target=None, weights="length")
        
        return distances


    def find_shortest_distance(self, 
                               kvadratnet, 
                               stop_gdf, 
                               stop_nodes_ig, 
                               centroid_nodes_ig, 
                               G_ig,
                               chunk_size):
        # opdel stop nodes ig i chunks
        stop_nodes_ig_chunks = [stop_nodes_ig[i:i+chunk_size] for i in range(0, len(stop_nodes_ig), chunk_size)]

        # processer hver chunk
        for chunk_id, stop_nodes_ig_chunk in enumerate(stop_nodes_ig_chunks):
            print('*'*50)
            print(f'Processerer stop chunk: {chunk_id+1}/{len(stop_nodes_ig_chunks)}')
            print(f'Antal stop i chunk: {len(stop_nodes_ig_chunk)}')
        
            time_start = time()
        
            # fjern duplikerede stop nodes hvis der er nogle, ellers fejler igraph
            stop_nodes_ig_noduplicates = list(set(stop_nodes_ig_chunk))

            # beregn distance af koreste vej
            distances = self.multi_source_all_targets_distances(stop_nodes_ig_noduplicates, G_ig)

            # opdater kvadratnet
            kvadratnet = self.task_strategy.associate_centroids_and_stops(kvadratnet,
                                                                          stop_gdf,
                                                                          distances,
                                                                          centroid_nodes_ig,
                                                                          stop_nodes_ig_noduplicates
            )
        
            time_end = time()
            print(f'Processerede chunk på {round(time_end-time_start, 2)} sekunder.')
        
        return kvadratnet



    #-------------------------------------------------------------------------------------------------------------------------
    def get_route_geometry(self, source, destination, G_ig, G_proj):
        # udregn kortest vej (liste af nodes) mellem to konkrete punkter
        route_ig = G_ig.get_shortest_paths(source, to=destination, weights='length', output='vpath')
        
        # konverter igraph knuder til osm knuder
        route_osm = [self.map_id_to_osmid[node_ig] for node_ig in route_ig[0]]

        edges = []
        for u, v in zip(route_osm[:-1], route_osm[1:]):
            # hent kant, hvis der findes flere tages den første.
            edge_data = G_proj.get_edge_data(u, v)
            edge = edge_data[0]
            
            # hent linje geometrien ellers konstruer en linje geometri fra to koordinater.
            if "geometry" in edge:
                edges.append(edge["geometry"])
            else:
                # lav lige linje
                point_u = (G_proj.nodes[u]["x"], G_proj.nodes[u]["y"])
                point_v = (G_proj.nodes[v]["x"], G_proj.nodes[v]["y"])
                edges.append(LineString([point_u, point_v]))

        # sammensæt til en lang vej
        route_line = LineString([point for line in edges for point in line.coords])
        
        return route_line


    def get_routes(self, kvadratnet, sources, destinations, G_ig, G_proj):
        # initialiser geometrikolonne for vej
        kvadratnet['the_geom'] = None
        
        # find geometrien af vejen
        for i in range(0, len(sources)):
            source = sources[i]
            destination = destinations[i]
            kvadratnet.loc[i, 'the_geom'] = self.get_route_geometry(source, destination, G_ig, G_proj)
            
            if i % 1000 == 0:
                print(f'Hentet {i}/{kvadratnet.shape[0]} geometrier.')
        
        return kvadratnet


    #-------------------------------------------------------------------------------------------------------------------------
    def add_suffix_to_output_filename(self, suffix, filename):
        # tilføj _suffix som endelse på filnavnet
        suffix_formatted = '_' + suffix
        output_filename = filename.split('.')[0] + suffix_formatted
        
        return output_filename


    def compute(self, write_result=True):
        """Kør algoritmen.

        Args:
            write_result (bool, optional): bestemmer om resultatet skal skrives. Default er True, False anvendes kun til integration test.
        """
        
        #------------------------------------------
        start = time()
        print('-'*50)
        print('1/6 påbegynder indlæsning af data.')

        # læs kvadratnet og valider at alle kolonner er med
        kvadratnet = self.kvadratnet_loader.get_data()
        assert 'id' in kvadratnet.columns, 'Input skal indeholde kolonnen: id'
        assert 'geometry_center' in kvadratnet.columns, f'Input skal indeholde kolonnen: geometry_center'
        assert isinstance(kvadratnet.loc[0, 'geometry_center'], Point), 'Input skal have geometry_center af typen Point'
        print(f'Læst {kvadratnet.shape[0]} kvadrater.')
        
        # fjern objekt hvis geometrien mangler eller er tom
        kvadratnet_rows_before = kvadratnet.shape[0]
        kvadratnet = kvadratnet[(kvadratnet['geometry_center'].isna()==False) & (kvadratnet['geometry_center'].is_empty==False)]
        kvadratnet_rows_after = kvadratnet.shape[0]
        if kvadratnet_rows_after != kvadratnet_rows_before:
            print(f'Fjernet {kvadratnet_rows_before - kvadratnet_rows_after} rækker i input med ugyldige eller tom geometri.')
        
        # tilføj nye kolonner som bruges af task.
        kvadratnet = self.task_strategy.prepare_input(kvadratnet)
        kvadratnet = kvadratnet.reset_index(drop=True)


        # læs stop data og valider at alle kolonner er med
        stop_gdf = self.stop_loader.get_data()
        assert 'stop_name' in stop_gdf.columns, 'Stop skal indeholde kolonnen: stop_name'
        assert 'stop_code' in stop_gdf.columns, 'Stop skal indeholde kolonnen: stop_code'
        assert 'geometry' in stop_gdf.columns, 'Stop skal indeholde kolonnen: geometry'
        assert isinstance(stop_gdf.loc[0, 'geometry'], Point), 'Stop skal have geometry_center af typen Point'
        print(f'Læst {stop_gdf.shape[0]} stop.')
        
        # fjern objekt hvis geometrien mangler eller er tom
        stop_gdf_rows_before = stop_gdf.shape[0]
        stop_gdf = stop_gdf[(stop_gdf['geometry'].isna()==False) & (stop_gdf['geometry'].is_empty==False)]
        stop_gdf_rows_after = stop_gdf.shape[0]
        if stop_gdf_rows_after != stop_gdf_rows_before:
            print(f'Fjernet {stop_gdf_rows_before - stop_gdf_rows_after} rækker i stop med ugyldig eller tom geometri.')
        
        stop_gdf = stop_gdf.reset_index(drop=True)
        

        # hent OSM polygon
        polygon = self.get_OSM_polygon(self.osm_place, self.crs)
        
        # fjern kvadrater udenfor OSM polygon
        kvadratnet = self.remove_objects_outside_polygon(kvadratnet, polygon, geom_col='geometry_center')
        print(f'Fjernet kvadrater udenfor {self.osm_place}, antallet af kvadrater er nu {kvadratnet.shape[0]}')
        
        # fjern stop udenfor OSM polygon
        stop_gdf = self.remove_objects_outside_polygon(stop_gdf, polygon, geom_col='geometry')
        print(f'Fjernet stop udenfor {self.osm_place}, antallet af stop er nu {stop_gdf.shape[0]}')

        # frigør plads i memory da den ikke skal bruges mere
        del polygon

        # hent osm data, projicer til crs og fjern connected components hvis de indeholder færre knuder end fastsatte grænse
        G_proj = self.read_and_project_OSM(self.osm_place, self.crs)
        G_proj = self.remove_small_components_OSM(G_proj, self.minimum_components)
        print(f'Læst og projiceret OSM netværk ({len(G_proj.nodes)} knuder og {len(G_proj.edges)} stier).')

        end = time()
        print(f'Læst data på {round(end-start, 2)} sekunder.')
        
        
        #----------------------------------
        start = time()
        print('-'*50)
        print('2/6 Påbegynder konvertering af OSM til igraph.')

        # konverter projiceret OSM graf til iGraph graf
        G_ig, map_id_to_osmid, map_osmid_to_id = self.graph_networkx_to_igraph(G_proj)
        self.map_id_to_osmid = map_id_to_osmid
        self.map_osmid_to_id = map_osmid_to_id

        end = time()
        print(f'Konverteret OSM netværk til igraph på {round(end-start, 2)} sekunder.')
        
        
        #------------------------------------------
        start = time()
        print('-'*50)
        print('3/6 Påbegynder transformering af centroider og stop til igraph id\'er.')

        # kvadratnet projiceres til OSM nodes og igraph nodes
        centroids = kvadratnet['geometry_center']
        centroid_nodes_osm, centroid_nodes_ig, distance_centroid_node = self.transform_osm_node_to_ig_node(centroids, G_proj)
        kvadratnet['osmid'] = centroid_nodes_osm
        kvadratnet['iGraph_id'] = centroid_nodes_ig
        kvadratnet['dist_input'] = distance_centroid_node

        # stop projiceres til OSM nodes og igraph nodes
        stoppoints = stop_gdf['geometry']
        stop_nodes_osm, stop_nodes_ig, distance_stop_node = self.transform_osm_node_to_ig_node(stoppoints, G_proj)
        stop_gdf['osmid'] = stop_nodes_osm
        stop_gdf['iGraph_id'] = stop_nodes_ig
        stop_gdf['dist_stop'] = distance_stop_node

        end = time()
        print(f'Transformeret centroider og stop til igraph id\'er på {round(end-start, 2)} sekunder.')
        
        
        #-------------------
        start = time()
        print('-'*50)
        print('4/6 Påbegynder udregning af korteste distancer.')

        kvadratnet = self.find_shortest_distance(kvadratnet, stop_gdf, stop_nodes_ig, centroid_nodes_ig, G_ig, self.chunk_size)

        end = time()
        print(f'Udregnet korteste distancer på {round(end-start, 2)} sekunder.')
        
        
        #---------------------------
        start = time()
        print('-'*50)
        print('5/6 Henter geometrier for korteste veje.')
        
        # hent sources og targets hvis vej geometrien skal udregnes
        sources, destinations = self.task_strategy.get_route_items(kvadratnet)
        if len(sources) == 0:
            print('Ingen geometrier hentet.')
        else:
            kvadratnet = self.get_routes(kvadratnet, sources, destinations, G_ig, G_proj)

        end = time()
        print(f'Henetet geometrier for korteste veje på {round(end-start, 2)} sekunder.')
        
        
        #------------------------------
        print('-'*50)
        print('6/6 Påbegynder klargøring af resultat.')
        start = time()

        # forbedre kvadratnet til udskrivning
        output = self.task_strategy.prepare_output(kvadratnet)
        
        if write_result == False:
            sys.exit()

        # skriv kvadratnet
        suffix = self.task_strategy.get_output_suffix()
        output_filename = self.add_suffix_to_output_filename(suffix, self.kvadratnet_filename)
        self.task_strategy.write_output(output, self.result_path, output_filename)

        end = time()
        print(f'Resultat gemt som {output_filename} på {round(end-start, 2)} sekunder.')
