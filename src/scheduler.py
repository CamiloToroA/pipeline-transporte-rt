import time
import sys
from datetime import datetime, timedelta, timezone
from config import ZONA_ESPAÑA
from ingest_gtfs_rt import fetch_and_process_rt, esperar_bd, aplicar_esquema, lineas_validas, cargar_dimensiones

HORA_INICIO = 6   # 06:00
HORA_FIN = 24     # 00:00; el último servicio sale a las 23:00 y termina pasadas las 23:30

# Límites de itranvias.com: 1/s, 4/min, 199/h y 1999/día (los indica la propia respuesta 429).
# Repartimos el 95 % de la cuota diaria en la ventana operativa: ~34 s entre consultas, ~105/h
CUOTA_DIARIA = 1999
ESPACIADO_SEGUNDOS = (HORA_FIN - HORA_INICIO) * 3600 / (CUOTA_DIARIA * 0.95)

# Ante un 429 dejamos de consultar; la pausa se duplica mientras siga bloqueada
PAUSA_429_INICIAL = 5 * 60
PAUSA_429_MAXIMA = 60 * 60


def segundos_hasta_inicio(ahora_españa):
    siguiente_inicio = ahora_españa.replace(hour=HORA_INICIO, minute=0, second=0, microsecond=0)
    if ahora_españa.hour >= HORA_INICIO:
        siguiente_inicio += timedelta(days=1)
    # Restamos en UTC: con la misma tzinfo Python ignora el cambio de hora (DST)
    return (siguiente_inicio.astimezone(timezone.utc) - ahora_españa.astimezone(timezone.utc)).total_seconds()


if __name__ == "__main__":
    print("=== INICIANDO ORQUESTADOR AUTOMATIZADO (VENTANA HORARIA ESPAÑA) ===")
    print(f"Horario de operación: de {HORA_INICIO}:00 a {HORA_FIN % 24}:00 hrs (Europe/Madrid).")
    print("Presionar [Ctrl + C] en cualquier momento para un apagado de emergencia.\n")

    try:
        esperar_bd()
        aplicar_esquema()
        lineas = lineas_validas()
        if not lineas:
            sys.exit("[ERROR] No hay líneas válidas para consultar.")
        cargar_dimensiones(lineas)
        print(f"Líneas monitoreadas: {', '.join(lineas)} (una consulta cada {ESPACIADO_SEGUNDOS:.0f} s, "
              f"cada línea cada {ESPACIADO_SEGUNDOS * len(lineas) / 60:.1f} min).\n")
        pausa_429 = PAUSA_429_INICIAL

        while True:
            ahora_españa = datetime.now(ZONA_ESPAÑA)
            hora_actual = ahora_españa.hour

            if hora_actual < HORA_INICIO or hora_actual >= HORA_FIN:
                segundos_a_dormir = segundos_hasta_inicio(ahora_españa)
                print(f"[{ahora_españa.strftime('%Y-%m-%d %H:%M:%S')}] -> Fuera de horario operativo.")
                print(f"[*] Entrando en modo reposo nocturno. Despertará a las {HORA_INICIO}:00 (en ~{segundos_a_dormir / 3600:.2f} horas)...\n")
                time.sleep(segundos_a_dormir)
                continue

            print(f"[{ahora_españa.strftime('%Y-%m-%d %H:%M:%S')}] -> Ejecutando ciclo programado...")
            inicio_ciclo = time.monotonic()
            for i, linea in enumerate(lineas):
                _, http_status = fetch_and_process_rt(linea)
                if http_status == 429:
                    print(f"[!] Cuota de la API excedida (429). Pausa de {pausa_429 / 60:.0f} min antes de volver a consultar.\n")
                    time.sleep(pausa_429)
                    pausa_429 = min(pausa_429 * 2, PAUSA_429_MAXIMA)
                    break
                pausa_429 = PAUSA_429_INICIAL
                # Esperamos hasta el turno de la siguiente línea, descontando lo que tardó la consulta
                time.sleep(max(0, inicio_ciclo + (i + 1) * ESPACIADO_SEGUNDOS - time.monotonic()))

    except KeyboardInterrupt:
        print("\n\n[!]: ¡Señal de interrupción recibida (Ctrl + C)!")
        print("[!]: Deteniendo el orquestador de forma segura...")
        sys.exit(0)
