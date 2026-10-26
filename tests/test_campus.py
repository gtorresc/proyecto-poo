"""Datos del campus, su geometría de OSM y demo por consola (sin internet: usa el clima simulado)."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from flota.campus import cargar_campus, cargar_geometria, crear_red_senderos
from flota.dominio.estado_robot import EstadoRobot
from flota.dominio.ubicacion import Ubicacion, Zona
from flota.gui.centro_control import dentro

RAIZ = Path(__file__).resolve().parent.parent


def test_campus_trae_ubicaciones_de_las_tres_zonas_y_la_flota_inicial():
    sitio, flota = cargar_campus()
    assert {u.zona for u in sitio.values()} == set(Zona)
    assert sorted(r.id for r in flota.robots) == ["D-01", "O-01", "R-01", "R-02"]
    assert all(r.ubicacion is sitio["estacion"] and r.estado is EstadoRobot.DISPONIBLE
               for r in flota.robots)
    assert flota.buscar("R-02").tiene_control_temperatura and not flota.buscar("R-01").tiene_control_temperatura


def test_la_demo_corre_completa():
    r = subprocess.run([sys.executable, str(RAIZ / "main.py")], capture_output=True,
                       encoding="utf-8", timeout=30)
    assert r.returncode == 0, r.stderr
    assert "rechazo por clima: 2" in r.stdout and "entrega exitosa: 5" in r.stdout


def test_la_geometria_trae_perimetro_edificios_caminos_y_atribucion():
    geo = cargar_geometria()
    assert "OpenStreetMap" in geo["fuente"]
    assert len(geo["perimetro"]) >= 3
    assert len(geo["edificios"]) > 50 and len(geo["caminos"]) > 100
    assert all(len(e["contorno"]) >= 3 for e in geo["edificios"])
    assert all(e["niveles"] is None or e["niveles"] > 0 for e in geo["edificios"])


def test_cada_punto_de_entrega_queda_sobre_un_edificio_o_dentro_del_campus():
    geo = cargar_geometria()
    sitio, _ = cargar_campus()
    for clave, u in sitio.items():
        assert dentro((u.latitud, u.longitud), geo["perimetro"]), f"{clave} está fuera del campus"
        if u.zona is Zona.ZONA_VERDE:
            continue  # canchas y huertas no son edificios
        cerca = any(dentro((u.latitud, u.longitud), e["contorno"])
                    or min(u.distancia_km(Ubicacion("v", la, lo, Zona.EDIFICIO))
                           for la, lo in e["contorno"]) <= 0.02
                    for e in geo["edificios"])
        assert cerca, f"{clave} no tiene un edificio a menos de 20 m"


@pytest.fixture
def script_osm():
    ruta = RAIZ / "scripts" / "descargar_campus_osm.py"
    spec = importlib.util.spec_from_file_location("descargar_campus_osm", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_el_script_convierte_la_respuesta_de_overpass(script_osm):
    punto = lambda la, lo: {"lat": la, "lon": lo}
    respuesta = {"elements": [
        {"id": script_osm.ID_CAMPUS, "tags": {"amenity": "university"},
         "geometry": [punto(6.0, -75.0), punto(6.1, -75.0), punto(6.1, -75.1)]},
        {"id": 1, "tags": {"building": "university", "name": "Bloque X", "building:levels": "3"},
         "geometry": [punto(6.05, -75.05)] * 4},
        {"id": 2, "tags": {"building": "yes", "building:levels": "dos"},
         "geometry": [punto(6.05, -75.05)] * 4},
        {"id": 3, "tags": {"highway": "footway"}, "geometry": [punto(6.0, -75.0), punto(6.1, -75.1)]},
    ]}
    geo = script_osm.convertir(respuesta)
    assert [e["niveles"] for e in geo["edificios"][:2]] == [3, None]  # "dos" no es un número
    assert geo["edificios"][0]["nombre"] == "Bloque X"
    assert len(geo["edificios"]) == 2 + len(script_osm.TRAZADOS_A_MANO)
    assert geo["caminos"] == [{"tipo": "footway", "puntos": [[6.0, -75.0], [6.1, -75.1]]}]
    assert json.loads(script_osm.a_texto(geo)) == geo  # el formato de una fila por línea sigue siendo JSON


def test_el_script_falla_si_overpass_no_trae_el_perimetro(script_osm):
    with pytest.raises(ValueError):
        script_osm.convertir({"elements": []})


def test_los_senderos_reales_conectan_todos_los_puntos_de_entrega():
    sitio, _ = cargar_campus()
    red = crear_red_senderos(cargar_geometria())
    lugares = list(sitio.values())
    for i, origen in enumerate(lugares):
        for destino in lugares[i + 1:]:
            ruta = red.ruta(origen, destino)
            assert ruta is not None, f"{origen.nombre} y {destino.nombre} no están conectados"
            assert ruta.distancia_km >= origen.distancia_km(destino)


def test_los_robots_del_campus_usan_los_senderos():
    sitio, flota = cargar_campus()
    o, d = sitio["cafeteria"], sitio["biblioteca"]
    assert len(flota.buscar("R-01").trazar_ruta(o, d).puntos) > 2  # pasa por los senderos
    assert len(flota.buscar("D-01").trazar_ruta(o, d).puntos) == 2  # vuela recto
