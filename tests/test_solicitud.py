"""SolicitudEntrega y las reglas del robot para atenderla."""
import pytest

from flota.dominio.carga import Alimento, Documento, Fragil, MaterialPeligroso
from flota.dominio.estado_robot import EstadoRobot
from flota.dominio.robot import Dron, RobotOrugas, RobotRuedas
from flota.dominio.solicitud import EstadoSolicitud, SolicitudEntrega
from flota.dominio.ubicacion import Ubicacion, Zona

ESTACION = Ubicacion("Bloque 20 - Servicios generales", 6.231081, -75.612645, Zona.EDIFICIO)
CAFETERIA = Ubicacion("Zona de comidas - Ingenierías", 6.230213, -75.611780, Zona.EDIFICIO)
BIBLIOTECA = Ubicacion("Bloque 13 - Biblioteca", 6.231948, -75.611169, Zona.EDIFICIO)
JARDIN = Ubicacion("Jardín central", 6.231500, -75.611900, Zona.ZONA_VERDE)
AZOTEA = Ubicacion("Azotea Bloque 13", 6.231948, -75.611169, Zona.AZOTEA)


def solicitud(carga=None, origen=CAFETERIA, destino=BIBLIOTECA):
    return SolicitudEntrega(origen, destino, carga or Documento("Tesis", 1))


# --- SolicitudEntrega ------------------------------------------------------
def test_solicitud_nace_pendiente():
    s = solicitud()
    assert s.estado is EstadoSolicitud.PENDIENTE and s.robot is None


def test_ciclo_de_vida_feliz():
    s, robot = solicitud(), RobotRuedas("R-01", ESTACION)
    s.asignar(robot, 3000, 4.5)
    assert (s.estado, s.robot, s.costo) == (EstadoSolicitud.ASIGNADA, robot, 3000)
    s.marcar_entregada()
    assert s.estado is EstadoSolicitud.ENTREGADA


def test_pendiente_guarda_el_motivo_y_puede_reasignarse():
    s = solicitud()
    s.marcar_pendiente("sin robots libres")
    assert s.motivo == "sin robots libres"
    s.asignar(RobotRuedas("R-01", ESTACION), 1, 1)
    assert s.motivo == ""


def test_transiciones_invalidas():
    s = solicitud()
    with pytest.raises(ValueError):
        s.marcar_entregada()  # nunca fue asignada
    s.marcar_fallida("clima")
    for operacion in (lambda: s.asignar(None, 1, 1), s.marcar_entregada,
                      lambda: s.marcar_pendiente("x"), lambda: s.marcar_fallida("y")):
        with pytest.raises(ValueError):
            operacion()


def test_solicitud_rechaza_datos_invalidos():
    with pytest.raises(TypeError):
        SolicitudEntrega(CAFETERIA, BIBLIOTECA, "caja")
    with pytest.raises(ValueError):
        SolicitudEntrega(CAFETERIA, CAFETERIA, Documento("Tesis", 1))


def test_cada_solicitud_tiene_id_distinto():
    assert solicitud().id != solicitud().id


# --- Robot.puede_atender ---------------------------------------------------
def test_ruedas_atiende_un_documento_entre_edificios():
    assert RobotRuedas("R-01", ESTACION).puede_atender(solicitud())


def test_zona_inaccesible_no_atiende():
    s = solicitud(destino=AZOTEA)
    assert not RobotRuedas("R-01", ESTACION).puede_atender(s)
    assert not RobotOrugas("O-01", ESTACION).puede_atender(solicitud(destino=AZOTEA))
    assert Dron("D-01", ESTACION).puede_atender(solicitud(destino=AZOTEA))
    assert RobotOrugas("O-01", ESTACION).puede_atender(solicitud(destino=JARDIN))


def test_sobrepeso_no_atiende():
    assert not RobotRuedas("R-01", ESTACION).puede_atender(solicitud(Documento("Cajas", 25)))
    assert RobotOrugas("O-01", ESTACION).puede_atender(solicitud(Documento("Cajas", 25)))


