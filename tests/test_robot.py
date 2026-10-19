import pytest

from flota.dominio.estado_robot import EstadoRobot
from flota.dominio.robot import Dron, Robot, RobotOrugas, RobotRuedas
from flota.dominio.ubicacion import Ubicacion, Zona

ESTACION = Ubicacion("Bloque 20 - Servicios generales", 6.231081, -75.612645, Zona.EDIFICIO)
CAFETERIA = Ubicacion("Zona de comidas - Ingenierías", 6.230213, -75.611780, Zona.EDIFICIO)
BIBLIOTECA = Ubicacion("Bloque 13 - Biblioteca", 6.231948, -75.611169, Zona.EDIFICIO)


@pytest.fixture
def flota():
    return [RobotRuedas("R-01", ESTACION), RobotOrugas("O-01", ESTACION), Dron("D-01", ESTACION)]


def test_robot_es_abstracto():
    with pytest.raises(TypeError):
        Robot("X-01", ESTACION, 10, 10)


def test_polimorfismo_cada_subtipo_responde_distinto(flota):
    ruedas, orugas, dron = flota
    assert [r.requiere_clima() for r in flota] == [False, False, True]
    assert ruedas.zonas_accesibles() == {Zona.EDIFICIO}
    assert Zona.ZONA_VERDE in orugas.zonas_accesibles()
    assert Zona.AZOTEA in dron.zonas_accesibles()
    assert len({r.costo_por_km() for r in flota}) == 3


def test_solo_el_dron_llega_a_azoteas(flota):
    assert [Zona.AZOTEA in r.zonas_accesibles() for r in flota] == [False, False, True]


def test_capacidades_que_consultan_las_cargas(flota):
    ruedas, orugas, dron = flota
    assert dron.es_aereo() and not ruedas.es_aereo()
    assert orugas.terreno_irregular() and not ruedas.terreno_irregular()


def test_el_dron_vuela_en_linea_recta_y_los_terrestres_rodean(flota):
    ruedas, _, dron = flota
    recta_km = CAFETERIA.distancia_km(BIBLIOTECA)
    assert dron.calcular_tiempo_min(CAFETERIA, BIBLIOTECA) == pytest.approx(recta_km / 30 * 60)
    assert ruedas.calcular_tiempo_min(CAFETERIA, BIBLIOTECA) == pytest.approx(recta_km * 1.3 / 12 * 60)


def test_composicion_cada_robot_tiene_su_propia_bateria():
    r1 = RobotRuedas("R-01", ESTACION)
    r2 = RobotRuedas("R-02", ESTACION, nivel_bateria=40)
    assert r1.nivel_bateria == 100
    assert r2.nivel_bateria == 40
    assert r1._bateria is not r2._bateria


def test_robot_nuevo_esta_disponible_y_sin_carga(flota):
    assert all(r.estado is EstadoRobot.DISPONIBLE for r in flota)
    assert all(r.carga_actual is None for r in flota)


def test_atributos_de_solo_lectura(flota):
    with pytest.raises(AttributeError):
        flota[0].estado = EstadoRobot.MANTENIMIENTO
    with pytest.raises(AttributeError):
        flota[0].nivel_bateria = 100


@pytest.mark.parametrize("args", [
    ("", ESTACION, 10, 10),
    ("R-09", ESTACION, 0, 10),
    ("R-09", ESTACION, 10, -1),
])
def test_rechaza_datos_invalidos(args):
    with pytest.raises(ValueError):
        RobotRuedas(*args)
