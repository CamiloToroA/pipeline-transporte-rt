import os
import sys
import json
import time
from datetime import datetime, timezone

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from sqlalchemy import create_engine, text, table, column
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import OperationalError

from config import DATABASE_URL, RT_URL, LINEAS, TIPOLOGIAS, SQL_DIR, ROUTES_PATH, STOPS_PATH
from validation import validar_respuesta, ErrorFormato, DESFASE_MAXIMO

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Referer": "https://itranvias.com/"
}

bus_parada_rt = table(
    "bus_parada_rt",
    column("id"), column("ciclo_id"), column("linea_id"), column("sentido"), column("parada_id"),
    column("bus_id"), column("estado"), column("distancia"), column("fecha_peticion"), column("extraido_en"),
)

_engine = None
_session = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return _engine


def get_session():
    # Reintenta errores de red y respuestas 5xx con espera creciente (1s, 2s).
    # El 429 no se reintenta: cada intento gasta cuota; el scheduler pausa en su lugar
    global _session
    if _session is None:
        reintentos = Retry(total=2, backoff_factor=1, status_forcelist=[500, 502, 503, 504],
                           allowed_methods=["GET"], raise_on_status=False)
        _session = requests.Session()
        _session.headers.update(HEADERS)
        _session.mount("https://", HTTPAdapter(max_retries=reintentos))
    return _session


def esperar_bd(intentos=30, espera=2):
    """Bloquea hasta que PostgreSQL acepte conexiones (en Docker puede tardar unos segundos)."""
    for intento in range(1, intentos + 1):
        try:
            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError:
            print(f"[BD] Esperando a PostgreSQL ({intento}/{intentos})...")
            time.sleep(espera)
    raise RuntimeError("PostgreSQL no respondió a tiempo.")


def aplicar_esquema():
    """Crea tablas y vistas si no existen (ambos scripts son idempotentes)."""
    with get_engine().begin() as conn:
        # Cursor DBAPI sin parámetros: así los '%' de los LIKE no se interpretan como placeholders
        cursor = conn.connection.cursor()
        for nombre in ("schema.sql", "views.sql"):
            with open(os.path.join(SQL_DIR, nombre), encoding="utf-8") as f:
                cursor.execute(f.read())
    print("[BD] Esquema y vistas aplicados.")


def cargar_dimensiones(lineas):
    """Actualiza dim_linea y dim_parada desde el GTFS estático (upsert, se puede repetir)."""
    if not (os.path.exists(ROUTES_PATH) and os.path.exists(STOPS_PATH)):
        print("[WARN] Sin GTFS estático; no se cargan las dimensiones.")
        return
    rutas = pd.read_csv(ROUTES_PATH, dtype=str).fillna("")
    paradas = pd.read_csv(STOPS_PATH, dtype=str).fillna("")
    with get_engine().begin() as conn:
        conn.execute(text("""
            INSERT INTO dim_linea (linea_id, nombre_corto, nombre, tipologia, monitoreada)
            VALUES (:linea_id, :nombre_corto, :nombre, :tipologia, :monitoreada)
            ON CONFLICT (linea_id) DO UPDATE SET
                nombre_corto = EXCLUDED.nombre_corto, nombre = EXCLUDED.nombre,
                tipologia = EXCLUDED.tipologia, monitoreada = EXCLUDED.monitoreada
        """), [{"linea_id": r.route_id, "nombre_corto": r.route_short_name, "nombre": r.route_long_name,
                "tipologia": TIPOLOGIAS.get(r.route_id, "No monitoreada"), "monitoreada": r.route_id in lineas}
               for r in rutas.itertuples()])
        conn.execute(text("""
            INSERT INTO dim_parada (parada_id, nombre, latitud, longitud)
            VALUES (:parada_id, :nombre, CAST(NULLIF(:latitud, '') AS NUMERIC), CAST(NULLIF(:longitud, '') AS NUMERIC))
            ON CONFLICT (parada_id) DO UPDATE SET
                nombre = EXCLUDED.nombre, latitud = EXCLUDED.latitud, longitud = EXCLUDED.longitud
        """), [{"parada_id": p.stop_id, "nombre": p.stop_name, "latitud": p.stop_lat, "longitud": p.stop_lon}
               for p in paradas.itertuples()])
    print(f"[BD] Dimensiones cargadas: {len(rutas)} líneas, {len(paradas)} paradas.")


def lineas_validas(lineas=LINEAS):
    """
    La API responde 'OK' con lista vacía incluso para líneas inexistentes,
    así que validamos los ids contra el GTFS estático antes de consultar.
    """
    if not os.path.exists(ROUTES_PATH):
        print(f"[WARN] No se encontró {ROUTES_PATH}; no se pueden validar las líneas.")
        return lineas
    conocidas = set(pd.read_csv(ROUTES_PATH, dtype=str)["route_id"])
    desconocidas = [l for l in lineas if l not in conocidas]
    if desconocidas:
        print(f"[WARN] Líneas que no existen en el GTFS estático (se omiten): {desconocidas}")
    return [l for l in lineas if l in conocidas]


