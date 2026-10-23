"""Flujo de procesamiento: validar -> limpiar -> filtrar -> calcular -> verificar -> guardar.

Las funciones de este módulo NO leen archivos de entrada: reciben los datos ya
cargados por una fuente (CSV o JSON). Solo guardar_resultados() escribe en disco.
"""

import csv
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from dominio import ErrorDatos, Gasto, Grupo
from fuentes import COLUMNAS

# Expresiones regulares: comprueban el FORMATO del texto (no su significado).
PATRON_ID = re.compile(r"G\d{3}")                    # G001, G002, ...
PATRON_FECHA = re.compile(r"\d{4}-\d{2}-\d{2}")      # AAAA-MM-DD
PATRON_MONTO = re.compile(r"\d+(\.\d{1,2})?")        # 1500 o 1500.5 o 1500.50

# Categorías aceptadas: una lista cerrada permite agrupar y comparar sin ambigüedad.
CATEGORIAS = (
    "Alojamiento",
    "Transporte",
    "Supermercado",
    "Comidas y bebidas",
    "Actividades y entradas",
    "Regalos",
    "Otros",
)


class ErrorVerificacion(Exception):
    """El resultado calculado no cumple una propiedad que debería cumplir."""


# ---------- utilidades ----------

def pesos_a_centavos(texto):
    """'1500.5' -> 150050. Se usa después de validar el texto con PATRON_MONTO."""
    entero, _, decimales = texto.partition(".")
    return int(entero) * 100 + int(decimales.ljust(2, "0") or 0)


def centavos_a_texto(centavos):
    """150050 -> '1500.50' (para mostrar y exportar)."""
    signo = "-" if centavos < 0 else ""
    centavos = abs(centavos)
    return f"{signo}{centavos // 100}.{centavos % 100:02d}"


def leer_fecha(texto):
    """Convierte 'AAAA-MM-DD' en date, controlando formato y calendario."""
    if not PATRON_FECHA.fullmatch(texto):
        raise ValueError(f"fecha con formato inválido '{texto}' (usar AAAA-MM-DD)")
    try:
        return datetime.strptime(texto, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"fecha inexistente en el calendario '{texto}'") from None


# ---------- 1. validar ----------

def validar_esquema(filas):
    """Detiene el flujo si no hay datos o faltan columnas obligatorias."""
    if not filas:
        raise ErrorDatos("No hay gastos para procesar: la entrada está vacía")
    faltantes = sorted({c for fila in filas for c in COLUMNAS if c not in fila})
    if faltantes:
        raise ErrorDatos(f"Faltan columnas obligatorias: {', '.join(faltantes)}")


# ---------- 2. limpiar ----------

def _motivos_de_rechazo(fila, grupo, ids_duplicados):
    """Devuelve la lista de problemas de una fila (vacía si es válida)."""
    motivos = []
    gasto_id = fila["gasto_id"].strip()
    if not PATRON_ID.fullmatch(gasto_id):
        motivos.append(f"id con formato inválido '{gasto_id}' (usar G seguido de 3 dígitos)")
    elif gasto_id in ids_duplicados:
        motivos.append(f"id duplicado '{gasto_id}'")
    try:
        leer_fecha(fila["fecha"].strip())
    except ValueError as error:
        motivos.append(str(error))
    if not fila["descripcion"].strip():
        motivos.append("descripción vacía")
    if not fila["evento"].strip():
        motivos.append("evento vacío")
    categoria = fila["categoria"].strip()
    if categoria not in CATEGORIAS:
        motivos.append(f"categoría desconocida '{categoria}' (usar una de: {', '.join(CATEGORIAS)})")
    monto = fila["monto"].strip()
    if not PATRON_MONTO.fullmatch(monto):
        motivos.append(f"monto inválido '{monto}' (número positivo con punto decimal)")
    elif pesos_a_centavos(monto) == 0:
        motivos.append("monto igual a cero")
    pagador = fila["pagador"].strip()
    if not grupo.es_integrante(pagador):
        motivos.append(f"pagador fuera del grupo '{pagador}'")
    participantes = fila["participantes"]
    if not participantes:
        motivos.append("sin participantes")
    else:
        ajenos = [p for p in participantes if not grupo.es_integrante(p)]
        if ajenos:
            motivos.append(f"participantes fuera del grupo: {', '.join(ajenos)}")
        if len(set(participantes)) != len(participantes):
            motivos.append("participantes repetidos")
    return motivos


