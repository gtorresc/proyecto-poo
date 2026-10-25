"""Piezas de la interfaz que tienen lógica propia (sin abrir ventanas)."""
import pytest
import requests

from flota.gui import retratos
from flota.gui.panel_clima import rumbo, texto_clima
from flota.gui.plantilla import EJES, puntos_radar


def test_radar_pone_cada_eje_en_su_vertice():
    lleno = {eje: 1 for eje, _ in EJES}
    puntos = puntos_radar(lleno, 100, 100, 50)
    assert len(puntos) == 5
    assert puntos[0] == pytest.approx((100, 50))  # el primer eje apunta hacia arriba
    medio = puntos_radar({eje: 0.5 for eje, _ in EJES}, 100, 100, 50)
    assert medio[0] == pytest.approx((100, 75))
    vacio = puntos_radar({eje: 0 for eje, _ in EJES}, 100, 100, 50)
    assert vacio[0] != (100, 100)  # un eje en cero no colapsa el pentágono


@pytest.mark.parametrize("grados, esperado", [(0, "N"), (44, "NE"), (180, "S"), (235, "SO"), (350, "N")])
def test_rumbo_del_viento(grados, esperado):
    assert rumbo(grados) == esperado


def test_texto_del_clima_omite_lo_que_no_llega():
    base = {"consultando": False, "disponible": True, "temperatura": None, "humedad": 92,
            "viento": 8.4, "direccion": 235, "lluvia": 100}
    assert texto_clima(base) == "humedad 92%  |  viento 8 km/h SO 235°  |  lluvia 100%"
    assert texto_clima({**base, "consultando": True}) == "consultando clima..."
    assert texto_clima({**base, "disponible": False}) == "clima no disponible"


def test_retrato_guardado_se_usa_sin_red(tmp_path, monkeypatch):
    retratos.icono("Dron").save(tmp_path / "X-01.png")
    monkeypatch.setattr(retratos.requests, "get", lambda *a, **k: pytest.fail("no debía bajarlo"))
    assert retratos.retrato("X-01", "Dron", tmp_path).size == (200, 200)


def test_sin_red_se_dibuja_un_icono_y_no_se_guarda(tmp_path, monkeypatch):
    def sin_red(*args, **kwargs):
        raise requests.ConnectionError("sin internet")
    monkeypatch.setattr(retratos.requests, "get", sin_red)
    assert retratos.retrato("X-02", "Orugas", tmp_path).size == (200, 200)
    assert not (tmp_path / "X-02.png").exists()  # se reintenta la próxima vez
