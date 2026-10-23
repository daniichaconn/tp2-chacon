"""Genera los datos simulados del proyecto (data/gastos.csv y data/gastos.json).

Simula un año (enero a octubre de 2026) de gastos compartidos de un grupo de
seis amigos: vacaciones, viajes, asados, cumpleaños, partidos del Mundial y un
recital. Cada evento tiene sus propios integrantes y tipos de gasto.

Usa una semilla fija: si se vuelve a ejecutar, produce exactamente los mismos
archivos. Al final agrega filas con errores A PROPÓSITO para mostrar que el
programa las detecta y las rechaza.

Uso (desde la carpeta raíz):  python scripts/generar_datos.py
"""

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

SEMILLA = 2026
RAIZ = Path(__file__).resolve().parents[1]
CARPETA = RAIZ / "data"
COLUMNAS = ["gasto_id", "fecha", "evento", "categoria", "descripcion",
            "pagador", "monto", "participantes"]

TODOS = ["Ana", "Bruno", "Carla", "Diego", "Elena", "Facundo"]

# Tipos de gasto: (descripción, categoría, monto mínimo, monto máximo)
SUPER = ("Supermercado", "Supermercado", 25000, 95000)
VERDULERIA = ("Verdulería", "Supermercado", 6000, 18000)
BEBIDAS = ("Bebidas para la casa", "Supermercado", 12000, 40000)
CENA = ("Cena afuera", "Comidas y bebidas", 60000, 170000)
ALMUERZO = ("Almuerzo", "Comidas y bebidas", 30000, 95000)
CAFE = ("Café y medialunas", "Comidas y bebidas", 6000, 18000)
HELADO = ("Helado", "Comidas y bebidas", 8000, 22000)
CERVECERIA = ("Cervecería", "Comidas y bebidas", 25000, 75000)
REMIS = ("Remis", "Transporte", 7000, 25000)
NAFTA = ("Nafta", "Transporte", 40000, 90000)
PEAJE = ("Peaje", "Transporte", 3000, 9000)
FARMACIA = ("Farmacia", "Otros", 5000, 20000)


class Generador:
    """Acumula los gastos y numera los identificadores G001, G002, ..."""

    def __init__(self, semilla):
        self.rng = random.Random(semilla)
        self.filas = []

    def monto(self, minimo, maximo):
        """Importe al azar, a veces con centavos (por ejemplo 23456.5)."""
        return round(self.rng.randint(minimo, maximo) + self.rng.choice([0, 0, 0, 0.5, 0.25, 0.99]), 2)

    def agregar(self, fecha, evento, categoria, descripcion, pagador, monto, participantes):
        self.filas.append({
            "gasto_id": f"G{len(self.filas) + 1:03d}",
            "fecha": fecha.isoformat(),
            "evento": evento,
            "categoria": categoria,
            "descripcion": descripcion,
            "pagador": pagador,
            "monto": monto,
            "participantes": sorted(participantes),
        })

    def gasto_al_azar(self, fecha, evento, tipo, miembros, minimo_participantes=2):
        """Un gasto de cierto tipo, pagado y compartido por miembros al azar."""
        descripcion, categoria, minimo, maximo = tipo
        cantidad = self.rng.randint(min(minimo_participantes, len(miembros)), len(miembros))
        participantes = self.rng.sample(miembros, cantidad)
        pagador = self.rng.choice(miembros)
        self.agregar(fecha, evento, categoria, descripcion, pagador,
                     self.monto(minimo, maximo), participantes)

    def viaje(self, evento, inicio, dias, miembros, alojamiento, traslado, tipos_diarios, por_dia):
        """Un viaje: alojamiento y traslado al principio, y gastos cada día."""
        nombre, minimo, maximo = alojamiento
        self.agregar(inicio, evento, "Alojamiento", nombre, self.rng.choice(miembros),
                     self.monto(minimo, maximo), miembros)
        nombre, minimo, maximo = traslado
        self.agregar(inicio, evento, "Transporte", nombre, self.rng.choice(miembros),
                     self.monto(minimo, maximo), miembros)
        for dia in range(dias):
            fecha = inicio + timedelta(days=dia)
            for _ in range(self.rng.randint(*por_dia)):
                self.gasto_al_azar(fecha, evento, self.rng.choice(tipos_diarios), miembros)

    def cumpleanos(self, persona, fecha):
        """Regalo (lo pagan todos menos quien cumple) y gastos de la fiesta."""
        evento = f"Cumpleaños de {persona}"
        otros = [p for p in TODOS if p != persona]
        self.agregar(fecha - timedelta(days=2), evento, "Regalos", f"Regalo para {persona}",
                     self.rng.choice(otros), self.monto(60000, 120000), otros)
        fiesta = [
            ("Torta", "Comidas y bebidas", 25000, 45000),
            ("Picada", "Supermercado", 30000, 60000),
            BEBIDAS,
            ("Hielo y descartables", "Otros", 6000, 15000),
            ("Entradas al boliche", "Actividades y entradas", 50000, 110000),
            REMIS,
            ("Pizzas de madrugada", "Comidas y bebidas", 20000, 45000),
        ]
        for tipo in fiesta:
            self.gasto_al_azar(fecha, evento, tipo, TODOS, minimo_participantes=3)
        self.gasto_al_azar(fecha + timedelta(days=1), evento, CAFE, TODOS)


