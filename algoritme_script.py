import osmnx as ox
import networkx as nx
import igraph as ig
import geopandas as gpd
import pandas as pd
import numpy as np
from time import time
import os
import sys
import click
from data_handler import *

#sys.exit()

# modtag input
input_read_method_name = click.prompt("Navn på input konfigurationsmetode", type=str)
stop_read_method_name = click.prompt("Navn på stop konfigurationensmetode", type=str, default='MobilePlan')

stop_filename = click.prompt("Navn på stopfil uden sti til mappe", type=str)
kvadratnet_filename = click.prompt("Navn på kvadratnetsfil uden sti til mappe", type=str)
osm_place = click.prompt("Navn på administrativt OSM område", type=str, default='Region Midtjylland')
write_routes = click.prompt("Vis ruter på vejnettet", type=bool, default=True)
flex = click.prompt("Fjern Flextur", type=bool, default=True)
plus = click.prompt("Fjern Plustur", type=bool, default=True)
stander_9 = click.prompt("Fjern 09 stander", type=bool, default=False)
stander_nedlagt = click.prompt("Fjern nedlagte standere", type=bool, default=True)
chunk_size = click.prompt("Chunk size", type=int, default=500)
minimum_components = click.prompt("Minimum forbundende komponenter", type=int, default=200)
crs = click.prompt("CRS", type=str, default='EPSG:25832')
data_path = click.prompt("Sti til data", type=str, default='Data\\')
result_path = click.prompt("Sti til resultater", type=str, default='Resultater\\')

stop_filter = {'Fjern Flextur':flex,
               'Fjern Plustur':plus,
               'Fjern 09 stander':stander_9,
               'Fjern nedlagte standere':stander_nedlagt}

dataHandler = DataHandler(input_read_method_name=input_read_method_name,
                          stop_read_method_name=stop_read_method_name,
                          crs=crs)

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
def prepare_input(input_gdf):
    # definer kolonnerne vi ønsker at udregne
    stort_tal = 100*1000 # 100km er et stort tal cirka ligmed uendelighed 
    input_gdf['min_distance_node_to_node'] = stort_tal
    input_gdf['distance_centroid_to_node'] = stort_tal
    input_gdf['distance_stop_to_node'] = stort_tal
    input_gdf['closest_stopname'] = None
    input_gdf['closest_stopid'] = None
    input_gdf['stop_osmid'] = None
    input_gdf['stop_iGraph_id'] = None
    return input_gdf


def read_and_project_OSM(place, crs):
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


def remove_small_components_OSM(G, minimum_components):
    # find alle komponenter som ikke er indbyrdes forbundende
    connected_components = list(nx.connected_components(G.to_undirected()))

    # fjern komponenter hvis komponenten indeholder for få knuder og kanter
    large_components = [c for c in connected_components if len(c) >= minimum_components]

    # genopbyg grafen ved brug af filtreret komponenter
    nodes_to_keep = set().union(*large_components)
    G_filtered = G.subgraph(nodes_to_keep).copy() 
    
    return G_filtered


def get_OSM_polygon(place, crs):
    # hent polygonet fra stednavnet
    place_boundary = ox.geocode_to_gdf(place)
    place_boundary = place_boundary.to_crs(crs)
    polygon = place_boundary.geometry.iloc[0]
    
    return polygon


def remove_objects_outside_polygon(gdf, polygon, geom_col):
    gdf_filtered = gdf[gdf[geom_col].intersects(polygon)]
    gdf_filtered = gdf_filtered.reset_index(drop=True)
    return gdf_filtered


start = time()
print('-'*50)
print('1/6 påbegynder indlæsning af data.')

# læs input data
dataHandler.load_and_process_input(path=data_path,
                                   filename=kvadratnet_filename)
kvadratnet = dataHandler.get_input()
kvadratnet = prepare_input(kvadratnet)
print(f'Læst {kvadratnet.shape[0]} kvadrater.')

# læs stop data
dataHandler.load_and_process_stops(path=data_path,
                                   filename=stop_filename,
                                   stop_filters=stop_filter)
stop_gdf = dataHandler.get_stops()
print(f'Læst {stop_gdf.shape[0]} filtreret stop.')

# fjern objekter udenfor polygon
polygon = get_OSM_polygon(osm_place, crs)

stop_gdf = remove_objects_outside_polygon(stop_gdf, polygon, geom_col='geometry')
print(f'Fjernet stop udenfor {osm_place}, antallet af stop er nu {stop_gdf.shape[0]}')

#kvadratnet = remove_objects_outside_polygon(kvadratnet, polygon, geom_col='geometry_center')
#print(f'Fjernet kvadrater udenfor {osm_place}, antallet af kvadrater er nu {kvadratnet.shape[0]}')

