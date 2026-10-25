"""Festivos reales de Colombia desde Nager.Date. Un fallo se toma como día hábil."""
from datetime import date
from typing import Optional

import requests

from flota.servicios.proveedor_calendario import ProveedorCalendario

URL = "https://date.nager.at/api/v3/PublicHolidays/{anio}/{pais}"
TIMEOUT_S = 5


class CalendarioNagerDate(ProveedorCalendario):

    def __init__(self, pais: str = "CO", timeout_s: float = TIMEOUT_S):
        self._pais = pais
        self._timeout_s = timeout_s
        self._por_anio: dict[int, dict[date, str]] = {}  # una consulta por año, no por solicitud

    def festivo(self, fecha: date) -> Optional[str]:
        if fecha.year not in self._por_anio:
            festivos = self._consultar(fecha.year)
            if festivos is None:
                # supuesto S10: sin datos se atiende normal; equivocarse solo deja un almuerzo sin vender
                return None
            self._por_anio[fecha.year] = festivos  # los fallos no se guardan: se reintenta luego
        return self._por_anio[fecha.year].get(fecha)

    def _consultar(self, anio: int) -> Optional[dict[date, str]]:
        try:
            respuesta = requests.get(URL.format(anio=anio, pais=self._pais), timeout=self._timeout_s)
            respuesta.raise_for_status()
            return {date.fromisoformat(f["date"]): f["localName"] for f in respuesta.json()}
        except (requests.RequestException, ValueError, KeyError, TypeError):
            return None
