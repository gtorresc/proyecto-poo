"""CentroControl, el modelo de presentación: se prueba sin ventana y con un reloj falso."""
import time

import pytest

from flota.asignacion.asignador import AsignadorEntregas
from flota.campus import cargar_campus, cargar_geometria
from flota.dominio.bitacora import Bitacora
from flota.dominio.estado_robot import EstadoRobot
from flota.dominio.solicitud import EstadoSolicitud
from flota.gui.centro_control import (CENTRO_CAMPUS, RECARGA_S, CentroControl, a_metros,
                                      punto_en_recorrido)
from flota.servicios.calendario_simulado import CalendarioSimulado
from flota.servicios.clima_simulado import ServicioClimaSimulado


class Reloj:
    def __init__(self):
        self.ahora = 1000.0

    def __call__(self):
        return self.ahora


@pytest.fixture
def reloj():
    return Reloj()


@pytest.fixture
def centro(reloj):
    ubicaciones, flota = cargar_campus()
    bitacora = Bitacora()
    asignador = AsignadorEntregas(flota, ServicioClimaSimulado(), bitacora)
    clima_real = ServicioClimaSimulado(viento_kmh=50)  # hace de "Open-Meteo" sin red
    centro = CentroControl(ubicaciones, flota, asignador, bitacora, cargar_geometria(),
                           clima_real=clima_real, calendario_real=CalendarioSimulado("Festivo real"),
                           reloj=reloj)
    centro.usar_clima(False)
    centro.usar_calendario(False)
    return centro


def robot(centro, id_robot):
    return next(r for r in centro.estado()["robots"] if r["id"] == id_robot)


def test_conversion_a_metros():
    assert a_metros(*CENTRO_CAMPUS) == (0, 0)
    x, y = a_metros(6.2326, -75.6101)  # ~110 m al norte y ~110 m al este
    assert 100 < x < 120 and 100 < y < 120


def test_punto_en_recorrido_sigue_la_polilinea():
    ele = [(0, 0), (10, 0), (10, 10)]
    assert punto_en_recorrido(ele, 0) == (0, 0)
    assert punto_en_recorrido(ele, 0.5) == (10, 0)  # mitad de 20 m: la esquina
    assert punto_en_recorrido(ele, 0.75) == (10, 5)
    assert punto_en_recorrido(ele, 1.5) == (10, 10)


def test_geometria_en_metros_con_alturas_y_puntos_de_entrega(centro):
    geo = centro.geometria()
    assert all(e["altura"] > 0 for e in geo["edificios"])
    assert {e["en_campus"] for e in geo["edificios"]} == {True, False}  # campus y ciudad alrededor
    por_clave = {u["clave"]: u for u in geo["ubicaciones"]}
    biblioteca = geo["edificios"][por_clave["biblioteca"]["edificio"]]
    assert biblioteca["nombre"].startswith("Bloque 13")
    assert {t["clave"] for t in geo["tipos_carga"]} == {"documento", "alimento", "fragil", "peligroso"}


def test_la_solicitud_nueva_es_una_baliza_y_no_se_asigna_sola(centro, reloj):
    id_sol = centro.crear_solicitud("cafeteria", "biblioteca", "documento", 1)
    reloj.ahora += 4
    [baliza] = centro.estado()["balizas"]
    assert baliza["id"] == id_sol and not baliza["automatica"] and baliza["espera_s"] == 4
    assert centro.estado()["resumen"]["en_ruta"] == 0


@pytest.mark.parametrize("args", [("cafeteria", "cafeteria", "documento", 1),
                                  ("cafeteria", "biblioteca", "plutonio", 1),
                                  ("cafeteria", "biblioteca", "documento", 0),
                                  ("marte", "biblioteca", "documento", 1)])
def test_datos_invalidos_de_la_solicitud(centro, args):
    with pytest.raises(ValueError):
        centro.crear_solicitud(*args)


def test_viaje_completo_por_los_senderos(centro, reloj):
    id_sol = centro.crear_solicitud("cafeteria", "biblioteca", "documento", 1)
    assert centro.despachar_auto(id_sol) == (True, "")
    assert not centro.tick()  # empieza el viaje
    r = robot(centro, "R-01")
    assert r["franja"] == "ocupado" and len(r["recorrido"]) > 2 and r["z"] == 0
    inicio = (r["x"], r["y"])
    reloj.ahora += 1
    assert (robot(centro, "R-01")["x"], robot(centro, "R-01")["y"]) != inicio  # se mueve
    reloj.ahora += 600
    assert centro.tick()  # llegó
    r = robot(centro, "R-01")
    destino = next(u for u in centro.geometria()["ubicaciones"] if u["clave"] == "biblioteca")
    assert r["franja"] == "libre" and r["mision"] is None
    assert (r["x"], r["y"]) == pytest.approx((destino["x"], destino["y"]))


