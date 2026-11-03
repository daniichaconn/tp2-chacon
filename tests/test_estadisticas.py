"""Pruebas de las estadísticas y conclusiones."""

import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

import estadisticas  # noqa: E402
from dominio import Gasto, Grupo  # noqa: E402
from fuentes import FuenteCSV, cargar_grupo  # noqa: E402
from pipeline import calcular, cargar_y_limpiar  # noqa: E402

INTEGRANTES = {"Ana": "ana.viaja.mp", "Bruno": "bruno.bari.26", "Carla": "carla-ahorro"}


def gasto(gasto_id, dia, evento, categoria, pagador, pesos, participantes):
    return Gasto(gasto_id, dia, "prueba", pagador, pesos * 100, tuple(participantes),
                 evento=evento, categoria=categoria)


class TestCasoChico(unittest.TestCase):
    """Un caso calculado a mano: 4 gastos, 2 eventos, 3 personas."""

    def setUp(self):
        self.gastos = [
            gasto("G001", date(2026, 1, 10), "Costa", "Alojamiento", "Ana", 9000, ["Ana", "Bruno", "Carla"]),
            gasto("G002", date(2026, 1, 11), "Costa", "Comidas y bebidas", "Bruno", 3000, ["Ana", "Bruno", "Carla"]),
            gasto("G003", date(2026, 3, 5), "Asado", "Supermercado", "Carla", 2000, ["Ana", "Carla"]),
            gasto("G004", date(2026, 3, 5), "Asado", "Comidas y bebidas", "Ana", 1000, ["Ana", "Carla"]),
        ]
        self.grupo = Grupo("Prueba", INTEGRANTES)
        for g in self.gastos:
            self.grupo.registrar(g)

    def test_resumen_general(self):
        general = estadisticas.resumen_general(self.gastos)
        self.assertEqual(general["cantidad"], 4)
        self.assertEqual(general["total"], 1500000)
        self.assertEqual(general["promedio"], 375000)
        self.assertEqual(general["mediana"], 250000)
        self.assertEqual(general["mas_caro"].gasto_id, "G001")

    def test_resumen_de_lista_vacia(self):
        self.assertIsNone(estadisticas.resumen_general([]))

    def test_por_evento(self):
        eventos = estadisticas.por_evento(self.gastos)
        self.assertEqual([e["evento"] for e in eventos], ["Costa", "Asado"])  # ordenados por fecha
        costa, asado = eventos
        self.assertEqual(costa["total"], 1200000)
        self.assertEqual(costa["por_persona"], 400000)   # 12.000 entre 3
        self.assertEqual(asado["personas"], 2)
        self.assertEqual(asado["por_persona"], 150000)   # 3.000 entre 2

    def test_por_categoria_suma_100(self):
        categorias = estadisticas.por_categoria(self.gastos)
        self.assertEqual(categorias[0]["categoria"], "Alojamiento")   # la más grande primero
        self.assertAlmostEqual(sum(c["porcentaje"] for c in categorias), 100.0)
        self.assertEqual(sum(c["total"] for c in categorias), 1500000)

    def test_por_mes(self):
        meses = estadisticas.por_mes(self.gastos)
        self.assertEqual([m["clave"] for m in meses], ["2026-01", "2026-03"])
        self.assertEqual(meses[0]["evento_principal"], "Costa")
        self.assertEqual(meses[1]["total"], 300000)

    def test_por_persona(self):
        filas = {f["persona"]: f for f in estadisticas.por_persona(self.grupo)}
        self.assertEqual(filas["Ana"]["pagado"], 1000000)
        self.assertEqual(filas["Ana"]["pagos"], 2)
        self.assertAlmostEqual(sum(f["porcentaje_pagado"] for f in filas.values()), 100.0)
        self.assertEqual(sum(f["saldo"] for f in filas.values()), 0)

    def test_persona_por_evento_suma_su_saldo_total(self):
        filas = estadisticas.persona_por_evento(self.gastos, "Carla")
        self.assertEqual([f["evento"] for f in filas], ["Costa", "Asado"])
        self.assertEqual(sum(f["saldo"] for f in filas), self.grupo.saldos()["Carla"])

    def test_comparar_transferencias(self):
        comparacion = estadisticas.comparar_transferencias(self.grupo)
        # partes a pagar: G001 2 + G002 2 + G003 1 + G004 1 = 6
        self.assertEqual(comparacion["sin_organizar"], 6)
        self.assertLessEqual(comparacion["por_pares"], comparacion["sin_organizar"])
        self.assertLessEqual(comparacion["con_programa"], len(INTEGRANTES) - 1)
        self.assertGreater(comparacion["ahorro"], 0)

    def test_conclusiones(self):
        frases = estadisticas.conclusiones(self.gastos, self.grupo, rechazados=[{}], filas_leidas=5)
        texto = " ".join(frases)
        self.assertIn("4 gastos", texto)
        self.assertIn("Costa", texto)
        self.assertIn("Alojamiento", texto)
        self.assertIn("1 de 5 filas", texto)

    def test_conclusiones_sin_gastos(self):
        self.assertEqual(estadisticas.conclusiones([], Grupo("Prueba", INTEGRANTES)),
                         ["No hay gastos para analizar."])


class TestDatosDelProyecto(unittest.TestCase):

    def setUp(self):
        nombre, integrantes = cargar_grupo(RAIZ / "data" / "grupo.json")
        _, self.validos, self.rechazados = cargar_y_limpiar(
            FuenteCSV(RAIZ / "data" / "gastos.csv"), nombre, integrantes)
        self.grupo, _, _ = calcular(nombre, integrantes, self.validos)

    def test_los_totales_coinciden_en_todas_las_vistas(self):
        """Propiedad: por evento, por categoría y por mes suman el mismo total."""
        total = sum(g.monto_centavos for g in self.validos)
        self.assertEqual(sum(e["total"] for e in estadisticas.por_evento(self.validos)), total)
        self.assertEqual(sum(c["total"] for c in estadisticas.por_categoria(self.validos)), total)
        self.assertEqual(sum(m["total"] for m in estadisticas.por_mes(self.validos)), total)
        self.assertEqual(sum(p["pagado"] for p in estadisticas.por_persona(self.grupo)), total)

    def test_el_programa_ahorra_transferencias(self):
        comparacion = estadisticas.comparar_transferencias(self.grupo)
        self.assertGreater(comparacion["sin_organizar"], 300)
        self.assertLessEqual(comparacion["con_programa"], 5)

    def test_guardar_estadisticas(self):
        frases = estadisticas.conclusiones(self.validos, self.grupo)
        with tempfile.TemporaryDirectory() as carpeta:
            estadisticas.guardar_estadisticas(carpeta, self.validos, frases)
            archivos = sorted(p.name for p in Path(carpeta).iterdir())
            lineas_eventos = (Path(carpeta) / "eventos.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(archivos, ["categorias.csv", "conclusiones.txt", "eventos.csv", "meses.csv"])
        self.assertEqual(len(lineas_eventos), 1 + 8)  # encabezado + 8 eventos


if __name__ == "__main__":
    unittest.main()
