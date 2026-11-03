"""Divisor de gastos compartidos: programa de consola.

Sin argumentos abre el MENÚ interactivo:
    python src/main.py

También se puede usar con comandos (útil para una demo rápida):
    python src/main.py resumen                       saldos y transferencias de todo el año
    python src/main.py resumen --evento bariloche    cerrar las cuentas de un evento
    python src/main.py estadisticas                  estadísticas y conclusiones
    python src/main.py persona Ana                   detalle de una persona
    python src/main.py comparar                      transferencias sin organizar vs. con el programa
    python src/main.py eventos                       lista de eventos
    python src/main.py rechazados                    filas descartadas y su motivo
    python src/main.py graficos                      gráficos PNG en outputs/graficos

Opciones para cualquier comando: --datos (CSV o JSON), --grupo, --salida.
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

import estadisticas
import graficos
import vista
from dominio import ErrorDatos
from fuentes import cargar_grupo, crear_fuente
from pipeline import (
    ErrorVerificacion,
    calcular,
    cargar_y_limpiar,
    detalle_persona,
    eventos_disponibles,
    filtrar_evento,
    filtrar_periodo,
    guardar_resultados,
    leer_fecha,
    normalizar,
)

RAIZ = Path(__file__).resolve().parents[1]
ERRORES_ESPERADOS = (ErrorDatos, ErrorVerificacion, FileNotFoundError, ValueError)


class Pregunta(Prompt):
    """Prompt de rich con los mensajes en castellano."""

    illegal_choice_message = "[prompt.invalid.choice]Esa opción no existe: escribí uno de los números de la lista."


class Sesion:
    """Datos cargados una sola vez y las acciones que se pueden pedir sobre ellos.

    Cada acción filtra los gastos válidos, calcula y le pasa el resultado a la vista.
    """

    def __init__(self, ruta_datos, ruta_grupo, carpeta_salida, console):
        self.console = console
        self.archivo = Path(ruta_datos)
        self.salida = Path(carpeta_salida)
        self.nombre, self.integrantes = cargar_grupo(ruta_grupo)
        filas, self.validos, self.rechazados = cargar_y_limpiar(
            crear_fuente(ruta_datos), self.nombre, self.integrantes)
        self.filas_leidas = len(filas)
        self.eventos = eventos_disponibles(self.validos)

    # ----- utilidades -----

    def auditoria(self):
        return {"filas_leidas": self.filas_leidas, "validas": len(self.validos),
                "rechazadas": len(self.rechazados)}

    def encabezado(self, filtro=None):
        try:
            archivo = self.archivo.resolve().relative_to(RAIZ)
        except ValueError:
            archivo = self.archivo
        vista.encabezado(self.console, self.nombre, archivo, self.auditoria(), filtro)

    def seleccionar(self, evento=None, desde=None, hasta=None):
        """Devuelve (gastos elegidos, nombre exacto del evento o None, descripción del filtro)."""
        gastos = filtrar_evento(self.validos, evento)
        nombre_evento = gastos[0].evento if evento and gastos else None
        gastos = filtrar_periodo(gastos, desde, hasta)
        partes = [nombre_evento or "todos los eventos"]
        if desde or hasta:
            partes.append(f"del {vista.fecha_corta(desde) if desde else 'inicio'} "
                          f"al {vista.fecha_corta(hasta) if hasta else 'final'}")
        return gastos, nombre_evento, " · ".join(partes)

    def persona_exacta(self, texto):
        """'bruno' -> 'Bruno'. Error claro si no es del grupo."""
        for persona in self.integrantes:
            if normalizar(persona) == normalizar(texto):
                return persona
        raise ErrorDatos(f"'{texto}' no pertenece al grupo. Integrantes: {', '.join(sorted(self.integrantes))}")

    # ----- acciones -----

    def resumen(self, evento=None, desde=None, hasta=None, guardar=True):
        gastos, _, filtro = self.seleccionar(evento, desde, hasta)
        grupo, resumen, transferencias = calcular(self.nombre, self.integrantes, gastos)
        vista.titulo_seccion(self.console, f"Cuentas · {filtro}")
        vista.aviso(self.console, f"{len(gastos)} gastos · {vista.pesos(sum(g.monto_centavos for g in gastos))}")
        vista.tabla_saldos(self.console, resumen)
        vista.tabla_transferencias(self.console, transferencias, grupo)
        if guardar:
            carpeta = guardar_resultados({"grupo": grupo, "resumen": resumen,
                                          "transferencias": transferencias,
                                          "rechazados": self.rechazados}, self.salida)
            vista.aviso(self.console, f"Guardado en {carpeta}: saldos.csv, transferencias.csv, rechazados.csv")

    def estadisticas(self, evento=None, guardar=True):
        gastos, nombre_evento, filtro = self.seleccionar(evento)
        grupo, _, _ = calcular(self.nombre, self.integrantes, gastos)
        vista.titulo_seccion(self.console, f"Estadísticas · {filtro}")
        vista.panel_general(self.console, estadisticas.resumen_general(gastos))
        if nombre_evento is None:
            vista.tabla_eventos(self.console, estadisticas.por_evento(gastos))
        vista.tabla_categorias(self.console, estadisticas.por_categoria(gastos))
        meses = estadisticas.por_mes(gastos)
        if len(meses) > 1:
            vista.tabla_meses(self.console, meses)
        vista.tabla_personas(self.console, estadisticas.por_persona(grupo))
        frases = estadisticas.conclusiones(
            gastos, grupo,
            rechazados=self.rechazados if nombre_evento is None else (),
            filas_leidas=self.filas_leidas if nombre_evento is None else None)
        vista.panel_conclusiones(self.console, frases)
        if guardar:
            carpeta = estadisticas.guardar_estadisticas(self.salida, gastos, frases)
            vista.aviso(self.console, f"Guardado en {carpeta}: eventos.csv, categorias.csv, "
                                      "meses.csv, conclusiones.txt")

    def persona(self, nombre, evento=None):
        """Sin evento: resumen de la persona evento por evento. Con evento: cada gasto."""
        persona = self.persona_exacta(nombre)
        gastos, nombre_evento, filtro = self.seleccionar(evento)
        grupo, resumen, _ = calcular(self.nombre, self.integrantes, gastos)
        fila = next(f for f in resumen if f["persona"] == persona)
        vista.titulo_seccion(self.console, f"{persona} · {filtro}")
        if nombre_evento is None:
            vista.tabla_persona_por_evento(
                self.console, persona, estadisticas.persona_por_evento(gastos, persona), fila)
        else:
            vista.tabla_detalle_persona(self.console, persona, detalle_persona(grupo, persona), fila)

    def comparar(self, evento=None):
        gastos, _, filtro = self.seleccionar(evento)
        grupo, _, _ = calcular(self.nombre, self.integrantes, gastos)
        vista.titulo_seccion(self.console, f"Comparación de transferencias · {filtro}")
        vista.panel_comparacion(self.console, estadisticas.comparar_transferencias(grupo))

    def listar_eventos(self):
        vista.titulo_seccion(self.console, "Eventos")
        vista.tabla_eventos(self.console, estadisticas.por_evento(self.validos), numerada=True)

    def ver_rechazados(self):
        vista.titulo_seccion(self.console, "Filas rechazadas")
        vista.tabla_rechazados(self.console, self.rechazados)

    def graficos(self, evento=None):
        gastos, nombre_evento, filtro = self.seleccionar(evento)
        _, resumen, _ = calcular(self.nombre, self.integrantes, gastos)
        vista.titulo_seccion(self.console, f"Gráficos · {filtro}")
        with self.console.status("Dibujando los gráficos..."):
            rutas = graficos.generar_todos(gastos, resumen, self.salida / "graficos", nombre_evento)
        vista.lista_archivos(self.console, "Gráficos guardados", rutas)

    def exportar(self):
        self.resumen(guardar=True)
        self.estadisticas(guardar=True)
        self.graficos()


# ---------- menú interactivo ----------

OPCIONES_MENU = [
    ("1", "Resumen del año: saldos y transferencias"),
    ("2", "Cerrar las cuentas de un evento"),
    ("3", "Estadísticas y conclusiones del año"),
    ("4", "Estadísticas de un evento"),
    ("5", "Detalle de una persona"),
    ("6", "Comparar transferencias: sin organizar vs. con el programa"),
    ("7", "Ver gastos rechazados"),
    ("8", "Generar gráficos (imágenes PNG)"),
    ("9", "Exportar todos los resultados a la carpeta outputs"),
    ("0", "Salir"),
]


def elegir(console, stream, titulo, opciones):
    """Muestra opciones numeradas y devuelve la elegida (sin escribir nombres a mano)."""
    vista.lista_opciones(console, titulo, opciones)
    numero = Pregunta.ask("Elegí un número", console=console, stream=stream,
                        choices=[str(i) for i in range(1, len(opciones) + 1)], show_choices=False)
    return opciones[int(numero) - 1]


def menu(sesion, stream=None):
    console = sesion.console
    sesion.encabezado()
    while True:
        vista.menu(console, OPCIONES_MENU)
        opcion = Pregunta.ask("Elegí una opción", console=console, stream=stream,
                            choices=[clave for clave, _ in OPCIONES_MENU], show_choices=False)
        if opcion == "0":
            console.print("[bold cyan]¡Hasta luego![/]")
            return 0
        try:
            if opcion == "1":
                sesion.resumen()
            elif opcion == "2":
                sesion.resumen(evento=elegir(console, stream, "¿Qué evento?", sesion.eventos))
            elif opcion == "3":
                sesion.estadisticas()
            elif opcion == "4":
                sesion.estadisticas(evento=elegir(console, stream, "¿Qué evento?", sesion.eventos))
            elif opcion == "5":
                persona = elegir(console, stream, "¿Quién?", sorted(sesion.integrantes))
                sesion.persona(persona)
                if Pregunta.ask("¿Ver cada gasto de un evento? (s/n)", console=console, stream=stream,
                                choices=["s", "n"], default="n", show_choices=False) == "s":
                    sesion.persona(persona, elegir(console, stream, "¿Qué evento?", sesion.eventos))
            elif opcion == "6":
                sesion.comparar()
            elif opcion == "7":
                sesion.ver_rechazados()
            elif opcion == "8":
                sesion.graficos()
            elif opcion == "9":
                sesion.exportar()
        except ERRORES_ESPERADOS as problema:
            vista.error(console, str(problema))
        Pregunta.ask("\n[dim]Enter para volver al menú[/]", console=console, stream=stream,
                   default="", show_default=False)


# ---------- argumentos ----------

def leer_argumentos(argv=None):
    comunes = argparse.ArgumentParser(add_help=False)
    comunes.add_argument("--datos", default=str(RAIZ / "data" / "gastos.csv"),
                         help="archivo de gastos .csv o .json (por defecto data/gastos.csv)")
    comunes.add_argument("--grupo", default=str(RAIZ / "data" / "grupo.json"),
                         help="archivo JSON con los integrantes y sus alias")
    comunes.add_argument("--salida", default=str(RAIZ / "outputs"),
                         help="carpeta donde se guardan los resultados")

    con_evento = argparse.ArgumentParser(add_help=False)
    con_evento.add_argument("--evento", help="nombre o parte del nombre de un evento (ej.: bariloche)")

    parser = argparse.ArgumentParser(
        description="Divisor de gastos compartidos. Sin comando, abre el menú interactivo.",
        parents=[comunes])
    comandos = parser.add_subparsers(dest="comando", metavar="comando")
    resumen = comandos.add_parser("resumen", parents=[comunes, con_evento],
                                  help="saldos y transferencias")
    resumen.add_argument("--desde", help="fecha inicial AAAA-MM-DD (incluida)")
    resumen.add_argument("--hasta", help="fecha final AAAA-MM-DD (incluida)")
    comandos.add_parser("estadisticas", parents=[comunes, con_evento],
                        help="estadísticas y conclusiones")
    persona = comandos.add_parser("persona", parents=[comunes, con_evento],
                                  help="detalle de los gastos de una persona")
    persona.add_argument("nombre", help="nombre de la persona (ej.: Ana)")
    comandos.add_parser("comparar", parents=[comunes, con_evento],
                        help="cuántas transferencias hacen falta con y sin el programa")
    comandos.add_parser("eventos", parents=[comunes], help="lista de eventos")
    comandos.add_parser("rechazados", parents=[comunes], help="filas descartadas y su motivo")
    comandos.add_parser("graficos", parents=[comunes, con_evento],
                        help="gráficos PNG por categoría, mes y saldos")
    comandos.add_parser("menu", parents=[comunes], help="abre el menú interactivo")
    return parser.parse_args(argv)


def main(argv=None, console=None, stream=None):
    args = leer_argumentos(argv)
    console = console or Console()
    try:
        sesion = Sesion(args.datos, args.grupo, args.salida, console)
        if args.comando in (None, "menu"):
            return menu(sesion, stream)
        evento = getattr(args, "evento", None)
        filtro = None
        if evento:
            filtro = filtrar_evento(sesion.validos, evento)[0].evento
        sesion.encabezado(filtro)
        if args.comando == "resumen":
            desde = leer_fecha(args.desde) if args.desde else None
            hasta = leer_fecha(args.hasta) if args.hasta else None
            sesion.resumen(evento, desde, hasta)
        elif args.comando == "estadisticas":
            sesion.estadisticas(evento)
        elif args.comando == "persona":
            sesion.persona(args.nombre, evento)
        elif args.comando == "comparar":
            sesion.comparar(evento)
        elif args.comando == "eventos":
            sesion.listar_eventos()
        elif args.comando == "rechazados":
            sesion.ver_rechazados()
        elif args.comando == "graficos":
            sesion.graficos(evento)
    except ERRORES_ESPERADOS as problema:
        vista.error(console, str(problema))
        return 1
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Interrumpido.[/]")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
