"""Festivos: contrato, simulador, Nager.Date sin internet y la regla de la cafetería."""
from datetime import date

import pytest
import requests

from flota.asignacion.asignador import AsignadorEntregas
from flota.dominio.bitacora import Bitacora
from flota.dominio.carga import Alimento, Documento, Fragil, MaterialPeligroso
from flota.dominio.flota import Flota
from flota.dominio.robot import RobotRuedas
from flota.dominio.solicitud import EstadoSolicitud, SolicitudEntrega
from flota.dominio.ubicacion import Ubicacion, Zona
from flota.servicios import calendario_nager_date
from flota.servicios.calendario_nager_date import CACHE_FALLO_S, CalendarioNagerDate
from flota.servicios.calendario_simulado import CalendarioSimulado
from flota.servicios.clima_simulado import ServicioClimaSimulado
from flota.servicios.proveedor_calendario import ProveedorCalendario

CAFETERIA = Ubicacion("Zona de comidas - Ingenierías", 6.230213, -75.611780, Zona.EDIFICIO)
DERECHO = Ubicacion("Bloque 16 - Facultad de Derecho", 6.232422, -75.610368, Zona.EDIFICIO)
FESTIVOS_2026 = [
    {"date": "2026-01-01", "localName": "Año Nuevo"},
    {"date": "2026-10-12", "localName": "Día de la Raza"},
]


class RespuestaFalsa:
    def __init__(self, datos):
        self._datos = datos

    def raise_for_status(self):
        pass

    def json(self):
        return self._datos


@pytest.fixture
def llamadas(monkeypatch):
    """Reemplaza requests.get; cada elemento de la lista es una respuesta o una excepción."""
    respuestas, urls = [], []

    def falso_get(url, timeout):
        urls.append(url)
        r = respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r
    monkeypatch.setattr(calendario_nager_date.requests, "get", falso_get)
    return respuestas, urls


def test_proveedor_es_abstracto():
    with pytest.raises(TypeError):
        ProveedorCalendario()


def test_simulador():
    cal = CalendarioSimulado()
    assert not cal.es_festivo(date(2026, 10, 25))
    cal.configurar("Día de la Raza")
    assert cal.festivo(date(2026, 10, 25)) == "Día de la Raza" and cal.es_festivo(date(2026, 10, 25))


def test_nager_date_lee_los_festivos_y_consulta_una_vez_por_anio(llamadas):
    respuestas, urls = llamadas
    respuestas.append(RespuestaFalsa(FESTIVOS_2026))
    cal = CalendarioNagerDate()
    assert cal.festivo(date(2026, 10, 12)) == "Día de la Raza"
    assert cal.festivo(date(2026, 10, 13)) is None
    assert urls == ["https://date.nager.at/api/v3/PublicHolidays/2026/CO"]


@pytest.mark.parametrize("fallo", [requests.Timeout("lento"), requests.ConnectionError("sin red"),
                                   RespuestaFalsa([{"sin": "fecha"}]), RespuestaFalsa("no es lista")])
def test_si_nager_date_falla_es_dia_habil_y_se_reintenta(llamadas, fallo):
    respuestas, urls = llamadas
    respuestas.extend([fallo, RespuestaFalsa(FESTIVOS_2026)])
    ahora = [0.0]
    cal = CalendarioNagerDate(reloj=lambda: ahora[0])
    assert cal.festivo(date(2026, 1, 1)) is None  # supuesto S10
    ahora[0] += CACHE_FALLO_S - 1
    assert cal.festivo(date(2026, 1, 1)) is None and len(urls) == 1  # sin red no espera el timeout otra vez
    ahora[0] += 1
    assert cal.festivo(date(2026, 1, 1)) == "Año Nuevo"  # pasado el plazo, se reintenta
    assert len(urls) == 2


def test_solo_el_alimento_sale_de_la_cafeteria():
    """Polimorfismo: cada carga responde a requiere_cafeteria."""
    cargas = [Alimento("Almuerzo", 1, 60), Documento("Acta", 1), Fragil("Equipo", 1),
              MaterialPeligroso("Reactivo", 1, 2)]
    assert [c.requiere_cafeteria() for c in cargas] == [True, False, False, False]


@pytest.fixture
def asignador():
    flota = Flota()
    flota.agregar(RobotRuedas("R-02", CAFETERIA, tiene_control_temperatura=True))
    return AsignadorEntregas(flota, ServicioClimaSimulado(), Bitacora(), CalendarioSimulado("Día de la Raza"))


def test_en_festivo_el_alimento_queda_pendiente(asignador):
    s = SolicitudEntrega(CAFETERIA, DERECHO, Alimento("Almuerzo", 1.5, 60))
    assert not asignador.asignar(s)
    assert s.estado is EstadoSolicitud.PENDIENTE
    assert s.motivo == "cafetería cerrada (festivo: Día de la Raza)"


def test_en_festivo_un_documento_si_se_entrega(asignador):
    assert asignador.asignar(SolicitudEntrega(CAFETERIA, DERECHO, Documento("Acta", 1)))


def test_al_cambiar_el_calendario_la_pendiente_se_asigna(asignador):
    s = SolicitudEntrega(CAFETERIA, DERECHO, Alimento("Almuerzo", 1.5, 60))
    asignador.asignar(s)
    asignador.cambiar_calendario(CalendarioSimulado())  # mismo cambio en vivo que el clima
    assert asignador.reintentar_pendientes() == 1 and s.robot.id == "R-02"


def test_sin_calendario_no_hay_regla_de_festivos(asignador):
    asignador.cambiar_calendario(None)
    assert asignador.asignar(SolicitudEntrega(CAFETERIA, DERECHO, Alimento("Almuerzo", 1.5, 60)))
    with pytest.raises(TypeError):
        asignador.cambiar_calendario("no es un calendario")
