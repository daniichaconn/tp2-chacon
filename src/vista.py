"""Vista: cómo se muestran los resultados en la terminal (con la librería rich).

Este módulo solo dibuja: recibe datos ya calculados y los presenta en tablas,
paneles y barras. No calcula nada. Si mañana quisiéramos una página web en
lugar de la terminal, cambiaríamos este archivo y nada más.
"""

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

ACENTO = "cyan"
POSITIVO = "green"
NEGATIVO = "red"
BLOQUES = " ▏▎▍▌▋▊▉█"


# ---------- formatos ----------

def pesos(centavos):
    """150050 -> '$ 1.500,50' (formato argentino)."""
    signo = "-" if centavos < 0 else ""
    centavos = abs(centavos)
    entero = f"{centavos // 100:,}".replace(",", ".")
    return f"{signo}$ {entero},{centavos % 100:02d}"


def fecha_corta(dia):
    return dia.strftime("%d/%m/%Y")


def porcentaje(valor):
    """31.234 -> '31,2%' (coma decimal, como se escribe en Argentina)."""
    return f"{valor:.1f}%".replace(".", ",")


def barra(valor, maximo, ancho=16):
    """Barra horizontal proporcional hecha con caracteres de bloque."""
    if maximo <= 0 or valor <= 0:
        return ""
    octavos = round(valor / maximo * ancho * 8)
    llenos, resto = divmod(octavos, 8)
    return "█" * llenos + (BLOQUES[resto] if resto else "")


def saldo_coloreado(centavos):
    if centavos > 0:
        return Text(pesos(centavos), style=f"bold {POSITIVO}")
    if centavos < 0:
        return Text(pesos(centavos), style=f"bold {NEGATIVO}")
    return Text(pesos(0), style="dim")


def _tabla(titulo, subtitulo=None):
    return Table(title=titulo, caption=subtitulo, box=box.ROUNDED, header_style=f"bold {ACENTO}",
                 title_style="bold", caption_style="dim", title_justify="left", expand=False)


# ---------- encabezado y mensajes ----------

def encabezado(console, nombre_grupo, archivo, auditoria, filtro=None):
    lineas = Text()
    lineas.append(f"{nombre_grupo}\n", style="bold")
    lineas.append(f"Datos: {archivo}\n", style="dim")
    lineas.append(f"Filas leídas {auditoria['filas_leidas']}  ·  ", style="dim")
    lineas.append(f"válidas {auditoria['validas']}", style=POSITIVO)
    lineas.append("  ·  ", style="dim")
    lineas.append(f"rechazadas {auditoria['rechazadas']}",
                  style=NEGATIVO if auditoria["rechazadas"] else "dim")
    if filtro:
        lineas.append(f"\nMostrando: {filtro}", style=f"bold {ACENTO}")
    console.print(Panel(lineas, title="[bold]Divisor de gastos compartidos[/]",
                        border_style=ACENTO, box=box.ROUNDED, expand=False, padding=(0, 2)))


def titulo_seccion(console, texto):
    console.print()
    console.rule(f"[bold {ACENTO}]{texto}[/]", align="left", style=ACENTO)


def error(console, texto):
    console.print(Panel(Text(texto), title="[bold]Error[/]", border_style=NEGATIVO,
                        box=box.ROUNDED, expand=False))


def aviso(console, texto):
    console.print(f"[dim]{texto}[/]")


# ---------- saldos y transferencias ----------

def tabla_saldos(console, resumen):
    tabla = _tabla("Saldos por persona", "Saldo = lo que pagó − lo que consumió")
    tabla.add_column("Persona", style="bold")
    tabla.add_column("Pagó", justify="right")
    tabla.add_column("Consumió", justify="right")
    tabla.add_column("Saldo", justify="right")
    tabla.add_column("Situación")
    for fila in resumen:
        if fila["pagado"] == 0 and fila["consumido"] == 0:
            continue
        saldo = fila["saldo"]
        situacion = ("[green]le deben[/]" if saldo > 0 else
                     "[red]debe[/]" if saldo < 0 else "[dim]a mano[/]")
        tabla.add_row(fila["persona"], pesos(fila["pagado"]), pesos(fila["consumido"]),
                      saldo_coloreado(saldo), situacion)
    console.print(tabla)


def tabla_transferencias(console, transferencias, grupo):
    if not transferencias:
        console.print(Panel("Nadie le debe nada a nadie.", border_style=POSITIVO,
                            box=box.ROUNDED, expand=False))
        return
    total = sum(m for _, _, m in transferencias)
    tabla = _tabla("Transferencias para quedar a mano",
                   f"{len(transferencias)} transferencias · {pesos(total)} en total")
    tabla.add_column("#", justify="right", style="dim")
    tabla.add_column("Paga", style=f"bold {NEGATIVO}")
    tabla.add_column("", justify="center", style="dim")
    tabla.add_column("Recibe", style=f"bold {POSITIVO}")
    tabla.add_column("Monto", justify="right", style="bold")
    tabla.add_column("Alias de destino", style=ACENTO)
    for i, (deudor, acreedor, monto) in enumerate(transferencias, start=1):
        tabla.add_row(str(i), deudor, "→", acreedor, pesos(monto), grupo.alias_de(acreedor))
    console.print(tabla)


