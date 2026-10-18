import pytest

from flota.dominio.estado_robot import EstadoRobot
from flota.dominio.ubicacion import Ubicacion, Zona

# Puntos reales del campus UdeM (OpenStreetMap)
CAFETERIA = Ubicacion("Zona de comidas - Ingenierías", 6.230213, -75.611780, Zona.EDIFICIO)
BIBLIOTECA = Ubicacion("Bloque 13 - Biblioteca", 6.231948, -75.611169, Zona.EDIFICIO)
AZOTEA_B12 = Ubicacion("Azotea Bloque 12 - Posgrados", 6.231935, -75.611643, Zona.AZOTEA)


def test_distancia_entre_bloques_del_campus():
    assert CAFETERIA.distancia_km(BIBLIOTECA) == pytest.approx(0.205, abs=0.005)


def test_distancia_es_simetrica_y_cero_consigo_misma():
    assert CAFETERIA.distancia_km(AZOTEA_B12) == pytest.approx(AZOTEA_B12.distancia_km(CAFETERIA))
    assert BIBLIOTECA.distancia_km(BIBLIOTECA) == 0


def test_cada_ubicacion_conoce_su_zona():
    assert BIBLIOTECA.zona is Zona.EDIFICIO
    assert AZOTEA_B12.zona is Zona.AZOTEA


def test_atributos_son_de_solo_lectura():
    with pytest.raises(AttributeError):
        BIBLIOTECA.zona = Zona.AZOTEA
    with pytest.raises(AttributeError):
        BIBLIOTECA.latitud = 0


@pytest.mark.parametrize("nombre, lat, lon", [
    ("", 6.23, -75.61),
    ("Bloque X", 91, -75.61),
    ("Bloque X", 6.23, -181),
])
def test_rechaza_datos_invalidos(nombre, lat, lon):
    with pytest.raises(ValueError):
        Ubicacion(nombre, lat, lon, Zona.EDIFICIO)


def test_zona_debe_ser_un_valor_de_zona():
    with pytest.raises(TypeError):
        Ubicacion("Bloque X", 6.23, -75.61, "azotea")


def test_estados_del_robot():
    assert {e.name for e in EstadoRobot} == {"DISPONIBLE", "EN_RUTA", "MANTENIMIENTO"}
