"""Piezas de la interfaz que tienen lógica propia: radar, clima, retratos y cámara (sin ventanas)."""
import pytest
import requests

from flota.gui import retratos
from flota.gui.capa_clima import MARGEN_NUBES_M, gotas, posicion_nube, sprite_nube
from flota.gui.panel_clima import rumbo, texto_clima
from flota.gui.panel_mapa import ZOOM_MAX, Camara, caras_visibles, edificio_bajo
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


# --- Clima dibujado sobre el mapa ----------------------------------------------------


def test_las_nubes_avanzan_con_el_viento_y_vuelven_a_entrar():
    limites, nube = [-300, -300, 300, 300], {"x": 0, "y": 0}
    assert posicion_nube(nube, [0, 5], 0, limites) == (0, 0)
    x, y = posicion_nube(nube, [0, 5], 1, limites)
    assert x == 0 and y > 0  # viento hacia el norte
    for t in range(0, 500, 7):
        x, y = posicion_nube(nube, [3, -4], t, limites)
        assert -300 - MARGEN_NUBES_M <= x <= 300 + MARGEN_NUBES_M and -300 - MARGEN_NUBES_M <= y <= 300 + MARGEN_NUBES_M


def test_las_gotas_quedan_dentro_de_la_pantalla_y_caen():
    antes = gotas(50, 400, 300, 20, 0)
    despues = gotas(50, 400, 300, 20, 0.01)
    assert len(antes) == 50 and all(0 <= x < 400 and 0 <= y < 300 for x, y in antes + despues)
    assert sum(d[1] > a[1] for a, d in zip(antes, despues)) > 40  # casi todas bajaron (las demás volvieron arriba)


def test_la_nube_es_transparente_en_los_bordes():
    img = sprite_nube(semilla=1, ancho_px=200, alto_px=120, opacidad=0.6)
    assert img.size == (200, 120)
    assert img.getpixel((0, 0))[3] == 0 and img.getpixel((100, 60))[3] > 0


# --- Vistas realistas -----------------------------------------------------------------
@pytest.mark.parametrize("modo, giros", [("2D", 0), ("3D", 0), ("3D", 1), ("2D", 3)])
def test_la_foto_queda_alineada_con_el_suelo(camara, modo, giros):
    if modo == "2D":
        camara.alternar()
    for _ in range(giros):
        camara.girar()
    caja, tamano = [-300, -200, 300, 200], (1200, 800)  # 2 píxeles por metro
    a, b, c, d, e, f = camara.afin_suelo(caja, tamano)
    for x, y in [(0, 0), (120, -80), (-250, 150)]:
        sx, sy = camara.proyectar(x, y)
        u, v = a * sx + b * sy + c, d * sx + e * sy + f  # lo que hace Image.transform con cada píxel
        assert (u, v) == pytest.approx(((x + 300) * 2, (200 - y) * 2))


def test_el_edificio_bajo_el_cursor_es_el_mas_cercano(camara):
    cerca = {"contorno": [[-20, -60], [20, -60], [20, -40], [-20, -40]], "altura": 10, "nombre": "Cerca"}
    lejos = {"contorno": [[-20, 40], [20, 40], [20, 60], [-20, 60]], "altura": 80, "nombre": "Lejos"}
    camara.alternar()  # en 2D cada uno se ve en su lugar
    assert edificio_bajo(camara, [lejos, cerca], *camara.proyectar(0, -50)) == 1
    assert edificio_bajo(camara, [lejos, cerca], *camara.proyectar(0, 50)) == 0
    assert edificio_bajo(camara, [lejos, cerca], *camara.proyectar(200, 0)) is None


def test_las_vistas_realistas_limitan_el_zoom_y_el_paneo(camara):
    caja = [-200, -200, 200, 200]
    camara.restringir(caja)
    assert camara.zoom >= camara.zoom_min > 1
    camara.acercar(0.1)
    assert camara.zoom == camara.zoom_min
    camara.mover(-100_000, 100_000)
    assert camara.centro == [120, 120]  # 60 % central de la caja
    camara.restringir(None)  # de vuelta a DESPACHO
    assert camara.zoom_min == 1
    camara.mover(-100_000, 100_000)
    assert camara.centro == [300, 300]