# ---------- estadísticas ----------

def panel_general(console, general):
    caro = general["mas_caro"]
    texto = Text()
    filas = [
        ("Período", f"{fecha_corta(general['desde'])} al {fecha_corta(general['hasta'])}"),
        ("Gastos", str(general["cantidad"])),
        ("Total gastado", pesos(general["total"])),
        ("Promedio por gasto", pesos(general["promedio"])),
        ("Mediana por gasto", pesos(general["mediana"])),
        ("Gasto más grande", f"{pesos(caro.monto_centavos)} · {caro.descripcion} ({caro.evento})"),
    ]
    for i, (etiqueta, valor) in enumerate(filas):
        texto.append(f"{etiqueta:<20}", style="dim")
        texto.append(valor + ("\n" if i < len(filas) - 1 else ""), style="bold")
    console.print(Panel(texto, title="[bold]Resumen general[/]", border_style=ACENTO,
                        box=box.ROUNDED, expand=False))


def tabla_eventos(console, eventos, numerada=False):
    maximo = max((e["total"] for e in eventos), default=0)
    tabla = _tabla("Gasto por evento")
    if numerada:
        tabla.add_column("#", justify="right", style=f"bold {ACENTO}")
    tabla.add_column("Evento", style="bold", no_wrap=True)
    tabla.add_column("Fechas", style="dim", no_wrap=True)
    tabla.add_column("Gastos", justify="right")
    tabla.add_column("Total", justify="right")
    tabla.add_column("", style=ACENTO, min_width=12)
    tabla.add_column("Personas", justify="right")
    tabla.add_column("Por persona", justify="right")
    for i, e in enumerate(eventos, start=1):
        fechas = (fecha_corta(e["desde"]) if e["desde"] == e["hasta"]
                  else f"{e['desde']:%d/%m} al {e['hasta']:%d/%m}")
        fila = [e["evento"], fechas, str(e["cantidad"]), pesos(e["total"]),
                barra(e["total"], maximo, 12), str(e["personas"]), pesos(e["por_persona"])]
        tabla.add_row(*([str(i)] + fila if numerada else fila))
    console.print(tabla)


def tabla_categorias(console, categorias):
    maximo = max((c["total"] for c in categorias), default=0)
    tabla = _tabla("Gasto por categoría")
    tabla.add_column("Categoría", style="bold")
    tabla.add_column("Gastos", justify="right")
    tabla.add_column("Total", justify="right")
    tabla.add_column("%", justify="right")
    tabla.add_column("", style=ACENTO, min_width=16)
    for c in categorias:
        tabla.add_row(c["categoria"], str(c["cantidad"]), pesos(c["total"]),
                      porcentaje(c["porcentaje"]), barra(c["total"], maximo))
    console.print(tabla)


def tabla_meses(console, meses):
    maximo = max((m["total"] for m in meses), default=0)
    tabla = _tabla("Gasto por mes")
    tabla.add_column("Mes", style="bold")
    tabla.add_column("Gastos", justify="right")
    tabla.add_column("Total", justify="right")
    tabla.add_column("", style=ACENTO, min_width=16)
    tabla.add_column("Lo que más pesó", style="dim", no_wrap=True)
    for m in meses:
        tabla.add_row(m["mes"].capitalize(), str(m["cantidad"]), pesos(m["total"]),
                      barra(m["total"], maximo), m["evento_principal"])
    console.print(tabla)


def tabla_personas(console, personas):
    tabla = _tabla("Quién pone y quién consume")
    tabla.add_column("Persona", style="bold")
    tabla.add_column("Pagos", justify="right")
    tabla.add_column("Pagó", justify="right")
    tabla.add_column("% de lo pagado", justify="right")
    tabla.add_column("Consumió", justify="right")
    tabla.add_column("Saldo", justify="right")
    for p in sorted(personas, key=lambda x: -x["pagado"]):
        if p["pagado"] == 0 and p["consumido"] == 0:
            continue
        tabla.add_row(p["persona"], str(p["pagos"]), pesos(p["pagado"]),
                      porcentaje(p["porcentaje_pagado"]), pesos(p["consumido"]),
                      saldo_coloreado(p["saldo"]))
    console.print(tabla)


def panel_conclusiones(console, frases):
    texto = Text()
    for i, frase in enumerate(frases, start=1):
        texto.append(f"{i}. ", style=f"bold {ACENTO}")
        texto.append(frase + ("\n" if i < len(frases) else ""))
    console.print(Panel(texto, title="[bold]Conclusiones[/]", border_style=POSITIVO,
                        box=box.ROUNDED, expand=False, padding=(1, 2)))


