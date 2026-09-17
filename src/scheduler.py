import time
import sys
from datetime import datetime
from ingest_gtfs_rt import fetch_and_process_rt  # Importamos la función de ingesta

# Intervalo de tiempo entre ejecuciones (ejemplo: cada 5 minutos = 300 segundos)
INTERVALO_SEGUNDOS = 300 

if __name__ == "__main__":
    print("=== INICIANDO ORQUESTADOR AUTOMATIZADO ===")
    print("Presiona [Ctrl + C] en cualquier momento para un apagado de emergencia.\n")
    
    try:
        while True:
            print(f"[{datetime.now()}] -> Ejecutando ciclo programado...")
            
            # Llamamos a la función importada
            fetch_and_process_rt()
            
            print(f"[{datetime.now()}] -> Ciclo finalizado.")
            print(f"Esperando {INTERVALO_SEGUNDOS} segundos para la siguiente ejecución...\n")
            
            time.sleep(INTERVALO_SEGUNDOS)
            
    except KeyboardInterrupt:
        print("\n\n[!]: ¡Señal de interrupción recibida (Ctrl + C)!")
        print("[!]: Deteniendo el orquestador de forma segura...")
        print("[*]: Recursos liberados. ¡Apagado completado con éxito!")
        sys.exit(0)