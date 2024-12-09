import pandas as pd
import geopandas as gpd
from shapely import Point

#----------------------------------------------------------------------------------------------------------
# Tilføj if case for hver type af data
#----------------------------------------------------------------------------------------------------------
def select_method(input_read_method_name, stop_read_method_name):
    input_read_method = None
    stop_read_method = None
    stop_filter_method = None
    stop_transform_method = None
    
    # tilføj cases for input
    if input_read_method_name in ['Polygoner']:
        input_read_method = polygoner
    elif input_read_method_name in ['Punkter']:
        input_read_method = punkter
    else:
        raise ValueError(f'Fejl i navn på input metode {input_read_method_name}')
    
    # tilføj cases for stop
    if stop_read_method_name in ['MobilePlan']:
        stop_read_method = stop_mobileplan
        stop_filter_method = filter_stops
        stop_transform_method = geotransform_stops
    else:
        raise ValueError(f'Fejl i navn på stop metode(r) {stop_read_method_name}')
    
    
    return {'input_read_method': input_read_method, 
            'stop_read_method': stop_read_method,
            'stop_filter_method': stop_filter_method,
            'stop_transform_method': stop_transform_method}


#----------------------------------------------------------------------------------------------------------
# Tilføj metoder for hver type input data.
# Argumenter skal være (path, filename, crs)
# Output skal indeholde geometry_center af typen Point
#----------------------------------------------------------------------------------------------------------
# Befolkningskvadratnet
def polygoner(path, filename, crs):
    kvadratnet = gpd.read_file(path + filename, 
                               crs=crs)
    
    # udregn centroider
    kvadratnet['geometry_center'] = kvadratnet.centroid
        
    return kvadratnet


# CVR Midtjylland
def punkter(path, filename, crs):
    punkter = gpd.read_file(path + filename,
                            crs=crs)
    
    # lav kopi af geometry kolonne
    punkter['geometry_center'] = punkter['geometry'].copy()
        
    return punkter


#----------------------------------------------------------------------------------------------------------
# Tilføj metode for hver type stop data
#----------------------------------------------------------------------------------------------------------
def stop_mobileplan(path, filename):
    # læs stop csv fil
    stop_df = pd.read_csv(path + filename, 
                          delimiter=';', 
                          decimal=',', 
                          encoding='Latin-1')
    
    # verificer at påkrævede kolonner eksisterer
    cols_to_keep = ['Kode til stoppunkt', 'Pos.nr.', 'Long name', 'UTM32_Easting', 'UTM32_Northing']
    for col in cols_to_keep:
        assert col in stop_df.columns, f'Standertabellen skal indeholde kolonnen {col}.'
    
    # behold kun påkrævede kolonner
    stop_df = stop_df[cols_to_keep]
    
    return stop_df


def filter_stops(stop_df, stop_filters):
    # fjern filtrer standere baseret på filtre
    assert len(stop_filters.keys()) == 4, 'Stop_filters skal indeholde præcis 4 filtre.'
    assert 'Fjern 09 stander' in stop_filters, 'Stop_filter mangler \'Fjern 09 stander\' med boolsk værdi.'
    assert 'Fjern Flextur' in stop_filters, 'Stop_filter mangler \'Fjern Flextur\' med boolsk værdi.'
    assert 'Fjern Plustur' in stop_filters, 'Stop_filter mangler \'Fjern Plustur\' med boolsk værdi.'
    assert 'Fjern nedlagte standere' in stop_filters, 'Stop_filter mangler \'Fjern nedlagte standere\' med boolsk værdi'
    
    if stop_filters['Fjern 09 stander']:
        stop_df = stop_df[stop_df['Pos.nr.'] != 9]
    if stop_filters['Fjern Flextur']:
        stop_df = stop_df[stop_df['Long name'].str.contains('knudepunkt', case=False)==False]
    if stop_filters['Fjern Plustur']:
        stop_df = stop_df[stop_df['Long name'].str.contains('plustur', case=False)==False]
    if stop_filters['Fjern nedlagte standere']:
        stop_df = stop_df[stop_df['Long name'].str.contains('nedlagt|nedlag|nedelagt', case=False)==False]
        
    return stop_df


def geotransform_stops(stop_df, crs):
    # transformer til geopandas
    stop_gdf = gpd.GeoDataFrame(stop_df, 
                                geometry=gpd.points_from_xy(x=stop_df['UTM32_Easting'], 
                                                            y=stop_df['UTM32_Northing']), 
                                crs=crs)
    stop_gdf = stop_gdf[['Kode til stoppunkt', 'Long name', 'geometry']]
    
    return stop_gdf


#----------------------------------------------------------------------------------------------------------
# Klasse til at håndtere data
class DataHandler():
    def __init__(self, input_read_method_name, stop_read_method_name, crs):
        
        selection = select_method(input_read_method_name, stop_read_method_name)
        
        self._input_read_method = selection['input_read_method']
        self._stop_read_method = selection['stop_read_method']
        self._stop_filter_method = selection['stop_filter_method']
        self._stop_transform_method = selection['stop_transform_method']
        
        self._crs = crs
        
        self._stop_gdf = None
        self._input_gdf = None
    
    
    def load_and_process_stops(self, path, filename, stop_filters):
        stop_df = self._stop_read_method(path, filename)
        stop_df = self._stop_filter_method(stop_df, stop_filters)
        stop_df = self._stop_transform_method(stop_df, self._crs)
        
        # reset index og gem
        self._stop_gdf = stop_df.reset_index(drop=True)
        
    
    def get_stops(self):
        return self._stop_gdf
    
    
    def load_and_process_input(self, path, filename):
        input_gdf = self._input_read_method(path, filename, self._crs)
        
        # find og drop NA værdier i geometrien
        NA_indexes = input_gdf['geometry_center'].isna()
        if NA_indexes.any():
            NA_antal = NA_indexes.sum()
            NA_list = input_gdf.index[NA_indexes==True].to_list()
            print(f'Fjernet {NA_antal} rækker i input hvor geometrien er NA! De vil ikke være tilstede i resultatet.')
            print(f'Rækkerne som er fjernet er: {NA_list}')
        input_gdf = input_gdf[NA_indexes==False]
        
        # reset index og gem
        self._input_gdf = input_gdf.reset_index(drop=True)
        
        # tjek at geometrien er gemt som geometry_center med typen Point
        assert 'id' in self._input_gdf.columns, f'{self._input_read_method} skal indeholde id kolonne.'
        assert 'geometry_center' in self._input_gdf.columns, f'{self._input_read_method} skal indeholde kolonnen geometry_center med punkt-geometrien.'
        assert isinstance(self._input_gdf.loc[0, 'geometry_center'], Point), 'Hvert punkt i geometry_center skal være af typen Point.'


    def get_input(self):
        return self._input_gdf