def generar_validos():
    g = Generador(SEMILLA)

    # 1. Vacaciones en Mar del Plata (10 días, 5 amigos)
    g.viaje(
        evento="Vacaciones en Mar del Plata",
        inicio=date(2026, 1, 12), dias=10,
        miembros=["Ana", "Bruno", "Carla", "Diego", "Elena"],
        alojamiento=("Departamento 10 noches", 950000, 1150000),
        traslado=("Micro ida y vuelta", 380000, 450000),
        tipos_diarios=[SUPER, VERDULERIA, BEBIDAS, CENA, ALMUERZO, CAFE, HELADO, REMIS,
                       ("Carpa en el balneario", "Actividades y entradas", 35000, 60000),
                       ("Entradas al boliche", "Actividades y entradas", 50000, 110000)],
        por_dia=(8, 10),
    )

    # 2. Finde largo de Carnaval en Córdoba (4 días, 4 amigos)
    g.viaje(
        evento="Finde largo en Córdoba",
        inicio=date(2026, 2, 14), dias=4,
        miembros=["Ana", "Carla", "Diego", "Facundo"],
        alojamiento=("Cabaña en Villa Carlos Paz", 320000, 420000),
        traslado=("Nafta ida y vuelta", 110000, 150000),
        tipos_diarios=[SUPER, CENA, ALMUERZO, HELADO, PEAJE, CERVECERIA,
                       ("Excursión en aerosilla", "Actividades y entradas", 40000, 80000)],
        por_dia=(7, 9),
    )

    # 3. Asados del grupo: uno por mes, de enero a octubre
    for mes in range(1, 11):
        fecha = date(2026, mes, 25 if mes != 2 else 27)
        presentes = g.rng.sample(TODOS, g.rng.randint(4, 6))
        evento = "Asados del grupo"
        carne = g.rng.choice(presentes)
        g.agregar(fecha, evento, "Supermercado", "Carne para el asado", carne,
                  g.monto(70000, 130000), presentes)
        g.agregar(fecha, evento, "Supermercado", "Carbón y leña", g.rng.choice(presentes),
                  g.monto(8000, 16000), presentes)
        g.agregar(fecha, evento, "Supermercado", "Bebidas", g.rng.choice(presentes),
                  g.monto(20000, 45000), presentes)
        g.gasto_al_azar(fecha, evento, VERDULERIA, presentes, minimo_participantes=len(presentes))
        g.gasto_al_azar(fecha, evento, HELADO, presentes, minimo_participantes=3)

    # 4. Cumpleaños
    g.cumpleanos("Bruno", date(2026, 4, 18))
    g.cumpleanos("Elena", date(2026, 8, 22))

    # 5. Mundial 2026: juntadas para ver los partidos de Argentina
    for numero, fecha in enumerate([date(2026, 6, 16), date(2026, 6, 22), date(2026, 6, 27),
                                    date(2026, 7, 3), date(2026, 7, 9), date(2026, 7, 14),
                                    date(2026, 7, 19)], start=1):
        evento = "Mundial 2026: partidos de Argentina"
        presentes = g.rng.sample(TODOS, g.rng.randint(4, 6))
        g.gasto_al_azar(fecha, evento, ("Pizzas", "Comidas y bebidas", 25000, 50000),
                        presentes, minimo_participantes=len(presentes))
        g.gasto_al_azar(fecha, evento, ("Empanadas", "Comidas y bebidas", 20000, 42000),
                        presentes, minimo_participantes=len(presentes))
        g.gasto_al_azar(fecha, evento, BEBIDAS, presentes, minimo_participantes=len(presentes))
        g.gasto_al_azar(fecha, evento, ("Facturas para el partido", "Comidas y bebidas", 8000, 16000),
                        presentes, minimo_participantes=2)

    # 6. Viaje a Bariloche en las vacaciones de invierno (7 días, 5 amigos)
    g.viaje(
        evento="Viaje a Bariloche",
        inicio=date(2026, 7, 27), dias=7,
        miembros=["Ana", "Bruno", "Carla", "Diego", "Elena"],
        alojamiento=("Cabaña 7 noches", 850000, 950000),
        traslado=("Pasajes de avión", 900000, 1100000),
        tipos_diarios=[SUPER, CENA, ALMUERZO, CAFE, CERVECERIA, REMIS, FARMACIA,
                       ("Chocolates", "Comidas y bebidas", 8000, 35000),
                       ("Alquiler de equipo de esquí", "Actividades y entradas", 45000, 120000),
                       ("Pase Cerro Catedral", "Actividades y entradas", 70000, 150000),
                       ("Excursión Circuito Chico", "Actividades y entradas", 30000, 90000)],
        por_dia=(9, 11),
    )

    # 7. Recital en Buenos Aires (2 días, 3 amigos)
    g.viaje(
        evento="Recital en Buenos Aires",
        inicio=date(2026, 9, 26), dias=2,
        miembros=["Bruno", "Elena", "Facundo"],
        alojamiento=("Hostel 1 noche", 60000, 90000),
        traslado=("Micro Rosario - Buenos Aires", 150000, 190000),
        tipos_diarios=[CENA, CAFE, REMIS, ("Merchandising", "Otros", 25000, 50000)],
        por_dia=(4, 5),
    )
    g.agregar(date(2026, 9, 26), "Recital en Buenos Aires", "Actividades y entradas",
              "Entradas al recital", "Facundo", 285000, ["Bruno", "Elena", "Facundo"])
    return g.filas


