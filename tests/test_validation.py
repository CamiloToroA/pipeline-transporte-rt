import os
import sys
import unittest
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from config import ZONA_ESPAÑA
from validation import validar_respuesta, parse_fecha_peticion, ErrorFormato
from scheduler import segundos_hasta_inicio, ESPACIADO_SEGUNDOS, CUOTA_DIARIA, HORA_INICIO, HORA_FIN

EXTRAIDO = datetime(2026, 10, 22, 8, 0, tzinfo=timezone.utc)


def respuesta(buses, fecha="20261022100000"):
    return {"resultado": "OK", "fecha_peticion": fecha,
            "paradas": [{"sentido": 0, "paradas": [{"parada": 523, "buses": buses}]}]}


class TestFechaPeticion(unittest.TestCase):
    def test_hora_española(self):
        fecha = parse_fecha_peticion("20261022100000")
        self.assertEqual(fecha.astimezone(timezone.utc), datetime(2026, 10, 22, 8, 0, tzinfo=timezone.utc))

    def test_formatos_invalidos(self):
        for valor in (None, "", "2026102210", "20261322100000", "2026-10-22 10:00", 20261022100000):
            with self.assertRaises(ErrorFormato, msg=valor):
                parse_fecha_peticion(valor)


class TestValidarRespuesta(unittest.TestCase):
    def test_bus_valido(self):
        _, validos, rechazados = validar_respuesta(
            respuesta([{"bus": 3502, "estado": 1, "distancia": "250"}]), "100", EXTRAIDO)
        self.assertEqual(rechazados, [])
        self.assertEqual(validos[0]["bus_id"], "3502")
        self.assertEqual(validos[0]["parada_id"], "523")
        self.assertEqual(validos[0]["sentido"], "0")
        self.assertEqual(validos[0]["distancia"], 250.0)

    def test_nulos_no_se_guardan_como_texto_none(self):
        _, validos, rechazados = validar_respuesta(respuesta([{"estado": 1}, {"bus": ""}]), "100", EXTRAIDO)
        self.assertEqual(validos, [])
        self.assertEqual([m for m, _ in rechazados], ["bus sin id", "bus sin id"])

    def test_estado_y_distancia_ausentes_son_null(self):
        _, validos, _ = validar_respuesta(respuesta([{"bus": 1}]), "100", EXTRAIDO)
        self.assertIsNone(validos[0]["estado"])
        self.assertIsNone(validos[0]["distancia"])

    def test_distancias_invalidas(self):
        buses = [{"bus": 1, "distancia": "abc"}, {"bus": 2, "distancia": -5}, {"bus": 3, "distancia": "nan"}]
        _, validos, rechazados = validar_respuesta(respuesta(buses), "100", EXTRAIDO)
        self.assertEqual(validos, [])
        self.assertEqual(len(rechazados), 3)

    def test_duplicado_en_la_misma_respuesta(self):
        _, validos, rechazados = validar_respuesta(respuesta([{"bus": 1}, {"bus": 1}]), "100", EXTRAIDO)
        self.assertEqual(len(validos), 1)
        self.assertEqual(rechazados[0][0], "bus duplicado en la misma respuesta")

    def test_parada_sin_id(self):
        data = {"resultado": "OK", "fecha_peticion": "20261022100000",
                "paradas": [{"sentido": 1, "paradas": [{"buses": [{"bus": 1}]}]}]}
        _, validos, rechazados = validar_respuesta(data, "100", EXTRAIDO)
        self.assertEqual(validos, [])
        self.assertEqual(len(rechazados), 1)

    def test_estructura_invalida(self):
        for data in ([], {"fecha_peticion": "20261022100000", "paradas": "x"}, {"paradas": []}):
            with self.assertRaises(ErrorFormato):
                validar_respuesta(data, "100", EXTRAIDO)

    def test_lista_vacia(self):
        _, validos, rechazados = validar_respuesta(
            {"resultado": "OK", "fecha_peticion": "20261022100000", "paradas": []}, "100", EXTRAIDO)
        self.assertEqual((validos, rechazados), ([], []))


class TestScheduler(unittest.TestCase):
    def test_reposo_noche_normal(self):
        ahora = datetime(2026, 10, 22, 0, 30, tzinfo=ZONA_ESPAÑA)
        self.assertEqual(segundos_hasta_inicio(ahora), 5.5 * 3600)

    def test_reposo_en_cambio_de_hora(self):
        # 25-oct-2026 a las 03:00 los relojes vuelven a las 02:00: la noche dura una hora más
        ahora = datetime(2026, 10, 25, 0, 30, tzinfo=ZONA_ESPAÑA)
        self.assertEqual(segundos_hasta_inicio(ahora), 6.5 * 3600)


class TestCuotaApi(unittest.TestCase):
    def test_espaciado_respeta_limites(self):
        self.assertLessEqual((HORA_FIN - HORA_INICIO) * 3600 / ESPACIADO_SEGUNDOS, CUOTA_DIARIA)
        self.assertLessEqual(3600 / ESPACIADO_SEGUNDOS, 199)
        self.assertLessEqual(60 / ESPACIADO_SEGUNDOS, 4)


if __name__ == "__main__":
    unittest.main()
