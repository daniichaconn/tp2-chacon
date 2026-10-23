"""Pruebas del flujo: validación, limpieza, filtros, cálculo y verificación."""

import copy
import sys
import unittest
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))

from dominio import ErrorDatos, Grupo  # noqa: E402
from fuentes import FuenteCSV, FuenteJSON, cargar_grupo  # noqa: E402
from pipeline import (  # noqa: E402
    buscar_evento,
    calcular,
    eventos_disponibles,
    filtrar_evento,
    filtrar_periodo,
    limpiar_gastos,
    pesos_a_centavos,
    procesar,
    validar_esquema,
)

INTEGRANTES = {"Ana": "ana.viaja.mp", "Bruno": "bruno.bari.26"}


def fila(**cambios):
    base = {"gasto_id": "G001", "fecha": "2026-07-06", "evento": "Asado",
            "categoria": "Supermercado", "descripcion": "Carne", "pagador": "Ana",
            "monto": "3000", "participantes": ["Ana", "Bruno"]}
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
        self.assertEqual(validos[0].evento, "Asado")
        self.assertEqual(validos[0].categoria, "Supermercado")

    def test_entrada_vacia(self):
        with self.assertRaises(ErrorDatos):
            validar_esquema([])

    def test_falta_una_columna(self):
        incompleta = fila()
        del incompleta["categoria"]
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

    def test_categoria_desconocida(self):
        self.assertIn("categoría desconocida", self.rechazo(categoria="Varios"))
        # mayúsculas distintas tampoco: la lista es cerrada y sin ambigüedad
        self.assertIn("categoría desconocida", self.rechazo(categoria="supermercado"))

    def test_evento_vacio(self):
        self.assertIn("evento vacío", self.rechazo(evento="  "))

    def test_persona_fuera_del_grupo(self):
        self.assertIn("pagador fuera", self.rechazo(pagador="Mateo"))
        self.assertIn("participantes fuera", self.rechazo(participantes=["Ana", "Mateo"]))

    def test_sin_participantes(self):
        self.assertIn("sin participantes", self.rechazo(participantes=[]))

    def test_participantes_repetidos(self):
        self.assertIn("repetidos", self.rechazo(participantes=["Ana", "Ana", "Bruno"]))

    def test_varios_motivos_a_la_vez(self):
        motivo = self.rechazo(monto="-1", categoria="Varios")
        self.assertIn("monto", motivo)
        self.assertIn("categoría", motivo)

    def test_ids_duplicados_se_rechazan_todos(self):
        filas = [fila(), fila(descripcion="Carne otra vez"), fila(gasto_id="G002")]
        validos, rechazados = limpiar_gastos(filas, self.grupo)
        self.assertEqual([g.gasto_id for g in validos], ["G002"])
        self.assertEqual(len(rechazados), 2)

    def test_no_modifica_la_entrada(self):
        filas = [fila(), fila(gasto_id="X")]
        original = copy.deepcopy(filas)
        limpiar_gastos(filas, self.grupo)
        self.assertEqual(filas, original)


class TestFiltros(unittest.TestCase):

    def setUp(self):
        grupo = Grupo("Prueba", INTEGRANTES)
        filas = [fila(gasto_id=f"G00{d}", fecha=f"2026-07-0{d}") for d in range(1, 6)]
        filas += [
            fila(gasto_id="G010", fecha="2026-01-15", evento="Vacaciones en la costa"),
            fila(gasto_id="G011", fecha="2026-03-10", evento="Viaje a Córdoba"),
            fila(gasto_id="G012", fecha="2026-03-11", evento="Viaje a Bariloche"),
        ]
        self.gastos, _ = limpiar_gastos(filas, grupo)

    def test_periodo_extremos_incluidos(self):
        elegidos = filtrar_periodo(self.gastos, date(2026, 7, 2), date(2026, 7, 4))
        self.assertEqual([g.gasto_id for g in elegidos], ["G002", "G003", "G004"])

    def test_periodo_sin_gastos(self):
        self.assertEqual(filtrar_periodo(self.gastos, date(2026, 8, 1), date(2026, 8, 5)), [])

    def test_periodo_invertido(self):
        with self.assertRaises(ErrorDatos):
            filtrar_periodo(self.gastos, date(2026, 7, 5), date(2026, 7, 1))

    def test_eventos_ordenados_por_fecha(self):
        self.assertEqual(eventos_disponibles(self.gastos),
                         ["Vacaciones en la costa", "Viaje a Córdoba", "Viaje a Bariloche", "Asado"])

    def test_buscar_evento_exacto_y_parcial(self):
        self.assertEqual(buscar_evento(self.gastos, "asado"), "Asado")
        self.assertEqual(buscar_evento(self.gastos, "BARILOCHE"), "Viaje a Bariloche")

    def test_buscar_evento_sin_tildes(self):
        self.assertEqual(buscar_evento(self.gastos, "cordoba"), "Viaje a Córdoba")

    def test_buscar_evento_ambiguo(self):
        with self.assertRaises(ErrorDatos) as contexto:
            buscar_evento(self.gastos, "viaje")
        self.assertIn("varios eventos", str(contexto.exception))

    def test_buscar_evento_inexistente(self):
        with self.assertRaises(ErrorDatos):
            buscar_evento(self.gastos, "Mundial")

    def test_filtrar_evento(self):
        self.assertEqual(len(filtrar_evento(self.gastos, "asado")), 5)
        self.assertEqual(len(filtrar_evento(self.gastos, None)), 8)


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
        self.assertGreaterEqual(a["validas"], 300)
        self.assertEqual(sum(f["saldo"] for f in r["resumen"]), 0)

    def test_cada_evento_cierra_sus_cuentas(self):
        """Propiedad: cualquier evento, por separado, deja los saldos en cero."""
        r = procesar(FuenteCSV(RAIZ / "data" / "gastos.csv"), self.nombre, self.integrantes)
        total = 0
        for evento in eventos_disponibles(r["validos"]):
            gastos = filtrar_evento(r["validos"], evento)
            grupo, resumen, transferencias = calcular(self.nombre, self.integrantes, gastos)
            self.assertEqual(sum(f["saldo"] for f in resumen), 0)
            total += sum(g.monto_centavos for g in gastos)
        # los eventos se reparten todos los gastos, sin perder ni repetir ninguno
        self.assertEqual(total, r["auditoria"]["total_gastado"])

    def test_procesar_un_evento(self):
        r = procesar(FuenteCSV(RAIZ / "data" / "gastos.csv"), self.nombre, self.integrantes,
                     evento="bariloche")
        self.assertEqual(r["evento"], "Viaje a Bariloche")
        self.assertTrue(all(g.evento == "Viaje a Bariloche" for g in r["seleccionados"]))

    def test_calcular_sin_gastos(self):
        with self.assertRaises(ErrorDatos):
            calcular(self.nombre, self.integrantes, [])


if __name__ == "__main__":
    unittest.main()