# frigør plads i memory
del polygon

# hent osm data
G_proj = read_and_project_OSM(osm_place, crs)
G_proj = remove_small_components_OSM(G_proj, minimum_components)
print(f'Læst og projiceret OSM netværk ({len(G_proj.nodes)} knuder og {len(G_proj.edges)} stier).')

end = time()
print(f'Læst data på {round(end-start, 2)} sekunder.')


#----------------------------------------------------------------------------------------------------------
def graph_networkx_to_igraph(G_nx):
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


start = time()
print('-'*50)
print('2/6 Påbegynder konvertering af OSM til igraph.')


# konverter projiceret OSM graf til iGraph graf
G_ig, map_id_to_osmid, map_osmid_to_id = graph_networkx_to_igraph(G_proj)


end = time()
print(f'Konverteret OSM netværk til igraph på {round(end-start, 2)} sekunder.')


#----------------------------------------------------------------------------------------------------------
def transform_osm_node_to_ig_node(points):
    # find nærmeste osm node id til punkt
    osm_nodes, distances_point_to_node = ox.nearest_nodes(G_proj, 
                                                          X=points.x.to_list(), 
                                                          Y=points.y.to_list(), 
                                                          return_dist=True)
    
    # map osm nodes til igraph id
    ig_nodes = [map_osmid_to_id.get(node) for node in osm_nodes]
    return osm_nodes, ig_nodes, distances_point_to_node


start = time()
print('-'*50)
print('3/6 Påbegynder transformering af centroider og stop til igraph id\'er.')


# transformer centroider til nodes
centroids = kvadratnet['geometry_center']
centroid_nodes_osm, centroid_nodes_ig, distance_centroid_node = transform_osm_node_to_ig_node(centroids)
kvadratnet['osmid'] = centroid_nodes_osm
kvadratnet['iGraph_id'] = centroid_nodes_ig
kvadratnet['distance_centroid_to_node'] = distance_centroid_node


# transformer stop til nodes
stoppoints = stop_gdf['geometry']
stop_nodes_osm, stop_nodes_ig, distance_stop_node = transform_osm_node_to_ig_node(stoppoints)
stop_gdf['osmid'] = stop_nodes_osm
stop_gdf['iGraph_id'] = stop_nodes_ig
stop_gdf['distance_stop_to_node'] = distance_stop_node


end = time()
print(f'Transformeret centroider og stop til igraph id\'er på {round(end-start, 2)} sekunder.')


#----------------------------------------------------------------------------------------------------------
def multi_source_all_targets_distances(sources, G_ig):
    distances = G_ig.distances(source=sources, target=None, weights="length")
    return distances


def argmin(lst):
    min_val = min(lst)
    return lst.index(min_val), min_val


def add_smallest_distance_to_centroid(kvadratnet_df, 
                                      stop_gdf, 
                                      distances, 
                                      centroid_nodes_ig, 
                                      stop_nodes_ig):
    
    number_of_stops = len(distances)
    
    # iterer igennem igraph listen af centroider
    for idx, centroid_node_ig in enumerate(centroid_nodes_ig):
        # find det stop index som minimerer distancen mellem stop og centroide
        min_distance_stop_idx, min_distance = argmin([distances[stop_idx][centroid_node_ig] for stop_idx in range(0, number_of_stops)])
        min_distance_formatted = round(min_distance, ndigits=2)
        
        if min_distance < kvadratnet_df.loc[idx, 'min_distance_node_to_node']:
            # opdater distancen hvis den er mindre end den nuværende
            kvadratnet_df.loc[idx, 'min_distance_node_to_node'] = min_distance_formatted
            
            # opdater distance fra stop til node, stop navn og stop nummer
            stop_gdf_ig_match = stop_gdf[stop_gdf['iGraph_id']==stop_nodes_ig[min_distance_stop_idx]]
            kvadratnet_df.loc[idx, 'distance_stop_to_node'] = stop_gdf_ig_match['distance_stop_to_node'].head(1).values
            kvadratnet_df.loc[idx, 'closest_stopname'] = stop_gdf_ig_match['Long name'].head(1).values
            kvadratnet_df.loc[idx, 'closest_stopid'] = stop_gdf_ig_match['Kode til stoppunkt'].head(1).values
            kvadratnet_df.loc[idx, 'stop_osmid'] = stop_gdf_ig_match['osmid'].head(1).values
            kvadratnet_df.loc[idx, 'stop_iGraph_id'] = stop_gdf_ig_match['iGraph_id'].head(1).values
            
    return kvadratnet_df

