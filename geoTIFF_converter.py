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
import rasterio
import pandas as pd
import geopandas as gpd
import numpy as np
from shapely.geometry import box
from sqlalchemy import create_engine
from queries import get_srid, get_geometry_table


# Funzione per convertire un file GeoTIFF in un dataframe pandas
def geoTIFF_to_dataframe(geoTIFF_path: str, date: str) -> gpd.GeoDataFrame:
    '''
    Converte un file GeoTIFF in un dataframe pandas con le colonne 'ids', 'geometries', 'date' e 'SWE_mm'. \n
    La funzione apre il file GeoTIFF, estrae la matrice dei dati e le informazioni di georeferenziazione,
    calcola le coordinate geografiche (latitudine e longitudine) a partire dalla matrice di trasformazione,
    crea un array di id delle celle e un array di poligoni che rappresentano i pixel. \n
    Args:
        geoTIFF_path: Il percorso del file GeoTIFF da convertire.
        date: La data associata al file, in formato 'YYYYMMDD'. \n
    Returns:
        gpd.GeoDataFrame: Un GeoDataFrame contenente le colonne 'ID', 'geometry', 'date' e 'SWE_mm'. \n
    '''
    with rasterio.open(geoTIFF_path) as raster:
        # Estrae la matrice dei dati e le informazioni di georeferenziazione
        raster_data = raster.read(1)
        raster_transform = raster.transform
        raster_crs = raster.crs
        raster_noData = raster.nodata
    
    # Modifica i valori noData a NaN
    raster_data = np.where(raster_data == raster_noData, np.nan, raster_data)

    print(f"CRS del raster: {raster_crs}")
    # Controlla che la larghezza e l'altezza dei pixel siano pari a 500
    if raster_transform.a != 500 or raster_transform.e != -500:
        raise ValueError("La larghezza e l'altezza dei pixel devono essere pari a 500.")
    # Crea un array di indici per le righe e le colonne della matrice
    rows, cols = np.indices(raster_data.shape)
    # Calcola le coordinate x e y a partire dalla matrice di trasformazione
    lons, lats = raster_transform * (cols, rows)

    # Crea un array di id delle celle
    ids = np.char.add(np.char.zfill(rows.astype(str), 3), "_")
    ids = np.char.add(ids, np.char.zfill(cols.astype(str), 3))
    # Crea un array di poligoni che rappresentano i pixel
    pixels = [
        box(lon, lat, lon + 500, lat - 500)
        for lon, lat in zip(lons.flatten(), lats.flatten())
    ]

    # Crea un geodataframe geopandas con le coordinate e i valori della matrice
    geodataframe = gpd.GeoDataFrame(
        {'ID': ids.flatten(), 
         'date': pd.to_datetime(date, format='%Y-%m-%d'), 
         'SWE_mm': raster_data.flatten()}, 
        geometry=pixels, crs=raster_crs
    )

    # Rimuove le righe con valori NaN
    geodataframe = geodataframe.dropna(subset=['SWE_mm'])

    # Ritorna il dataframe pandas
    return geodataframe


# Funzione per controllare il CRS e le geometrie di un GeoDataFrame rispetto a una tabella PostgreSQL
def postgresql_crs_check(gdf: gpd.GeoDataFrame, geometry_table: str, db_url: str) -> bool:
    '''
    Controlla se il CRS e le geometrie presente sulla tabella delle geometrie del database corrispondono
    a quelli estratti dal raster e ritorna True se il CRS corrisponde, False altrimenti. \n
    Apre una connessione al database e esegue una query per ottenere il CRS della tabella.
    Se la tabella non ha geometrie presenti la funzione carica le geometrie del GeoDataFrame.
    Se la tabella ha geometrie presenti, la funzione controlla che le geometrie del geoDataFrame
    siano presenti nella tabella e che il CRS corrisponda. \n
    1. Se il CRS del GeoDataFrame non corrisponde a quello della tabella, ritorna False.
    2. Se il CRS del GeoDataFrame corrisponde a quello della tabella, ritorna True.
    Se le geometrie del GeoDataFrame non sono presenti nella tabella, le carica. \n
    Args:
        gdf: Il GeoDataFrame contenente le geometrie e i dati da caricare.
        table_name: Il nome della tabella nel database.
        db_url: L'URL di connessione al database PostgreSQL. \n
    Returns:
        bool: True se i CRS corrispondono, False altrimenti. \n
    '''
    # gestione degli errori
    if not isinstance(gdf, gpd.GeoDataFrame):
        raise ValueError("Il parametro gdf deve essere un GeoDataFrame.")
    if gdf.empty:
        raise ValueError("Il GeoDataFrame è vuoto. Non ci sono geometrie da controllare.")
    if gdf.crs is None:
        raise ValueError("Il GeoDataFrame non ha un CRS definito. Assicurati che il CRS sia impostato correttamente.")
    
    # Elimina le colonne non necessarie dal GeoDataFrame
    gdf = gdf[['ID', 'geometry']]
    # estrae il CRS del GeoDataFrame
    gdf_crs = gdf.crs.to_epsg()
    
    # Crea un motore di connessione al database
    engine = create_engine(db_url)
    
    # Estrae il CRS della tabella delle geometrie
    db_crs = get_srid(engine, schema='public', table=geometry_table, geometry_column='cell_geometry')
    # Estrae tutte le geometrie dalla tabella del database
    pixel_db = get_geometry_table(engine, schema='public', table=geometry_table)
    
    # Controlla se il CRS del GeoDataFrame corrisponde a quello della tabella
    if gdf_crs != db_crs:
        raise ValueError(f"Il CRS del GeoDataFrame ({gdf_crs}) non corrisponde al CRS della tabella ({db_crs}).")

    # Crea una colonna temporanea con geometrie WKB per confronto veloce e efficiente
    gdf['geometry_wkb'] = gdf['geometry'].apply(lambda geom: geom.wkb_hex)
    pixel_db['geometry_wkb'] = pixel_db['geometry'].apply(lambda geom: geom.wkb_hex)
    # Elimina le geoemetrie ripetute dal GeoDataFrame
    gdf_unique = gdf.drop_duplicates(subset='geometry_wkb')
    # Filtra le geometrie del GeoDataFrame che non sono presenti nella tabella
    missing_geometries = gdf_unique[~gdf_unique['geometry_wkb'].isin(pixel_db['geometry_wkb'])]
    
    # Carica il numero di geometrie mancanti
    if not missing_geometries.empty:
        print(f"Ci sono {len(missing_geometries)} geometrie mancanti nella tabella {geometry_table}.")
        # Carica le geometrie mancanti nella tabella
        missing_geometries.drop(columns='geometry_wkb', inplace=True)
        missing_geometries.to_postgis(geometry_table, con=engine, if_exists='append', index=False)

    # Chiude la connessione al database
    engine.dispose()


