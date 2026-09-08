import os
import zipfile
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "adminpassword")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "transporte_db")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
ZIP_PATH = "coruna_gtfs.zip"
EXTRACT_PATH = "data_extracted"

def process_static_gtfs():
    print("Descomprimiendo el GTFS estático de A Coruña...")
    os.makedirs(EXTRACT_PATH, exist_ok=True)
    
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
        zip_ref.extractall(EXTRACT_PATH)
    
    engine = create_engine(DATABASE_URL)
    
    gtfs_files = {
        'routes': 'routes.txt',
        'stops': 'stops.txt',
        'trips': 'trips.txt'
    }
    
    for table_name, filename in gtfs_files.items():
        file_path = os.path.join(EXTRACT_PATH, filename)
        if os.path.exists(file_path):
            print(f"Cargando {filename} en la tabla '{table_name}'...")
            df = pd.read_csv(file_path)
            df.to_sql(table_name, engine, if_exists='replace', index=False)
            print(f" Tabla '{table_name}' creada con éxito ({len(df)} registros). Verifícalo consultando la base de datos.")
        else:
            print(f"️ No se encontró el archivo {filename}")

    print(" ¡Proceso de ingesta estática finalizado!")

if __name__ == "__main__":
    process_static_gtfs()