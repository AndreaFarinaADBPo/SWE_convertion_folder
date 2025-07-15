'''
Questo modulo contiene funzioni per convertire file GeoTIFF in formato tabellare e caricarli su un server postgreSQL. 
Le funzioni sono progettate per essere utilizzate in un contesto di interfaccia grafica, ma possono essere adattate per altri scopi. \n
I file geoTIFF vengono aperti utilizzando rasterio e viene estratta la matrice dei dati e le informazioni di georeferenziazione. \n
I dati vengono salvati in un dataframe pandas, con quattro colonne: 'ids', 'geometries', 'date' e 'SWE_mm':
latitudine e longitudine sono calcolate a partire dalla matrice di trasformazione assieme alla posizione del pixel,
la data è estratta dal nome del file e SWE_mm è il valore della matrice dei dati. \n
Infine il dataframe pandas viene caricato su un server postgreSQL utilizzando sqlalchemy. \n
'''
import os
import sys
import rasterio
from rasterio.crs import CRS
import affine
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import box
from sqlalchemy import create_engine, text
from functions import get_srid, is_valid_file, nivological_year

if hasattr(sys, '_MEIPASS'):
    # Percorso in esecuzione da exe creato da PyInstaller
    os.environ['PROJ_LIB'] = os.path.join(sys._MEIPASS, 'share', 'proj')
else:
    # Percorso durante lo sviluppo / da IDE
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.environ['PROJ_LIB'] = os.path.join(base_dir, ".venv", "Lib", "site-packages", "pyproj", "proj_dir", "share", "proj")

# Funzione per convertire un file GeoTIFF in un dataframe pandas
def geoTIFF_to_dataframe(geoTIFF_path: str, date: str, snow_year: int) -> tuple[pd.DataFrame, CRS, affine.Affine]:
    '''
    '''
    with rasterio.open(geoTIFF_path) as raster:
        # Estrae la matrice dei dati e le informazioni di georeferenziazione
        raster_data = raster.read(1)
        raster_transform = raster.transform
        raster_crs = raster.crs
        raster_noData = raster.nodata

    # Modifica i valori noData a NaN
    raster_data = np.where(raster_data == raster_noData, np.nan, raster_data)

    #  Crea un array di indici per le righe e le colonne della matrice
    rows, cols = np.indices(raster_data.shape)
    # Calcola le coordinate x e y a partire dalla matrice di trasformazione
    lons, lats = raster_transform * (cols, rows)
    # Converte le coordinate in interi
    lons = lons.astype(int)
    lats = lats.astype(int)
    # Crea gli indici delle celle come stringhe con zfill
    ids = np.char.add(np.char.zfill(lons.astype(str), 7), "_")
    ids = np.char.add(ids, np.char.zfill(lats.astype(str), 7))
    # Crea un geodataframe geopandas con le coordinate e i valori della matrice
    dataframe = pd.DataFrame(
        {'cell_id': ids.flatten(), 
         'snow_year' : snow_year,
         'date': pd.to_datetime(date, format='%Y-%m-%d'), 
         'swe_mm': raster_data.flatten()}
    )

    # Rimuove le righe con valori NaN
    dataframe = dataframe.dropna(subset=['swe_mm'])
    # Ritorna il dataframe pandas
    return dataframe, raster_crs, raster_transform


# Funzione per controllare il CRS e gli ID del GeoDataFrame rispetto alla tabella del database
def geometry_check(df_ids: pd.Series, crs, transform, geometry_table: str, db_url: str) -> bool:
    '''
    '''
    # Estrae il CRS e gli ID della tabella delle geometrie dal database
    engine = create_engine(db_url)
    try:
        # Estrae il CRS della tabella delle geometrie e i cell_id già presenti
        db_crs = get_srid(engine, schema='public', table=geometry_table, geometry_column='cell_geom')
        query = f'SELECT "cell_id" FROM {geometry_table}'
        db_ids = pd.read_sql(query, engine)["cell_id"]
    finally:
        engine.dispose()
    
    # Controlla che la larghezza e l'altezza dei pixel siano pari a 500
    if transform.a != 500 or transform.e != -500:
        raise ValueError("La larghezza e l'altezza dei pixel devono essere pari a 500.")
    # Controlla se il CRS del GeoDataFrame corrisponde a quello della tabella
    if db_crs.to_epsg() != crs.to_epsg():
        raise ValueError(f"Il CRS del geoTIFF {crs} non corrisponde al CRS della tabella {db_crs}.")

    # Trova i cell_id mancanti
    missing = df_ids[~df_ids.isin(db_ids)].tolist()
    return missing


