import time
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from ingest_gtfs_rt import fetch_and_process_rt

# Intervalo de tiempo: cada 1 minuto = 60 segundos
INTERVALO_SEGUNDOS = 60 

# Definimos la ventana operativa en hora peninsular de España
HORA_INICIO = 6   # Comienza a las 06:00 AM
HORA_FIN = 23     # Se detiene a las 23:00 (11:00 PM)

ZONA_ESPAÑA = ZoneInfo("Europe/Madrid")

if __name__ == "__main__":
    print("=== INICIANDO ORQUESTADOR AUTOMATIZADO (VENTANA HORARIA ESPAÑA) ===")
    print(f"Horario de operación: de {HORA_INICIO}:00 a {HORA_FIN}:00 hrs.")
    print(f"Frecuencia de consulta: Cada {INTERVALO_SEGUNDOS} segundos.")
    print("Presiona [Ctrl + C] en cualquier momento para un apagado de emergencia.\n")
    
    try:
        while True:
            ahora_españa = datetime.now(ZONA_ESPAÑA)
            hora_actual = ahora_españa.hour
            
            # Si aún no es la hora de inicio, esperamos al siguiente ciclo
            if hora_actual < HORA_INICIO:
                print(f"[{ahora_españa}] -> Fuera de horario operativo (Aún no son las {HORA_INICIO}:00 AM). En pausa...")
                time.sleep(INTERVALO_SEGUNDOS)
                continue

            # Si ya pasamos la hora de fin, el servicio finaliza por hoy
            if hora_actual >= HORA_FIN:
                print(f"[{ahora_españa}] -> Hora límite nocturna alcanzada ({HORA_FIN}:00 hrs). El servicio finaliza por hoy.")
                break

            # Ejecutamos dentro de la ventana diurna
            print(f"[{ahora_españa}] -> Ejecutando ciclo programado...")
            
            fetch_and_process_rt()
            
            print(f"[{ahora_españa}] -> Ciclo finalizado.")
            print(f"Esperando {INTERVALO_SEGUNDOS} segundos para la siguiente ejecución...\n")
            
            time.sleep(INTERVALO_SEGUNDOS)
            
    except KeyboardInterrupt:
        print("\n\n[!]: ¡Señal de interrupción recibida (Ctrl + C)!")
        print("[!]: Deteniendo el orquestador de forma segura...")
        print("[*]: Recursos liberados. ¡Apagado completado con éxito!")
        sys.exit(0)