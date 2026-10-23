"""Pruebas del flujo: validación, limpieza, filtros, cálculo y verificación."""

import contextlib
import copy
import io
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from dominio import ErrorDatos, Grupo  # noqa: E402
from fuentes import FuenteCSV, FuenteJSON, cargar_grupo  # noqa: E402
from main import main  # noqa: E402
from pipeline import (  # noqa: E402
    filtrar_periodo,
    limpiar_gastos,
    pesos_a_centavos,
    procesar,
    validar_esquema,
)

INTEGRANTES = {"Ana": "ana.viaja.mp", "Bruno": "bruno.bari.26"}


def fila(**cambios):
    base = {"gasto_id": "G001", "fecha": "2026-07-06", "descripcion": "Pizza",
            "pagador": "Ana", "monto": "3000", "participantes": ["Ana", "Bruno"]}
    base.update(cambios)
    return base


class TestValidacionYLimpieza(unittest.TestCase):

    def setUp(self):
        self.grupo = Grupo("Prueba", INTEGRANTES)

    def rechazo(self, **cambios):
        validos, rechazados = limpiar_gastos([fila(**cambios)], self.grupo)
        self.assertEqual(validos, [])
        return rechazados[0]["motivo"]

    def test_fila_valida(self):
        validos, rechazados = limpiar_gastos([fila()], self.grupo)
        self.assertEqual(len(validos), 1)
        self.assertEqual(rechazados, [])
        self.assertEqual(validos[0].monto_centavos, 300000)

    def test_entrada_vacia(self):
        with self.assertRaises(ErrorDatos):
            validar_esquema([])

    def test_falta_una_columna(self):
        incompleta = fila()
        del incompleta["monto"]
        with self.assertRaises(ErrorDatos):
            validar_esquema([incompleta])

    def test_id_con_formato_invalido(self):
        self.assertIn("id con formato", self.rechazo(gasto_id="G1"))
        self.assertIn("id con formato", self.rechazo(gasto_id="g001"))

    def test_fecha_con_formato_invalido(self):
        self.assertIn("formato", self.rechazo(fecha="06/07/2026"))

    def test_fecha_que_no_existe(self):
        # cumple el patrón AAAA-MM-DD, pero el 29/02/2026 no existe
        self.assertIn("inexistente", self.rechazo(fecha="2026-02-29"))

    def test_fecha_bisiesta_valida(self):
        validos, _ = limpiar_gastos([fila(fecha="2024-02-29")], self.grupo)
        self.assertEqual(len(validos), 1)

    def test_montos_invalidos(self):
        for monto in ["-2500", "1.500,00", "abc", "", "12.345", "inf", "0"]:
            with self.subTest(monto=monto):
                self.assertIn("monto", self.rechazo(monto=monto))

    def test_conversion_de_montos(self):
        self.assertEqual(pesos_a_centavos("1500"), 150000)
        self.assertEqual(pesos_a_centavos("1500.5"), 150050)
        self.assertEqual(pesos_a_centavos("0.07"), 7)

    def test_persona_fuera_del_grupo(self):
        self.assertIn("pagador fuera", self.rechazo(pagador="Franco"))
        self.assertIn("participantes fuera", self.rechazo(participantes=["Ana", "Franco"]))

    def test_sin_participantes(self):
        self.assertIn("sin participantes", self.rechazo(participantes=[]))

    def test_ids_duplicados_se_rechazan_todos(self):
        filas = [fila(), fila(descripcion="Pizza otra vez"), fila(gasto_id="G002")]
        validos, rechazados = limpiar_gastos(filas, self.grupo)
        self.assertEqual([g.gasto_id for g in validos], ["G002"])
        self.assertEqual(len(rechazados), 2)

    def test_no_modifica_la_entrada(self):
        filas = [fila(), fila(gasto_id="X")]
        original = copy.deepcopy(filas)
        limpiar_gastos(filas, self.grupo)
        self.assertEqual(filas, original)


class TestFiltroPeriodo(unittest.TestCase):

    def setUp(self):
        grupo = Grupo("Prueba", INTEGRANTES)
        filas = [fila(gasto_id=f"G00{d}", fecha=f"2026-07-0{d}") for d in range(1, 6)]
        self.gastos, _ = limpiar_gastos(filas, grupo)

    def test_extremos_incluidos(self):
        elegidos = filtrar_periodo(self.gastos, date(2026, 7, 2), date(2026, 7, 4))
        self.assertEqual([g.gasto_id for g in elegidos], ["G002", "G003", "G004"])

    def test_periodo_sin_gastos(self):
        self.assertEqual(filtrar_periodo(self.gastos, date(2026, 8, 1), date(2026, 8, 5)), [])

    def test_periodo_invertido(self):
        with self.assertRaises(ErrorDatos):
            filtrar_periodo(self.gastos, date(2026, 7, 5), date(2026, 7, 1))


class TestFlujoCompleto(unittest.TestCase):

    def setUp(self):
        self.nombre, self.integrantes = cargar_grupo(RAIZ / "data" / "grupo.json")

    def test_csv_y_json_dan_el_mismo_resultado(self):
        r_csv = procesar(FuenteCSV(RAIZ / "data" / "gastos.csv"), self.nombre, self.integrantes)
        r_json = procesar(FuenteJSON(RAIZ / "data" / "gastos.json"), self.nombre, self.integrantes)
        self.assertEqual(r_csv["resumen"], r_json["resumen"])
        self.assertEqual(r_csv["transferencias"], r_json["transferencias"])
        self.assertEqual(r_csv["rechazados"], r_json["rechazados"])

    def test_auditoria_cuadra(self):
        r = procesar(FuenteCSV(RAIZ / "data" / "gastos.csv"), self.nombre, self.integrantes)
        a = r["auditoria"]
        self.assertEqual(a["filas_leidas"], a["validas"] + a["rechazadas"])
        self.assertGreaterEqual(a["validas"], 50)
        self.assertEqual(sum(f["saldo"] for f in r["resumen"]), 0)

    def test_main_con_persona_inexistente_devuelve_error(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                codigo = main(["--persona", "Franco", "--salida", carpeta])
        self.assertEqual(codigo, 1)

    def test_main_guarda_los_archivos(self):
        with tempfile.TemporaryDirectory() as carpeta:
            with contextlib.redirect_stdout(io.StringIO()):
                codigo = main(["--salida", carpeta])
            archivos = sorted(p.name for p in Path(carpeta).iterdir())
        self.assertEqual(codigo, 0)
        self.assertEqual(archivos, ["rechazados.csv", "saldos.csv", "transferencias.csv"])


if __name__ == "__main__":
    unittest.main()