def find_shortest_distance(kvadratnet, 
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
        distances = multi_source_all_targets_distances(stop_nodes_ig_noduplicates, G_ig)

        # opdater kvadratnet med korteste distance
        kvadratnet = add_smallest_distance_to_centroid(kvadratnet, 
                                                       stop_gdf, 
                                                       distances, 
                                                       centroid_nodes_ig,
                                                       stop_nodes_ig_noduplicates)
    
        time_end = time()
        print(f'Processerede chunk på {round(time_end-time_start, 2)} sekunder.')

    # beregn total distance fra centroid -> node -> node -> stop
    kvadratnet['min_distance_total'] = (kvadratnet['min_distance_node_to_node'] 
                                        + kvadratnet['distance_centroid_to_node'] 
                                        + kvadratnet['distance_stop_to_node'])
    
    return kvadratnet


start = time()
print('-'*50)
print('4/6 Påbegynder udregning af korteste distancer.')

kvadratnet = find_shortest_distance(kvadratnet, stop_gdf, stop_nodes_ig, centroid_nodes_ig, G_ig, chunk_size)

end = time()
print(f'Udregnet korteste distancer på {round(end-start, 2)} sekunder.')


#-------------------------------------------------------------------------------------------------------------------------
from shapely.geometry import LineString

def get_route_geometry(source, destination, G_ig, G_proj):
    # udregn korteste vej
    route_ig = G_ig.get_shortest_paths(source, to=destination, weights='length', output='vpath')
    
    # konverter igraph knuder til osm knuder
    route_osm = [map_id_to_osmid[node_ig] for node_ig in route_ig[0]]

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


def get_routes(kvadratnet, G_ig, G_proj):
    kvadratnet['line_geometry'] = None
    for i in range(0, kvadratnet.shape[0]):
        source = kvadratnet.loc[i, 'iGraph_id']
        destination = kvadratnet.loc[i, 'stop_iGraph_id']
        kvadratnet.loc[i, 'line_geometry'] = get_route_geometry(source, destination, G_ig, G_proj)
        if i % 1000 == 0:
            print(f'Hentet {i}/{kvadratnet.shape[0]} geometrier.')
            
    return kvadratnet


start = time()
print('-'*50)
print('5/6 Henter geometrier for korteste veje.')

if write_routes:
    kvadratnet = get_routes(kvadratnet, G_ig, G_proj)

end = time()
print(f'Henetet geometrier for korteste veje på {round(end-start, 2)} sekunder.')


#-------------------------------------------------------------------------------------------------------------------------
def format_output(kvadratnet_df):
    # drop ligegyldige kolonner
    output = kvadratnet_df.drop(columns=['geometry_center', 'iGraph_id', 'stop_iGraph_id'])

    # formater datatyper og afrunding
    output['min_distance_total'] = output['min_distance_total'].round(2)
    output['min_distance_node_to_node'] = output['min_distance_node_to_node'].round(2)
    output['distance_centroid_to_node'] = output['distance_centroid_to_node'].round(2)
    output['distance_stop_to_node'] = output['distance_stop_to_node'].round(2)
    output['closest_stopname'] = output['closest_stopname'].astype(str)
    output['closest_stopid'] = output['closest_stopid'].astype(str)
    output['stop_osmid'] = output['stop_osmid'].astype(str)

    # simplificer kolonnenavne så de ikke er for lange
    output = output.rename(columns={'min_distance_total':'dist_total',
                                    'min_distance_node_to_node':'dist_path',
                                    'distance_centroid_to_node':'dist_input',
                                    'distance_stop_to_node':'dist_stop',
                                    'closest_stopname':'stop_name',
                                    'closest_stopid':'stop_id',
                                    })
    
    return output


def write_output(output, path, filename, suffix):
    # tilføj _distance som endelse på filnavnet
    suffix_formatted = '_' + suffix + '.'
    output_filename = suffix_formatted.join(filename.split('.'))
    
    # skriv shapefil
    output.to_file(path + output_filename, 
                   driver='ESRI Shapefile')
    
    return output_filename


print('-'*50)
print('6/6 Påbegynder klargøring af resultat.')
start = time()

# formater output
output = format_output(kvadratnet)

# klargør line data
if write_routes:
    output_line = output.set_geometry('line_geometry')
    output_line = output_line.drop(columns=['geometry'])
    
    output = output.drop(columns=['line_geometry'])

# skriv fil med objekter
output_filename = write_output(output=output, path=result_path, filename=kvadratnet_filename, suffix='distance')

# skriv fil med lines
if write_routes:
    output_line_filename = write_output(output=output_line, path=result_path, filename=kvadratnet_filename, suffix='line')

end = time()
print(f'Resultat gemt som {output_filename} på {round(end-start, 2)} sekunder.')
