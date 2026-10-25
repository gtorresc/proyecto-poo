"""Rutas: línea recta, Dijkstra sobre los senderos y polimorfismo de trazar_ruta."""
import pytest

from flota.dominio.carga import Documento
from flota.dominio.robot import FACTOR_RODEO_TERRESTRE, Dron, RobotOrugas, RobotRuedas
from flota.dominio.ruta import RedSenderos, Ruta
from flota.dominio.ubicacion import Ubicacion, Zona

# Una cuadra de ~110 m por lado cerca de (0, 0): de A a C se puede ir por B (corto) o por F (largo)
A, B, C, F = (0.0, 0.0), (0.0, 0.001), (0.001, 0.001), (0.003, -0.002)
LUGAR_A = Ubicacion("A", *A, Zona.EDIFICIO)
LUGAR_C = Ubicacion("C", *C, Zona.EDIFICIO)
AISLADO = Ubicacion("Aislado", 0.05, 0.05, Zona.EDIFICIO)


@pytest.fixture
def red():
    return RedSenderos([[A, B, C], [A, F], [F, C], [(0.05, 0.05), (0.051, 0.05)]])


def test_ruta_valida_sus_datos():
    with pytest.raises(ValueError):
        Ruta([A], 1)
    with pytest.raises(ValueError):
        Ruta([A, B], -1)


def test_linea_recta_usa_haversine_por_el_factor():
    ruta = Ruta.linea_recta(LUGAR_A, LUGAR_C, factor=1.3)
    assert ruta.puntos == (A, C)
    assert ruta.distancia_km == pytest.approx(LUGAR_A.distancia_km(LUGAR_C) * 1.3)


def test_dijkstra_elige_el_camino_mas_corto(red):
    ruta = red.ruta(LUGAR_A, LUGAR_C)
    assert ruta.puntos == (A, A, B, C, C)  # punto de entrega, nodos del sendero, punto de entrega
    assert ruta.distancia_km == pytest.approx(0.222, abs=0.001)  # dos lados de ~111 m
    assert ruta.distancia_km > LUGAR_A.distancia_km(LUGAR_C)  # por senderos nunca es más corto


def test_sin_camino_devuelve_none_y_mismo_lugar_cuesta_cero(red):
    assert red.ruta(LUGAR_A, AISLADO) is None
    assert red.ruta(LUGAR_A, Ubicacion("Otra A", *A, Zona.EDIFICIO)).distancia_km == 0


def test_la_red_necesita_senderos():
    with pytest.raises(ValueError):
        RedSenderos([])


def test_terrestre_sigue_los_senderos_y_el_dron_vuela_recto(red):
    """Polimorfismo: el mismo trazar_ruta da caminos distintos según el subtipo."""
    ruedas = RobotRuedas("R-01", LUGAR_A, red=red)
    orugas = RobotOrugas("O-01", LUGAR_A, red=red)
    dron = Dron("D-01", LUGAR_A, red=red)
    assert ruedas.trazar_ruta(LUGAR_A, LUGAR_C).puntos == (A, A, B, C, C)
    assert orugas.trazar_ruta(LUGAR_A, LUGAR_C).distancia_km == pytest.approx(0.222, abs=0.001)
    assert dron.trazar_ruta(LUGAR_A, LUGAR_C).puntos == (A, C)
    assert dron.calcular_tiempo_min(LUGAR_A, LUGAR_C) < ruedas.calcular_tiempo_min(LUGAR_A, LUGAR_C)


def test_sin_red_o_sin_camino_se_estima_el_rodeo(red):
    recta = LUGAR_A.distancia_km(AISLADO)
    sin_red = RobotRuedas("R-01", LUGAR_A)
    sin_camino = RobotRuedas("R-02", LUGAR_A, red=red)
    for robot in (sin_red, sin_camino):
        assert robot.trazar_ruta(LUGAR_A, AISLADO).distancia_km == pytest.approx(recta * FACTOR_RODEO_TERRESTRE)


def test_el_costo_sale_de_la_ruta_real(red):
    ruedas = RobotRuedas("R-01", LUGAR_A, red=red)
    assert ruedas.calcular_costo(LUGAR_A, LUGAR_C, Documento("Acta", 1)) == pytest.approx(
        red.ruta(LUGAR_A, LUGAR_C).distancia_km * ruedas.costo_por_km() * Documento("Acta", 1).recargo())
