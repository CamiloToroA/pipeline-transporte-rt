import os
import time
import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine
import pandas as pd

load_dotenv()

DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "adminpassword")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "transporte_db")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

RT_URL = "https://itranvias.com/queryitr_v3.php"

def fetch_and_process_rt():
    print(f"Conectando al endpoint de iTranvias: {RT_URL}")
    
    params = {
        "dato": "100",
        "func": "2",
        "_": int(time.time() * 1000)
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
        "Referer": "https://itranvias.com/"
    }

    try:
        response = requests.get(RT_URL, params=params, headers=headers, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            print("Conexion exitosa con la API de iTranvias.")
            
            # La respuesta viene estructurada por sentidos y paradas
            sentidos = data.get("paradas", [])
            
            records = []
            # Recorremos cada sentido (ida/vuelta)
            for sentido_item in sentidos:
                sentido_id = sentido_item.get("sentido")
                lista_paradas = sentido_item.get("paradas", [])
                
                # Recorremos cada parada dentro del sentido
                for parada_item in lista_paradas:
                    parada_id = parada_item.get("parada")
                    buses = parada_item.get("buses", [])
                    
                    # Recorremos cada bus asignado a la parada actual
                    for bus_item in buses:
                        records.append({
                            "sentido": sentido_id,
                            "parada_id": parada_id,
                            "bus_id": bus_item.get("bus"),
                            "estado": bus_item.get("estado"),
                            "distancia": bus_item.get("distancia"),
                            "fecha_peticion": data.get("fecha_peticion")
                        })
            
            if records:
                df = pd.DataFrame(records)
                print(f"Se obtuvieron {len(df)} registros de buses en paradas.")
                
                engine = create_engine(DATABASE_URL)
                # Guardamos en una tabla especifica para el estado de lineas en tiempo real
                df.to_sql('line_status_rt', engine, if_exists='replace', index=False)
                print("Tabla 'line_status_rt' actualizada con exito en PostgreSQL.")

                # ---> FRAGMENTO USADO PARA VALIDAR LA DATA DE LA API - TEMPORAL <---
                print("\n--- Visualizacion de los datos guardados en PostgreSQL ---")
                query_df = pd.read_sql("SELECT * FROM line_status_rt;", engine)
                print(query_df.to_markdown(index=False))

            else:
                print("La API respondio, pero no se encontraron buses activos en la estructura de paradas.")
                print(f"Respuesta completa del servidor: {data}")
        else:
            print(f"Error HTTP {response.status_code}: {response.text}")

    except Exception as e:
        print(f"Error al conectar con el servicio: {e}")

if __name__ == "__main__":
    fetch_and_process_rt()