def test_bateria_insuficiente_no_atiende():
    assert not RobotRuedas("R-01", ESTACION, nivel_bateria=16).puede_atender(solicitud())


def test_carga_incompatible_no_atiende():
    assert not RobotRuedas("R-01", ESTACION).puede_atender(solicitud(Alimento("Almuerzo", 1, 60)))
    assert RobotRuedas("R-02", ESTACION, tiene_control_temperatura=True).puede_atender(
        solicitud(Alimento("Almuerzo", 1, 60)))
    assert not RobotOrugas("O-01", ESTACION).puede_atender(solicitud(Fragil("Vidrio", 1)))
    assert not Dron("D-01", ESTACION).puede_atender(solicitud(MaterialPeligroso("Ácido", 1, 2)))


def test_robot_ocupado_o_en_mantenimiento_no_atiende():
    robot = RobotRuedas("R-01", ESTACION)
    robot.enviar_a_mantenimiento()
    assert not robot.puede_atender(solicitud())


# --- Robot.calcular_costo / cargar / entregar / mantenimiento --------------
def test_costo_usa_distancia_tarifa_y_recargo():
    ruedas = RobotRuedas("R-01", ESTACION)
    km = CAFETERIA.distancia_km(BIBLIOTECA) * 1.3
    assert ruedas.calcular_costo(CAFETERIA, BIBLIOTECA, Documento("Tesis", 1)) == pytest.approx(km * 1500)
    assert ruedas.calcular_costo(CAFETERIA, BIBLIOTECA, Fragil("Vidrio", 1)) == pytest.approx(km * 1500 * 1.3)


def test_cargar_y_entregar_cambian_estado_ubicacion_y_bateria():
    robot, carga = RobotRuedas("R-01", CAFETERIA), Documento("Tesis", 1)
    robot.cargar(carga)
    assert robot.estado is EstadoRobot.EN_RUTA and robot.carga_actual is carga
    robot.entregar(BIBLIOTECA)
    assert robot.estado is EstadoRobot.DISPONIBLE and robot.carga_actual is None
    assert robot.ubicacion is BIBLIOTECA
    assert robot.nivel_bateria == pytest.approx(100 - CAFETERIA.distancia_km(BIBLIOTECA) * 1.3 * 4)


def test_cargar_con_origen_viaja_al_origen_primero():
    robot = RobotRuedas("R-01", ESTACION)
    robot.cargar(Documento("Tesis", 1), origen=CAFETERIA)
    assert robot.ubicacion is CAFETERIA and robot.nivel_bateria < 100


def test_cargar_rechaza_lo_que_no_puede_llevar():
    robot = RobotRuedas("R-01", ESTACION)
    with pytest.raises(ValueError):
        robot.cargar(Documento("Cajas", 25))
    with pytest.raises(ValueError):
        robot.cargar(Alimento("Almuerzo", 1, 60))
    robot.cargar(Documento("Tesis", 1))
    with pytest.raises(ValueError):
        robot.cargar(Documento("Otra", 1))  # ya va en ruta


def test_entregar_sin_carga_falla():
    with pytest.raises(ValueError):
        RobotRuedas("R-01", ESTACION).entregar(BIBLIOTECA)


def test_mantenimiento_recarga_y_bloquea_hasta_terminar():
    robot = RobotRuedas("R-01", ESTACION, nivel_bateria=10)
    robot.enviar_a_mantenimiento()
    assert robot.estado is EstadoRobot.MANTENIMIENTO and robot.nivel_bateria == 100
    with pytest.raises(ValueError):
        robot.cargar(Documento("Tesis", 1))
    robot.terminar_mantenimiento()
    assert robot.estado is EstadoRobot.DISPONIBLE


def test_no_se_envia_a_mantenimiento_con_carga():
    robot = RobotRuedas("R-01", ESTACION)
    robot.cargar(Documento("Tesis", 1))
    with pytest.raises(ValueError):
        robot.enviar_a_mantenimiento()
