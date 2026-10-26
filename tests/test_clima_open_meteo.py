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


def test_lee_visibilidad_tormenta_humedad_y_direccion(monkeypatch):
    datos = {**JSON_EJEMPLO, "current": {**JSON_EJEMPLO["current"], "visibility": 2960.0,
                                         "weather_code": 95, "relative_humidity_2m": 92,
                                         "wind_direction_10m": 235}}
    simular(monkeypatch, RespuestaFalsa(datos))
    r = ServicioClimaOpenMeteo().obtener_reporte(AZOTEA)
    assert (r.visibilidad_m, r.tormenta, r.humedad_pct, r.direccion_viento_grados) == (2960.0, True, 92, 235)
    assert r.es_favorable(ServicioClimaOpenMeteo().umbrales) == (False, "tormenta eléctrica")


def test_si_faltan_los_datos_nuevos_no_es_un_error(monkeypatch):
    datos = {**JSON_EJEMPLO, "current": {**JSON_EJEMPLO["current"], "visibility": None, "weather_code": 81}}
    simular(monkeypatch, RespuestaFalsa(datos))
    r = ServicioClimaOpenMeteo().obtener_reporte(AZOTEA)
    assert r.disponible and r.visibilidad_m is None and not r.tormenta and r.humedad_pct is None


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


def test_dos_consultas_seguidas_hacen_una_sola_peticion(monkeypatch):
    pedidos = []

    def falso_get(url, params, timeout):
        pedidos.append(params["latitude"])
        return RespuestaFalsa(JSON_EJEMPLO)
    monkeypatch.setattr(clima_open_meteo.requests, "get", falso_get)
    reloj = [1000.0]
    servicio = ServicioClimaOpenMeteo(reloj=lambda: reloj[0])
    vecina = Ubicacion("Azotea vecina", 6.2321, -75.6114, Zona.AZOTEA)  # misma zona de ~1 km
    assert servicio.obtener_reporte(AZOTEA).disponible and servicio.obtener_reporte(vecina).disponible
    assert len(pedidos) == 1
    reloj[0] += clima_open_meteo.CACHE_S
    servicio.obtener_reporte(AZOTEA)  # venció: se consulta otra vez
    assert len(pedidos) == 2


def test_sin_red_tampoco_espera_el_timeout_en_cada_consulta(monkeypatch):
    intentos = []

    def sin_red(url, params, timeout):
        intentos.append(1)
        raise requests.ConnectionError("sin internet")
    monkeypatch.setattr(clima_open_meteo.requests, "get", sin_red)
    reloj = [0.0]
    servicio = ServicioClimaOpenMeteo(reloj=lambda: reloj[0])
    for _ in range(5):
        assert not servicio.obtener_reporte(AZOTEA).disponible
    assert len(intentos) == 1
    reloj[0] += clima_open_meteo.CACHE_FALLO_S  # pasado el plazo se reintenta
    servicio.obtener_reporte(AZOTEA)
    assert len(intentos) == 2