# Funzione per caricare un dataframe pandas su un server postgreSQL
def dataframe_to_postgresql(df: pd.DataFrame, SWE_table: str, db_url: str) -> None:
    '''
    Carica un dataframe pandas su un server postgreSQL. \n
    Args:
        df: Il dataframe pandas da caricare.
        SWE_table: Il nome della tabella in cui caricare i dati.
        db_url: L'URL di connessione al database PostgreSQL. \n
    Returns:
        None \n
    '''
    # gestione degli errori
    if not isinstance(df, pd.DataFrame):
        raise ValueError("Il parametro gdf deve essere un DataFrame.")
    if df.empty:
        raise ValueError("Il DataFrame è vuoto. Non ci sono geometrie da controllare.")

    # Crea un motore di connessione al database
    engine = create_engine(db_url)
    # Carica il dataframe nella tabella specificata
    df.to_sql(SWE_table, con=engine, if_exists='append', index=False)
    # Chiude la connessione al database
    engine.dispose()


# Funzione per controllare se un file GeoTIFF è valido
def is_valid_file(file_name: str) -> str:
    '''
    Controlla se il file è un GeoTIFF valido, ovvero se è nel formato 'SWE_YYYY-MM-DD.tif'. \n
    Ritorna la data se il file è un GeoTIFF valido, altrimenti solleva un'eccezione. \n
    Args:
        file_name: Il nome del file da controllare. \n
    Returns:
        str: La data estratta dal nome del file nel formato 'YYYY-MM-DD'. \
    '''
    # Controlla che il nome del file sia una stringa
    if not isinstance(file_name, str):
        raise ValueError("Il nome del file deve essere una stringa.")
    
    # Divide il nome del file 'SWE_YYYY-MM-DD.tif' in parti
    # Estrae il prefisso 'SWE' e la data dal nome del file
    parts = file_name.split('_')
    prefix = parts[0]
    # Estrae la data dal nome del file
    parts = parts[1].split('.') 
    date = parts[0]  # Estrae la data dal nome del file
    # Estrae l'estensione del file
    extension = parts[1]

    # Controlla che il prefisso sia 'SWE' e l'estensione sia 'tif'
    if prefix != 'SWE' or extension != 'tif':
        raise ValueError("Il nome del file deve essere nel formato 'SWE_YYYY-MM-DD.tif'.")
    # Controlla che la data sia nel formato 'YYYY-MM-DD'
    try:
        pd.to_datetime(date, format='%Y-%m-%d')
    except ValueError:
        raise ValueError("La data nel nome del file deve essere nel formato 'YYYY-MM-DD'.")
    
    return date


# funzione completa per eseguire la conversione e il caricamento dei file GeoTIFF
def convert_and_upload(file_path: str, db_url: str, geometry_table: str = 'geometry_table', swe_table: str = 'daily_SWE_table') -> None:
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
    file = os.path.basename(file_path)    # Controlla che il nome del file sia salvato nel formato 'SWE_YYYY-MM-DD.tif'
    date = is_valid_file(file)

    # Converte il file GeoTIFF in un geodataframe geopandas
    gdf = geoTIFF_to_dataframe(file_path, date)
    # Controlla il CRS e le geometrie del GeoDataFrame rispetto alla tabella del database
    postgresql_crs_check(gdf, geometry_table, db_url)
    # Converte il GeoDataFrame in un dataframe pandas eliminando le geometrie
    df = gdf[['IDs', 'date', 'SWE_mm']]
    # Carica il GeoDataFrame nella tabella delle geometrie del database
    dataframe_to_postgresql(df, swe_table, db_url)
