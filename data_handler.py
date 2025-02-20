import pandas as pd
import geopandas as gpd
from abc import ABC, abstractmethod

class DataLoader(ABC):
    def __init__(self, path, filename, crs):
        self.path = path
        self.filename = filename
        self.crs = crs
        self.data = None
    
    @abstractmethod
    def load_and_process(self):
        pass
    
    def get_data(self):
        if self.data is None:
            raise ValueError('Data er ikke indlæst og gemt i self.data, kald load_and_process() først.')
        return self.data
    

class Polygoner(DataLoader):
    def load_and_process(self):
        kvadratnet = gpd.read_file(
            self.path + self.filename, 
            crs=self.crs
        )
        
        # udregn centroider
        kvadratnet['geometry_center'] = kvadratnet.centroid
        self.data = kvadratnet


class Punkter(DataLoader):
    def load_and_process(self):
        punkter = gpd.read_file(
            self.path + self.filename,
            crs=self.crs
        )
    
        # lav kopi af geometry kolonne
        punkter['geometry_center'] = punkter['geometry'].copy()
        self.data = punkter
    

class MobilePlan(DataLoader):
    def __init__(self, path, filename, crs, flex, plus, stander_9, stander_nedlagt):
        super().__init__(path, filename, crs)
        self.flex = flex
        self.plus = plus
        self.stander_9 = stander_9
        self.stander_nedlagt = stander_nedlagt
        
    def load_and_process(self):
        # læs stop csv fil
        stop_df = pd.read_csv(
            self.path + self.filename, 
            delimiter=';', 
            decimal=',', 
            encoding='Latin-1'
        )
        
        # verificer at påkrævede kolonner eksisterer
        cols_to_keep = ['Kode til stoppunkt', 'Pos.nr.', 'Long name', 'UTM32_Easting', 'UTM32_Northing']
        for col in cols_to_keep:
            assert col in stop_df.columns, f'Standertabellen skal indeholde kolonnen {col}.'
        
        # behold kun påkrævede kolonner
        stop_df = stop_df[cols_to_keep]
        
        if self.stander_9:
            stop_df = stop_df[stop_df['Pos.nr.'] != 9]
        if self.flex:
            stop_df = stop_df[stop_df['Long name'].str.contains('knudepunkt', case=False)==False]
        if self.plus:
            stop_df = stop_df[stop_df['Long name'].str.contains('plustur', case=False)==False]
        if self.stander_nedlagt:
            stop_df = stop_df[stop_df['Long name'].str.contains('nedlagt|nedlag|nedelagt', case=False)==False]
        
        # transformer til geopandas
        stop_gdf = gpd.GeoDataFrame(
            stop_df, 
            geometry=gpd.points_from_xy(
                x=stop_df['UTM32_Easting'], 
                y=stop_df['UTM32_Northing']
            ), 
            crs=self.crs
        )
        stop_gdf = stop_gdf[['Kode til stoppunkt', 'Long name', 'geometry']]
        self.data = stop_gdf


