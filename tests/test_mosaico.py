"""Mosaico de tiles para las vistas realistas, sin internet (requests se reemplaza)."""
import io

import pytest
import requests
from PIL import Image

from flota.presentacion import mosaico
from flota.presentacion.centro_control import a_metros

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


def test_una_cache_corrupta_se_vuelve_a_bajar(tmp_path, monkeypatch):
    (tmp_path / "calles-z19.jpg").write_bytes(bytes([0xFF, 0xD8]) + b"esto no es un JPEG completo")
    monkeypatch.setattr(requests.Session, "get", lambda self, url, timeout: RespuestaFalsa())
    imagen, _ = mosaico.mosaico("calles", tmp_path, CAMPUS)
    assert imagen.size[0] > 0
    assert Image.open(tmp_path / "calles-z19.jpg").size == imagen.size  # quedó una caché sana
    assert not list(tmp_path.glob("*.tmp"))


def test_dos_pedidos_a_la_vez_bajan_los_tiles_una_sola_vez(tmp_path, monkeypatch):
    import threading
    import time
    pedidos = []

    def lento(self, url, timeout):
        pedidos.append(url)
        time.sleep(0.005)
        return RespuestaFalsa()
    monkeypatch.setattr(requests.Session, "get", lento)
    hilos = [threading.Thread(target=mosaico.mosaico, args=("satelite", tmp_path, CAMPUS)) for _ in range(2)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    xs, ys = mosaico.rango_tiles(CAMPUS, 19)
    assert len(pedidos) == len(xs) * len(ys)  # el segundo esperó y leyó la caché

