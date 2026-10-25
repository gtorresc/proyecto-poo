"""Despacho manual: el operador elige el robot y el sistema explica por qué no puede."""
import pytest

from flota.asignacion.asignador import AsignadorEntregas
from flota.dominio.bitacora import Bitacora, TipoEvento
from flota.dominio.carga import Alimento, Documento, Fragil
from flota.dominio.estado_robot import EstadoRobot
from flota.dominio.flota import Flota
from flota.dominio.robot import Dron, RobotOrugas, RobotRuedas
from flota.dominio.solicitud import EstadoSolicitud, SolicitudEntrega
from flota.dominio.ubicacion import Ubicacion, Zona
from flota.servicios.calendario_simulado import CalendarioSimulado
from flota.servicios.clima_simulado import ServicioClimaSimulado

ESTACION = Ubicacion("Bloque 20 - Servicios generales", 6.231081, -75.612645, Zona.EDIFICIO)
CAFETERIA = Ubicacion("Zona de comidas - Ingenierías", 6.230213, -75.611780, Zona.EDIFICIO)
BIBLIOTECA = Ubicacion("Bloque 13 - Biblioteca", 6.231948, -75.611169, Zona.EDIFICIO)
AZOTEA = Ubicacion("Azotea Bloque 11", 6.231989, -75.612080, Zona.AZOTEA)


@pytest.fixture
def entorno():
    flota, bitacora, clima = Flota(), Bitacora(), ServicioClimaSimulado()
    for robot in (RobotRuedas("R-01", ESTACION), RobotOrugas("O-01", ESTACION), Dron("D-01", ESTACION)):
        flota.agregar(robot)
    return flota, bitacora, clima, AsignadorEntregas(flota, clima, bitacora)


@pytest.mark.parametrize("robot, solicitud, motivo", [
    (RobotRuedas("R-01", ESTACION, carga_maxima_kg=5),
     SolicitudEntrega(CAFETERIA, BIBLIOTECA, Documento("Cajas", 8)), "sobrepeso: 8 kg > 5 kg"),
    (RobotRuedas("R-01", ESTACION),
     SolicitudEntrega(CAFETERIA, AZOTEA, Documento("Acta", 1)), "R-01 no llega a Azotea Bloque 11 (azotea)"),
    (RobotOrugas("O-01", ESTACION),
     SolicitudEntrega(CAFETERIA, BIBLIOTECA, Fragil("Microscopio", 2)), "carga incompatible: Fragil en O-01"),
    (RobotRuedas("R-01", ESTACION, nivel_bateria=16),
     SolicitudEntrega(CAFETERIA, BIBLIOTECA, Documento("Acta", 1)), "batería insuficiente: 16 %"),
])
def test_motivo_rechazo_nombra_la_regla_que_falla(robot, solicitud, motivo):
    assert robot.motivo_rechazo(solicitud) == motivo
    assert not robot.puede_atender(solicitud)


def test_robot_ocupado_y_robot_apto():
    robot = RobotRuedas("R-01", ESTACION)
    solicitud = SolicitudEntrega(CAFETERIA, BIBLIOTECA, Documento("Acta", 1))
    assert robot.motivo_rechazo(solicitud) is None and robot.puede_atender(solicitud)
    robot.cargar(Documento("Otra", 1))
    assert robot.motivo_rechazo(solicitud) == "R-01 no está disponible (en ruta)"


def test_el_operador_puede_elegir_un_robot_mas_caro(entorno):
    flota, _, _, asignador = entorno
    s = SolicitudEntrega(CAFETERIA, BIBLIOTECA, Documento("Tesis", 1))
    assert asignador.despachar(s, flota.buscar("O-01")) == (True, "")
    assert s.robot.id == "O-01" and s.estado is EstadoSolicitud.ASIGNADA
    assert s in asignador.en_curso and flota.buscar("O-01").estado is EstadoRobot.EN_RUTA


def test_dron_con_tormenta_se_rechaza_y_se_puede_elegir_otro(entorno):
    flota, bitacora, clima, asignador = entorno
    clima.configurar(viento=10, rafagas=15, lluvia=10, dia=True, tormenta=True)
    s = SolicitudEntrega(CAFETERIA, BIBLIOTECA, Documento("Tesis", 1))
    assert asignador.despachar(s, flota.buscar("D-01")) == (False, "clima desfavorable: tormenta eléctrica")
    assert s.estado is EstadoSolicitud.PENDIENTE and s.motivo.startswith("clima")
    assert s not in asignador.pendientes  # sigue esperando al operador, no al reintento automático
    assert [e.tipo for e in bitacora.eventos()][-2:] == [TipoEvento.RECHAZO_CLIMA, TipoEvento.DESPACHO_RECHAZADO]
    assert asignador.despachar(s, flota.buscar("R-01"))[0]


def test_regla_de_robot_tambien_queda_en_la_bitacora(entorno):
    flota, bitacora, _, asignador = entorno
    s = SolicitudEntrega(CAFETERIA, AZOTEA, Documento("Acta", 1))
    ok, motivo = asignador.despachar(s, flota.buscar("R-01"))
    assert not ok and "no llega" in motivo
    assert bitacora.filtrar(TipoEvento.DESPACHO_RECHAZADO)[-1].robot_id == "R-01"


def test_despachar_una_pendiente_la_saca_de_los_reintentos(entorno):
    flota, _, clima, asignador = entorno
    clima.configurar(viento=60, rafagas=70, lluvia=10, dia=True)
    s = SolicitudEntrega(CAFETERIA, AZOTEA, Documento("Acta", 1))  # solo el dron llega a la azotea
    assert not asignador.asignar(s) and s in asignador.pendientes
    clima.configurar(viento=10, rafagas=15, lluvia=10, dia=True)
    assert asignador.despachar(s, flota.buscar("D-01"))[0]
    assert s not in asignador.pendientes


def test_el_festivo_aplica_tambien_al_despacho_manual(entorno):
    flota, _, _, asignador = entorno
    flota.agregar(RobotRuedas("R-02", ESTACION, tiene_control_temperatura=True))
    asignador.cambiar_calendario(CalendarioSimulado("Día de la Raza"))
    s = SolicitudEntrega(CAFETERIA, BIBLIOTECA, Alimento("Almuerzo", 1, 60))
    assert asignador.despachar(s, flota.buscar("R-02")) == (False, "cafetería cerrada (festivo: Día de la Raza)")


def test_no_se_despacha_un_robot_ajeno_a_la_flota(entorno):
    _, _, _, asignador = entorno
    with pytest.raises(ValueError):
        asignador.despachar(SolicitudEntrega(CAFETERIA, BIBLIOTECA, Documento("Acta", 1)),
                            RobotRuedas("R-99", ESTACION))
