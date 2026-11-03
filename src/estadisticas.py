"""Estadísticas y conclusiones sobre los gastos.

Todas las funciones reciben una lista de gastos (objetos Gasto) ya validados
y devuelven datos (listas y diccionarios). No imprimen nada: mostrar los
resultados es trabajo de vista.py. Los importes siguen en centavos.
La única función que escribe en disco es guardar_estadisticas(), al final.
"""

import csv
from pathlib import Path
from statistics import median

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def _porcentaje(parte, total):
    return 100 * parte / total if total else 0.0


def _personas_de(gastos):
    """Todas las personas que pagaron o participaron en esos gastos."""
    return {p for g in gastos for p in (g.pagador, *g.participantes)}


def resumen_general(gastos):
    """Totales del conjunto: cantidad, total, promedio, mediana, gasto más caro."""
    if not gastos:
        return None
    montos = [g.monto_centavos for g in gastos]
    mas_caro = max(gastos, key=lambda g: (g.monto_centavos, g.gasto_id))
    return {
        "cantidad": len(gastos),
        "total": sum(montos),
        "promedio": sum(montos) // len(montos),
        "mediana": int(median(montos)),
        "mas_caro": mas_caro,
        "desde": min(g.fecha for g in gastos),
        "hasta": max(g.fecha for g in gastos),
        "personas": len(_personas_de(gastos)),
    }


def por_evento(gastos):
    """Una fila por evento, ordenadas por fecha: total, cantidad y costo por persona."""
    grupos = {}
    for g in gastos:
        grupos.setdefault(g.evento, []).append(g)
    filas = []
    for evento, lista in grupos.items():
        total = sum(g.monto_centavos for g in lista)
        personas = _personas_de(lista)
        filas.append({
            "evento": evento,
            "desde": min(g.fecha for g in lista),
            "hasta": max(g.fecha for g in lista),
            "cantidad": len(lista),
            "total": total,
            "personas": len(personas),
            "por_persona": total // len(personas),
        })
    return sorted(filas, key=lambda f: (f["desde"], f["evento"]))


def por_categoria(gastos):
    """Una fila por categoría, de la que más gasto tuvo a la que menos."""
    total = sum(g.monto_centavos for g in gastos)
    acumulado = {}
    cantidad = {}
    for g in gastos:
        acumulado[g.categoria] = acumulado.get(g.categoria, 0) + g.monto_centavos
        cantidad[g.categoria] = cantidad.get(g.categoria, 0) + 1
    filas = [
        {"categoria": c, "cantidad": cantidad[c], "total": t, "porcentaje": _porcentaje(t, total)}
        for c, t in acumulado.items()
    ]
    return sorted(filas, key=lambda f: (-f["total"], f["categoria"]))


def por_mes(gastos):
    """Una fila por mes (en orden): total, cantidad y el evento que más pesó."""
    meses = {}
    for g in gastos:
        meses.setdefault((g.fecha.year, g.fecha.month), []).append(g)
    filas = []
    for (anio, mes), lista in sorted(meses.items()):
        por_ev = {}
        for g in lista:
            por_ev[g.evento] = por_ev.get(g.evento, 0) + g.monto_centavos
        principal = max(por_ev, key=lambda e: (por_ev[e], e))
        filas.append({
            "mes": f"{MESES[mes - 1]} {anio}",
            "clave": f"{anio}-{mes:02d}",
            "cantidad": len(lista),
            "total": sum(g.monto_centavos for g in lista),
            "evento_principal": principal,
        })
    return filas


def por_persona(grupo):
    """Para cada integrante: pagado, consumido, saldo, pagos hechos y % del total pagado."""
    pagado = grupo.pagado_por_persona()
    consumido = grupo.consumido_por_persona()
    saldos = grupo.saldos()
    total = sum(pagado.values())
    pagos = {p: 0 for p in grupo.integrantes}
    for g in grupo.gastos:
        pagos[g.pagador] += 1
    return [
        {
            "persona": p,
            "pagado": pagado[p],
            "consumido": consumido[p],
            "saldo": saldos[p],
            "pagos": pagos[p],
            "porcentaje_pagado": _porcentaje(pagado[p], total),
        }
        for p in grupo.integrantes
    ]


def persona_por_evento(gastos, persona):
    """Para una persona: cuánto pagó, cuánto consumió y su saldo en cada evento."""
    filas = []
    for fila in por_evento(gastos):
        del_evento = [g for g in gastos if g.evento == fila["evento"]]
        pagado = sum(g.monto_centavos for g in del_evento if g.pagador == persona)
        consumido = sum(g.cuota_por_persona().get(persona, 0) for g in del_evento)
        if pagado or consumido:
            filas.append({"evento": fila["evento"], "desde": fila["desde"], "pagado": pagado,
                          "consumido": consumido, "saldo": pagado - consumido})
    return filas