def limpiar_gastos(filas, grupo):
    """Separa las filas en gastos válidos y rechazados (con su motivo).

    Política: una fila con cualquier problema se rechaza entera y se informa.
    Si un id aparece repetido, se rechazan TODAS sus filas, porque no sabemos
    cuál es la correcta. No se modifica la lista original.
    """
    conteo_ids = {}
    for fila in filas:
        clave = fila["gasto_id"].strip()
        conteo_ids[clave] = conteo_ids.get(clave, 0) + 1
    ids_duplicados = {i for i, n in conteo_ids.items() if n > 1}

    validos, rechazados = [], []
    for fila in filas:
        motivos = _motivos_de_rechazo(fila, grupo, ids_duplicados)
        if motivos:
            rechazado = {c: fila[c] for c in COLUMNAS}
            rechazado["participantes"] = ";".join(fila["participantes"])
            rechazado["motivo"] = " | ".join(motivos)
            rechazados.append(rechazado)
        else:
            validos.append(Gasto(
                gasto_id=fila["gasto_id"].strip(),
                fecha=leer_fecha(fila["fecha"].strip()),
                descripcion=fila["descripcion"].strip(),
                pagador=fila["pagador"].strip(),
                monto_centavos=pesos_a_centavos(fila["monto"].strip()),
                participantes=tuple(fila["participantes"]),
                evento=fila["evento"].strip(),
                categoria=fila["categoria"].strip(),
            ))
    return validos, rechazados


# ---------- 3. filtrar ----------

def filtrar_periodo(gastos, desde=None, hasta=None):
    """Deja los gastos con fecha entre desde y hasta (ambas incluidas)."""
    if desde and hasta and desde > hasta:
        raise ErrorDatos(f"Período inválido: {desde} es posterior a {hasta}")
    return [
        g for g in gastos
        if (desde is None or g.fecha >= desde) and (hasta is None or g.fecha <= hasta)
    ]


def eventos_disponibles(gastos):
    """Nombres de los eventos, ordenados por la fecha de su primer gasto."""
    primero = {}
    for g in gastos:
        if g.evento not in primero or g.fecha < primero[g.evento]:
            primero[g.evento] = g.fecha
    return sorted(primero, key=lambda e: (primero[e], e))


def normalizar(texto):
    """'Córdoba ' -> 'cordoba': sin tildes, sin espacios de más y en minúsculas."""
    sin_tildes = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return sin_tildes.strip().lower()


def buscar_evento(gastos, texto):
    """Encuentra el evento que corresponde a lo que escribió la persona.

    Acepta el nombre completo o una parte, sin importar mayúsculas ni tildes:
    'bariloche' encuentra 'Viaje a Bariloche' y 'cordoba' encuentra
    'Finde largo en Córdoba'. Si el texto coincide con ninguno o con varios
    eventos, se informa con un error claro.
    """
    eventos = eventos_disponibles(gastos)
    buscado = normalizar(texto)
    exactos = [e for e in eventos if normalizar(e) == buscado]
    if exactos:
        return exactos[0]
    parciales = [e for e in eventos if buscado and buscado in normalizar(e)]
    if len(parciales) == 1:
        return parciales[0]
    if not parciales:
        raise ErrorDatos(f"No hay ningún evento que coincida con '{texto}'. "
                         f"Eventos: {', '.join(eventos)}")
    raise ErrorDatos(f"'{texto}' coincide con varios eventos: {', '.join(parciales)}. "
                     "Escribí una parte más específica del nombre.")


def filtrar_evento(gastos, evento=None):
    """Deja solo los gastos de un evento (None = todos)."""
    if evento is None:
        return list(gastos)
    nombre = buscar_evento(gastos, evento)
    return [g for g in gastos if g.evento == nombre]


# ---------- 4. calcular ----------

def calcular_resumen(grupo):
    """Tabla con lo pagado, lo consumido y el saldo de cada persona."""
    pagado = grupo.pagado_por_persona()
    consumido = grupo.consumido_por_persona()
    saldos = grupo.saldos()
    return [
        {
            "persona": p,
            "alias": grupo.alias_de(p),
            "pagado": pagado[p],
            "consumido": consumido[p],
            "saldo": saldos[p],
        }
        for p in grupo.integrantes
    ]


def detalle_persona(grupo, persona):
    """Gastos en los que una persona pagó o participó, con su parte."""
    if not grupo.es_integrante(persona):
        raise ErrorDatos(f"'{persona}' no pertenece al grupo. Integrantes: {', '.join(grupo.integrantes)}")
    detalle = []
    for gasto in grupo.gastos:
        cuota = gasto.cuota_por_persona().get(persona, 0)
        puso = gasto.monto_centavos if gasto.pagador == persona else 0
        if cuota or puso:
            detalle.append({
                "gasto_id": gasto.gasto_id,
                "fecha": gasto.fecha.isoformat(),
                "evento": gasto.evento,
                "descripcion": gasto.descripcion,
                "pago": puso,
                "su_parte": cuota,
            })
    return detalle


