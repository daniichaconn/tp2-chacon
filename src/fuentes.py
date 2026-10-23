"""Fuentes de datos: leen los gastos desde CSV o JSON.

Contrato común de cargar(): devuelve una LISTA DE DICCIONARIOS, uno por gasto,
con las claves de COLUMNAS. Todos los valores son texto, salvo
"participantes", que es una lista de nombres.
Así, el resto del programa no necesita saber de qué formato vino el dato.
"""

import csv
import json
from abc import ABC, abstractmethod
from pathlib import Path

from dominio import ErrorDatos

COLUMNAS = ["gasto_id", "fecha", "evento", "categoria", "descripcion",
            "pagador", "monto", "participantes"]
SEPARADOR_PARTICIPANTES = ";"


class FuenteDatos(ABC):
    """Clase base: guarda la ruta del archivo y define el método cargar()."""

    def __init__(self, ruta):
        self._ruta = Path(ruta)

    @property
    def ruta(self):
        return self._ruta

    def _verificar_que_existe(self):
        if not self._ruta.is_file():
            raise FileNotFoundError(f"No existe el archivo de datos: {self._ruta}")

    @abstractmethod
    def cargar(self):
        """Devuelve la lista de gastos en la representación común."""


class FuenteCSV(FuenteDatos):
    """Lee un CSV con encabezados. Los participantes van separados por ';'."""

    def cargar(self):
        self._verificar_que_existe()
        with self._ruta.open(encoding="utf-8", newline="") as archivo:
            lector = csv.DictReader(archivo)
            if lector.fieldnames is None:
                raise ErrorDatos(f"El CSV está vacío: {self._ruta}")
            filas = []
            for fila in lector:
                texto = fila.get("participantes") or ""
                fila["participantes"] = [
                    p.strip() for p in texto.split(SEPARADOR_PARTICIPANTES) if p.strip()
                ]
                filas.append(fila)
        return filas


class FuenteJSON(FuenteDatos):
    """Lee un JSON que debe ser una lista de objetos (un objeto por gasto)."""

    def cargar(self):
        self._verificar_que_existe()
        with self._ruta.open(encoding="utf-8") as archivo:
            try:
                contenido = json.load(archivo)
            except json.JSONDecodeError as error:
                raise ErrorDatos(f"JSON mal formado en {self._ruta}: {error}") from error
        if not isinstance(contenido, list) or not all(isinstance(x, dict) for x in contenido):
            raise ErrorDatos("El JSON debe ser una lista de objetos, uno por gasto")
        filas = []
        for objeto in contenido:
            fila = {}
            for clave, valor in objeto.items():
                if clave == "participantes":
                    if not isinstance(valor, list):
                        valor = []  # se rechazará luego por no tener participantes
                    fila[clave] = [str(p).strip() for p in valor if str(p).strip()]
                else:
                    fila[clave] = "" if valor is None else str(valor)
            filas.append(fila)
        return filas


def crear_fuente(ruta):
    """Elige la fuente adecuada según la extensión del archivo."""
    extension = Path(ruta).suffix.lower()
    if extension == ".csv":
        return FuenteCSV(ruta)
    if extension == ".json":
        return FuenteJSON(ruta)
    raise ErrorDatos(f"Formato no soportado: '{extension}' (usar .csv o .json)")


def cargar_grupo(ruta):
    """Lee la configuración del grupo: {"nombre": ..., "integrantes": {nombre: alias}}."""
    ruta = Path(ruta)
    if not ruta.is_file():
        raise FileNotFoundError(f"No existe el archivo del grupo: {ruta}")
    with ruta.open(encoding="utf-8") as archivo:
        try:
            config = json.load(archivo)
        except json.JSONDecodeError as error:
            raise ErrorDatos(f"JSON mal formado en {ruta}: {error}") from error
    if not isinstance(config, dict) or not isinstance(config.get("integrantes"), dict):
        raise ErrorDatos("El grupo debe tener 'nombre' e 'integrantes' {nombre: alias}")
    return config.get("nombre", "Grupo sin nombre"), config["integrantes"]
