"""Gráficos con matplotlib (como en la Clase 3 de la materia).

Cada función recibe datos ya calculados por estadisticas.py, dibuja un gráfico
y lo guarda como imagen PNG. No se abre ninguna ventana: los archivos quedan
en la carpeta de salida para abrirlos o compartirlos.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # dibujar en archivos, sin abrir ventanas
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

import estadisticas  # noqa: E402

COLOR = "#2a9d8f"
POSITIVO = "#2e7d32"
NEGATIVO = "#c62828"


def _miles_de_pesos(valor, _posicion):
    """Etiqueta de los ejes: 1500000 (pesos) -> '$1.500k'."""
    signo = "-" if valor < 0 else ""
    return f"{signo}${abs(valor) / 1000:,.0f}k".replace(",", ".")


def _guardar(figura, carpeta, nombre):
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / nombre
    figura.tight_layout()
    figura.savefig(ruta, dpi=120)
    plt.close(figura)
    return ruta


def grafico_categorias(gastos, carpeta, titulo="Gasto por categoría"):
    """Barras horizontales: cuánto se gastó en cada categoría (de mayor a menor)."""
    filas = estadisticas.por_categoria(gastos)[::-1]  # la más grande queda arriba
    nombres = [f["categoria"] for f in filas]
    totales = [f["total"] / 100 for f in filas]  # de centavos a pesos

    figura, eje = plt.subplots(figsize=(8, 4.5))
    barras = eje.barh(nombres, totales, color=COLOR)
    eje.bar_label(barras, labels=[f"{f['porcentaje']:.0f}%" for f in filas], padding=4)
    eje.xaxis.set_major_formatter(FuncFormatter(_miles_de_pesos))
    eje.set_title(titulo)
    eje.set_xlabel("Total gastado")
    eje.spines[["top", "right"]].set_visible(False)
    return _guardar(figura, carpeta, "categorias.png")


def grafico_meses(gastos, carpeta, titulo="Gasto por mes"):
    """Barras por mes: muestra en qué momentos del año se concentró el gasto."""
    filas = estadisticas.por_mes(gastos)
    meses = [f["mes"].split()[0][:3].capitalize() for f in filas]  # 'enero 2026' -> 'Ene'
    totales = [f["total"] / 100 for f in filas]

    figura, eje = plt.subplots(figsize=(8, 4.5))
    eje.bar(meses, totales, color=COLOR)
    eje.yaxis.set_major_formatter(FuncFormatter(_miles_de_pesos))
    eje.set_title(titulo)
    eje.set_ylabel("Total gastado")
    eje.spines[["top", "right"]].set_visible(False)
    return _guardar(figura, carpeta, "meses.png")


def grafico_saldos(resumen, carpeta, titulo="Saldo de cada persona"):
    """Barras de saldo: verde = le deben plata, rojo = debe plata."""
    filas = [f for f in resumen if f["pagado"] or f["consumido"]]
    filas.sort(key=lambda f: f["saldo"])
    nombres = [f["persona"] for f in filas]
    saldos = [f["saldo"] / 100 for f in filas]
    colores = [POSITIVO if s >= 0 else NEGATIVO for s in saldos]

    figura, eje = plt.subplots(figsize=(8, 4.5))
    eje.barh(nombres, saldos, color=colores)
    eje.axvline(0, color="black", linewidth=0.8)
    eje.xaxis.set_major_formatter(FuncFormatter(_miles_de_pesos))
    eje.set_title(titulo)
    eje.set_xlabel("Saldo (positivo: le deben · negativo: debe)")
    eje.spines[["top", "right"]].set_visible(False)
    return _guardar(figura, carpeta, "saldos.png")


def generar_todos(gastos, resumen, carpeta, nombre=None):
    """Genera los tres gráficos y devuelve las rutas de los archivos."""
    sufijo = f" · {nombre}" if nombre else ""
    rutas = [
        grafico_categorias(gastos, carpeta, "Gasto por categoría" + sufijo),
        grafico_saldos(resumen, carpeta, "Saldo de cada persona" + sufijo),
    ]
    if len(estadisticas.por_mes(gastos)) > 1:  # con un solo mes no tiene sentido
        rutas.append(grafico_meses(gastos, carpeta, "Gasto por mes" + sufijo))
    return rutas
