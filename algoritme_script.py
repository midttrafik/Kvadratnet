import osmnx as ox
import networkx as nx
import igraph as ig
import geopandas as gpd
import pandas as pd
import numpy as np
from time import time
from shapely import Point
from shapely.geometry import LineString
import os
import sys
import click
from data_handler import *

#sys.exit()



class PathAlgorithm:
    """
        Udarbejdet af Midttrafik
        
        Formål: 
            Udregne distance til nærmeste stoppested fra centroide af hvert kvadrat i kvadratnettet
        
        Input:
            - Standere som csv fil
            - Kvadratnet som shapefil

        Output:
            - Kvadratnet som shapefil med distance til nærmeste stander samt navn og nummer på stander
    """
    def __init__(self, 
                 kvadratnet_filename,
                 osm_place,
                 chunk_size,
                 minimum_components,
                 crs,
                 data_path,
                 result_path,
                 kvadratnet_loader, 
                 stop_loader):
        
        self.kvadratnet_filename = kvadratnet_filename
        self.osm_place = osm_place
        self.chunk_size = chunk_size
        self.minimum_components = minimum_components
        self.crs = crs
        self.data_path = data_path
        self.result_path = result_path
        self.kvadratnet_loader = kvadratnet_loader
        self.stop_loader = stop_loader

        
        # sæt working directory til denne fils placering
        abspath = os.path.abspath(__file__)
        dname = os.path.dirname(abspath)
        os.chdir(dname)
        print('Working directory:', os.getcwd())

        # aktiver caching
        ox.settings.use_cache = True

        # deaktiver at OSM download skrives til konsolen
        ox.settings.log_console = False
    
    
    #----------------------------------------------------------------------------------------------------------
    def prepare_input(self, input_gdf):
        # definer kolonnerne vi ønsker at udregne
        stort_tal = 100*1000 # 100km er et stort tal cirka ligmed uendelighed 
        input_gdf['dist_path'] = stort_tal
        input_gdf['dist_input'] = stort_tal
        input_gdf['dist_stop'] = stort_tal
        input_gdf['stop_name'] = None
        input_gdf['stop_id'] = None
        input_gdf['stop_osmid'] = None
        input_gdf['stop_iGraph_id'] = None
        return input_gdf


    def read_and_project_OSM(self, place, crs):
        # hent OSM lag
        G = ox.graph_from_place(place, 
                                network_type='all', # alle vej- og stityper # ændret
                                custom_filter=None,
                                simplify=True, # simplificer nodes og edges
                                retain_all=True # behold nodes som ikke kan nåes fra regions centrum, det forhindrer at stier på Venø og Samsø droppes
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
        # hent polygonet fra stednavnet
        place_boundary = ox.geocode_to_gdf(place)
        place_boundary = place_boundary.to_crs(crs)
        polygon = place_boundary.geometry.iloc[0]
        
        return polygon


    def remove_objects_outside_polygon(self, gdf, polygon, geom_col):
        gdf_filtered = gdf[gdf[geom_col].intersects(polygon)]
        gdf_filtered = gdf_filtered.reset_index(drop=True)
        return gdf_filtered



    #----------------------------------------------------------------------------------------------------------
    def graph_networkx_to_igraph(self, G_nx):
        # lav igraph graf
        osmids = list(G_nx.nodes)
        G_nx = nx.relabel.convert_node_labels_to_integers(G_nx)

        # lav mapping mellem osmid og igraph id
        map_id_to_osmid = {k: v for k, v in zip(G_nx.nodes, osmids)}
        map_osmid_to_id = {k: v for k, v in zip(osmids, G_nx.nodes)}
        
        # giv hver node en attribut osmid
        nx.set_node_attributes(G_nx, map_id_to_osmid, "osmid")

        # converter OSM graf til igraph graf
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
                                                            return_dist=True)
        
        # map osm nodes til igraph id
        ig_nodes = [self.map_osmid_to_id.get(node) for node in osm_nodes]
        return osm_nodes, ig_nodes, distances_point_to_node



    #----------------------------------------------------------------------------------------------------------
    def multi_source_all_targets_distances(self, sources, G_ig):
        distances = G_ig.distances(source=sources, target=None, weights="length")
        return distances


    def argmin(self, lst):
        min_val = min(lst)
        return lst.index(min_val), min_val


    def add_smallest_distance_to_centroid(self,
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
                kvadratnet_df.loc[idx, 'stop_name'] = stop_gdf_ig_match['Long name'].head(1).values
                kvadratnet_df.loc[idx, 'stop_id'] = stop_gdf_ig_match['Kode til stoppunkt'].head(1).values
                kvadratnet_df.loc[idx, 'stop_osmid'] = stop_gdf_ig_match['osmid'].head(1).values
                kvadratnet_df.loc[idx, 'stop_iGraph_id'] = stop_gdf_ig_match['iGraph_id'].head(1).values
                
        return kvadratnet_df

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
        
            # fjern duplikerede stop nodes
            stop_nodes_ig_noduplicates = list(set(stop_nodes_ig_chunk))

            # beregn distance af koreste vej som multi source all targets problem
            distances = self.multi_source_all_targets_distances(stop_nodes_ig_noduplicates, G_ig)

            # opdater kvadratnet med korteste distance
            kvadratnet = self.add_smallest_distance_to_centroid(kvadratnet, 
                                                        stop_gdf, 
                                                        distances, 
                                                        centroid_nodes_ig,
                                                        stop_nodes_ig_noduplicates)
        
            time_end = time()
            print(f'Processerede chunk på {round(time_end-time_start, 2)} sekunder.')

        # beregn total distance fra centroid -> node -> node -> stop
        kvadratnet['dist_total'] = (kvadratnet['dist_path'] 
                                    + kvadratnet['dist_input'] 
                                    + kvadratnet['dist_stop'])
        
        return kvadratnet



    #-------------------------------------------------------------------------------------------------------------------------
    def get_route_geometry(self, source, destination, G_ig, G_proj):
        # udregn korteste vej
        route_ig = G_ig.get_shortest_paths(source, to=destination, weights='length', output='vpath')
        
        # konverter igraph knuder til osm knuder
        route_osm = [self.map_id_to_osmid[node_ig] for node_ig in route_ig[0]]

        edges = []
        for u, v in zip(route_osm[:-1], route_osm[1:]):
            # hent kant, hvis der findes flere tages den første.
            edge_data = G_proj.get_edge_data(u, v)
            edge = edge_data[0]
            if "geometry" in edge:
                edges.append(edge["geometry"])
            else:
                # lav lige linje
                point_u = (G_proj.nodes[u]["x"], G_proj.nodes[u]["y"])
                point_v = (G_proj.nodes[v]["x"], G_proj.nodes[v]["y"])
                edges.append(LineString([point_u, point_v]))

        # lav linje
        route_line = LineString([point for line in edges for point in line.coords])
        
        return route_line


    def get_routes(self, kvadratnet, G_ig, G_proj):
        kvadratnet['the_geom'] = None
        for i in range(0, kvadratnet.shape[0]):
            source = kvadratnet.loc[i, 'iGraph_id']
            destination = kvadratnet.loc[i, 'stop_iGraph_id']
            kvadratnet.loc[i, 'the_geom'] = self.get_route_geometry(source, destination, G_ig, G_proj)
            if i % 1000 == 0:
                print(f'Hentet {i}/{kvadratnet.shape[0]} geometrier.')
                
        return kvadratnet


    #-------------------------------------------------------------------------------------------------------------------------
    def format_output(self, kvadratnet_df):
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


    def write_output(self, output, path, filename, suffix):
        # tilføj _distance som endelse på filnavnet
        suffix_formatted = '_' + suffix + '.'
        output_filename = suffix_formatted.join(filename.split('.'))
        
        # skriv shapefil
        output.to_file(path + output_filename, 
                    driver='ESRI Shapefile')
        
        return output_filename


    def compute(self):
        #------------------------------------------
        start = time()
        print('-'*50)
        print('1/6 påbegynder indlæsning af data.')

        # læs input data
        self.kvadratnet_loader.load_and_process()
        kvadratnet = self.kvadratnet_loader.get_data()
        assert 'id' in kvadratnet.columns, 'Input skal indeholde kolonnen: id'
        assert 'geometry_center' in kvadratnet.columns, f'Input skal indeholde kolonnen: geometry_center'
        assert isinstance(kvadratnet.loc[0, 'geometry_center'], Point), 'Input skal have geometry_center af typen Point'
        print(f'Læst {kvadratnet.shape[0]} kvadrater.')
        
        kvadratnet_rows_before = kvadratnet.shape[0]
        kvadratnet = kvadratnet[(kvadratnet['geometry_center'].isna()==False) & (kvadratnet['geometry_center'].is_empty==False)]
        kvadratnet_rows_after = kvadratnet.shape[0]
        if kvadratnet_rows_after != kvadratnet_rows_before:
            print(f'Fjernet {kvadratnet_rows_before - kvadratnet_rows_after} rækker i input med ugyldige eller tom geometri.')
            
        kvadratnet = self.prepare_input(kvadratnet)
        kvadratnet = kvadratnet.reset_index(drop=True)


        # læs stop data
        self.stop_loader.load_and_process()
        stop_gdf = self.stop_loader.get_data()
        #assert 'stop_name' in stop_gdf.columns, 'Stop skal indeholde kolonnen: stop_name'
        #assert 'stop_code' in stop_gdf.columns, 'Stop skal indeholde kolonnen: stop_code'
        assert 'geometry' in stop_gdf.columns, 'Stop skal indeholde kolonnen: geometry'
        print(f'Læst {stop_gdf.shape[0]} stop.')
        
        stop_gdf_rows_before = stop_gdf.shape[0]
        stop_gdf = stop_gdf[(stop_gdf['geometry'].isna()==False) & (stop_gdf['geometry'].is_empty==False)]
        stop_gdf_rows_after = stop_gdf.shape[0]
        if stop_gdf_rows_after != stop_gdf_rows_before:
            print(f'Fjernet {stop_gdf_rows_before - stop_gdf_rows_after} rækker i stop med ugyldig eller tom geometri.')
        
        stop_gdf = stop_gdf.reset_index(drop=True)
        

        # fjern objekter udenfor polygon
        polygon = self.get_OSM_polygon(self.osm_place, self.crs)

        stop_gdf = self.remove_objects_outside_polygon(stop_gdf, polygon, geom_col='geometry')
        print(f'Fjernet stop udenfor {self.osm_place}, antallet af stop er nu {stop_gdf.shape[0]}')

        # frigør plads i memory
        del polygon

        # hent osm data
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

        # transformer centroider til nodes
        centroids = kvadratnet['geometry_center']
        centroid_nodes_osm, centroid_nodes_ig, distance_centroid_node = self.transform_osm_node_to_ig_node(centroids, G_proj)
        kvadratnet['osmid'] = centroid_nodes_osm
        kvadratnet['iGraph_id'] = centroid_nodes_ig
        kvadratnet['dist_input'] = distance_centroid_node

        # transformer stop til nodes
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

        kvadratnet = self.get_routes(kvadratnet, G_ig, G_proj)

        end = time()
        print(f'Henetet geometrier for korteste veje på {round(end-start, 2)} sekunder.')
        
        
        #------------------------------
        print('-'*50)
        print('6/6 Påbegynder klargøring af resultat.')
        start = time()

        # formater output
        output = self.format_output(kvadratnet)
        
        sys.exit()

        # skriv fil med objekter
        output_filename = self.write_output(output=output, path=self.result_path, filename=self.kvadratnet_filename, suffix='distance')

        end = time()
        print(f'Resultat gemt som {output_filename} på {round(end-start, 2)} sekunder.')



if __name__ == '__main__':
    # modtag input
    stop_filename = click.prompt("Navn på stopfil uden sti til mappe", type=str)
    kvadratnet_filename = click.prompt("Navn på kvadratnetsfil uden sti til mappe", type=str)
    osm_place = click.prompt("Navn på administrativt OSM område", type=str, default='Region Midtjylland')
    flex = click.prompt("Fjern Flextur", type=bool, default=True)
    plus = click.prompt("Fjern Plustur", type=bool, default=True)
    stander_9 = click.prompt("Fjern 09 stander", type=bool, default=False)
    stander_nedlagt = click.prompt("Fjern nedlagte standere", type=bool, default=True)
    chunk_size = click.prompt("Chunk size", type=int, default=500)
    minimum_components = click.prompt("Minimum forbundende komponenter", type=int, default=200)
    crs = click.prompt("CRS", type=str, default='EPSG:25832')
    data_path = click.prompt("Sti til data", type=str, default='Data\\')
    result_path = click.prompt("Sti til resultater", type=str, default='Resultater\\')


    #kvadratnet_handler = Polygoner(
    #    path=data_path,
    #    filename=kvadratnet_filename,
    #    crs=crs
    #)
    
    kvadratnet_handler = Punkter(
        path=data_path,
        filename=kvadratnet_filename,
        crs=crs
    )

    stop_handler = MobilePlan(
        path=data_path,
        filename=stop_filename,
        crs=crs,
        flex=flex,
        plus=plus,
        stander_9=stander_9,
        stander_nedlagt=stander_nedlagt
    )


    algorithm = PathAlgorithm(
        kvadratnet_filename=kvadratnet_filename,
        osm_place=osm_place,
        chunk_size=chunk_size,
        minimum_components=minimum_components,
        crs=crs,
        data_path=data_path,
        result_path=result_path,
        kvadratnet_loader=kvadratnet_handler,
        stop_loader=stop_handler
    )

    algorithm.compute()