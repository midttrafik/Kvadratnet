import pandas as pd
import geopandas as gpd
from shapely import LineString
from src.abstract.DataLoader import DataLoader


class Polygoner(DataLoader):
    def __init__(self, 
                 path: str, 
                 filename: str, 
                 crs: str) -> None:
        self.path = path
        self.filename = filename
        self.crs = crs
        
    def get_data(self) -> pd.DataFrame:
        kvadratnet = gpd.read_file(
            self.path + self.filename, 
            crs=self.crs
        )
        
        # udregn centroider
        kvadratnet['geometry_center'] = kvadratnet.centroid
        return kvadratnet


class Punkter(DataLoader):
    def __init__(self, 
                 path: str, 
                 filename: str, 
                 crs: str) -> None:
        self.path = path
        self.filename = filename
        self.crs = crs
        
    def get_data(self) -> pd.DataFrame:
        punkter = gpd.read_file(
            self.path + self.filename,
            crs=self.crs
        )
    
        # lav kopi af geometry kolonne
        punkter['geometry_center'] = punkter['geometry'].copy()
        return punkter


class FlexturData(DataLoader):
    def __init__(self,
                 path: str,
                 filename: str,
                 crs: str,
                 method: str) -> None:
        self.path = path
        self.filename = filename
        self.crs = crs
        self.method = method
    
    def get_data(self) -> pd.DataFrame:
        # indlæs fil
        df = pd.read_csv(
            self.path + self.filename,
            delimiter=';',
            decimal=',',
            encoding='utf-8'
        )
        
        df.rename(
            columns={'Antal Rejser': 'Rejser',
                     'Antal passagerer': 'Passagerer'}, 
            inplace=True
        )
        
        # til føj id kolonne
        df['id'] = [i for i in range(0, df.shape[0])]
        
        # lav geometri for fra punkt og til punkt
        point_from = gpd.points_from_xy(
            x=df['Fra X'], 
            y=df['Fra Y'],
            crs=self.crs
        )
        point_to = gpd.points_from_xy(
            x=df['Til X'], 
            y=df['Til Y'],
            crs=self.crs
        )
        
        if self.method == 'Input':
            # lav geometri dataframe
            gdf = gpd.GeoDataFrame(
                df, 
                geometry=None
            )
            
            # opbevar fra punkt og til punkt
            gdf['point_from'] = point_from
            gdf['point_to'] = point_to
            
            # lav fugleflugtslinje mellem fra og til punkt for senere brug
            gdf['bird_flight'] = gdf.apply(
                lambda row: LineString([row['point_from'], row['point_to']]), 
                axis=1
            )

            # tilføj geometri
            gdf.set_geometry('point_from', inplace=True, crs=self.crs)           
            gdf.rename_geometry('geometry_center', inplace=True)
            
        elif self.method == 'Stop':
            # lav geometri dataframe
            gdf = gpd.GeoDataFrame(
                df,
                geometry=point_to,
                crs=self.crs
            )
            
            gdf['stop_name'] = None
            gdf['stop_code'] = None
            
        else:
            raise Exception('Fejl i indlæsning af Flexturs data')
        
        return gdf
    

class MobilePlan(DataLoader):
    def __init__(self, 
                 path: str, 
                 filename: str, 
                 crs: str, 
                 flex: bool, 
                 plus: bool, 
                 stander_9: bool, 
                 stander_nedlagt: bool) -> None:
        self.path = path
        self.filename = filename
        self.crs = crs
        self.flex = flex
        self.plus = plus
        self.stander_9 = stander_9
        self.stander_nedlagt = stander_nedlagt
        
    def get_data(self) -> pd.DataFrame:
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
            assert col in stop_df.columns, f'MobilePlan fil skal indeholde kolonnen {col}.'
        
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
        stop_gdf = stop_gdf.rename(columns={'Kode til stoppunkt': 'stop_code', 
                                            'Long name': 'stop_name'})
        return stop_gdf


class StopShapefile(DataLoader):
    def __init__(self, 
                 path: str, 
                 filename: str, 
                 crs: str,
                 flex: bool, 
                 plus: bool, 
                 stander_9: bool, 
                 stander_nedlagt: bool,
                 stop_code_col: str,
                 stop_name_col: str,
                 stop_geometry_col: str) -> None:
        self.path = path
        self.filename = filename
        self.crs = crs
        self.flex = flex
        self.plus = plus
        self.stander_9 = stander_9
        self.stander_nedlagt = stander_nedlagt
        self.stop_code_col = stop_code_col
        self.stop_name_col = stop_name_col
        self.stop_geometry_col = stop_geometry_col
        
    def get_data(self) -> pd.DataFrame:
        # indlæs stop shapefil
        stop_gdf = gpd.read_file(self.path + self.filename)
        
        # ændre geometri til angivet crs hvis ikke den er tom eller har det i forvejen
        if stop_gdf.crs is None:
            assert 'Stopfil mangler CRS f.eks. EPSG:25832'
        elif stop_gdf.crs.name != self.crs:
            stop_gdf.to_crs(crs=self.crs, inplace=True)
        
        # tjek at angivne kolonner er korrekte
        assert self.stop_code_col in stop_gdf.columns, f'Kolonnen {self.stop_code_col} findes ikke i {self.filename}'
        assert self.stop_name_col in stop_gdf.columns, f'Kolonnen {self.stop_name_col} findes ikke i {self.filename}'
        assert self.stop_geometry_col == stop_gdf.geometry.name, f'Kolonnen {self.stop_geometry_col} findes ikke i {self.filename}'
        
        # standardiser navne og opdater geometrikolonne til det nye navn
        stop_gdf = stop_gdf.rename(columns={self.stop_code_col: 'stop_code',
                                            self.stop_name_col: 'stop_name',
                                            self.stop_geometry_col: 'geometry'})
        stop_gdf.set_geometry('geometry', inplace=True)
        
        # behold kun relevante kolonner og udfør filtre
        stop_gdf = stop_gdf[['stop_code', 'stop_name', 'geometry']]
        if self.stander_9:
            stop_gdf = stop_gdf[stop_gdf['stop_code'] % 10 != 9]
        if self.flex:
            stop_gdf = stop_gdf[stop_gdf['stop_name'].str.contains('knudepunkt', case=False)==False]
        if self.plus:
            stop_gdf = stop_gdf[stop_gdf['stop_name'].str.contains('plustur', case=False)==False]
        if self.stander_nedlagt:
            stop_gdf = stop_gdf[stop_gdf['stop_name'].str.contains('nedlagt|nedlag|nedelagt', case=False)==False]
            
        return stop_gdf