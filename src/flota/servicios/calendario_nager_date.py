"""Festivos reales de Colombia desde Nager.Date. Un fallo se toma como día hábil."""
import time
from datetime import date
from typing import Callable, Optional

import requests

from flota.servicios.proveedor_calendario import ProveedorCalendario

URL = "https://date.nager.at/api/v3/PublicHolidays/{anio}/{pais}"
TIMEOUT_S = 5
CACHE_FALLO_S = 30  # sin red, no esperar el timeout en cada pedido de comida (como el clima)


class CalendarioNagerDate(ProveedorCalendario):

    def __init__(self, pais: str = "CO", timeout_s: float = TIMEOUT_S,
                 reloj: Callable[[], float] = time.monotonic):
        self._pais = pais
        self._timeout_s = timeout_s
        self._reloj = reloj
        self._por_anio: dict[int, dict[date, str]] = {}  # una consulta por año, no por solicitud
        self._reintentar_en = float("-inf")  # tras un fallo, no se vuelve a consultar antes de este instante

    def festivo(self, fecha: date) -> Optional[str]:
        if fecha.year not in self._por_anio:
            # supuesto S10: sin datos se atiende normal; equivocarse solo deja un almuerzo sin vender
            if self._reloj() < self._reintentar_en:
                return None
            festivos = self._consultar(fecha.year)
            if festivos is None:
                self._reintentar_en = self._reloj() + CACHE_FALLO_S
                return None
            self._por_anio[fecha.year] = festivos  # el fallo solo se recuerda CACHE_FALLO_S: luego se reintenta
        return self._por_anio[fecha.year].get(fecha)

    def _consultar(self, anio: int) -> Optional[dict[date, str]]:
        try:
            respuesta = requests.get(URL.format(anio=anio, pais=self._pais), timeout=self._timeout_s)
            respuesta.raise_for_status()
            return {date.fromisoformat(f["date"]): f["localName"] for f in respuesta.json()}
        except (requests.RequestException, ValueError, KeyError, TypeError):
            return None
