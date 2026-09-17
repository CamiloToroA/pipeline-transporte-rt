import time
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from ingest_gtfs_rt import fetch_and_process_rt

INTERVALO_SEGUNDOS = 60 
HORA_INICIO = 6   # 06:00 AM
HORA_FIN = 23     # 23:00 PM

ZONA_ESPAÑA = ZoneInfo("Europe/Madrid")

if __name__ == "__main__":
    print("=== INICIANDO ORQUESTADOR AUTOMATIZADO (VENTANA HORARIA ESPAÑA) ===")
    print(f"Horario de operación: de {HORA_INICIO}:00 a {HORA_FIN}:00 hrs.")
    print("Presionar [Ctrl + C] en cualquier momento para un apagado de emergencia.\n")
    
    try:
        while True:
            ahora_españa = datetime.now(ZONA_ESPAÑA)
            hora_actual = ahora_españa.hour
            
            # Si estamos fuera de horario operativo (madrugada o noche pasada las 23:00)
            if hora_actual < HORA_INICIO or hora_actual >= HORA_FIN:
                # Calculamos el próximo inicio (las 6:00 AM)
                siguiente_inicio = ahora_españa.replace(hour=HORA_INICIO, minute=0, second=0, microsecond=0)
                
                # Si ya pasaron las 23:00, el inicio programado es para mañana
                if hora_actual >= HORA_FIN:
                    siguiente_inicio += timedelta(days=1)
                
                segundos_a_dormir = (siguiente_inicio - ahora_españa).total_seconds()
                horas_a_dormir = segundos_a_dormir / 3600
                
                print(f"[{ahora_españa.strftime('%Y-%m-%d %H:%M:%S')}] -> Fuera de horario operativo.")
                print(f"[*] Entrando en modo reposo nocturno. Despertará a las {HORA_INICIO}:00 AM (en ~{horas_a_dormir:.2f} horas)...\n")
                
                time.sleep(segundos_a_dormir)
                continue

            # Si estamos dentro de la ventana diurna, ejecutamos normalmente
            print(f"[{ahora_españa.strftime('%Y-%m-%d %H:%M:%S')}] -> Ejecutando ciclo programado...")
            fetch_and_process_rt()
            
            print(f"Esperando {INTERVALO_SEGUNDOS} segundos para la siguiente ejecución...\n")
            time.sleep(INTERVALO_SEGUNDOS)
            
    except KeyboardInterrupt:
        print("\n\n[!]: ¡Señal de interrupción recibida (Ctrl + C)!")
        print("[!]: Deteniendo el orquestador de forma segura...")
        sys.exit(0)