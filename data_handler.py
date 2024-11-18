import pandas as pd
import geopandas as gpd

#----------------------------------------------------------------------------------------------------------
# Tilføj if case for hver type af data
#----------------------------------------------------------------------------------------------------------
def select_method(input_read_method_name, stop_read_method_name):
    input_read_method = None
    stop_read_method = None
    stop_filter_method = None
    stop_transform_method = None
    
    # tilføj cases for input
    if input_read_method_name in ['Befolkningskvadratnet']:
        input_read_method = befolkningskvadratnet
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
# Tilføj metoder for hver type input data
#----------------------------------------------------------------------------------------------------------
# Befolkningskvadratnet
def befolkningskvadratnet(path, filename, crs):
    kvadratnet = gpd.read_file(path + filename, 
                               crs=crs)
    
    # udregn centroider
    kvadratnet['geometry_center'] = kvadratnet.centroid
    
    return kvadratnet


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
        stop_df = stop_df[stop_df['Long name'].str.contains('Knudepunkt|knudepunkt')==False]
    if stop_filters['Fjern Plustur']:
        stop_df = stop_df[stop_df['Long name'].str.contains('Plustur|plustur')==False]
    if stop_filters['Fjern nedlagte standere']:
        stop_df = stop_df[stop_df['Long name'].str.contains('NEDLAGT|nedlagt|Nedlagt')==False]
        
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
        self._stop_gdf = self._stop_transform_method(stop_df, self._crs)
        
    
    def get_stops(self):
        return self._stop_gdf
    
    
    def load_and_process_input(self, path, filename):
        self._input_gdf = self._input_read_method(path, filename, self._crs)
        
        # tjek at geometrien er gemt som geometry_center
        assert 'geometry_center' in self._input_gdf.columns, f'{self._input_read_method} skal indeholde kolonnen geometry_center med punkt-geometrien.'


    def get_input(self):
        return self._input_gdf