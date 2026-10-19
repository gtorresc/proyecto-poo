import pytest

from flota.dominio.bateria import Bateria


def test_empieza_llena_con_reserva_de_15():
    bateria = Bateria()
    assert bateria.nivel == 100
    assert bateria.reserva_minima == 15


def test_consumir_descuenta_el_nivel():
    bateria = Bateria(80)
    bateria.consumir(30)
    assert bateria.nivel == 50


def test_no_puede_quedar_por_debajo_de_cero():
    bateria = Bateria(10)
    with pytest.raises(ValueError):
        bateria.consumir(11)
    assert bateria.nivel == 10


def test_no_acepta_consumo_negativo():
    with pytest.raises(ValueError):
        Bateria().consumir(-5)


def test_recargar_vuelve_a_100():
    bateria = Bateria(20)
    bateria.recargar()
    assert bateria.nivel == 100


@pytest.mark.parametrize("nivel, consumo, esperado", [
    (50, 35, True),    # quedan 15: justo la reserva
    (50, 36, False),   # quedarían 14: por debajo de la reserva
    (20, 5, True),
    (15, 1, False),
])
def test_alcanza_para_respeta_la_reserva_minima(nivel, consumo, esperado):
    assert Bateria(nivel).alcanza_para(consumo) is esperado


@pytest.mark.parametrize("nivel", [-1, 101])
def test_rechaza_nivel_inicial_invalido(nivel):
    with pytest.raises(ValueError):
        Bateria(nivel)


def test_el_nivel_no_se_puede_asignar_desde_afuera():
    bateria = Bateria()
    with pytest.raises(AttributeError):
        bateria.nivel = 150
