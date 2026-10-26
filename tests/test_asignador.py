"""AsignadorEntregas: robot más barato y consulta de clima."""
import pytest

from flota.asignacion.asignador import DURACION_MANTENIMIENTO_S, AsignadorEntregas
from flota.dominio.bitacora import Bitacora, TipoEvento
from flota.dominio.carga import Alimento, Documento
from flota.dominio.estado_robot import EstadoRobot
from flota.dominio.flota import Flota
from flota.dominio.robot import Dron, RobotOrugas, RobotRuedas
from flota.dominio.solicitud import EstadoSolicitud, SolicitudEntrega
from flota.dominio.ubicacion import Ubicacion, Zona
from flota.servicios.clima_simulado import ServicioClimaSimulado
from flota.servicios.proveedor_clima import ProveedorClima

ESTACION = Ubicacion("Bloque 20 - Servicios generales", 6.231081, -75.612645, Zona.EDIFICIO)
CAFETERIA = Ubicacion("Zona de comidas - Ingenierías", 6.230213, -75.611780, Zona.EDIFICIO)
BIBLIOTECA = Ubicacion("Bloque 13 - Biblioteca", 6.231948, -75.611169, Zona.EDIFICIO)
JARDIN = Ubicacion("Jardín central", 6.231500, -75.611900, Zona.ZONA_VERDE)
AZOTEA = Ubicacion("Azotea Bloque 13", 6.231948, -75.611169, Zona.AZOTEA)


class ClimaQueNoSeDebeConsultar(ProveedorClima):
    def obtener_reporte(self, ubicacion):
        raise AssertionError("un robot terrestre no necesita clima")


@pytest.fixture
def entorno():
    flota, bitacora, clima = Flota(), Bitacora(), ServicioClimaSimulado()
    for robot in (RobotRuedas("R-01", ESTACION), RobotOrugas("O-01", ESTACION), Dron("D-01", ESTACION)):
        flota.agregar(robot)
    return flota, bitacora, clima, AsignadorEntregas(flota, clima, bitacora)


def test_documento_entre_edificios_va_en_ruedas_el_mas_barato(entorno):
    flota, _, _, asignador = entorno
    s = SolicitudEntrega(CAFETERIA, BIBLIOTECA, Documento("Tesis", 1))
    assert asignador.asignar(s)
    assert s.robot.id == "R-01" and s.estado is EstadoSolicitud.ASIGNADA
    assert s.costo > 0 and s.tiempo_min > 0
    assert flota.buscar("R-01").estado is EstadoRobot.EN_RUTA


def test_azotea_con_buen_clima_va_en_dron(entorno):
    _, _, _, asignador = entorno
    s = SolicitudEntrega(CAFETERIA, AZOTEA, Documento("Tesis", 1))
    assert asignador.asignar(s) and s.robot.id == "D-01"


def test_mal_clima_rechaza_al_dron_y_lo_registra(entorno):
    _, bitacora, clima, asignador = entorno
    clima.configurar(viento=45, rafagas=50, lluvia=10, dia=True)
    s = SolicitudEntrega(CAFETERIA, AZOTEA, Documento("Tesis", 1))
    assert not asignador.asignar(s)
    assert s.estado is EstadoSolicitud.PENDIENTE and s.robot is None
    rechazo, = bitacora.filtrar(TipoEvento.RECHAZO_CLIMA)
    assert rechazo.robot_id == "D-01" and "viento" in rechazo.mensaje


def test_mal_clima_reasigna_a_un_terrestre_si_puede(entorno):
    _, bitacora, clima, asignador = entorno
    clima.configurar(viento=45, rafagas=50, lluvia=10, dia=True)
    s = SolicitudEntrega(CAFETERIA, JARDIN, Documento("Tesis", 1))  # Orugas o dron
    assert asignador.asignar(s) and s.robot.id == "O-01"
    assert len(bitacora.filtrar(TipoEvento.RECHAZO_CLIMA)) == 0  # el dron era más caro: ni se consultó


def test_los_terrestres_no_consultan_el_clima(entorno):
    flota, bitacora, _, _ = entorno
    asignador = AsignadorEntregas(flota, ClimaQueNoSeDebeConsultar(), bitacora)
    assert asignador.asignar(SolicitudEntrega(CAFETERIA, BIBLIOTECA, Documento("Tesis", 1)))


