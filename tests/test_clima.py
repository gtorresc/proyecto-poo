"""Contrato del clima y simulador."""
import pytest

from flota.dominio.ubicacion import Ubicacion, Zona
from flota.servicios.clima_simulado import ServicioClimaSimulado
from flota.servicios.proveedor_clima import ProveedorClima, ReporteClima, UmbralesClima

AZOTEA = Ubicacion("Azotea Bloque 13", 6.231948, -75.611169, Zona.AZOTEA)
UMBRALES = UmbralesClima()


def test_proveedor_es_abstracto():
    with pytest.raises(TypeError):
        ProveedorClima()


def test_clima_tranquilo_es_favorable():
    assert ReporteClima(12, 18, 10, True).es_favorable(UMBRALES) == (True, "condiciones favorables")


@pytest.mark.parametrize("reporte, motivo", [
    (ReporteClima(45, 20, 10, True), "viento"),
    (ReporteClima(10, 55, 10, True), "ráfagas"),
    (ReporteClima(10, 15, 80, True), "lluvia"),
    (ReporteClima(10, 15, 10, False), "noche"),
    (ReporteClima.no_disponible(), "no disponible"),
])
def test_condiciones_que_no_son_favorables(reporte, motivo):
    favorable, texto = reporte.es_favorable(UMBRALES)
    assert not favorable and motivo in texto


def test_el_limite_exacto_todavia_es_favorable():
    assert ReporteClima(30, 40, 50, True).es_favorable(UMBRALES)[0]


def test_umbrales_personalizados_cambian_el_resultado():
    assert ReporteClima(45, 20, 10, True).es_favorable(UmbralesClima(viento_max_kmh=50))[0]


def test_simulador_usa_el_contrato():
    sim = ServicioClimaSimulado()
    assert sim.condiciones_favorables(AZOTEA)
    sim.configurar(viento=45, rafagas=50, lluvia=10, dia=True)
    assert not sim.condiciones_favorables(AZOTEA)
    sim.configurar(viento=10, rafagas=15, lluvia=10, dia=False)
    assert not sim.condiciones_favorables(AZOTEA)


def test_valores_invalidos():
    with pytest.raises(ValueError):
        ReporteClima(-1, 0, 10, True)
    with pytest.raises(ValueError):
        ReporteClima(10, 10, 120, True)
    with pytest.raises(ValueError):
        ServicioClimaSimulado().configurar(10, 10, -5, True)
    with pytest.raises(ValueError):
        UmbralesClima(viento_max_kmh=-1)


@pytest.mark.parametrize("reporte, motivo", [
    (ReporteClima(10, 15, 10, True, tormenta=True), "tormenta eléctrica"),
    (ReporteClima(10, 15, 10, True, visibilidad_m=400), "niebla: visibilidad 400 m < 1000 m"),
])
def test_tormenta_y_niebla_no_son_favorables(reporte, motivo):
    assert reporte.es_favorable(UMBRALES) == (False, motivo)


def test_visibilidad_en_el_limite_o_sin_dato_no_bloquea_al_dron():
    assert ReporteClima(10, 15, 10, True, visibilidad_m=1000).es_favorable(UMBRALES)[0]
    assert ReporteClima(10, 15, 10, True, visibilidad_m=None).es_favorable(UMBRALES)[0]
    assert not ReporteClima(10, 15, 10, True, visibilidad_m=1500).es_favorable(
        UmbralesClima(visibilidad_min_m=2000))[0]


@pytest.mark.parametrize("extras", [{"visibilidad_m": -1}, {"humedad_pct": 120},
                                    {"direccion_viento_grados": 400}])
def test_datos_nuevos_fuera_de_rango(extras):
    with pytest.raises(ValueError):
        ReporteClima(10, 15, 10, True, **extras)


def test_simulador_con_tormenta_y_niebla():
    sim = ServicioClimaSimulado()
    sim.configurar(viento=10, rafagas=15, lluvia=10, dia=True, tormenta=True)
    assert sim.obtener_reporte(AZOTEA).es_favorable(sim.umbrales) == (False, "tormenta eléctrica")
    sim.configurar(viento=10, rafagas=15, lluvia=10, dia=True, visibilidad=300, humedad=95, direccion=235)
    r = sim.obtener_reporte(AZOTEA)
    assert not r.es_favorable(sim.umbrales)[0] and (r.humedad_pct, r.direccion_viento_grados) == (95, 235)
