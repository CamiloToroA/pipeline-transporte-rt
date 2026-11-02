"""Validación de la respuesta de iTranvias, separada de la red y la BD para poder probarla."""
import math
from datetime import datetime, timedelta

from config import ZONA_ESPAÑA

# Si la API devuelve una fecha_peticion más alejada que esto del reloj local,
# el ciclo se marca para revisión (respuesta cacheada o reloj desfasado).
DESFASE_MAXIMO = timedelta(minutes=10)


class ErrorFormato(Exception):
    """La respuesta no tiene la estructura esperada; se descarta el ciclo completo."""


def parse_fecha_peticion(valor):
    """'20261022030301' (hora local de España) -> datetime con zona horaria."""
    if not isinstance(valor, str) or len(valor) != 14 or not valor.isdigit():
        raise ErrorFormato(f"fecha_peticion inválida: {valor!r}")
    try:
        return datetime.strptime(valor, "%Y%m%d%H%M%S").replace(tzinfo=ZONA_ESPAÑA)
    except ValueError as e:
        raise ErrorFormato(f"fecha_peticion inválida: {valor!r}") from e


def _texto_requerido(valor):
    """Devuelve el valor como texto o None si falta (evita guardar el literal 'None')."""
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _distancia(valor):
    """Devuelve (distancia, motivo_rechazo). Una distancia ausente es válida (NULL)."""
    if valor is None or valor == "":
        return None, None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None, f"distancia no numérica: {valor!r}"
    if math.isnan(numero) or math.isinf(numero):
        return None, f"distancia no finita: {valor!r}"
    if numero < 0:
        return None, f"distancia negativa: {numero}"
    return numero, None


def validar_respuesta(data, linea_id, extraido_en):
    """
    Valida la respuesta completa de una línea.

    Devuelve (fecha_peticion, validos, rechazados):
      - validos: filas listas para bus_parada_rt
      - rechazados: (motivo, payload) por cada bus descartado
    Lanza ErrorFormato si la estructura general no es la esperada.
    """
    if not isinstance(data, dict):
        raise ErrorFormato(f"la respuesta no es un objeto JSON sino {type(data).__name__}")

    fecha_peticion = parse_fecha_peticion(data.get("fecha_peticion"))

    sentidos = data.get("paradas")
    if not isinstance(sentidos, list):
        raise ErrorFormato(f"'paradas' no es una lista: {type(sentidos).__name__}")

    validos, rechazados = [], []
    vistos = set()

    for sentido_item in sentidos:
        if not isinstance(sentido_item, dict):
            rechazados.append(("sentido con formato inválido", sentido_item))
            continue
        sentido_id = _texto_requerido(sentido_item.get("sentido"))
        lista_paradas = sentido_item.get("paradas")
        if sentido_id is None or not isinstance(lista_paradas, list):
            rechazados.append(("sentido sin id o sin lista de paradas", sentido_item))
            continue

        for parada_item in lista_paradas:
            if not isinstance(parada_item, dict):
                rechazados.append(("parada con formato inválido", parada_item))
                continue
            parada_id = _texto_requerido(parada_item.get("parada"))
            buses = parada_item.get("buses") or []
            if parada_id is None or not isinstance(buses, list):
                rechazados.append(("parada sin id o con buses inválidos", parada_item))
                continue

            for bus_item in buses:
                payload = {"sentido": sentido_id, "parada": parada_id, "bus": bus_item}
                if not isinstance(bus_item, dict):
                    rechazados.append(("bus con formato inválido", payload))
                    continue
                bus_id = _texto_requerido(bus_item.get("bus"))
                if bus_id is None:
                    rechazados.append(("bus sin id", payload))
                    continue
                distancia, motivo = _distancia(bus_item.get("distancia"))
                if motivo:
                    rechazados.append((motivo, payload))
                    continue
                clave = (sentido_id, parada_id, bus_id)
                if clave in vistos:
                    rechazados.append(("bus duplicado en la misma respuesta", payload))
                    continue
                vistos.add(clave)

                validos.append({
                    "linea_id": linea_id,
                    "sentido": sentido_id,
                    "parada_id": parada_id,
                    "bus_id": bus_id,
                    "estado": _texto_requerido(bus_item.get("estado")),
                    "distancia": distancia,
                    "fecha_peticion": fecha_peticion,
                    "extraido_en": extraido_en,
                })

    return fecha_peticion, validos, rechazados