# Funzione per aggiungere le geometrie mancanti al database
def add_missing_geometries(missing_ids: list, crs, geometry_table: str, db_url: str):
    '''
    Calcola le geometrie solo per gli ID mancanti e le carica nella geometry_table.
    '''
    if not missing_ids:
        return
    # Ricostruisce le geometrie per gli ID mancanti
    lons = [int(missing_id.split('_')[0]) for missing_id in missing_ids]
    lats = [int(missing_id.split('_')[1]) for missing_id in missing_ids]
    # Crea i poligoni per i pixel mancanti
    pixels = [box(lon, lat, lon + 500, lat - 500) for lon, lat in zip(lons, lats)]
    # Crea un GeoDataFrame con gli ID mancanti e le geometrie
    gdf = gpd.GeoDataFrame({'cell_id': missing_ids, 'cell_geom': pixels}, geometry='cell_geom', crs=crs)

    # Aggiunge le geometrie al database
    engine = create_engine(db_url)
    try:
        gdf.to_postgis(geometry_table, con=engine, if_exists='append', index=False)
    finally:
        engine.dispose()


# Funzione per caricare un dataframe pandas su un server postgreSQL
def dataframe_to_postgresql(df: pd.DataFrame, SWE_table: str, db_url: str) -> None:
    '''
    '''
    # gestione degli errori
    if not isinstance(df, pd.DataFrame):
        raise ValueError("Il parametro df deve essere un DataFrame.")
    if df.empty:
        raise ValueError("Il DataFrame è vuoto. Non ci sono dati da caricare.")

    # Carica il dataframe nella tabella specificata
    engine = create_engine(db_url)
    try:
        with engine.begin() as connection:
            # Scrivi su una tabella temporanea
            temp_table = "temp_swe_upload"
            df.to_sql(temp_table, con=connection, if_exists='replace', index=False)
            # Inserisci ignorando i duplicati
            insert_sql = f'''
                INSERT INTO {SWE_table} (cell_id, snow_year, date, swe_mm)
                SELECT cell_id, snow_year, date, swe_mm FROM {temp_table}
                ON CONFLICT (cell_id, snow_year, date) DO NOTHING;
                DROP TABLE {temp_table};
            '''
            connection.execute(text(insert_sql))
    finally:
        engine.dispose()


# funzione completa per eseguire la conversione e il caricamento dei file GeoTIFF
def convert_and_upload(file_path: str, db_url: str, geometry_table: str = 'cell_geom_table', swe_table: str = 'cell_daily_swe_table') -> None:
    '''
    Converte un file GeoTIFF in un dataframe pandas e lo carica su un server postgreSQL. \n
    Args:
        file_path: Il percorso del file GeoTIFF da convertire.
        db_url: L'URL di connessione al database PostgreSQL.
        geometry_table: Il nome della tabella delle geometrie nel database.
        swe_table: Il nome della tabella dei dati SWE nel database. \n
    Returns:
        None \n
    '''
    # Estrae il nome del file dal percorso
    file = os.path.basename(file_path)
    # Controlla che il nome del file sia salvato nel formato 'SWE_YYYY-MM-DD.tif'
    date = is_valid_file(file)
    # Calcola l'anno nivologico a partire dalla data
    snow_year = nivological_year(date)

    # Converte il file GeoTIFF in un geodataframe geopandas
    df, crs, transform = geoTIFF_to_dataframe(file_path, date, snow_year)
    # Controlla il CRS e gli ID del GeoDataFrame rispetto alla tabella del database
    missing_ids = geometry_check(df['cell_id'], crs, transform, geometry_table, db_url)
    # Aggiunge le geometrie mancanti al database
    add_missing_geometries(missing_ids, crs, geometry_table, db_url)
    # Carica il GeoDataFrame nella tabella delle geometrie del database
    dataframe_to_postgresql(df, swe_table, db_url)