def panel_comparacion(console, comparacion):
    maximo = comparacion["sin_organizar"]
    filas = [
        ("Pagar cada gasto por separado", comparacion["sin_organizar"], NEGATIVO),
        ("Compensar entre cada par de personas", comparacion["por_pares"], "yellow"),
        ("Con el programa (saldos)", comparacion["con_programa"], POSITIVO),
    ]
    tabla = Table.grid(padding=(0, 2))
    tabla.add_column(style="bold")
    tabla.add_column(justify="right")
    tabla.add_column()
    for etiqueta, valor, color in filas:
        tabla.add_row(etiqueta, f"[bold {color}]{valor}[/]", f"[{color}]{barra(valor, maximo, 30)}[/]")
    pie = Text(f"\nCon el programa se hacen {comparacion['ahorro']:.0f}% menos transferencias.",
               style=f"bold {POSITIVO}")
    console.print(Panel(Group(tabla, pie), title="[bold]¿Cuántas transferencias hacen falta?[/]",
                        border_style=ACENTO, box=box.ROUNDED, expand=False, padding=(1, 2)))


# ---------- persona y rechazados ----------

def tabla_detalle_persona(console, persona, detalle, fila_resumen):
    tabla = _tabla(f"Gastos de {persona}",
                   f"Pagó {pesos(fila_resumen['pagado'])} · consumió {pesos(fila_resumen['consumido'])}")
    tabla.add_column("Fecha", style="dim")
    tabla.add_column("Evento")
    tabla.add_column("Descripción")
    tabla.add_column("Pagó", justify="right")
    tabla.add_column("Su parte", justify="right")
    for d in detalle:
        pago = pesos(d["pago"]) if d["pago"] else "[dim]–[/]"
        parte = pesos(d["su_parte"]) if d["su_parte"] else "[dim]–[/]"
        tabla.add_row(d["fecha"], d["evento"], d["descripcion"], pago, parte)
    console.print(tabla)
    saldo = fila_resumen["saldo"]
    if saldo > 0:
        console.print(Text.assemble("Resultado: ", (f"le deben {pesos(saldo)}", f"bold {POSITIVO}")))
    elif saldo < 0:
        console.print(Text.assemble("Resultado: ", (f"debe {pesos(-saldo)}", f"bold {NEGATIVO}")))
    else:
        console.print("Resultado: [dim]está a mano[/]")


def tabla_persona_por_evento(console, persona, filas, fila_resumen):
    tabla = _tabla(f"{persona}: evento por evento",
                   "Para ver cada gasto: elegí un evento (o usá el comando persona con --evento)")
    tabla.add_column("Evento", style="bold", no_wrap=True)
    tabla.add_column("Pagó", justify="right")
    tabla.add_column("Consumió", justify="right")
    tabla.add_column("Saldo", justify="right")
    for f in filas:
        tabla.add_row(f["evento"], pesos(f["pagado"]), pesos(f["consumido"]), saldo_coloreado(f["saldo"]))
    tabla.add_section()
    tabla.add_row("[bold]Total[/]", pesos(fila_resumen["pagado"]), pesos(fila_resumen["consumido"]),
                  saldo_coloreado(fila_resumen["saldo"]))
    console.print(tabla)


def tabla_rechazados(console, rechazados):
    if not rechazados:
        console.print(Panel("No hubo filas rechazadas.", border_style=POSITIVO,
                            box=box.ROUNDED, expand=False))
        return
    tabla = _tabla("Gastos rechazados", f"{len(rechazados)} filas no se usaron en los cálculos")
    tabla.add_column("Id", style="bold")
    tabla.add_column("Fecha", style="dim")
    tabla.add_column("Descripción")
    tabla.add_column("Motivo", style=NEGATIVO)
    for r in rechazados:
        tabla.add_row(r["gasto_id"] or "–", r["fecha"], r["descripcion"], r["motivo"])
    console.print(tabla)


def lista_archivos(console, titulo, rutas):
    texto = Text()
    for i, ruta in enumerate(rutas):
        texto.append("✓ ", style=f"bold {POSITIVO}")
        texto.append(str(ruta) + ("\n" if i < len(rutas) - 1 else ""))
    console.print(Panel(texto, title=f"[bold]{titulo}[/]", border_style=POSITIVO,
                        box=box.ROUNDED, expand=False))


def lista_opciones(console, titulo, opciones):
    """Muestra opciones numeradas (para elegir un evento o una persona)."""
    tabla = Table.grid(padding=(0, 2))
    tabla.add_column(justify="right", style=f"bold {ACENTO}")
    tabla.add_column()
    for i, opcion in enumerate(opciones, start=1):
        tabla.add_row(str(i), opcion)
    console.print(Panel(tabla, title=f"[bold]{titulo}[/]", border_style=ACENTO,
                        box=box.ROUNDED, expand=False))


def menu(console, opciones):
    tabla = Table.grid(padding=(0, 2))
    tabla.add_column(justify="right", style=f"bold {ACENTO}")
    tabla.add_column()
    for clave, texto in opciones:
        tabla.add_row(clave, texto)
    console.print()
    console.print(Panel(tabla, title="[bold]Menú[/]", border_style=ACENTO,
                        box=box.ROUNDED, expand=False, padding=(0, 2)))
