"""ServicioClimaOpenMeteo sin internet: requests.get se reemplaza con monkeypatch."""
import pytest
import requests

from flota.dominio.ubicacion import Ubicacion, Zona
from flota.servicios import clima_open_meteo
from flota.servicios.clima_open_meteo import ServicioClimaOpenMeteo

AZOTEA = Ubicacion("Azotea Bloque 13", 6.231948, -75.611169, Zona.AZOTEA)

JSON_EJEMPLO = {
    "current": {"time": "2026-10-21T09:30", "wind_speed_10m": 12.5, "wind_gusts_10m": 20.0,
                "temperature_2m": 24.1, "is_day": 1},
    "hourly": {"time": ["2026-10-21T08:00", "2026-10-21T09:00", "2026-10-21T10:00"],
               "precipitation_probability": [5, 35, 90]},
}


class RespuestaFalsa:
    def __init__(self, datos=None, error_http=False, json_roto=False):
        self._datos, self._error_http, self._json_roto = datos, error_http, json_roto

    def raise_for_status(self):
        if self._error_http:
            raise requests.HTTPError("500")

    def json(self):
        if self._json_roto:
            raise ValueError("no es JSON")
        return self._datos


def simular(monkeypatch, respuesta=None, excepcion=None):
    def falso_get(url, params, timeout):
        if excepcion:
            raise excepcion
        return respuesta
    monkeypatch.setattr(clima_open_meteo.requests, "get", falso_get)


def test_lee_el_json_de_ejemplo(monkeypatch):
    simular(monkeypatch, RespuestaFalsa(JSON_EJEMPLO))
    r = ServicioClimaOpenMeteo().obtener_reporte(AZOTEA)
    assert r.disponible and r.es_de_dia
    assert (r.viento_kmh, r.rafagas_kmh, r.temperatura_c) == (12.5, 20.0, 24.1)
    assert r.prob_lluvia_pct == 35  # la hora actual es las 09:xx


def test_con_buen_clima_el_dron_puede_volar(monkeypatch):
    simular(monkeypatch, RespuestaFalsa(JSON_EJEMPLO))
    assert ServicioClimaOpenMeteo().condiciones_favorables(AZOTEA)


@pytest.mark.parametrize("respuesta, excepcion", [
    (None, requests.Timeout("lento")),
    (None, requests.ConnectionError("sin internet")),
    (RespuestaFalsa(error_http=True), None),
    (RespuestaFalsa(json_roto=True), None),
    (RespuestaFalsa({"current": {}}), None),
    (RespuestaFalsa({"current": {"time": "2026-10-21T23:00"}, "hourly": {"time": []}}), None),
])
def test_cualquier_fallo_deja_el_clima_no_disponible(monkeypatch, respuesta, excepcion):
    simular(monkeypatch, respuesta, excepcion)
    servicio = ServicioClimaOpenMeteo()
    assert not servicio.obtener_reporte(AZOTEA).disponible
    assert not servicio.condiciones_favorables(AZOTEA)
