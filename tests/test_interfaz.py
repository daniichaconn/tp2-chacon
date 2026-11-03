"""Pruebas del programa de consola: comandos, menú y formatos de la vista."""

import io
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from rich.console import Console  # noqa: E402

import vista  # noqa: E402
from main import main  # noqa: E402


def ejecutar(argumentos, entrada=None):
    """Corre main() con una consola falsa y devuelve (código de salida, texto mostrado)."""
    pantalla = io.StringIO()
    consola = Console(file=pantalla, width=140, color_system=None)
    with tempfile.TemporaryDirectory() as carpeta:
        codigo = main(argumentos + ["--salida", carpeta], console=consola,
                      stream=io.StringIO(entrada) if entrada is not None else None)
        archivos = sorted(p.name for p in Path(carpeta).iterdir())
    return codigo, pantalla.getvalue(), archivos


class TestFormatos(unittest.TestCase):

    def test_pesos(self):
        self.assertEqual(vista.pesos(123456789), "$ 1.234.567,89")
        self.assertEqual(vista.pesos(-5), "-$ 0,05")

    def test_porcentaje(self):
        self.assertEqual(vista.porcentaje(31.25), "31,2%")

    def test_barra(self):
        self.assertEqual(vista.barra(10, 10, ancho=4), "████")
        self.assertEqual(vista.barra(0, 10), "")
        self.assertEqual(len(vista.barra(5, 10, ancho=4)), 2)


class TestComandos(unittest.TestCase):

    def test_resumen_guarda_archivos(self):
        codigo, texto, archivos = ejecutar(["resumen"])
        self.assertEqual(codigo, 0)
        self.assertIn("Transferencias para quedar a mano", texto)
        self.assertEqual(archivos, ["rechazados.csv", "saldos.csv", "transferencias.csv"])

    def test_resumen_de_un_evento_sin_tildes(self):
        codigo, texto, _ = ejecutar(["resumen", "--evento", "cordoba"])
        self.assertEqual(codigo, 0)
        self.assertIn("Finde largo en Córdoba", texto)

    def test_estadisticas(self):
        codigo, texto, archivos = ejecutar(["estadisticas"])
        self.assertEqual(codigo, 0)
        self.assertIn("Conclusiones", texto)
        self.assertIn("conclusiones.txt", archivos)

    def test_persona_en_minusculas(self):
        codigo, texto, _ = ejecutar(["persona", "bruno"])
        self.assertEqual(codigo, 0)
        self.assertIn("Bruno: evento por evento", texto)

    def test_comparar(self):
        codigo, texto, _ = ejecutar(["comparar", "--evento", "bariloche"])
        self.assertEqual(codigo, 0)
        self.assertIn("Con el programa", texto)

    def test_graficos(self):
        codigo, texto, archivos = ejecutar(["graficos"])
        self.assertEqual(codigo, 0)
        self.assertIn("graficos", archivos)
        self.assertIn("categorias.png", texto)

    def test_persona_inexistente(self):
        codigo, texto, _ = ejecutar(["persona", "Mateo"])
        self.assertEqual(codigo, 1)
        self.assertIn("no pertenece al grupo", texto)

    def test_evento_ambiguo(self):
        codigo, texto, _ = ejecutar(["resumen", "--evento", "cumple"])
        self.assertEqual(codigo, 1)
        self.assertIn("varios eventos", texto)

    def test_archivo_inexistente(self):
        codigo, texto, _ = ejecutar(["resumen", "--datos", "no_existe.csv"])
        self.assertEqual(codigo, 1)
        self.assertIn("No existe", texto)


class TestMenu(unittest.TestCase):

    def test_recorrido_del_menu(self):
        # 2 = cerrar un evento (elige el 6: Bariloche), Enter, 99 = opción inválida,
        # 6 = comparar, Enter, 0 = salir
        codigo, texto, _ = ejecutar(["menu"], entrada="2\n6\n\n99\n6\n\n0\n")
        self.assertEqual(codigo, 0)
        self.assertIn("Cuentas · Viaje a Bariloche", texto)
        self.assertIn("Esa opción no existe", texto)
        self.assertIn("¿Cuántas transferencias hacen falta?", texto)
        self.assertIn("Hasta luego", texto)


if __name__ == "__main__":
    unittest.main()
