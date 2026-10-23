"""Divisor de gastos compartidos: punto de entrada por consola.

Ejemplos (desde la carpeta raíz del proyecto):
    python src/main.py
    python src/main.py --datos data/gastos.json
    python src/main.py --desde 2026-07-10 --hasta 2026-07-12
    python src/main.py --persona Ana
"""

import argparse
import sys
from pathlib import Path

from dominio import ErrorDatos
from fuentes import cargar_grupo, crear_fuente
from pipeline import (
    ErrorVerificacion,
    centavos_a_texto,
    detalle_persona,
    guardar_resultados,
    leer_fecha,
    procesar,
)

RAIZ = Path(__file__).resolve().parents[1]


def leer_argumentos(argv=None):
    parser = argparse.ArgumentParser(
        description="Calcula saldos y las transferencias para saldar gastos compartidos."
    )
    parser.add_argument("--datos", default=str(RAIZ / "data" / "gastos.csv"),
                        help="archivo de gastos .csv o .json (por defecto data/gastos.csv)")
    parser.add_argument("--grupo", default=str(RAIZ / "data" / "grupo.json"),
                        help="archivo JSON con los integrantes y sus alias")
    parser.add_argument("--desde", help="fecha inicial AAAA-MM-DD (incluida)")
    parser.add_argument("--hasta", help="fecha final AAAA-MM-DD (incluida)")
    parser.add_argument("--persona", help="muestra el detalle de gastos de una persona")
    parser.add_argument("--salida", default=str(RAIZ / "outputs"),
                        help="carpeta donde se guardan los CSV de resultados")
    return parser.parse_args(argv)


def pesos(centavos):
    """Formato para mostrar en pantalla: $ 12.345,67"""
    texto = centavos_a_texto(abs(centavos))
    entero, decimales = texto.split(".")
    entero = f"{int(entero):,}".replace(",", ".")
    return f"{'-' if centavos < 0 else ''}$ {entero},{decimales}"


def mostrar(resultado, persona=None, detalle=None):
    grupo = resultado["grupo"]
    auditoria = resultado["auditoria"]
    print(f"\n=== {grupo.nombre} ===")
    print(f"Filas leídas: {auditoria['filas_leidas']} | válidas: {auditoria['validas']} | "
          f"rechazadas: {auditoria['rechazadas']} | en el período: {auditoria['en_periodo']}")
    print(f"Total gastado en el período: {pesos(auditoria['total_gastado'])}\n")

    print(f"{'Persona':<10}{'Pagó':>16}{'Consumió':>16}{'Saldo':>16}")
    for fila in resultado["resumen"]:
        print(f"{fila['persona']:<10}{pesos(fila['pagado']):>16}"
              f"{pesos(fila['consumido']):>16}{pesos(fila['saldo']):>16}")
    print("(saldo positivo: le deben plata | negativo: debe plata)\n")

    print("Transferencias para quedar a mano:")
    if not resultado["transferencias"]:
        print("  Nadie le debe nada a nadie.")
    for deudor, acreedor, monto in resultado["transferencias"]:
        print(f"  {deudor} -> {acreedor}: {pesos(monto)}  (alias: {grupo.alias_de(acreedor)})")

    if persona:
        print(f"\nDetalle de {persona}:")
        for fila in detalle:
            print(f"  {fila['gasto_id']} {fila['fecha']} {fila['descripcion']:<28}"
                  f" pagó {pesos(fila['pago']):>14}  su parte {pesos(fila['su_parte']):>12}")


def main(argv=None):
    args = leer_argumentos(argv)
    try:
        desde = leer_fecha(args.desde) if args.desde else None
        hasta = leer_fecha(args.hasta) if args.hasta else None
        nombre, integrantes = cargar_grupo(args.grupo)
        fuente = crear_fuente(args.datos)
        resultado = procesar(fuente, nombre, integrantes, desde, hasta)
        # se calcula antes de mostrar para avisar enseguida si la persona no existe
        detalle = detalle_persona(resultado["grupo"], args.persona) if args.persona else None
        mostrar(resultado, args.persona, detalle)
        carpeta = guardar_resultados(resultado, args.salida)
    except (ErrorDatos, ErrorVerificacion, FileNotFoundError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    print(f"\nResultados guardados en: {carpeta}")
    if resultado["rechazados"]:
        print(f"Revisar {carpeta / 'rechazados.csv'} para ver los gastos descartados y su motivo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
