"""Imágenes reales del campus para las vistas CALLES y SATÉLITE: tiles unidos en un solo mosaico.

Se bajan la primera vez y se guardan en una caché del usuario, fuera del repositorio (la licencia de
Esri no permite redistribuirlas). Sin red devuelve None y la interfaz se queda en la vista DESPACHO.
"""
import math
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from typing import Optional

import requests
from PIL import Image

from flota.campus import cargar_geometria
from flota.presentacion.centro_control import a_metros

CACHE = Path.home() / ".cache" / "flota-udem"
TIMEOUT_S = 10
USER_AGENT = "FlotaRobotsUdeM/1.0 (proyecto academico de POO)"
MAX_TILES = 200  # tope de seguridad: el campus necesita ~110 tiles por capa
_candado = threading.Lock()  # una descarga a la vez: un segundo pedido espera y lee la caché
CAPAS = {
    # CARTO pide API key desde 2026; los tiles de OSM se pueden usar con un User-Agent propio y caché
    "calles": {"url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png", "zoom": 19,
               "lado": 256, "credito": "© OpenStreetMap contributors"},
    "satelite": {"url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                 "zoom": 19, "lado": 256, "credito": "Imágenes © Esri, Maxar, Earthstar Geographics"},
}


def a_tile(lat: float, lon: float, zoom: int) -> tuple[float, float]:
    """Coordenadas de tile (Web Mercator) con decimales: la parte entera es el tile."""
    n = 2 ** zoom
    return (lon + 180) / 360 * n, (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n


def de_tile(x: float, y: float, zoom: int) -> tuple[float, float]:
    n = 2 ** zoom
    return math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * y / n)))), x / n * 360 - 180


def rango_tiles(limites: dict, zoom: int) -> tuple[range, range]:
    """Tiles que cubren el área {sur, oeste, norte, este}; en Web Mercator el norte tiene y menor."""
    x0, y0 = a_tile(limites["norte"], limites["oeste"], zoom)
    x1, y1 = a_tile(limites["sur"], limites["este"], zoom)
    return range(int(x0), int(x1) + 1), range(int(y0), int(y1) + 1)


def caja_metros(xs: range, ys: range, zoom: int) -> list[float]:
    """[x_oeste, y_sur, x_este, y_norte] en metros del campus que cubre el mosaico."""
    norte, oeste = de_tile(xs.start, ys.start, zoom)
    sur, este = de_tile(xs.stop, ys.stop, zoom)
    return [*a_metros(sur, oeste), *a_metros(norte, este)]


def mosaico(capa: str, carpeta: Path = CACHE, limites: Optional[dict] = None):
    """(imagen, caja en metros) de la capa, o None si no se pudo bajar algún tile."""
    with _candado:
        return _mosaico(capa, carpeta, limites)


def _mosaico(capa: str, carpeta: Path, limites: Optional[dict]):
    datos = CAPAS[capa]
    zoom, lado = datos["zoom"], datos["lado"]
    xs, ys = rango_tiles(limites or cargar_geometria()["limites"], zoom)
    caja = caja_metros(xs, ys, zoom)
    archivo = carpeta / f"{capa}-z{zoom}.jpg"
    if archivo.exists():
        try:
            return Image.open(archivo).convert("RGB"), caja
        except OSError:  # caché corrupta (p. ej. la app se cerró mientras guardaba): se vuelve a bajar
            archivo.unlink(missing_ok=True)
    if len(xs) * len(ys) > MAX_TILES:
        raise ValueError("Demasiados tiles para el área pedida")
    sesion = requests.Session()
    sesion.headers["User-Agent"] = USER_AGENT

    def bajar(xy):
        respuesta = sesion.get(datos["url"].format(z=zoom, x=xy[0], y=xy[1]), timeout=TIMEOUT_S)
        respuesta.raise_for_status()
        return xy, Image.open(BytesIO(respuesta.content)).convert("RGB")

    imagen = Image.new("RGB", (len(xs) * lado, len(ys) * lado))
    try:
        with ThreadPoolExecutor(8) as hilos:
            for (x, y), tile in hilos.map(bajar, [(x, y) for y in ys for x in xs]):
                imagen.paste(tile.resize((lado, lado)), ((x - xs.start) * lado, (y - ys.start) * lado))
    except (requests.RequestException, OSError):  # sin red, error HTTP o imagen rota
        return None
    carpeta.mkdir(parents=True, exist_ok=True)
    temporal = archivo.with_suffix(".tmp")
    imagen.save(temporal, format="JPEG", quality=88)
    os.replace(temporal, archivo)  # atómico: nunca queda un JPEG a medio escribir con el nombre bueno
    return imagen, caja