def test_sin_robot_compatible_no_asigna(entorno):
    _, _, _, asignador = entorno
    s = SolicitudEntrega(CAFETERIA, BIBLIOTECA, Alimento("Almuerzo", 1, 60))  # nadie tiene frío
    assert not asignador.asignar(s)


def test_cambiar_proveedor_en_vivo(entorno):
    flota, bitacora, clima, asignador = entorno
    clima.configurar(viento=45, rafagas=50, lluvia=10, dia=True)
    s = SolicitudEntrega(CAFETERIA, AZOTEA, Documento("Tesis", 1))
    assert not asignador.asignar(s)
    asignador.cambiar_proveedor_clima(ServicioClimaSimulado())  # clima despejado
    assert asignador.asignar(s)
    with pytest.raises(TypeError):
        asignador.cambiar_proveedor_clima("real")


# --- Commit 11: pendientes, reintentos, entregas y mantenimiento ------------
def test_sin_robot_queda_pendiente_y_se_registra(entorno):
    _, bitacora, _, asignador = entorno
    s = SolicitudEntrega(CAFETERIA, BIBLIOTECA, Alimento("Almuerzo", 1, 60))
    assert not asignador.asignar(s)
    assert asignador.pendientes == (s,) and s.motivo
    assert len(bitacora.filtrar(TipoEvento.SOLICITUD_PENDIENTE)) == 1
    asignador.reintentar_pendientes()  # sigue sin poder: ni se duplica ni se registra de nuevo
    assert asignador.pendientes == (s,)
    assert len(bitacora.filtrar(TipoEvento.SOLICITUD_PENDIENTE)) == 1


def test_pendiente_por_clima_se_reintenta_cuando_mejora(entorno):
    _, _, clima, asignador = entorno
    clima.configurar(viento=45, rafagas=50, lluvia=10, dia=True)
    s = SolicitudEntrega(CAFETERIA, AZOTEA, Documento("Tesis", 1))
    assert not asignador.asignar(s) and "clima" in s.motivo
    clima.configurar(viento=10, rafagas=15, lluvia=10, dia=True)
    assert asignador.reintentar_pendientes() == 1
    assert s.robot.id == "D-01" and asignador.pendientes == ()


def test_se_reintenta_sola_al_liberar_un_robot():
    flota, bitacora, clima = Flota(), Bitacora(), ServicioClimaSimulado()
    flota.agregar(RobotRuedas("R-01", ESTACION))
    asignador = AsignadorEntregas(flota, clima, bitacora)
    primera = SolicitudEntrega(CAFETERIA, BIBLIOTECA, Documento("Tesis", 1))
    segunda = SolicitudEntrega(CAFETERIA, BIBLIOTECA, Documento("Apuntes", 1))
    assert asignador.asignar(primera) and not asignador.asignar(segunda)
    asignador.completar_entrega(primera)
    assert primera.estado is EstadoSolicitud.ENTREGADA
    assert segunda.estado is EstadoSolicitud.ASIGNADA and asignador.pendientes == ()
    assert len(bitacora.filtrar(TipoEvento.ENTREGA_EXITOSA)) == 1


def test_bateria_bajo_la_reserva_manda_a_mantenimiento(entorno):
    flota, bitacora, _, asignador = entorno
    flota.quitar("O-01")
    flota.quitar("D-01")
    flota.quitar("R-01")
    flota.agregar(RobotRuedas("R-02", CAFETERIA, nivel_bateria=17))
    s = SolicitudEntrega(CAFETERIA, BIBLIOTECA, Documento("Tesis", 1))
    assert asignador.asignar(s)
    asignador.completar_entrega(s)
    robot = flota.buscar("R-02")
    assert robot.estado is EstadoRobot.MANTENIMIENTO and robot.nivel_bateria == 100
    assert bitacora.filtrar(TipoEvento.MANTENIMIENTO)[0].robot_id == "R-02"


def test_no_se_completa_lo_que_no_esta_asignado(entorno):
    _, _, _, asignador = entorno
    with pytest.raises(ValueError):
        asignador.completar_entrega(SolicitudEntrega(CAFETERIA, BIBLIOTECA, Documento("Tesis", 1)))


