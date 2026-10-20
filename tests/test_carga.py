import pytest

from flota.dominio.carga import Alimento, Carga, Documento, Fragil, MaterialPeligroso
from flota.dominio.robot import Dron, RobotOrugas, RobotRuedas
from flota.dominio.ubicacion import Ubicacion, Zona

ESTACION = Ubicacion("Bloque 20 - Servicios generales", 6.231081, -75.612645, Zona.EDIFICIO)
RUEDAS = RobotRuedas("R-01", ESTACION)
RUEDAS_FRIO = RobotRuedas("R-02", ESTACION, tiene_control_temperatura=True)
ORUGAS = RobotOrugas("O-01", ESTACION)
DRON = Dron("D-01", ESTACION)


def test_carga_es_abstracta():
    with pytest.raises(TypeError):
        Carga("algo", 1)


def test_documento_va_en_cualquier_robot():
    doc = Documento("Acta de grado", 0.5)
    assert all(doc.es_compatible_con(r) for r in (RUEDAS, ORUGAS, DRON))


def test_alimento_exige_control_de_temperatura():
    almuerzo = Alimento("Almuerzo", 1.5, temperatura_c=60)
    assert not almuerzo.es_compatible_con(RUEDAS)
    assert almuerzo.es_compatible_con(RUEDAS_FRIO)


def test_fragil_no_va_en_orugas():
    vidrio = Fragil("Probetas", 2)
    assert not vidrio.es_compatible_con(ORUGAS)
    assert vidrio.es_compatible_con(RUEDAS) and vidrio.es_compatible_con(DRON)


def test_material_peligroso_nunca_va_en_dron():
    acido = MaterialPeligroso("Ácido clorhídrico", 1, nivel_riesgo=3)
    assert not acido.es_compatible_con(DRON)
    assert acido.es_compatible_con(RUEDAS)


def test_polimorfismo_del_recargo():
    cargas = [Documento("d", 1), Alimento("a", 1, 5), Fragil("f", 1), MaterialPeligroso("m", 1, 1)]
    assert [c.recargo() for c in cargas] == [1.0, 1.2, 1.3, 1.5]


@pytest.mark.parametrize("peso", [0, -2])
def test_peso_debe_ser_positivo(peso):
    with pytest.raises(ValueError):
        Documento("Sobre", peso)


def test_nivel_de_riesgo_valido():
    with pytest.raises(ValueError):
        MaterialPeligroso("Reactivo", 1, nivel_riesgo=5)


def test_peso_de_solo_lectura():
    with pytest.raises(AttributeError):
        Documento("Sobre", 1).peso_kg = 100
