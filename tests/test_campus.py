"""Datos del campus y demo por consola (sin internet: usa el clima simulado)."""
import subprocess
import sys
from pathlib import Path

from flota.campus import cargar_campus
from flota.dominio.estado_robot import EstadoRobot
from flota.dominio.ubicacion import Zona

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
