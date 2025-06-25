'''
Questo modulo fornisce le query SQL per la gestione dei dati nel database PostgreSQL. \n
'''
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


# Funzione per ottenere un GeoDataFrame contenente le geometrie da una tabella geometrica in un database PostgreSQL
def get_geometry_table(engine, schema: str, table: str) -> gpd.GeoDataFrame:
    '''
    Ottiene un GeoDataFrame contenente le geometrie da una tabella geometrica in un database PostgreSQL. \n
    Args:
        engine: L'engine SQLAlchemy per la connessione al database.
        schema: Lo schema della tabella nel database.
        table: Il nome della tabella geometrica. \n
    Returns:
        gpd.GeoDataFrame: Un GeoDataFrame contenente le geometrie della tabella. \n
    '''
    query = f"SELECT * FROM {schema}.{table}"
    gdf = gpd.read_postgis(query, con=engine, geom_col='cell_geometry')
    return gdf