def comparar_transferencias(grupo):
    """Cuántas transferencias hacen falta según cómo se organicen las cuentas."""
    sin_organizar = len(grupo.deudas_por_gasto())
    por_pares = len(grupo.deudas_netas_por_pares())
    con_programa = len(grupo.transferencias())
    return {
        "sin_organizar": sin_organizar,
        "por_pares": por_pares,
        "con_programa": con_programa,
        "ahorro": _porcentaje(sin_organizar - con_programa, sin_organizar),
    }


def conclusiones(gastos, grupo, rechazados=(), filas_leidas=None):
    """Frases con lo más importante que muestran los números."""
    general = resumen_general(gastos)
    if general is None:
        return ["No hay gastos para analizar."]
    frases = []
    frases.append(
        f"Se registraron {general['cantidad']} gastos por {_pesos(general['total'])} "
        f"entre el {_fecha(general['desde'])} y el {_fecha(general['hasta'])} "
        f"(promedio {_pesos(general['promedio'])} por gasto)."
    )

    eventos = por_evento(gastos)
    if len(eventos) > 1:
        caro = max(eventos, key=lambda e: e["total"])
        caro_pp = max(eventos, key=lambda e: e["por_persona"])
        frases.append(f"El evento con más gasto fue {caro['evento']}: {_pesos(caro['total'])}, "
                      f"el {_porcentaje(caro['total'], general['total']):.0f}% del total.")
        if caro_pp["evento"] != caro["evento"]:
            frases.append(f"Por persona, el más caro fue {caro_pp['evento']} "
                          f"({_pesos(caro_pp['por_persona'])} cada uno).")

    categorias = por_categoria(gastos)
    primera = categorias[0]
    frases.append(f"{primera['categoria']} es la categoría que más pesa: "
                  f"{primera['porcentaje']:.0f}% del total en {primera['cantidad']} gastos.")

    meses = por_mes(gastos)
    if len(meses) > 1:
        pico = max(meses, key=lambda m: m["total"])
        frases.append(f"El mes de mayor gasto fue {pico['mes']} ({_pesos(pico['total'])}), "
                      f"sobre todo por {pico['evento_principal']}.")

    personas = [p for p in por_persona(grupo) if p["pagado"] or p["consumido"]]
    adelanto = max(personas, key=lambda p: (p["pagado"], p["persona"]))
    frases.append(f"{adelanto['persona']} fue quien más plata adelantó: {_pesos(adelanto['pagado'])} "
                  f"({adelanto['porcentaje_pagado']:.0f}% de todo lo pagado).")
    deudor = min(personas, key=lambda p: (p["saldo"], p["persona"]))
    if deudor["saldo"] < 0:
        frases.append(f"Al cierre, {deudor['persona']} es quien más debe: {_pesos(-deudor['saldo'])}.")

    caro = general["mas_caro"]
    frases.append(f"El gasto individual más grande fue \"{caro.descripcion}\" "
                  f"({caro.evento}): {_pesos(caro.monto_centavos)}.")

    comparacion = comparar_transferencias(grupo)
    if comparacion["sin_organizar"]:
        frases.append(f"Pagando cada gasto por separado harían falta {comparacion['sin_organizar']} "
                      f"transferencias; con el programa alcanzan {comparacion['con_programa']} "
                      f"({comparacion['ahorro']:.0f}% menos).")

    if filas_leidas:
        frases.append(f"Se descartaron {len(rechazados)} de {filas_leidas} filas "
                      f"({_porcentaje(len(rechazados), filas_leidas):.1f}%) por errores de carga: "
                      "conviene revisarlas.")
    return frases


# --- formato breve para las frases (la vista tiene su propio formato) ---

def _pesos(centavos):
    entero = f"{centavos // 100:,}".replace(",", ".")
    return f"${entero}"


def _fecha(dia):
    return f"{dia.day} de {MESES[dia.month - 1]}"


# --- exportar ---

def guardar_estadisticas(carpeta, gastos, frases):
    """Escribe eventos.csv, categorias.csv, meses.csv y conclusiones.txt."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)

    def escribir(nombre, columnas, filas):
        with (carpeta / nombre).open("w", encoding="utf-8", newline="") as archivo:
            escritor = csv.DictWriter(archivo, fieldnames=columnas, extrasaction="ignore")
            escritor.writeheader()
            escritor.writerows(filas)

    def a_pesos(fila, *claves):
        return {**fila, **{k: f"{fila[k] / 100:.2f}" for k in claves}}

    escribir("eventos.csv", ["evento", "desde", "hasta", "cantidad", "total", "personas", "por_persona"],
             [a_pesos(f, "total", "por_persona") for f in por_evento(gastos)])
    escribir("categorias.csv", ["categoria", "cantidad", "total", "porcentaje"],
             [{**a_pesos(f, "total"), "porcentaje": f"{f['porcentaje']:.2f}"} for f in por_categoria(gastos)])
    escribir("meses.csv", ["clave", "mes", "cantidad", "total", "evento_principal"],
             [a_pesos(f, "total") for f in por_mes(gastos)])
    (carpeta / "conclusiones.txt").write_text(
        "\n".join(f"{i}. {frase}" for i, frase in enumerate(frases, start=1)) + "\n", encoding="utf-8")
    return carpeta
