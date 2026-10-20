"""Solicitud de entrega y su ciclo de vida: pendiente -> asignada -> entregada/fallida."""
from enum import Enum
from itertools import count
from typing import Optional

from flota.dominio.carga import Carga
from flota.dominio.ubicacion import Ubicacion

_ids = count(1)


class EstadoSolicitud(Enum):
    PENDIENTE = "pendiente"
    ASIGNADA = "asignada"
    ENTREGADA = "entregada"
    FALLIDA = "fallida"


class SolicitudEntrega:

    def __init__(self, origen: Ubicacion, destino: Ubicacion, carga: Carga):
        if not isinstance(origen, Ubicacion) or not isinstance(destino, Ubicacion):
            raise TypeError("Origen y destino deben ser Ubicacion")
        if not isinstance(carga, Carga):
            raise TypeError("La carga debe ser una Carga")
        if origen is destino:
            raise ValueError("El origen y el destino no pueden ser el mismo lugar")
        self._id = next(_ids)
        self._origen = origen
        self._destino = destino
        self._carga = carga
        self._estado = EstadoSolicitud.PENDIENTE
        self._robot = None
        self._costo = 0.0
        self._tiempo_min = 0.0
        self._motivo = ""

    @property
    def id(self) -> int:
        return self._id

    @property
    def origen(self) -> Ubicacion:
        return self._origen

    @property
    def destino(self) -> Ubicacion:
        return self._destino

    @property
    def carga(self) -> Carga:
        return self._carga

    @property
    def estado(self) -> EstadoSolicitud:
        return self._estado

    @property
    def robot(self) -> Optional[object]:
        return self._robot

    @property
    def costo(self) -> float:
        return self._costo

    @property
    def tiempo_min(self) -> float:
        return self._tiempo_min

    @property
    def motivo(self) -> str:
        return self._motivo

    # --- Transiciones: solo se permiten las del ciclo de vida -------------
    def _exigir(self, *permitidos: EstadoSolicitud) -> None:
        if self._estado not in permitidos:
            raise ValueError(f"Solicitud {self._id}: no se puede pasar de {self._estado.value}")

    def asignar(self, robot, costo: float, tiempo_min: float) -> None:
        self._exigir(EstadoSolicitud.PENDIENTE)
        if costo < 0 or tiempo_min < 0:
            raise ValueError("Costo y tiempo no pueden ser negativos")
        self._robot = robot
        self._costo = float(costo)
        self._tiempo_min = float(tiempo_min)
        self._motivo = ""
        self._estado = EstadoSolicitud.ASIGNADA

    def marcar_pendiente(self, motivo: str) -> None:
        self._exigir(EstadoSolicitud.PENDIENTE)  # repetir el motivo en cada reintento es válido
        self._motivo = motivo

    def marcar_entregada(self) -> None:
        self._exigir(EstadoSolicitud.ASIGNADA)
        self._estado = EstadoSolicitud.ENTREGADA

    def marcar_fallida(self, motivo: str) -> None:
        self._exigir(EstadoSolicitud.PENDIENTE, EstadoSolicitud.ASIGNADA)
        self._motivo = motivo
        self._estado = EstadoSolicitud.FALLIDA

    def __repr__(self) -> str:
        return f"SolicitudEntrega(#{self._id}, {self._estado.value})"
