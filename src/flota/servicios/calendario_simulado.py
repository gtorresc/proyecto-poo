"""Calendario controlado a mano: para demos, tests y la GUI sin internet."""
from datetime import date
from typing import Optional

from flota.servicios.proveedor_calendario import ProveedorCalendario


class CalendarioSimulado(ProveedorCalendario):
    """Todos los días son iguales: festivos con el nombre dado, o hábiles si es None."""

    def __init__(self, festivo: Optional[str] = None):
        self.configurar(festivo)

    def configurar(self, festivo: Optional[str]) -> None:
        self._festivo = festivo

    def festivo(self, fecha: date) -> Optional[str]:
        return self._festivo