# ---------- 5. verificar ----------

def verificar_resultado(grupo, transferencias):
    """Comprueba propiedades que SIEMPRE deben cumplirse."""
    saldos = grupo.saldos()
    if sum(saldos.values()) != 0:
        raise ErrorVerificacion("Los saldos no suman cero")
    total_gastado = sum(g.monto_centavos for g in grupo.gastos)
    if sum(grupo.consumido_por_persona().values()) != total_gastado:
        raise ErrorVerificacion("Lo consumido no coincide con el total gastado")
    pendiente = dict(saldos)
    for deudor, acreedor, monto in transferencias:
        if monto <= 0:
            raise ErrorVerificacion("Hay una transferencia sin monto positivo")
        pendiente[deudor] += monto
        pendiente[acreedor] -= monto
    if any(pendiente.values()):
        raise ErrorVerificacion("Las transferencias no dejan a todos en cero")
    if len(transferencias) > max(len(grupo.integrantes) - 1, 0):
        raise ErrorVerificacion("Hay más transferencias que integrantes - 1")


# ---------- flujo completo ----------

def cargar_y_limpiar(fuente, nombre_grupo, integrantes):
    """Lee, valida y limpia. Devuelve (filas leídas, gastos válidos, rechazados)."""
    filas = fuente.cargar()
    validar_esquema(filas)
    grupo = Grupo(nombre_grupo, integrantes)
    validos, rechazados = limpiar_gastos(filas, grupo)
    if not validos:
        raise ErrorDatos("Ningún gasto superó la validación; revisar los rechazados")
    return filas, validos, rechazados


def calcular(nombre_grupo, integrantes, gastos):
    """Registra los gastos en un grupo nuevo, calcula y verifica el resultado."""
    if not gastos:
        raise ErrorDatos("No hay gastos para la selección pedida")
    grupo = Grupo(nombre_grupo, integrantes)
    for gasto in gastos:
        grupo.registrar(gasto)
    transferencias = grupo.transferencias()
    verificar_resultado(grupo, transferencias)
    return grupo, calcular_resumen(grupo), transferencias


def procesar(fuente, nombre_grupo, integrantes, desde=None, hasta=None, evento=None):
    """Ejecuta todo el flujo y devuelve un diccionario con los resultados."""
    filas, validos, rechazados = cargar_y_limpiar(fuente, nombre_grupo, integrantes)
    seleccionados = filtrar_periodo(filtrar_evento(validos, evento), desde, hasta)
    grupo, resumen, transferencias = calcular(nombre_grupo, integrantes, seleccionados)
    return {
        "grupo": grupo,
        "resumen": resumen,
        "transferencias": transferencias,
        "rechazados": rechazados,
        "validos": validos,
        "seleccionados": seleccionados,
        "evento": buscar_evento(validos, evento) if evento else None,
        "auditoria": {
            "filas_leidas": len(filas),
            "validas": len(validos),
            "rechazadas": len(rechazados),
            "en_periodo": len(seleccionados),
            "total_gastado": sum(g.monto_centavos for g in seleccionados),
        },
    }


# ---------- 6. guardar ----------

def _escribir_csv(ruta, columnas, filas):
    with ruta.open("w", encoding="utf-8", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=columnas)
        escritor.writeheader()
        escritor.writerows(filas)


def guardar_resultados(resultado, carpeta):
    """Escribe saldos.csv, transferencias.csv y rechazados.csv en la carpeta."""
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    grupo = resultado["grupo"]
    _escribir_csv(
        carpeta / "saldos.csv",
        ["persona", "alias", "pagado", "consumido", "saldo"],
        [
            {**fila, **{k: centavos_a_texto(fila[k]) for k in ("pagado", "consumido", "saldo")}}
            for fila in resultado["resumen"]
        ],
    )
    _escribir_csv(
        carpeta / "transferencias.csv",
        ["paga", "recibe", "alias_destino", "monto"],
        [
            {"paga": d, "recibe": a, "alias_destino": grupo.alias_de(a), "monto": centavos_a_texto(m)}
            for d, a, m in resultado["transferencias"]
        ],
    )
    _escribir_csv(carpeta / "rechazados.csv", COLUMNAS + ["motivo"], resultado["rechazados"])
    return carpeta
