"""Mosaico de tiles para las vistas realistas, sin internet (requests se reemplaza)."""
import io

import pytest
import requests
from PIL import Image

from flota.gui import mosaico
from flota.gui.centro_control import a_metros

CAMPUS = {"sur": 6.2279, "oeste": -75.6161, "norte": 6.2341, "este": -75.6089}


class RespuestaFalsa:
    def __init__(self, color=(10, 120, 30), lado=256, roto=False):
        self._roto = roto
        buffer = io.BytesIO()
        Image.new("RGB", (lado, lado), color).save(buffer, format="PNG")
        self.content = buffer.getvalue()

    def raise_for_status(self):
        if self._roto:
            raise requests.HTTPError("404")


def test_de_grados_a_tile_y_de_vuelta():
    x, y = mosaico.a_tile(6.2316, -75.6111, 19)
    assert mosaico.de_tile(x, y, 19) == pytest.approx((6.2316, -75.6111))


def test_el_rango_de_tiles_cubre_el_campus():
    xs, ys = mosaico.rango_tiles(CAMPUS, 19)
    assert len(xs) * len(ys) < mosaico.MAX_TILES
    caja = mosaico.caja_metros(xs, ys, 19)
    oeste_sur, este_norte = a_metros(CAMPUS["sur"], CAMPUS["oeste"]), a_metros(CAMPUS["norte"], CAMPUS["este"])
    assert caja[0] <= oeste_sur[0] and caja[1] <= oeste_sur[1]
    assert caja[2] >= este_norte[0] and caja[3] >= este_norte[1]


def test_de_metros_a_pixel():
    caja = [-100, -50, 100, 50]
    assert mosaico.a_pixel(-100, 50, caja, (400, 200)) == (0, 0)  # esquina noroeste
    assert mosaico.a_pixel(0, 0, caja, (400, 200)) == (200, 100)


def test_une_los_tiles_y_los_guarda_en_la_cache(tmp_path, monkeypatch):
    pedidos = []

    def falso_get(self, url, timeout):
        pedidos.append(url)
        return RespuestaFalsa()
    monkeypatch.setattr(requests.Session, "get", falso_get)
    imagen, caja = mosaico.mosaico("satelite", tmp_path, CAMPUS)
    xs, ys = mosaico.rango_tiles(CAMPUS, 19)
    assert imagen.size == (len(xs) * 256, len(ys) * 256) and len(pedidos) == len(xs) * len(ys)
    assert (tmp_path / "satelite-z19.jpg").exists()
    monkeypatch.setattr(requests.Session, "get", lambda *a, **k: pytest.fail("no debía usar la red"))
    assert mosaico.mosaico("satelite", tmp_path, CAMPUS)[1] == caja  # la segunda vez sale de la caché


@pytest.mark.parametrize("falla", [requests.ConnectionError("sin red"), RespuestaFalsa(roto=True)])
def test_sin_red_o_con_un_tile_roto_devuelve_none(tmp_path, monkeypatch, falla):
    def falso_get(self, url, timeout):
        if isinstance(falla, Exception):
            raise falla
        return falla
    monkeypatch.setattr(requests.Session, "get", falso_get)
    assert mosaico.mosaico("calles", tmp_path, CAMPUS) is None
    assert not any(tmp_path.iterdir())  # no se guarda un mosaico incompleto


def test_color_del_techo_es_el_promedio_dentro_del_contorno():
    imagen = Image.new("RGB", (200, 100), (0, 0, 0))
    imagen.paste((200, 100, 50), (0, 0, 100, 100))  # mitad oeste naranja, mitad este negra
    caja = [0, 0, 200, 100]
    assert mosaico.color_techo(imagen, caja, [[10, 10], [90, 10], [90, 90], [10, 90]]) == "#c86432"
    assert mosaico.color_techo(imagen, caja, [[110, 10], [190, 10], [190, 90]]) == "#000000"


def test_la_mascara_es_opaca_en_el_centro_y_transparente_en_los_bordes():
    m = mosaico.mascara_bordes((200, 100))
    assert m.size == (200, 100)
    assert m.getpixel((100, 50)) == 255
    assert m.getpixel((0, 0)) == 0 and m.getpixel((199, 50)) == 0 and m.getpixel((100, 99)) == 0
    assert 0 < m.getpixel((10, 50)) < 255  # la transición es gradual
