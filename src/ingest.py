import os
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Cargar variables del archivo .env
load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "transporte_db")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "adminpassword")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def generate_mock_gtfs_data():
    """Genera un DataFrame simulado con estructura GTFS-Realtime."""
    data = {
        "vehicle_id": ["BUS_101", "BUS_102", "BUS_103"],
        "route_id": ["R_01", "R_02", "R_01"],
        "latitude": [40.416775, 40.418000, 40.420000],
        "longitude": [-3.703790, -3.704000, -3.705000],
        "speed": [24.5, 18.0, 0.0],
        "timestamp": [datetime.now(timezone.utc), datetime.now(timezone.utc), datetime.now(timezone.utc)]
    }
    return pd.DataFrame(data)

def save_to_db(df):
    """Guarda el DataFrame en la base de datos PostgreSQL en Docker."""
    engine = create_engine(DATABASE_URL)
    df.to_sql("vehicle_positions", con=engine, if_exists="append", index=False)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Registros insertados con éxito: {len(df)}")

if __name__ == "__main__":
    df_positions = generate_mock_gtfs_data()
    save_to_db(df_positions)