def test_el_dron_vuela_recto_y_en_altura(centro, reloj):
    id_sol = centro.crear_solicitud("biblioteca", "azotea_b11", "documento", 1)
    assert centro.despachar(id_sol, "D-01") == (True, "")
    centro.tick()
    reloj.ahora += 2
    dron = robot(centro, "D-01")
    assert len(dron["recorrido"]) == 2 and dron["z"] > 0 and 0 < dron["mision"]["progreso"] < 1


def test_despacho_manual_rechazado_deja_la_baliza_con_el_motivo(centro):
    centro.configurar_clima(viento=10, lluvia=10, dia=True, tormenta=True)
    id_sol = centro.crear_solicitud("biblioteca", "azotea_b11", "documento", 1)
    assert centro.despachar(id_sol, "D-01") == (False, "clima desfavorable: tormenta eléctrica")
    [baliza] = centro.estado()["balizas"]
    assert baliza["motivo"] == "clima desfavorable: tormenta eléctrica"
    assert not centro.estado()["clima"]["drones_autorizados"]
    with pytest.raises(ValueError):
        centro.despachar(id_sol, "X-99")


def test_radar_sale_de_los_metodos_de_cada_subtipo(centro):
    radar = {r["id"]: r["radar"] for r in centro.estado()["robots"]}
    assert radar["D-01"]["velocidad"] == 1 and radar["D-01"]["alcance"] == 1
    assert radar["O-01"]["carga"] == 1
    assert radar["R-01"]["economia"] == 1 and radar["R-01"]["autonomia"] == 1
    assert radar["R-01"] == radar["R-02"]  # mismo subtipo, misma forma


def test_festivo_simulado_y_su_reintento(centro):
    centro.configurar_festivo("Día de la Raza")
    id_sol = centro.crear_solicitud("cafeteria", "derecho", "alimento", 1)
    assert centro.despachar_auto(id_sol) == (False, "cafetería cerrada (festivo: Día de la Raza)")
    assert centro.estado()["balizas"][0]["automatica"]
    assert centro.estado()["calendario"] == {"proveedor": "simulado", "festivo": "Día de la Raza"}
    centro.configurar_festivo(None)  # vuelve a ser día hábil: la pendiente se asigna sola
    assert centro.estado()["balizas"] == [] and robot(centro, "R-02")["franja"] == "ocupado"


def test_cambiar_a_los_proveedores_reales(centro):
    centro.usar_calendario(True)
    centro.usar_clima(True)
    for _ in range(100):  # los reales se leen en un hilo
        if not centro.estado()["clima"]["consultando"] and centro.estado()["calendario"]["festivo"]:
            break
        time.sleep(0.01)
    clima = centro.estado()["clima"]
    assert clima["proveedor"] == "Open-Meteo" and clima["viento"] == 50 and not clima["drones_autorizados"]
    assert centro.estado()["calendario"] == {"proveedor": "Nager.Date", "festivo": "Festivo real"}


def test_el_mantenimiento_termina_solo(centro, reloj):
    centro._flota.buscar("R-01").enviar_a_mantenimiento()
    centro.tick()
    assert robot(centro, "R-01")["franja"] == "falla"
    reloj.ahora += RECARGA_S
    assert centro.tick()
    assert centro._flota.buscar("R-01").estado is EstadoRobot.DISPONIBLE


def test_la_bitacora_llega_como_texto(centro):
    id_sol = centro.crear_solicitud("cafeteria", "biblioteca", "documento", 1)
    centro.despachar(id_sol, "D-01")  # el dron sí puede, sin tormenta
    centro.despachar_auto(centro.crear_solicitud("cafeteria", "azotea_b11", "peligroso", 1))
    eventos = centro.estado()["bitacora"]
    assert eventos["total"] == len(eventos["ultimos"]) >= 1
    assert eventos["ultimos"][-1]["tipo"] == "SOLICITUD_PENDIENTE"
    assert "REPORTE" in centro.exportar_bitacora()
    assert next(s for s in centro._asignador.en_curso).estado is EstadoSolicitud.ASIGNADA


def test_los_robots_quietos_en_el_mismo_lugar_no_se_tapan(centro):
    posiciones = {(round(r["x"], 1), round(r["y"], 1)) for r in centro.estado()["robots"]}
    assert len(posiciones) == 4  # los cuatro empiezan en la estación