def generar_invalidos(filas_validas):
    """Filas con errores deliberados (cada una prueba una regla distinta)."""
    siguiente = len(filas_validas) + 1

    def fila(**datos):
        nonlocal siguiente
        base = {"gasto_id": f"G{siguiente:03d}", "fecha": "2026-05-25",
                "evento": "Asados del grupo", "categoria": "Supermercado",
                "descripcion": "Gasto", "pagador": "Ana", "monto": 10000,
                "participantes": ["Ana", "Bruno"]}
        siguiente += 1
        base.update(datos)
        return base

    repetido = dict(filas_validas[40])  # mismo id que una fila válida -> duplicado
    repetido["descripcion"] += " (cargado dos veces)"
    return [
        repetido,
        fila(gasto_id="G12", descripcion="Helado"),
        fila(fecha="2026-02-30", descripcion="Peaje"),
        fila(fecha="15/03/2026", descripcion="Fernet"),
        fila(monto="1.500,00", descripcion="Farmacia"),
        fila(monto=-2500, descripcion="Devolución"),
        fila(monto=0, descripcion="Propina"),
        fila(pagador="Mateo", participantes=["Ana", "Mateo"], descripcion="Pizza"),
        fila(participantes=[], descripcion="Hielo"),
        fila(participantes=["Ana", "Ana", "Bruno"], descripcion="Bebidas"),
        fila(categoria="Varios", descripcion="Cosas sueltas"),
        fila(evento="", descripcion="Taxi sin evento", categoria="Transporte"),
    ]


def texto_monto(monto):
    """Representación del monto en el CSV (punto decimal, sin separador de miles)."""
    if isinstance(monto, float):
        return f"{monto:.2f}".rstrip("0").rstrip(".")
    return str(monto)


def main():
    validos = generar_validos()
    filas = validos + generar_invalidos(validos)
    CARPETA.mkdir(exist_ok=True)

    with (CARPETA / "gastos.csv").open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(COLUMNAS)
        for f in filas:
            escritor.writerow([f["gasto_id"], f["fecha"], f["evento"], f["categoria"],
                               f["descripcion"], f["pagador"], texto_monto(f["monto"]),
                               ";".join(f["participantes"])])

    # En el JSON los montos válidos van como número (así es lo habitual en JSON)
    salida_json = []
    for f in filas:
        copia = dict(f)
        if isinstance(copia["monto"], float):
            numero = float(texto_monto(copia["monto"]))
            copia["monto"] = int(numero) if numero.is_integer() else numero
        salida_json.append(copia)
    with (CARPETA / "gastos.json").open("w", encoding="utf-8") as archivo:
        json.dump(salida_json, archivo, ensure_ascii=False, indent=2)

    print(f"Generadas {len(filas)} filas ({len(validos)} válidas + "
          f"{len(filas) - len(validos)} con errores) en {CARPETA}")


if __name__ == "__main__":
    main()
