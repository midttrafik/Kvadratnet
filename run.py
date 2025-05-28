import os
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname)

from src.algoritme_script import PathAlgorithm
from src.strategy.DataStrategy import *
from src.strategy.TaskStrategy import *

import click


if __name__ == '__main__':
    
    osm_place = click.prompt("Navn på administrativt OSM område", type=str, default='Region Midtjylland')
    crs = click.prompt("CRS", type=str, default='EPSG:25832')
    data_path = click.prompt("Sti til data", type=str, default='src\Data\\')
    result_path = click.prompt("Sti til resultater", type=str, default='src\Resultater\\')
    
    print("-"*50)
    print("Indtast information om opgaven.")
    task_type = click.prompt("Opgave type", type=click.Choice(['Nærmeste stop', 'Stop indenfor distance']))
    
    if task_type == 'Nærmeste stop':
        task_strategy = ShortestPath()
    elif task_type == 'Stop indenfor distance':
        max_distances = click.prompt("Liste af distancer", type=str, default='400,500,600,800,1000,2000')
        max_distances = [int(dist) for dist in max_distances.split(',')]
        task_strategy = AllNearbyStops(max_distances=max_distances)
    
    
    print("-"*50)
    print("Indtast information om kvadratnet.")
    kvadratnet_type = click.prompt("Indlæsning af data", type=click.Choice(['Polygoner', 'Punkter']))
    kvadratnet_filename = click.prompt("Navn på datafil uden sti til mappe", type=str)
    
    if kvadratnet_type == 'Polygoner':
        kvadratnet_handler = Polygoner(
            path=data_path,
            filename=kvadratnet_filename,
            crs=crs
        )
    elif kvadratnet_type == 'Punkter':
        kvadratnet_handler = Punkter(
            path=data_path,
            filename=kvadratnet_filename,
            crs=crs
        )
    else:
        raise Exception('Ugyldig metode til indlæsning af kvadratnet.')

    
    print("-"*50)
    print("Indtast information om stop.")
    stop_type = click.prompt("Indlæsning af stop", type=click.Choice(['MobilePlan', 'Shapefil']))
    stop_filename = click.prompt("Navn på stopfil uden sti til mappe", type=str)
    flex = click.prompt("Fjern Flextur", type=bool, default=False)
    plus = click.prompt("Fjern Plustur", type=bool, default=True)
    stander_9 = click.prompt("Fjern 09 stander", type=bool, default=False)
    stander_nedlagt = click.prompt("Fjern nedlagte standere", type=bool, default=True)

    if stop_type == 'MobilePlan':
        stop_handler = MobilePlan(
            path=data_path,
            filename=stop_filename,
            crs=crs,
            flex=flex,
            plus=plus,
            stander_9=stander_9,
            stander_nedlagt=stander_nedlagt
        )
    elif stop_type == 'Shapefil':
        stop_code_col = click.prompt("Navn på kolonne som indeholder stopnummer", type=str)
        stop_name_col = click.prompt("Navn på kolonne som indeholder stopnavn", type=str)
        stop_geometry_col = click.prompt("Navn på kolonne som indeholder geometri", type=str)
        stop_handler = StopShapefile(
            path=data_path, 
            filename=stop_filename, 
            crs=crs, 
            flex=flex, 
            plus=plus, 
            stander_9=stander_9, 
            stander_nedlagt=stander_nedlagt, 
            stop_code_col=stop_code_col, 
            stop_name_col=stop_name_col, 
            stop_geometry_col=stop_geometry_col
        )
    else:
        raise Exception('Ugyldig metode til indlæsning af stop.')
    
    
    print("-"*50)
    print("Evt. ændre parametre.")
    write_result = click.prompt("Skriv resultat", type=bool, default=True)
    chunk_size = click.prompt("Chunk size", type=int, default=500)
    minimum_components = click.prompt("Mindste antal knuder i et uforbundet komponent", type=int, default=200)

    algorithm = PathAlgorithm(
        kvadratnet_filename=kvadratnet_filename,
        osm_place=osm_place,
        chunk_size=chunk_size,
        minimum_components=minimum_components,
        crs=crs,
        data_path=data_path,
        result_path=result_path,
        kvadratnet_loader=kvadratnet_handler,
        stop_loader=stop_handler,
        task_strategy=task_strategy
    )

    algorithm.compute(write_result=write_result)
