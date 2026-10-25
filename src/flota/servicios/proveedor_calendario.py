"""Contrato del calendario: cualquier fuente (real o simulada) dice si una fecha es festiva."""
from abc import ABC, abstractmethod
from datetime import date
from typing import Optional


class ProveedorCalendario(ABC):

    @abstractmethod
    def festivo(self, fecha: date) -> Optional[str]:
        """Nombre del festivo, o None si es un día hábil."""

    def es_festivo(self, fecha: date) -> bool:
        return self.festivo(fecha) is not None
