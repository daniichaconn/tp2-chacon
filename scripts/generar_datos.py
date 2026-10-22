"""Genera los datos simulados del proyecto (data/gastos.csv y data/gastos.json).

Simula los gastos de un viaje de 5 amigos a Bariloche durante una semana.
Usa una semilla fija: si se vuelve a ejecutar, produce exactamente los mismos
archivos. Al final agrega algunas filas con errores A PROPÓSITO para mostrar
que el programa las detecta y las rechaza.

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

PERSONAS = ["Ana", "Bruno", "Carla", "Diego", "Elena"]
INICIO = date(2026, 7, 6)
DIAS = 7

# (descripción, monto mínimo, monto máximo, cantidad mínima de participantes)
TIPOS_DE_GASTO = [
    ("Supermercado", 25000, 90000, 5),
    ("Nafta", 40000, 85000, 5),
    ("Cena", 60000, 160000, 3),
    ("Almuerzo", 30000, 90000, 2),
    ("Café y medialunas", 6000, 18000, 2),
    ("Cervecería", 20000, 70000, 2),
    ("Chocolates", 8000, 35000, 1),
    ("Remis", 9000, 25000, 2),
    ("Alquiler de equipo de esquí", 45000, 120000, 2),
    ("Pase Cerro Catedral", 70000, 150000, 2),
    ("Excursión Circuito Chico", 30000, 90000, 3),
]


def generar_validos(rng):
    filas = [{
        "gasto_id": "G001",
        "fecha": INICIO.isoformat(),
        "descripcion": "Alojamiento cabaña 7 noches",
        "pagador": "Ana",
        "monto": 875000.0,
        "participantes": list(PERSONAS),
    }]
    numero = 2
    for dia in range(DIAS):
        fecha = INICIO + timedelta(days=dia)
        for _ in range(rng.randint(7, 10)):
            descripcion, minimo, maximo, min_part = rng.choice(TIPOS_DE_GASTO)
            cantidad = rng.randint(min_part, len(PERSONAS))
            participantes = sorted(rng.sample(PERSONAS, cantidad))
            pagador = rng.choice(PERSONAS)
            # importe con centavos a veces (por ejemplo 23456.75)
            monto = rng.randint(minimo, maximo) + rng.choice([0, 0, 0, 0.5, 0.25, 0.99])
            filas.append({
                "gasto_id": f"G{numero:03d}",
                "fecha": fecha.isoformat(),
                "descripcion": descripcion,
                "pagador": pagador,
                "monto": round(monto, 2),
                "participantes": participantes,
            })
            numero += 1
    return filas, numero


def generar_invalidos(numero, filas_validas):
    """Filas con errores deliberados (cada una prueba una regla distinta)."""
    repetido = dict(filas_validas[10])  # mismo id que una fila válida -> duplicado
    repetido["descripcion"] += " (cargado dos veces)"
    return [
        repetido,
        {"gasto_id": "G9", "fecha": "2026-07-08", "descripcion": "Helado",
         "pagador": "Bruno", "monto": 9000, "participantes": ["Bruno", "Carla"]},
        {"gasto_id": f"G{numero:03d}", "fecha": "2026-06-31", "descripcion": "Peaje",
         "pagador": "Diego", "monto": 4500, "participantes": list(PERSONAS)},
        {"gasto_id": f"G{numero + 1:03d}", "fecha": "2026-07-09", "descripcion": "Farmacia",
         "pagador": "Elena", "monto": "1.500,00", "participantes": ["Elena"]},
        {"gasto_id": f"G{numero + 2:03d}", "fecha": "2026-07-10", "descripcion": "Devolución",
         "pagador": "Carla", "monto": -2500, "participantes": ["Ana", "Carla"]},
        {"gasto_id": f"G{numero + 3:03d}", "fecha": "2026-07-11", "descripcion": "Pizza",
         "pagador": "Franco", "monto": 32000, "participantes": ["Ana", "Franco"]},
        {"gasto_id": f"G{numero + 4:03d}", "fecha": "2026-07-12", "descripcion": "Propina",
         "pagador": "Ana", "monto": 5000, "participantes": []},
    ]


def texto_monto(monto):
    """Representación del monto en el CSV (punto decimal, sin separador de miles)."""
    if isinstance(monto, float):
        return f"{monto:.2f}".rstrip("0").rstrip(".")
    return str(monto)


def main():
    rng = random.Random(SEMILLA)
    validos, siguiente = generar_validos(rng)
    filas = validos + generar_invalidos(siguiente, validos)
    CARPETA.mkdir(exist_ok=True)

    with (CARPETA / "gastos.csv").open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(["gasto_id", "fecha", "descripcion", "pagador", "monto", "participantes"])
        for f in filas:
            escritor.writerow([f["gasto_id"], f["fecha"], f["descripcion"], f["pagador"],
                               texto_monto(f["monto"]), ";".join(f["participantes"])])

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
