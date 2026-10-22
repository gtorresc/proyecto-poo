"""Contrato del clima: cualquier fuente (real o simulada) entrega un ReporteClima."""
from abc import ABC, abstractmethod
from typing import Optional

from flota.dominio.ubicacion import Ubicacion


class UmbralesClima:
    """Límites del supuesto S1; se pasan al proveedor para no atarlos a ninguna API."""

    def __init__(self, viento_max_kmh: float = 30, rafagas_max_kmh: float = 40,
                 lluvia_max_pct: float = 50):
        if min(viento_max_kmh, rafagas_max_kmh, lluvia_max_pct) < 0:
            raise ValueError("Los umbrales no pueden ser negativos")
        self._viento_max_kmh = float(viento_max_kmh)
        self._rafagas_max_kmh = float(rafagas_max_kmh)
        self._lluvia_max_pct = float(lluvia_max_pct)

    @property
    def viento_max_kmh(self) -> float:
        return self._viento_max_kmh

    @property
    def rafagas_max_kmh(self) -> float:
        return self._rafagas_max_kmh

    @property
    def lluvia_max_pct(self) -> float:
        return self._lluvia_max_pct


class ReporteClima:

    def __init__(self, viento_kmh: float, rafagas_kmh: float, prob_lluvia_pct: float,
                 es_de_dia: bool, disponible: bool = True, temperatura_c: Optional[float] = None):
        if min(viento_kmh, rafagas_kmh) < 0 or not 0 <= prob_lluvia_pct <= 100:
            raise ValueError("Valores de clima fuera de rango")
        self._viento_kmh = float(viento_kmh)
        self._rafagas_kmh = float(rafagas_kmh)
        self._prob_lluvia_pct = float(prob_lluvia_pct)
        self._es_de_dia = es_de_dia
        self._disponible = disponible
        self._temperatura_c = temperatura_c

    @classmethod
    def no_disponible(cls) -> "ReporteClima":
        return cls(0, 0, 0, False, disponible=False)

    @property
    def viento_kmh(self) -> float:
        return self._viento_kmh

    @property
    def rafagas_kmh(self) -> float:
        return self._rafagas_kmh

    @property
    def prob_lluvia_pct(self) -> float:
        return self._prob_lluvia_pct

    @property
    def es_de_dia(self) -> bool:
        return self._es_de_dia

    @property
    def disponible(self) -> bool:
        return self._disponible

    @property
    def temperatura_c(self) -> Optional[float]:
        return self._temperatura_c

    def es_favorable(self, umbrales: UmbralesClima) -> tuple[bool, str]:
        """Sin datos nunca es favorable: ante la duda, el dron no vuela."""
        if not self._disponible:
            return False, "clima no disponible"
        if not self._es_de_dia:
            return False, "es de noche"
        if self._viento_kmh > umbrales.viento_max_kmh:
            return False, f"viento {self._viento_kmh:.0f} km/h > {umbrales.viento_max_kmh:.0f}"
        if self._rafagas_kmh > umbrales.rafagas_max_kmh:
            return False, f"ráfagas {self._rafagas_kmh:.0f} km/h > {umbrales.rafagas_max_kmh:.0f}"
        if self._prob_lluvia_pct > umbrales.lluvia_max_pct:
            return False, f"lluvia {self._prob_lluvia_pct:.0f} % > {umbrales.lluvia_max_pct:.0f} %"
        return True, "condiciones favorables"


class ProveedorClima(ABC):

    def __init__(self, umbrales: Optional[UmbralesClima] = None):
        self._umbrales = umbrales or UmbralesClima()

    @property
    def umbrales(self) -> UmbralesClima:
        return self._umbrales

    @abstractmethod
    def obtener_reporte(self, ubicacion: Ubicacion) -> ReporteClima:
        ...

    def condiciones_favorables(self, ubicacion: Ubicacion) -> bool:
        return self.obtener_reporte(ubicacion).es_favorable(self._umbrales)[0]
