"""Clima real desde Open-Meteo. Cualquier fallo se convierte en un reporte no disponible."""
from typing import Optional

import requests

from flota.dominio.ubicacion import Ubicacion
from flota.servicios.proveedor_clima import ProveedorClima, ReporteClima, UmbralesClima

URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT_S = 5
CODIGOS_TORMENTA = range(95, 100)  # códigos WMO 95-99: tormenta eléctrica (con o sin granizo)


class ServicioClimaOpenMeteo(ProveedorClima):

    def __init__(self, umbrales: Optional[UmbralesClima] = None, timeout_s: float = TIMEOUT_S):
        super().__init__(umbrales)
        self._timeout_s = timeout_s

    def obtener_reporte(self, ubicacion: Ubicacion) -> ReporteClima:
        params = {
            "latitude": ubicacion.latitud, "longitude": ubicacion.longitud,
            "current": ("wind_speed_10m,wind_gusts_10m,temperature_2m,is_day,visibility,"
                        "weather_code,relative_humidity_2m,wind_direction_10m"),
            "hourly": "precipitation_probability", "forecast_days": 1, "timezone": "auto",
        }
        try:
            respuesta = requests.get(URL, params=params, timeout=self._timeout_s)
            respuesta.raise_for_status()
            return self._parsear_respuesta(respuesta.json())
        except (requests.RequestException, ValueError, KeyError, TypeError, IndexError, StopIteration):
            # fail-safe: sin datos confiables el dron no vuela (JSON roto cae aquí como ValueError)
            return ReporteClima.no_disponible()

    def _parsear_respuesta(self, datos: dict) -> ReporteClima:
        actual = datos["current"]
        hora = actual["time"][:13]  # "2026-10-21T09": la lluvia solo viene por hora
        indice = next(i for i, t in enumerate(datos["hourly"]["time"]) if t.startswith(hora))
        return ReporteClima(
            viento_kmh=actual["wind_speed_10m"], rafagas_kmh=actual["wind_gusts_10m"],
            prob_lluvia_pct=datos["hourly"]["precipitation_probability"][indice],
            es_de_dia=bool(actual["is_day"]), temperatura_c=actual["temperature_2m"],
            # .get: si el modelo no publica un dato llega null o no llega, y no es un error
            visibilidad_m=actual.get("visibility"),
            tormenta=actual.get("weather_code") in CODIGOS_TORMENTA,
            humedad_pct=actual.get("relative_humidity_2m"),
            direccion_viento_grados=actual.get("wind_direction_10m"),
        )
