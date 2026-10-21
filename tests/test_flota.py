"""Flota como agregación de robots."""
import pytest

from flota.dominio.carga import Documento
from flota.dominio.flota import Flota
from flota.dominio.robot import Dron, RobotRuedas
from flota.dominio.ubicacion import Ubicacion, Zona

ESTACION = Ubicacion("Bloque 20 - Servicios generales", 6.231081, -75.612645, Zona.EDIFICIO)


@pytest.fixture
def flota():
    f = Flota()
    f.agregar(RobotRuedas("R-01", ESTACION))
    f.agregar(Dron("D-01", ESTACION))
    return f


def test_agregar_y_buscar(flota):
    assert flota.buscar("D-01").id == "D-01"
    assert flota.buscar("X-99") is None


def test_no_acepta_ids_repetidos_ni_objetos_que_no_son_robots(flota):
    with pytest.raises(ValueError):
        flota.agregar(RobotRuedas("R-01", ESTACION))
    with pytest.raises(TypeError):
        flota.agregar("R-02")


def test_quitar(flota):
    flota.quitar("R-01")
    assert flota.buscar("R-01") is None
    with pytest.raises(ValueError):
        flota.quitar("R-01")


def test_no_se_quita_un_robot_en_ruta(flota):
    flota.buscar("R-01").cargar(Documento("Tesis", 1))
    with pytest.raises(ValueError):
        flota.quitar("R-01")


def test_disponibles_excluye_en_ruta_y_mantenimiento(flota):
    flota.agregar(RobotRuedas("R-02", ESTACION))
    flota.buscar("R-01").cargar(Documento("Tesis", 1))
    flota.buscar("D-01").enviar_a_mantenimiento()
    assert [r.id for r in flota.disponibles()] == ["R-02"]


def test_robots_devuelve_copia(flota):
    flota.robots.clear()
    assert len(flota.robots) == 2
