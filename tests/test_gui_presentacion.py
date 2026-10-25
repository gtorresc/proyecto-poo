"""Piezas de la interfaz que tienen lógica propia: radar, clima, retratos y cámara (sin ventanas)."""
import pytest
import requests

from flota.gui import retratos
from flota.gui.panel_clima import rumbo, texto_clima
from flota.gui.panel_mapa import ZOOM_MAX, Camara, caras_visibles
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


# --- Cámara del mapa vectorial ------------------------------------------------------

CUADRADO = [[-100, -100], [100, -100], [100, 100], [-100, 100]]  # campus de 200 m


@pytest.fixture
def camara():
    cam = Camara(limites=[-300, -300, 300, 300], campus=CUADRADO)
    cam.ancho, cam.alto = 400, 400
    return cam


def test_el_centro_del_campus_queda_en_el_centro_de_la_pantalla(camara):
    assert camara.proyectar(0, 0) == (200, 200)


def test_en_2d_el_norte_esta_arriba_y_la_altura_no_cuenta(camara):
    camara.alternar()
    assert camara.modo == "2D"
    assert camara.proyectar(0, 100)[1] < 200 and camara.proyectar(100, 0)[0] > 200
    assert camara.proyectar(0, 0, 50) == camara.proyectar(0, 0)


def test_en_3d_la_altura_sube_en_pantalla(camara):
    assert camara.proyectar(0, 0, 20)[1] < camara.proyectar(0, 0)[1]


def test_girar_rota_90_grados(camara):
    camara.alternar()  # en 2D es más fácil de ver
    camara.girar()
    x, y = camara.proyectar(100, 0)  # el este pasa a estar arriba
    assert x == pytest.approx(200) and y < 200
    for _ in range(3):
        camara.girar()
    assert camara.giro == 0


def test_zoom_y_arrastre_no_salen_del_campus(camara):
    for _ in range(20):
        camara.acercar(2)
    assert camara.zoom == ZOOM_MAX
    for _ in range(20):
        camara.acercar(0.5)
    assert camara.zoom == 1
    camara.mover(-100_000, 100_000)  # arrastrar muy lejos hacia el noreste
    assert camara.centro == [300, 300]


def test_solo_se_dibujan_las_paredes_que_miran_a_la_camara(camara):
    paredes = caras_visibles(CUADRADO, [camara.rotar(x, y) for x, y in CUADRADO])
    assert paredes == [([-100, -100], [100, -100])]  # la del sur; las otras tres no se ven
    al_reves = list(reversed(CUADRADO))  # el sentido del contorno no cambia el resultado
    assert len(caras_visibles(al_reves, [camara.rotar(x, y) for x, y in al_reves])) == 1
