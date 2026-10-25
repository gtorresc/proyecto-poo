"""Bitácora: registro inmutable de lo que pasa en la flota."""
from datetime import datetime
from enum import Enum
from typing import Optional


class TipoEvento(Enum):
    ENTREGA_EXITOSA = "entrega exitosa"
    ENTREGA_FALLIDA = "entrega fallida"
    RECHAZO_CLIMA = "rechazo por clima"
    SOLICITUD_PENDIENTE = "solicitud pendiente"
    MANTENIMIENTO = "mantenimiento"
    DESPACHO_RECHAZADO = "despacho rechazado"


class EventoBitacora:

    def __init__(self, tipo: TipoEvento, mensaje: str, robot_id: Optional[str] = None,
                 fecha: Optional[datetime] = None):
        if not isinstance(tipo, TipoEvento):
            raise TypeError("El tipo debe ser un TipoEvento")
        if not mensaje or not mensaje.strip():
            raise ValueError("El evento necesita un mensaje")
        self._fecha = fecha or datetime.now()
        self._tipo = tipo
        self._mensaje = mensaje.strip()
        self._robot_id = robot_id

    @property
    def fecha(self) -> datetime:
        return self._fecha

    @property
    def tipo(self) -> TipoEvento:
        return self._tipo

    @property
    def mensaje(self) -> str:
        return self._mensaje

    @property
    def robot_id(self) -> Optional[str]:
        return self._robot_id

    def como_texto(self) -> str:
        robot = f" [{self._robot_id}]" if self._robot_id else ""
        return f"{self._fecha:%Y-%m-%d %H:%M:%S} {self._tipo.value.upper()}{robot}: {self._mensaje}"


class Bitacora:

    def __init__(self):
        self._eventos: list[EventoBitacora] = []

    def registrar(self, tipo: TipoEvento, mensaje: str, robot_id: Optional[str] = None) -> None:
        self._eventos.append(EventoBitacora(tipo, mensaje, robot_id))

    def eventos(self) -> tuple[EventoBitacora, ...]:
        return tuple(self._eventos)  # copia: solo se escribe con registrar

    def filtrar(self, tipo: TipoEvento) -> list[EventoBitacora]:
        return [e for e in self._eventos if e.tipo is tipo]

    def generar_reporte(self) -> str:
        resumen = [f"{t.value}: {len(self.filtrar(t))}" for t in TipoEvento]
        lineas = [e.como_texto() for e in self._eventos] or ["(sin eventos)"]
        return "\n".join(["REPORTE DE LA FLOTA", *resumen, "", *lineas])
