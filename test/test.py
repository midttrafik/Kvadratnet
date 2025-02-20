import os
import sys
abspath = os.path.abspath(__file__)
dname = os.path.dirname(abspath)
os.chdir(dname+'\\..')
sys.path.insert(0, os.getcwd())

from src.strategy.DataStrategy import Polygoner, Punkter, MobilePlan
from src.algoritme_script import PathAlgorithm


def test_polygon_mobileplan_aarhus():
    stop_filename = 'MT_Stoppunkter_20241015.csv'
    kvadratnet_filename = 'befolkning_2024.shp'
    osm_place = 'Aarhus Kommune'
    flex = True
    plus = True
    stander_9 = False
    stander_nedlagt = True
    chunk_size = 500
    minimum_components = 200
    crs = 'EPSG:25832'
    data_path = 'src\Data\\'
    result_path = 'src\Resultater\\'

    
    kvadratnet_handler = Polygoner(
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

    algorithm.compute(write_result=False)


def test_punkt_mobileplan_aarhus():
    stop_filename = 'MT_Stoppunkter_20241015.csv'
    kvadratnet_filename = 'cvr_midtjylland.shp'
    osm_place = 'Aarhus Kommune'
    flex = True
    plus = True
    stander_9 = False
    stander_nedlagt = True
    chunk_size = 500
    minimum_components = 200
    crs = 'EPSG:25832'
    data_path = 'src\Data\\'
    result_path = 'src\Resultater\\'

    
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

    algorithm.compute(write_result=False)



if __name__ == '__main__':
    test_polygon_mobileplan_aarhus()
    #test_punkt_mobileplan_aarhus()