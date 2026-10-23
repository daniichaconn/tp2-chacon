"""Modelo del dominio: un gasto compartido y el grupo que lo comparte.

Todos los importes se manejan en CENTAVOS (números enteros) para evitar
los errores de redondeo de los float (por ejemplo, 0.1 + 0.2 != 0.3).
"""

import re
from dataclasses import dataclass
from datetime import date

# Alias de Mercado Pago / transferencias: entre 6 y 20 caracteres,
# solo letras minúsculas, números, puntos y guiones.
PATRON_ALIAS = re.compile(r"[a-z0-9.\-]{6,20}")


class ErrorDatos(Exception):
    """Error en los datos de entrada que impide continuar el análisis."""


@dataclass(frozen=True)
class Gasto:
    """Un gasto pagado por una persona y repartido en partes iguales."""

    gasto_id: str
    fecha: date
    descripcion: str
    pagador: str
    monto_centavos: int
    participantes: tuple

    def __post_init__(self):
        if self.monto_centavos <= 0:
            raise ValueError("El monto debe ser mayor que cero")
        if len(self.participantes) == 0:
            raise ValueError("El gasto debe tener al menos un participante")
        if len(set(self.participantes)) != len(self.participantes):
            raise ValueError("Hay participantes repetidos")

    def cuota_por_persona(self):
        """Devuelve {persona: centavos} con lo que le toca pagar a cada una.

        Si el monto no se divide justo, los centavos que sobran se asignan
        de a uno a los primeros participantes en orden alfabético.
        Así la suma de las cuotas es SIEMPRE igual al monto.
        """
        personas = sorted(self.participantes)
        base, resto = divmod(self.monto_centavos, len(personas))
        return {p: base + (1 if i < resto else 0) for i, p in enumerate(personas)}


class Grupo:
    """Un grupo de personas que comparten gastos.

    Guarda los gastos registrados y calcula cuánto pagó y cuánto consumió
    cada integrante, su saldo final y las transferencias para saldar deudas.
    """

    def __init__(self, nombre, integrantes):
        """integrantes: diccionario {nombre: alias para transferir}."""
        if len(integrantes) < 2:
            raise ErrorDatos("Un grupo necesita al menos dos integrantes")
        for persona, alias in integrantes.items():
            if not PATRON_ALIAS.fullmatch(alias):
                raise ErrorDatos(
                    f"Alias inválido para {persona}: '{alias}' "
                    "(6 a 20 caracteres: minúsculas, números, '.' o '-')"
                )
        self.nombre = nombre
        self._integrantes = dict(integrantes)
        self._gastos = []

    @property
    def integrantes(self):
        return sorted(self._integrantes)

    @property
    def gastos(self):
        return list(self._gastos)

    def alias_de(self, persona):
        return self._integrantes[persona]

    def es_integrante(self, persona):
        return persona in self._integrantes

    def registrar(self, gasto):
        """Agrega un gasto; todas las personas deben pertenecer al grupo."""
        personas = {gasto.pagador, *gasto.participantes}
        desconocidas = sorted(p for p in personas if not self.es_integrante(p))
        if desconocidas:
            raise ErrorDatos(f"Personas fuera del grupo: {', '.join(desconocidas)}")
        self._gastos.append(gasto)

    def pagado_por_persona(self):
        """{persona: centavos que puso de su bolsillo}."""
        pagado = {p: 0 for p in self.integrantes}
        for gasto in self._gastos:
            pagado[gasto.pagador] += gasto.monto_centavos
        return pagado

    def consumido_por_persona(self):
        """{persona: centavos que le corresponde pagar por lo que consumió}."""
        consumido = {p: 0 for p in self.integrantes}
        for gasto in self._gastos:
            for persona, cuota in gasto.cuota_por_persona().items():
                consumido[persona] += cuota
        return consumido

    def saldos(self):
        """{persona: pagado - consumido}.

        Positivo: el grupo le debe plata. Negativo: debe plata al grupo.
        La suma de todos los saldos es siempre 0.
        """
        pagado = self.pagado_por_persona()
        consumido = self.consumido_por_persona()
        return {p: pagado[p] - consumido[p] for p in self.integrantes}

    def transferencias(self):
        """Lista de transferencias (deudor, acreedor, centavos) que saldan todo.

        Método: en cada paso, la persona que más debe le paga a la que más
        tiene que cobrar, por el menor de los dos importes. Cada paso deja
        al menos a una persona en cero, así que con n personas se necesitan
        como máximo n - 1 transferencias.
        """
        deudores = {p: -s for p, s in self.saldos().items() if s < 0}
        acreedores = {p: s for p, s in self.saldos().items() if s > 0}
        resultado = []
        while deudores and acreedores:
            # max con desempate por nombre para que el resultado sea reproducible
            deudor = max(deudores, key=lambda p: (deudores[p], p))
            acreedor = max(acreedores, key=lambda p: (acreedores[p], p))
            monto = min(deudores[deudor], acreedores[acreedor])
            resultado.append((deudor, acreedor, monto))
            deudores[deudor] -= monto
            acreedores[acreedor] -= monto
            if deudores[deudor] == 0:
                del deudores[deudor]
            if acreedores[acreedor] == 0:
                del acreedores[acreedor]
        return resultado