def test_en_curso_lleva_las_asignadas_hasta_que_se_entregan(entorno):
    _, _, _, asignador = entorno
    s = SolicitudEntrega(CAFETERIA, BIBLIOTECA, Documento("Tesis", 1))
    assert asignador.en_curso == ()
    asignador.asignar(s)
    assert asignador.en_curso == (s,)
    asignador.completar_entrega(s)
    assert asignador.en_curso == ()


def test_una_pendiente_reasignada_entra_en_curso(entorno):
    _, _, clima, asignador = entorno
    clima.configurar(viento=45, rafagas=50, lluvia=10, dia=True)
    s = SolicitudEntrega(CAFETERIA, AZOTEA, Documento("Tesis", 1))
    asignador.asignar(s)
    assert asignador.en_curso == ()
    clima.configurar(viento=10, rafagas=15, lluvia=10, dia=True)
    asignador.reintentar_pendientes()
    assert asignador.en_curso == (s,)


def test_no_se_reasigna_una_solicitud_que_ya_no_esta_pendiente(entorno):
    flota, _, _, asignador = entorno
    s = SolicitudEntrega(CAFETERIA, BIBLIOTECA, Documento("Tesis", 1))
    assert asignador.asignar(s)
    with pytest.raises(ValueError):
        asignador.asignar(s)
    # el error llega antes de tocar otro robot: solo el asignado va en ruta
    assert [r.id for r in flota.robots if r.estado is EstadoRobot.EN_RUTA] == ["R-01"]


def test_una_pendiente_asignada_a_mano_sale_de_la_cola(entorno):
    flota, _, clima, asignador = entorno
    clima.configurar(viento=45, rafagas=50, lluvia=10, dia=True)
    s = SolicitudEntrega(CAFETERIA, AZOTEA, Documento("Tesis", 1))
    assert not asignador.asignar(s)
    clima.configurar(viento=10, rafagas=15, lluvia=10, dia=True)
    assert asignador.asignar(s) and asignador.pendientes == ()
    asignador.completar_entrega(s)  # antes, el reintento interno volvía a cargar un robot y fallaba
    assert all(r.estado is EstadoRobot.DISPONIBLE for r in flota.robots)


def test_el_robot_vuelve_de_mantenimiento_al_terminar_la_recarga():
    ahora = [0.0]
    flota, bitacora = Flota(), Bitacora()
    flota.agregar(RobotRuedas("R-02", CAFETERIA, nivel_bateria=17))
    asignador = AsignadorEntregas(flota, ServicioClimaSimulado(), bitacora, reloj=lambda: ahora[0])
    s = SolicitudEntrega(CAFETERIA, BIBLIOTECA, Documento("Tesis", 1))
    asignador.asignar(s)
    asignador.completar_entrega(s)
    robot = flota.buscar("R-02")
    assert robot.estado is EstadoRobot.MANTENIMIENTO
    ahora[0] = DURACION_MANTENIMIENTO_S - 1
    assert asignador.liberar_mantenimientos() == 0 and robot.estado is EstadoRobot.MANTENIMIENTO
    ahora[0] = DURACION_MANTENIMIENTO_S
    assert asignador.liberar_mantenimientos() == 1 and robot.estado is EstadoRobot.DISPONIBLE
    assert len(bitacora.filtrar(TipoEvento.MANTENIMIENTO)) == 2


def test_una_pendiente_espera_a_que_el_robot_salga_de_mantenimiento():
    ahora = [0.0]
    flota = Flota()
    flota.agregar(RobotRuedas("R-02", CAFETERIA, nivel_bateria=17))
    asignador = AsignadorEntregas(flota, ServicioClimaSimulado(), Bitacora(), reloj=lambda: ahora[0])
    primera = SolicitudEntrega(CAFETERIA, BIBLIOTECA, Documento("Tesis", 1))
    segunda = SolicitudEntrega(BIBLIOTECA, CAFETERIA, Documento("Apuntes", 1))
    assert asignador.asignar(primera) and not asignador.asignar(segunda)
    asignador.completar_entrega(primera)  # R-02 entra a mantenimiento: la segunda sigue pendiente
    assert segunda.estado is EstadoSolicitud.PENDIENTE
    ahora[0] = DURACION_MANTENIMIENTO_S
    assert asignador.reintentar_pendientes() == 1 and segunda.robot.id == "R-02"
