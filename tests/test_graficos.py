"""Pruebas de los gráficos: que se generen los archivos PNG."""

import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import graficos  # noqa: E402
from fuentes import FuenteCSV, cargar_grupo  # noqa: E402
from pipeline import calcular, cargar_y_limpiar, filtrar_evento  # noqa: E402

FIRMA_PNG = b"\x89PNG"


class TestGraficos(unittest.TestCase):

    def setUp(self):
        self.nombre, self.integrantes = cargar_grupo(RAIZ / "data" / "grupo.json")
        _, self.validos, _ = cargar_y_limpiar(FuenteCSV(RAIZ / "data" / "gastos.csv"),
                                              self.nombre, self.integrantes)

    def test_genera_los_tres_graficos_del_anio(self):
        _, resumen, _ = calcular(self.nombre, self.integrantes, self.validos)
        with tempfile.TemporaryDirectory() as carpeta:
            rutas = graficos.generar_todos(self.validos, resumen, carpeta)
            nombres = sorted(r.name for r in rutas)
            son_png = all(r.read_bytes().startswith(FIRMA_PNG) for r in rutas)
        self.assertEqual(nombres, ["categorias.png", "meses.png", "saldos.png"])
        self.assertTrue(son_png)

    def test_evento_de_un_solo_mes_no_dibuja_meses(self):
        gastos = filtrar_evento(self.validos, "cordoba")
        _, resumen, _ = calcular(self.nombre, self.integrantes, gastos)
        with tempfile.TemporaryDirectory() as carpeta:
            rutas = graficos.generar_todos(gastos, resumen, carpeta, "Córdoba")
        self.assertEqual(sorted(r.name for r in rutas), ["categorias.png", "saldos.png"])


if __name__ == "__main__":
    unittest.main()
