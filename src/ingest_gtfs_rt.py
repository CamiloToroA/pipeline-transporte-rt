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
    print(f"[{time.strftime('%H:%M:%S')}] Conectando al endpoint de iTranvias...")
    
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
            
            if data.get("resultado") != "OK":
                print("[WARN] La API no devolvió un estado OK.")
                return

            sentidos = data.get("paradas", [])
            
            if not sentidos:
                print("[INFO] Servidor consultado: No hay elementos activos en este momento (horario nocturno).")
                return

            print("Conexion exitosa con la API de iTranvias.")
            
            records = []
            timestamp_extraccion = pd.Timestamp.now()

            for sentido_item in sentidos:
                sentido_id = sentido_item.get("sentido")
                lista_paradas = sentido_item.get("paradas", [])
                
                for parada_item in lista_paradas:
                    parada_id = parada_item.get("parada")
                    buses = parada_item.get("buses", [])
                    
                    for bus_item in buses:
                        records.append({
                            "sentido": str(sentido_id),
                            "parada_id": str(parada_id),
                            "bus_id": str(bus_item.get("bus")),
                            "estado": str(bus_item.get("estado")),
                            "distancia": pd.to_numeric(bus_item.get("distancia"), errors='coerce'),
                            "fecha_peticion": data.get("fecha_peticion"),
                            "created_at": timestamp_extraccion # Marca de tiempo exacta de inserción
                        })
            
            if records:
                df = pd.DataFrame(records)
                print(f"Se obtuvieron {len(df)} registros de buses en paradas.")
                
                engine = create_engine(DATABASE_URL)
                
                # Usamos 'append' para conservar el histórico en lugar de borrar la tabla
                df.to_sql('line_status_rt', engine, if_exists='append', index=False)
                print("Tabla 'line_status_rt' actualizada (append) con exito en PostgreSQL.")
            else:
                print("Se encontraron estructuras de paradas, pero sin buses asignados actualmente.")

        else:
            print(f"Error HTTP {response.status_code}: {response.text}")

    except Exception as e:
        print(f"Error al conectar con el servicio: {e}")

if __name__ == "__main__":
    fetch_and_process_rt()