def _consultar_api(linea_id, ciclo):
    """Consulta y valida una línea. Rellena `ciclo` y devuelve (validos, rechazados)."""
    params = {"dato": linea_id, "func": "2", "_": int(time.time() * 1000)}

    try:
        response = get_session().get(RT_URL, params=params, timeout=15)
    except requests.RequestException as e:
        ciclo.update(estado="ERROR_RED", detalle=str(e))
        return [], []

    ciclo["http_status"] = response.status_code
    if response.status_code != 200:
        ciclo.update(estado="ERROR_HTTP", detalle=response.text[:500])
        return [], []

    try:
        data = response.json()
    except ValueError:
        ciclo.update(estado="ERROR_FORMATO", detalle=f"respuesta no es JSON: {response.text[:500]}")
        return [], []

    if not isinstance(data, dict) or data.get("resultado") != "OK":
        resultado = data.get("resultado") if isinstance(data, dict) else None
        ciclo.update(estado="ERROR_API", detalle=f"resultado={resultado!r}")
        return [], []

    try:
        fecha_peticion, validos, rechazados = validar_respuesta(data, linea_id, ciclo["inicio"])
    except ErrorFormato as e:
        ciclo.update(estado="ERROR_FORMATO", detalle=str(e))
        return [], []

    desfase = fecha_peticion - ciclo["inicio"]
    ciclo.update(
        fecha_peticion=fecha_peticion,
        desfase_seg=desfase.total_seconds(),
        # Una lista vacía de día no es "horario nocturno": queda registrada para revisión
        estado="OK" if validos else "VACIO",
    )
    if abs(desfase) > DESFASE_MAXIMO:
        ciclo["detalle"] = f"desfase de {desfase} entre fecha_peticion y el reloj local"
    return validos, rechazados


def _guardar(ciclo, validos, rechazados):
    """Guarda ciclo, observaciones y rechazos en una sola transacción."""
    with get_engine().begin() as conn:
        ciclo_id = conn.execute(text("""
            INSERT INTO ciclos_rt (linea_id, inicio, fin, estado, http_status, fecha_peticion,
                                   desfase_seg, registros_validos, registros_rechazados, detalle)
            VALUES (:linea_id, :inicio, :fin, :estado, :http_status, :fecha_peticion,
                    :desfase_seg, :registros_validos, :registros_rechazados, :detalle)
            RETURNING ciclo_id
        """), ciclo).scalar_one()

        insertados = 0
        if validos:
            filas = [{**fila, "ciclo_id": ciclo_id} for fila in validos]
            stmt = (insert(bus_parada_rt).values(filas)
                    .on_conflict_do_nothing(constraint="uq_bus_parada_rt")
                    .returning(bus_parada_rt.c.id))
            insertados = len(conn.execute(stmt).fetchall())
            conn.execute(text("UPDATE ciclos_rt SET registros_insertados = :n WHERE ciclo_id = :id"),
                         {"n": insertados, "id": ciclo_id})

        if rechazados:
            conn.execute(text("""
                INSERT INTO rechazos_rt (ciclo_id, linea_id, motivo, payload, extraido_en)
                VALUES (:ciclo_id, :linea_id, :motivo, CAST(:payload AS JSONB), :extraido_en)
            """), [{"ciclo_id": ciclo_id, "linea_id": ciclo["linea_id"], "motivo": motivo,
                    "payload": json.dumps(payload, ensure_ascii=False, default=str),
                    "extraido_en": ciclo["inicio"]} for motivo, payload in rechazados])
    return insertados


def fetch_and_process_rt(linea_id):
    """Ejecuta un ciclo completo para una línea. Devuelve (estado, http_status)."""
    hora = time.strftime('%H:%M:%S')
    ciclo = {
        "linea_id": linea_id, "inicio": datetime.now(timezone.utc), "fin": None, "estado": None,
        "http_status": None, "fecha_peticion": None, "desfase_seg": None, "detalle": None,
    }

    validos, rechazados = _consultar_api(linea_id, ciclo)
    ciclo.update(fin=datetime.now(timezone.utc),
                 registros_validos=len(validos), registros_rechazados=len(rechazados))

    try:
        insertados = _guardar(ciclo, validos, rechazados)
    except Exception as e:
        # Sin BD no hay bitácora: lo dejamos en stderr para los logs de Docker
        print(f"[{hora}] [ERROR_DB] línea {linea_id}: {e}", file=sys.stderr)
        return "ERROR_DB", ciclo["http_status"]

    duplicados = len(validos) - insertados
    resumen = f"{insertados} insertados, {duplicados} duplicados, {len(rechazados)} rechazados"
    print(f"[{hora}] línea {linea_id}: {ciclo['estado']} ({resumen})"
          + (f" - {ciclo['detalle']}" if ciclo["detalle"] else ""))
    return ciclo["estado"], ciclo["http_status"]


if __name__ == "__main__":
    esperar_bd()
    aplicar_esquema()
    lineas = lineas_validas()
    cargar_dimensiones(lineas)
    for linea in lineas:
        fetch_and_process_rt(linea)
