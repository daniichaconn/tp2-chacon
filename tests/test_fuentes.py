"""Pruebas de lectura de archivos CSV y JSON."""

import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from dominio import ErrorDatos  # noqa: E402
from fuentes import FuenteCSV, FuenteJSON, cargar_grupo, crear_fuente  # noqa: E402


class TestFuentes(unittest.TestCase):

    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.carpeta = Path(self.temporal.name)

    def tearDown(self):
        self.temporal.cleanup()

    def escribir(self, nombre, contenido):
        ruta = self.carpeta / nombre
        ruta.write_text(contenido, encoding="utf-8")
        return ruta

    def test_csv_y_json_del_proyecto_son_equivalentes(self):
        csv = FuenteCSV(RAIZ / "data" / "gastos.csv").cargar()
        json = FuenteJSON(RAIZ / "data" / "gastos.json").cargar()
        self.assertEqual(len(csv), len(json))
        self.assertGreaterEqual(len(csv), 50)
        self.assertEqual(csv, json)

    def test_csv_separa_participantes(self):
        ruta = self.escribir("g.csv", "gasto_id,fecha,descripcion,pagador,monto,participantes\n"
                                      "G001,2026-07-06,Pizza,Ana,3000,Ana; Bruno ;Carla\n")
        fila = FuenteCSV(ruta).cargar()[0]
        self.assertEqual(fila["participantes"], ["Ana", "Bruno", "Carla"])
        self.assertEqual(fila["monto"], "3000")

    def test_json_convierte_valores_a_texto(self):
        ruta = self.escribir("g.json", '[{"gasto_id": "G001", "monto": 1500.5, '
                                       '"participantes": ["Ana"]}]')
        fila = FuenteJSON(ruta).cargar()[0]
        self.assertEqual(fila["monto"], "1500.5")

    def test_archivo_inexistente(self):
        with self.assertRaises(FileNotFoundError):
            FuenteCSV(self.carpeta / "no_existe.csv").cargar()

    def test_json_mal_formado(self):
        ruta = self.escribir("roto.json", '[{"gasto_id": "G001",')
        with self.assertRaises(ErrorDatos):
            FuenteJSON(ruta).cargar()

    def test_json_con_estructura_inesperada(self):
        ruta = self.escribir("objeto.json", '{"gastos": []}')
        with self.assertRaises(ErrorDatos):
            FuenteJSON(ruta).cargar()

    def test_formato_no_soportado(self):
        with self.assertRaises(ErrorDatos):
            crear_fuente("gastos.xlsx")

    def test_crear_fuente_elige_la_clase(self):
        self.assertIsInstance(crear_fuente("a.csv"), FuenteCSV)
        self.assertIsInstance(crear_fuente("a.JSON"), FuenteJSON)

    def test_cargar_grupo(self):
        nombre, integrantes = cargar_grupo(RAIZ / "data" / "grupo.json")
        self.assertIn("Bariloche", nombre)
        self.assertEqual(len(integrantes), 5)


if __name__ == "__main__":
    unittest.main()
