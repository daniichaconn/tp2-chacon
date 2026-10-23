"""Pruebas de las clases del dominio: Gasto y Grupo."""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dominio import ErrorDatos, Gasto, Grupo  # noqa: E402

INTEGRANTES = {"Ana": "ana.viaja.mp", "Bruno": "bruno.bari.26", "Carla": "carla-ahorro"}


def gasto(gasto_id, pagador, pesos, participantes):
    return Gasto(gasto_id, date(2026, 7, 6), "prueba", pagador, pesos * 100, tuple(participantes))


class TestGasto(unittest.TestCase):

    def test_division_exacta(self):
        g = gasto("G001", "Ana", 3000, ["Ana", "Bruno", "Carla"])
        self.assertEqual(g.cuota_por_persona(), {"Ana": 100000, "Bruno": 100000, "Carla": 100000})

    def test_division_con_resto_conserva_el_total(self):
        # 10 pesos entre 3: 3,34 + 3,33 + 3,33. No se pierde ni se inventa un centavo.
        g = gasto("G001", "Ana", 10, ["Carla", "Ana", "Bruno"])
        cuotas = g.cuota_por_persona()
        self.assertEqual(sum(cuotas.values()), 1000)
        self.assertEqual(cuotas, {"Ana": 334, "Bruno": 333, "Carla": 333})

    def test_monto_cero_es_invalido(self):
        with self.assertRaises(ValueError):
            gasto("G001", "Ana", 0, ["Ana"])

    def test_sin_participantes_es_invalido(self):
        with self.assertRaises(ValueError):
            gasto("G001", "Ana", 100, [])


class TestGrupo(unittest.TestCase):

    def test_caso_normal(self):
        grupo = Grupo("Prueba", INTEGRANTES)
        grupo.registrar(gasto("G001", "Ana", 3000, ["Ana", "Bruno", "Carla"]))
        self.assertEqual(grupo.saldos(), {"Ana": 200000, "Bruno": -100000, "Carla": -100000})
        self.assertEqual(
            sorted(grupo.transferencias()),
            [("Bruno", "Ana", 100000), ("Carla", "Ana", 100000)],
        )

    def test_gastos_cruzados_se_compensan(self):
        # Ana pagó 600 para Ana y Bruno; Bruno pagó 600 para los dos: nadie debe nada.
        grupo = Grupo("Prueba", INTEGRANTES)
        grupo.registrar(gasto("G001", "Ana", 600, ["Ana", "Bruno"]))
        grupo.registrar(gasto("G002", "Bruno", 600, ["Ana", "Bruno"]))
        self.assertEqual(grupo.transferencias(), [])

    def test_sin_gastos_no_hay_transferencias(self):
        self.assertEqual(Grupo("Prueba", INTEGRANTES).transferencias(), [])

    def test_alias_invalido(self):
        with self.assertRaises(ErrorDatos):
            Grupo("Prueba", {"Ana": "ana.viaja.mp", "Bruno": "Bruno Pérez"})

    def test_grupo_de_una_persona(self):
        with self.assertRaises(ErrorDatos):
            Grupo("Prueba", {"Ana": "ana.viaja.mp"})

    def test_persona_fuera_del_grupo(self):
        grupo = Grupo("Prueba", INTEGRANTES)
        with self.assertRaises(ErrorDatos):
            grupo.registrar(gasto("G001", "Franco", 100, ["Ana", "Franco"]))

    def test_propiedades_con_muchos_gastos(self):
        """Propiedades que valen para cualquier conjunto de gastos."""
        grupo = Grupo("Prueba", INTEGRANTES)
        personas = sorted(INTEGRANTES)
        for i in range(1, 40):
            participantes = personas[: 1 + i % 3]
            grupo.registrar(gasto(f"G{i:03d}", personas[i % 3], 1000 + 37 * i, participantes))
        saldos = grupo.saldos()
        transferencias = grupo.transferencias()
        # 1) los saldos suman cero
        self.assertEqual(sum(saldos.values()), 0)
        # 2) después de transferir, todos quedan en cero
        for deudor, acreedor, monto in transferencias:
            saldos[deudor] += monto
            saldos[acreedor] -= monto
        self.assertTrue(all(s == 0 for s in saldos.values()))
        # 3) nunca más de n - 1 transferencias
        self.assertLessEqual(len(transferencias), len(personas) - 1)


if __name__ == "__main__":
    unittest.main()
