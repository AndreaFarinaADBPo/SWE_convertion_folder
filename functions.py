'''
Questo modulo fornisce le query SQL per la gestione dei dati nel database PostgreSQL. \n
'''
import pandas as pd
import geopandas as gpd
from sqlalchemy import text


# Funzione per ottenere il SRID (Spatial Reference Identifier) di una tabella geometrica in PostgreSQL
def get_srid(engine, schema: str, table: str, geometry_column: str) -> int:
    '''
    Ottiene il SRID (Spatial Reference Identifier) di una tabella geometrica in un database PostgreSQL. \n
    Args:
        engine: L'engine SQLAlchemy per la connessione al database.
        schema: Lo schema della tabella nel database.
        table: Il nome della tabella geometrica.
        geometry_column: Il nome della colonna geometrica nella tabella. \n
    Returns:
        int: Il SRID della colonna geometrica. \n
    '''
    crs_query = text("""
        SELECT srid
        FROM geometry_columns
        WHERE f_table_schema = :schema
          AND f_table_name = :table
          AND f_geometry_column = :geometry_column;
    """)
    with engine.connect() as connection:
        result = connection.execute(crs_query, {
            "schema": schema, 
            "table": table, 
            "geometry_column": geometry_column
        }).fetchone()
        return result[0] if result else None


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

